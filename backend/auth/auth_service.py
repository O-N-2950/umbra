"""
MATCHO — Auth Service (Magic Link)
Authentification sans mot de passe pour fiduciaires.

Flow:
1. User entre son email
2. MATCHO envoie un magic link (JWT signé, 15min expiry)
3. User clique → JWT vérifié → session créée
4. Access token (1h) + Refresh token (30j)

© 2026 PEP's Swiss SA
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict
from dataclasses import dataclass

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import User, Fiduciary, UserRole


# ── Config ─────────────────────────────────────────────

JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_hex(32))
JWT_ALGORITHM = "HS256"
MAGIC_LINK_EXPIRE = 15  # minutes
ACCESS_TOKEN_EXPIRE = 60  # minutes
REFRESH_TOKEN_EXPIRE = 30  # days
APP_URL = os.getenv("APP_URL", "http://localhost:3000")


# ── Token Types ────────────────────────────────────────

@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = ACCESS_TOKEN_EXPIRE * 60

    def to_dict(self):
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type,
            "expires_in": self.expires_in,
        }


@dataclass
class AuthUser:
    user_id: str
    fiduciary_id: str
    email: str
    name: str
    role: str

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "fiduciary_id": self.fiduciary_id,
            "email": self.email,
            "name": self.name,
            "role": self.role,
        }


# ── Token Functions ────────────────────────────────────

def create_magic_token(email: str) -> str:
    """Crée un token magic link (15 min)"""
    payload = {
        "sub": email,
        "type": "magic_link",
        "exp": datetime.utcnow() + timedelta(minutes=MAGIC_LINK_EXPIRE),
        "iat": datetime.utcnow(),
        "jti": secrets.token_hex(16),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_access_token(user_id: str, fiduciary_id: str, email: str, role: str) -> str:
    """Crée un access token (1h)"""
    payload = {
        "sub": user_id,
        "fid": fiduciary_id,
        "email": email,
        "role": role,
        "type": "access",
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    """Crée un refresh token (30j)"""
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE),
        "iat": datetime.utcnow(),
        "jti": secrets.token_hex(16),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str, expected_type: str = "access") -> Optional[Dict]:
    """Vérifie et décode un token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != expected_type:
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# ── Auth Service ───────────────────────────────────────

class AuthService:
    """
    Service d'authentification Magic Link.

    Usage:
        auth = AuthService(session)

        # 1. Envoyer magic link
        token = await auth.request_magic_link("olivier@winwin.swiss")
        # → envoyer par email: {APP_URL}/auth/verify?token={token}

        # 2. Vérifier magic link et créer session
        tokens = await auth.verify_magic_link(token)
        # → {access_token, refresh_token}

        # 3. Vérifier access token (middleware)
        user = await auth.get_current_user(access_token)

        # 4. Refresh
        new_tokens = await auth.refresh_session(refresh_token)
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def request_magic_link(self, email: str) -> Optional[str]:
        """
        Génère un magic link pour un email.
        Retourne le token si l'utilisateur existe, None sinon.
        """
        # Check user exists
        q = select(User).where(User.email == email, User.is_active == True)
        result = await self.session.execute(q)
        user = result.scalar_one_or_none()

        if not user:
            return None

        token = create_magic_token(email)
        magic_link = f"{APP_URL}/auth/verify?token={token}"
        return magic_link

    async def verify_magic_link(self, token: str) -> Optional[TokenPair]:
        """Vérifie un magic link et retourne une paire de tokens"""
        payload = verify_token(token, expected_type="magic_link")
        if not payload:
            return None

        email = payload.get("sub")
        if not email:
            return None

        # Get user
        q = select(User).where(User.email == email, User.is_active == True)
        result = await self.session.execute(q)
        user = result.scalar_one_or_none()

        if not user:
            return None

        # Update last login
        user.last_login = datetime.utcnow()
        await self.session.commit()

        # Create tokens
        access = create_access_token(user.id, user.fiduciary_id, user.email, user.role.value)
        refresh = create_refresh_token(user.id)

        return TokenPair(access_token=access, refresh_token=refresh)

    async def get_current_user(self, token: str) -> Optional[AuthUser]:
        """Vérifie un access token et retourne l'utilisateur"""
        payload = verify_token(token, expected_type="access")
        if not payload:
            return None

        return AuthUser(
            user_id=payload["sub"],
            fiduciary_id=payload["fid"],
            email=payload["email"],
            name="",  # Could fetch from DB
            role=payload["role"],
        )

    async def refresh_session(self, refresh_token: str) -> Optional[TokenPair]:
        """Renouvelle une session avec un refresh token"""
        payload = verify_token(refresh_token, expected_type="refresh")
        if not payload:
            return None

        user_id = payload.get("sub")
        q = select(User).where(User.id == user_id, User.is_active == True)
        result = await self.session.execute(q)
        user = result.scalar_one_or_none()

        if not user:
            return None

        access = create_access_token(user.id, user.fiduciary_id, user.email, user.role.value)
        refresh = create_refresh_token(user.id)

        return TokenPair(access_token=access, refresh_token=refresh)

    async def register_fiduciary(
        self,
        fiduciary_name: str,
        owner_name: str,
        owner_email: str,
        ide: str = "",
    ) -> Dict:
        """
        Inscription d'une nouvelle fiduciaire + premier utilisateur (owner).
        """
        # Check not already registered
        if ide:
            q = select(Fiduciary).where(Fiduciary.ide == ide)
            existing = await self.session.execute(q)
            if existing.scalar_one_or_none():
                return {"error": "Cette fiduciaire est déjà inscrite"}

        # Create fiduciary
        fiduciary = Fiduciary(name=fiduciary_name, ide=ide, email=owner_email)
        self.session.add(fiduciary)
        await self.session.flush()

        # Create owner user
        user = User(
            fiduciary_id=fiduciary.id,
            email=owner_email,
            name=owner_name,
            role=UserRole.OWNER,
        )
        self.session.add(user)
        await self.session.commit()

        # Generate magic link for first login
        token = create_magic_token(owner_email)
        magic_link = f"{APP_URL}/auth/verify?token={token}"

        return {
            "fiduciary_id": fiduciary.id,
            "user_id": user.id,
            "magic_link": magic_link,
            "message": f"Fiduciaire '{fiduciary_name}' créée. Vérifiez votre email.",
        }


# ── FastAPI Dependencies ───────────────────────────────

def create_auth_routes():
    """Routes FastAPI pour l'authentification"""
    from fastapi import APIRouter, Depends, HTTPException, Header
    from pydantic import BaseModel

    router = APIRouter(tags=["Auth"])

    class MagicLinkRequest(BaseModel):
        email: str

    class VerifyRequest(BaseModel):
        token: str

    class RefreshRequest(BaseModel):
        refresh_token: str

    class RegisterRequest(BaseModel):
        fiduciary_name: str
        owner_name: str
        owner_email: str
        ide: str = ""

    @router.post("/register")
    async def register(req: RegisterRequest, session=None):
        """Inscription d'une nouvelle fiduciaire"""
        auth = AuthService(session)
        result = await auth.register_fiduciary(
            req.fiduciary_name, req.owner_name, req.owner_email, req.ide
        )
        if "error" in result:
            raise HTTPException(409, detail=result["error"])
        return result

    @router.post("/magic-link")
    async def request_magic_link(req: MagicLinkRequest, session=None):
        """Demande un magic link par email"""
        auth = AuthService(session)
        link = await auth.request_magic_link(req.email)
        # Always return success (security: don't reveal if email exists)
        return {"message": "Si un compte existe, un email a été envoyé."}

    @router.post("/verify")
    async def verify(req: VerifyRequest, session=None):
        """Vérifie un magic link et retourne les tokens"""
        auth = AuthService(session)
        tokens = await auth.verify_magic_link(req.token)
        if not tokens:
            raise HTTPException(401, detail="Lien invalide ou expiré")
        return tokens.to_dict()

    @router.post("/refresh")
    async def refresh(req: RefreshRequest, session=None):
        """Renouvelle les tokens"""
        auth = AuthService(session)
        tokens = await auth.refresh_session(req.refresh_token)
        if not tokens:
            raise HTTPException(401, detail="Token expiré")
        return tokens.to_dict()

    @router.get("/me")
    async def me(authorization: str = Header(None), session=None):
        """Retourne l'utilisateur courant"""
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401, detail="Token requis")
        token = authorization.split(" ")[1]
        auth = AuthService(session)
        user = await auth.get_current_user(token)
        if not user:
            raise HTTPException(401, detail="Token invalide")
        return user.to_dict()

    return router
