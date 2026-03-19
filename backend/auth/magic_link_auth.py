"""
MATCHO — Authentification Magic Link + Multi-tenant Fiduciaire
© 2026 PEP's Swiss SA — Tous droits réservés

Architecture:
- Magic Link par email (pas de mot de passe)
- Multi-tenant : Fiduciaire → Mandats → Clients
- JWT tokens avec rôles embarqués
- Sessions sécurisées avec refresh tokens
"""

import os
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from dataclasses import dataclass, field
from enum import Enum

import jwt
from jwt import InvalidTokenError as JWTError

# ══════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════

SECRET_KEY = os.getenv("MATCHO_SECRET_KEY", secrets.token_hex(32))
ALGORITHM = "HS256"
MAGIC_LINK_EXPIRY_MINUTES = 15
ACCESS_TOKEN_EXPIRY_MINUTES = 60
REFRESH_TOKEN_EXPIRY_DAYS = 30


# ══════════════════════════════════════════════════════════
# RÔLES & PERMISSIONS
# ══════════════════════════════════════════════════════════

class Role(str, Enum):
    ADMIN = "admin"              # PEP's Swiss SA — accès total plateforme
    FIDUCIAIRE = "fiduciaire"    # Fiduciaire — supervise tous ses mandats
    COLLABORATEUR = "collaborateur"  # Collaborateur fiduciaire — accès limité
    CLIENT = "client"            # PME cliente — ses propres données uniquement
    REVISEUR = "reviseur"        # Réviseur externe — lecture seule


class Permission(str, Enum):
    # Réconciliation
    RECONCILE_CREATE = "reconcile:create"
    RECONCILE_VIEW = "reconcile:view"
    RECONCILE_VALIDATE = "reconcile:validate"
    RECONCILE_DELETE = "reconcile:delete"
    
    # Export
    EXPORT_CREATE = "export:create"
    EXPORT_VIEW = "export:view"
    
    # Mandats
    MANDAT_CREATE = "mandat:create"
    MANDAT_VIEW = "mandat:view"
    MANDAT_EDIT = "mandat:edit"
    MANDAT_DELETE = "mandat:delete"
    
    # Utilisateurs
    USER_INVITE = "user:invite"
    USER_MANAGE = "user:manage"
    USER_VIEW = "user:view"
    
    # Plan comptable
    PLAN_VIEW = "plan:view"
    PLAN_EDIT = "plan:edit"
    
    # Audit
    AUDIT_VIEW = "audit:view"
    
    # Admin plateforme
    PLATFORM_ADMIN = "platform:admin"


# Matrice des permissions par rôle
ROLE_PERMISSIONS: Dict[Role, List[Permission]] = {
    Role.ADMIN: list(Permission),  # Toutes les permissions
    
    Role.FIDUCIAIRE: [
        Permission.RECONCILE_CREATE,
        Permission.RECONCILE_VIEW,
        Permission.RECONCILE_VALIDATE,
        Permission.RECONCILE_DELETE,
        Permission.EXPORT_CREATE,
        Permission.EXPORT_VIEW,
        Permission.MANDAT_CREATE,
        Permission.MANDAT_VIEW,
        Permission.MANDAT_EDIT,
        Permission.MANDAT_DELETE,
        Permission.USER_INVITE,
        Permission.USER_MANAGE,
        Permission.USER_VIEW,
        Permission.PLAN_VIEW,
        Permission.PLAN_EDIT,
        Permission.AUDIT_VIEW,
    ],
    
    Role.COLLABORATEUR: [
        Permission.RECONCILE_CREATE,
        Permission.RECONCILE_VIEW,
        Permission.EXPORT_CREATE,
        Permission.EXPORT_VIEW,
        Permission.MANDAT_VIEW,
        Permission.USER_VIEW,
        Permission.PLAN_VIEW,
    ],
    
    Role.CLIENT: [
        Permission.RECONCILE_CREATE,
        Permission.RECONCILE_VIEW,
        Permission.EXPORT_CREATE,
        Permission.EXPORT_VIEW,
        Permission.PLAN_VIEW,
    ],
    
    Role.REVISEUR: [
        Permission.RECONCILE_VIEW,
        Permission.EXPORT_VIEW,
        Permission.MANDAT_VIEW,
        Permission.PLAN_VIEW,
        Permission.AUDIT_VIEW,
    ],
}


# ══════════════════════════════════════════════════════════
# MODÈLES DE DONNÉES
# ══════════════════════════════════════════════════════════

@dataclass
class User:
    """Utilisateur MATCHO"""
    id: str
    email: str
    name: str
    role: Role
    
    # Liens organisationnels
    fiduciaire_id: Optional[str] = None   # ID de la fiduciaire (si collaborateur/client)
    mandats: List[str] = field(default_factory=list)  # IDs des mandats accessibles
    
    # Métadonnées
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    is_active: bool = True
    
    # Préférences
    language: str = "fr"
    timezone: str = "Europe/Zurich"
    
    def has_permission(self, permission: Permission) -> bool:
        """Vérifie si l'utilisateur a une permission donnée"""
        return permission in ROLE_PERMISSIONS.get(self.role, [])
    
    def can_access_mandat(self, mandat_id: str) -> bool:
        """Vérifie l'accès à un mandat spécifique"""
        if self.role == Role.ADMIN:
            return True
        if self.role == Role.FIDUCIAIRE:
            return True  # Accède à tous ses mandats
        return mandat_id in self.mandats
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "role": self.role.value,
            "fiduciaire_id": self.fiduciaire_id,
            "mandats": self.mandats,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "is_active": self.is_active,
        }


@dataclass
class Fiduciaire:
    """Cabinet fiduciaire — gère plusieurs mandats PME"""
    id: str
    name: str                    # Ex: "Fiduciaire Cuenin & Partners"
    email: str                   # Email principal
    ide: Optional[str] = None    # CHE-xxx.xxx.xxx
    address: Optional[str] = None
    
    # Mandats gérés
    mandats: List[str] = field(default_factory=list)
    
    # Abonnement
    plan: str = "pro"  # "starter", "pro", "enterprise"
    max_mandats: int = 50
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True


@dataclass
class Mandat:
    """Mandat client — une PME gérée par une fiduciaire"""
    id: str
    name: str                    # Ex: "Alpes Digital Sàrl"
    fiduciaire_id: str           # Lien vers la fiduciaire
    
    # Infos entreprise
    ide: Optional[str] = None    # CHE-xxx.xxx.xxx
    address: Optional[str] = None
    contact_email: Optional[str] = None
    contact_name: Optional[str] = None
    
    # Comptabilité
    exercice_debut: Optional[str] = None  # "01.01.2024"
    exercice_fin: Optional[str] = None    # "31.12.2024"
    plan_comptable: str = "pme"           # "pme", "custom"
    logiciel: str = "cresus"              # "cresus", "bexio", "banana", "sage"
    devise: str = "CHF"
    
    # Banques
    ibans: List[str] = field(default_factory=list)
    
    # Stats
    total_reconciliations: int = 0
    last_reconciliation: Optional[datetime] = None
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True


@dataclass
class MagicLinkToken:
    """Token Magic Link pour authentification sans mot de passe"""
    token_hash: str         # SHA-256 du token (on ne stocke jamais le token en clair)
    email: str
    created_at: datetime
    expires_at: datetime
    used: bool = False
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


# ══════════════════════════════════════════════════════════
# SERVICE D'AUTHENTIFICATION
# ══════════════════════════════════════════════════════════

class AuthService:
    """
    Service d'authentification Magic Link
    
    Flow:
    1. L'utilisateur entre son email
    2. On génère un token unique + l'envoie par email
    3. L'utilisateur clique sur le lien
    4. On vérifie le token → génère un JWT access + refresh token
    5. Les requêtes suivantes utilisent le JWT
    """
    
    # En production : remplacer par PostgreSQL
    _magic_links: Dict[str, MagicLinkToken] = {}
    _users: Dict[str, User] = {}
    _refresh_tokens: Dict[str, dict] = {}
    
    def __init__(self, email_service=None):
        self.email_service = email_service
    
    # ── MAGIC LINK ──
    
    def create_magic_link(self, email: str, ip: str = None, ua: str = None) -> str:
        """
        Génère un Magic Link pour un email donné.
        
        Returns:
            Le token brut (à envoyer dans l'email)
        """
        # Générer un token cryptographiquement sécurisé
        token = secrets.token_urlsafe(48)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Invalider les anciens tokens pour cet email
        self._invalidate_existing_links(email)
        
        # Stocker le hash (jamais le token en clair)
        magic_link = MagicLinkToken(
            token_hash=token_hash,
            email=email,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=MAGIC_LINK_EXPIRY_MINUTES),
            ip_address=ip,
            user_agent=ua,
        )
        self._magic_links[token_hash] = magic_link
        
        return token
    
    def verify_magic_link(self, token: str) -> Optional[User]:
        """
        Vérifie un Magic Link token et retourne l'utilisateur.
        
        Returns:
            User si valide, None sinon
        """
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        magic_link = self._magic_links.get(token_hash)
        
        if not magic_link:
            return None
        
        # Vérifications
        if magic_link.used:
            return None  # Déjà utilisé (one-time use)
        
        if datetime.utcnow() > magic_link.expires_at:
            return None  # Expiré
        
        # Marquer comme utilisé
        magic_link.used = True
        
        # Trouver ou créer l'utilisateur
        user = self._find_user_by_email(magic_link.email)
        if user:
            user.last_login = datetime.utcnow()
        
        return user
    
    def _invalidate_existing_links(self, email: str):
        """Invalide tous les Magic Links existants pour un email"""
        for link in self._magic_links.values():
            if link.email == email and not link.used:
                link.used = True
    
    # ── JWT TOKENS ──
    
    def create_access_token(self, user: User) -> str:
        """Génère un JWT access token"""
        payload = {
            "sub": user.id,
            "email": user.email,
            "role": user.role.value,
            "fiduciaire_id": user.fiduciaire_id,
            "mandats": user.mandats,
            "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRY_MINUTES),
            "iat": datetime.utcnow(),
            "type": "access",
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    
    def create_refresh_token(self, user: User) -> str:
        """Génère un refresh token de longue durée"""
        token = secrets.token_urlsafe(48)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        self._refresh_tokens[token_hash] = {
            "user_id": user.id,
            "expires_at": datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS),
            "created_at": datetime.utcnow(),
        }
        
        return token
    
    def verify_access_token(self, token: str) -> Optional[dict]:
        """Vérifie et décode un JWT access token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("type") != "access":
                return None
            return payload
        except JWTError:
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """Utilise un refresh token pour obtenir un nouveau access token"""
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        stored = self._refresh_tokens.get(token_hash)
        
        if not stored:
            return None
        
        if datetime.utcnow() > stored["expires_at"]:
            del self._refresh_tokens[token_hash]
            return None
        
        user = self._users.get(stored["user_id"])
        if not user or not user.is_active:
            return None
        
        return self.create_access_token(user)
    
    # ── GESTION UTILISATEURS ──
    
    def create_user(
        self,
        email: str,
        name: str,
        role: Role,
        fiduciaire_id: Optional[str] = None,
        mandats: List[str] = None,
    ) -> User:
        """Crée un nouvel utilisateur"""
        user_id = secrets.token_hex(16)
        
        user = User(
            id=user_id,
            email=email.lower().strip(),
            name=name,
            role=role,
            fiduciaire_id=fiduciaire_id,
            mandats=mandats or [],
        )
        
        self._users[user_id] = user
        return user
    
    def invite_user(
        self,
        inviter: User,
        email: str,
        name: str,
        role: Role,
        mandats: List[str] = None,
    ) -> Optional[tuple]:
        """
        Invite un utilisateur (envoi Magic Link d'inscription).
        Seuls fiduciaire et admin peuvent inviter.
        
        Returns:
            (User, magic_link_token) ou None si pas autorisé
        """
        if not inviter.has_permission(Permission.USER_INVITE):
            return None
        
        # Vérifier les contraintes de rôle
        if inviter.role == Role.FIDUCIAIRE:
            # Un fiduciaire peut inviter collaborateurs et clients
            if role not in [Role.COLLABORATEUR, Role.CLIENT, Role.REVISEUR]:
                return None
        
        # Créer l'utilisateur
        user = self.create_user(
            email=email,
            name=name,
            role=role,
            fiduciaire_id=inviter.fiduciaire_id or inviter.id,
            mandats=mandats or [],
        )
        
        # Générer le Magic Link d'invitation
        token = self.create_magic_link(email)
        
        return (user, token)
    
    def _find_user_by_email(self, email: str) -> Optional[User]:
        """Trouve un utilisateur par email"""
        email_lower = email.lower().strip()
        for user in self._users.values():
            if user.email == email_lower:
                return user
        return None
    
    # ── GESTION MANDATS ──
    
    def get_user_mandats(self, user: User) -> List[Mandat]:
        """
        Retourne les mandats accessibles par un utilisateur.
        
        - Admin : tous
        - Fiduciaire : tous ses mandats
        - Collaborateur : mandats assignés
        - Client : son propre mandat
        """
        # En production : requête PostgreSQL
        # Ici : placeholder
        return []
    
    def assign_mandat_to_user(self, admin: User, user_id: str, mandat_id: str) -> bool:
        """Assigne un mandat à un collaborateur/client"""
        if not admin.has_permission(Permission.USER_MANAGE):
            return False
        
        user = self._users.get(user_id)
        if not user:
            return False
        
        if mandat_id not in user.mandats:
            user.mandats.append(mandat_id)
        
        return True


# ══════════════════════════════════════════════════════════
# API ROUTES — FastAPI
# ══════════════════════════════════════════════════════════

def create_auth_routes(auth_service: AuthService):
    """
    Crée les routes d'authentification FastAPI.
    
    À intégrer dans main.py :
        from auth.magic_link_auth import AuthService, create_auth_routes
        auth = AuthService(email_service)
        auth_router = create_auth_routes(auth)
        app.include_router(auth_router, prefix="/api/auth")
    """
    from fastapi import APIRouter, HTTPException, Request, Depends
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from pydantic import BaseModel, EmailStr
    
    router = APIRouter(tags=["Authentification"])
    security = HTTPBearer(auto_error=False)
    
    # ── Modèles Pydantic ──
    
    class MagicLinkRequest(BaseModel):
        email: str  # EmailStr en prod
    
    class MagicLinkVerify(BaseModel):
        token: str
    
    class InviteRequest(BaseModel):
        email: str
        name: str
        role: str  # "collaborateur", "client", "reviseur"
        mandats: List[str] = []
    
    class TokenResponse(BaseModel):
        access_token: str
        refresh_token: str
        token_type: str = "bearer"
        expires_in: int = ACCESS_TOKEN_EXPIRY_MINUTES * 60
        user: dict
    
    # ── Dependency: Current User ──
    
    async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
    ) -> User:
        """Extrait l'utilisateur courant du JWT"""
        if not credentials:
            raise HTTPException(status_code=401, detail="Token manquant")
        
        payload = auth_service.verify_access_token(credentials.credentials)
        if not payload:
            raise HTTPException(status_code=401, detail="Token invalide ou expiré")
        
        user = auth_service._users.get(payload["sub"])
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="Utilisateur inactif")
        
        return user
    
    # ── Routes ──
    
    @router.post("/magic-link", summary="Demander un Magic Link")
    async def request_magic_link(body: MagicLinkRequest, request: Request):
        """
        Envoie un Magic Link par email.
        L'utilisateur clique dessus pour se connecter — pas de mot de passe.
        """
        # Vérifier que l'email existe
        user = auth_service._find_user_by_email(body.email)
        if not user:
            # Pour des raisons de sécurité, on ne révèle pas si l'email existe
            # On retourne toujours un succès
            return {
                "message": "Si un compte existe avec cet email, un lien de connexion a été envoyé.",
                "expires_in_minutes": MAGIC_LINK_EXPIRY_MINUTES,
            }
        
        # Générer le Magic Link
        token = auth_service.create_magic_link(
            email=body.email,
            ip=request.client.host if request.client else None,
            ua=request.headers.get("user-agent"),
        )
        
        # Construire le lien
        base_url = os.getenv("MATCHO_FRONTEND_URL", "https://app.matcho.digital")
        magic_url = f"{base_url}/auth/verify?token={token}"
        
        # Envoyer l'email
        if auth_service.email_service:
            try:
                auth_service.email_service.send_magic_link(
                    to_email=body.email,
                    to_name=user.name,
                    magic_link_url=magic_url,
                    expires_minutes=MAGIC_LINK_EXPIRY_MINUTES,
                )
            except Exception as e:
                print(f"⚠️ Erreur envoi email: {e}")
                raise HTTPException(status_code=500, detail="Erreur envoi email")
        
        return {
            "message": "Si un compte existe avec cet email, un lien de connexion a été envoyé.",
            "expires_in_minutes": MAGIC_LINK_EXPIRY_MINUTES,
            # En dev uniquement :
            "_dev_magic_url": magic_url if os.getenv("MATCHO_ENV") == "development" else None,
        }
    
    @router.post("/verify", response_model=TokenResponse, summary="Vérifier un Magic Link")
    async def verify_magic_link(body: MagicLinkVerify):
        """
        Vérifie un token Magic Link et retourne les tokens JWT.
        Le Magic Link est à usage unique et expire après 15 minutes.
        """
        user = auth_service.verify_magic_link(body.token)
        
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Lien invalide, expiré ou déjà utilisé. Demandez un nouveau lien."
            )
        
        # Générer les tokens
        access_token = auth_service.create_access_token(user)
        refresh_token = auth_service.create_refresh_token(user)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=user.to_dict(),
        )
    
    @router.post("/refresh", summary="Rafraîchir le token d'accès")
    async def refresh_token(body: dict):
        """Utilise un refresh token pour obtenir un nouveau access token"""
        new_token = auth_service.refresh_access_token(body.get("refresh_token", ""))
        
        if not new_token:
            raise HTTPException(status_code=401, detail="Refresh token invalide ou expiré")
        
        return {
            "access_token": new_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRY_MINUTES * 60,
        }
    
    @router.get("/me", summary="Profil utilisateur courant")
    async def get_me(user: User = Depends(get_current_user)):
        """Retourne le profil de l'utilisateur connecté avec ses permissions"""
        return {
            "user": user.to_dict(),
            "permissions": [p.value for p in ROLE_PERMISSIONS.get(user.role, [])],
        }
    
    @router.post("/invite", summary="Inviter un utilisateur")
    async def invite_user(body: InviteRequest, user: User = Depends(get_current_user)):
        """
        Invite un collaborateur, client ou réviseur.
        Envoie un Magic Link d'inscription par email.
        
        Seuls les fiduciaires et admins peuvent inviter.
        """
        try:
            role = Role(body.role)
        except ValueError:
            raise HTTPException(status_code=400, detail="Rôle invalide")
        
        result = auth_service.invite_user(
            inviter=user,
            email=body.email,
            name=body.name,
            role=role,
            mandats=body.mandats,
        )
        
        if not result:
            raise HTTPException(
                status_code=403,
                detail="Vous n'avez pas la permission d'inviter avec ce rôle"
            )
        
        new_user, token = result
        
        # Envoyer l'email d'invitation
        base_url = os.getenv("MATCHO_FRONTEND_URL", "https://app.matcho.digital")
        invite_url = f"{base_url}/auth/verify?token={token}&invite=true"
        
        if auth_service.email_service:
            try:
                auth_service.email_service.send_invitation(
                    to_email=body.email,
                    to_name=body.name,
                    inviter_name=user.name,
                    role=role.value,
                    invite_url=invite_url,
                )
            except Exception:
                pass  # Log mais ne bloque pas
        
        return {
            "message": f"Invitation envoyée à {body.email}",
            "user": new_user.to_dict(),
            "_dev_invite_url": invite_url if os.getenv("MATCHO_ENV") == "development" else None,
        }
    
    @router.get("/mandats", summary="Lister les mandats accessibles")
    async def list_mandats(user: User = Depends(get_current_user)):
        """Liste les mandats auxquels l'utilisateur a accès"""
        if not user.has_permission(Permission.MANDAT_VIEW):
            raise HTTPException(status_code=403, detail="Accès refusé")
        
        mandats = auth_service.get_user_mandats(user)
        
        return {
            "mandats": [m.__dict__ for m in mandats] if mandats else [],
            "count": len(mandats) if mandats else 0,
            "role": user.role.value,
        }
    
    @router.post("/logout", summary="Déconnexion")
    async def logout():
        """
        Déconnexion côté serveur.
        Le client doit aussi supprimer les tokens locaux.
        """
        return {"message": "Déconnecté avec succès"}
    
    return router, get_current_user
