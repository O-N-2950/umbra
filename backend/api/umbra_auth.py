"""
UMBRA — Auth Service
Magic link (pas de mot de passe) + JWT avec profil anonyme dissocié.

Flow :
  1. POST /auth/register   → crée le compte, envoie magic link
  2. POST /auth/login      → envoie magic link à l'email
  3. GET  /auth/verify     → valide le token, retourne JWT access + refresh
  4. POST /auth/refresh    → refresh le JWT
  5. GET  /auth/me         → profil courant (compte + anonymous_profile)

Dissociation anonymat :
  Le JWT contient le account_id.
  Les endpoints publics (matching) ne reçoivent JAMAIS le account_id
  — ils reçoivent uniquement le anonymous_profile.id.
  La FK account_id → anonymous_profiles est uniquement résolue côté serveur.

© 2026 PEP's Swiss SA — UMBRA
"""

from __future__ import annotations

import os
import secrets
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

logger = logging.getLogger("umbra.auth")

# ── CONFIG ────────────────────────────────────────────────────────────────────

JWT_SECRET      = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise ValueError("❌ FATAL: JWT_SECRET environment variable is required.")
JWT_ALGORITHM   = "HS256"
ACCESS_TTL_MIN  = int(os.getenv("JWT_ACCESS_TTL_MIN",  "60"))     # 1h
REFRESH_TTL_DAY = int(os.getenv("JWT_REFRESH_TTL_DAY", "30"))     # 30j
MAGIC_TTL_MIN   = int(os.getenv("MAGIC_LINK_TTL_MIN",  "15"))     # 15min

# Magic tokens persistés en PostgreSQL
# (remplace le dict en mémoire qui se perdait au redémarrage)
from db.session import get_db
from sqlalchemy import text

router = APIRouter(prefix="/auth", tags=["auth"])
bearer = HTTPBearer(auto_error=False)


# ── SCHEMAS ───────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email:        EmailStr
    account_type: str   # "candidate" | "company"
    ide_number:   Optional[str] = None  # CHE-xxx.xxx.xxx (entreprises)

    @field_validator("account_type")
    @classmethod
    def validate_type(cls, v):
        if v not in ("candidate", "company"):
            raise ValueError("account_type must be 'candidate' or 'company'")
        return v


class LoginRequest(BaseModel):
    email: EmailStr


class TokenResponse(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"
    account_type:  str
    profile_id:    Optional[str] = None   # anonymous_profile.id si déjà créé


class RefreshRequest(BaseModel):
    refresh_token: str


# ── HELPERS ───────────────────────────────────────────────────────────────────

def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _create_magic_token(account_id: str, db=None) -> str:
    """Génère un token magic link sécurisé, le stocke en DB."""
    token = secrets.token_urlsafe(32)
    h = _hash_token(token)
    expires = datetime.utcnow() + timedelta(minutes=MAGIC_TTL_MIN)
    if db:
        db.execute(text(
            "INSERT INTO magic_tokens (token_hash, account_id, expires_at, used) "
            "VALUES (:h, :aid, :exp, false) "
            "ON CONFLICT (token_hash) DO NOTHING"
        ), {"h": h, "aid": account_id, "exp": expires})
        db.commit()
    return token


def _consume_magic_token(token: str, db=None) -> Optional[str]:
    """Valide et consomme un magic token depuis DB. Retourne account_id ou None."""
    h = _hash_token(token)
    if not db:
        return None
    try:
        row = db.execute(text(
            "SELECT account_id, expires_at, used FROM magic_tokens WHERE token_hash = :h"
        ), {"h": h}).fetchone()
        if not row:
            return None
        if row.used:
            return None
        if datetime.utcnow() > row.expires_at:
            db.execute(text("DELETE FROM magic_tokens WHERE token_hash = :h"), {"h": h})
            db.commit()
            return None
        db.execute(text("UPDATE magic_tokens SET used = true WHERE token_hash = :h"), {"h": h})
        db.commit()
        return row.account_id
    except Exception as e:
        logger.error("magic token consume error: %s", e)
        return None


def _create_jwt(account_id: str, token_type: str = "access") -> str:
    ttl = timedelta(
        minutes=ACCESS_TTL_MIN if token_type == "access" else 0,
        days=0 if token_type == "access" else REFRESH_TTL_DAY,
    )
    payload = {
        "sub": account_id,
        "type": token_type,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + ttl,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _decode_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expiré.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token invalide.")


# ── DEPENDENCY INJECTION ──────────────────────────────────────────────────────

def get_db():
    """FastAPI dependency — à overrider avec la vraie session."""
    from .db.session import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_account(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    db: Session = Depends(get_db),
):
    """Dependency : retourne le compte authentifié depuis le JWT."""
    if not creds:
        raise HTTPException(status_code=401, detail="Authentification requise.")
    payload = _decode_jwt(creds.credentials)
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Access token requis.")

    from .db.umbra_models import Account
    account = db.query(Account).filter(Account.id == payload["sub"]).first()
    if not account or not account.is_active:
        raise HTTPException(status_code=401, detail="Compte introuvable ou désactivé.")
    if account.is_suspended:
        raise HTTPException(
            status_code=403,
            detail="Compte suspendu. Contactez le support UMBRA."
        )
    return account


def get_current_profile(
    account=Depends(get_current_account),
    db: Session = Depends(get_db),
):
    """Dependency : retourne le profil anonyme du compte courant."""
    from .db.umbra_models import AnonymousProfile
    profile = db.query(AnonymousProfile).filter(
        AnonymousProfile.account_id == account.id
    ).first()
    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Profil non créé. Complétez l'onboarding."
        )
    return profile


# ── ENDPOINTS ─────────────────────────────────────────────────────────────────

@router.post("/register", status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """
    Crée un compte et envoie le magic link d'activation.
    Idempotent : si l'email existe déjà → renvoie juste le magic link.
    """
    from .db.umbra_models import Account, AccountType, CreditBalance, TrustScore

    existing = db.query(Account).filter(Account.email == req.email).first()
    if existing:
        # Email déjà inscrit → magic link de connexion
        token = _create_magic_token(existing.id)
        _send_magic_link(existing.email, token, "login")
        return {"message": "Magic link envoyé à votre adresse email.", "action": "login"}

    # Nouveau compte
    account = Account(
        email=req.email,
        account_type=AccountType(req.account_type),
        ide_number=req.ide_number,
    )
    db.add(account)
    db.flush()

    # Initialiser le solde crédits
    credits = CreditBalance(account_id=account.id, balance=5)  # 5 crédits offerts
    db.add(credits)

    # Initialiser le trust score
    trust = TrustScore(account_id=account.id)
    db.add(trust)

    db.commit()

    token = _create_magic_token(account.id)
    _send_magic_link(account.email, token, "register")

    logger.info("account registered: %s (%s)", account.id[:8], req.account_type)
    return {
        "message": "Compte créé. Vérifiez votre email pour vous connecter.",
        "action": "register",
    }


@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Envoie un magic link à l'adresse email fournie."""
    from .db.umbra_models import Account

    account = db.query(Account).filter(Account.email == req.email).first()
    # Réponse identique qu'il existe ou non (anti-enumeration)
    if account and account.is_active:
        token = _create_magic_token(account.id)
        _send_magic_link(account.email, token, "login")
    logger.info("login magic link requested: %s", req.email[:3] + "***")
    return {"message": "Si votre email est enregistré, vous recevrez un lien de connexion."}


@router.get("/verify", response_model=TokenResponse)
def verify(
    token: str = Query(..., description="Magic link token"),
    db: Session = Depends(get_db),
):
    """
    Valide le magic token et retourne les JWTs.
    Peut être appelé depuis le lien email : /auth/verify?token=xxx
    """
    from .db.umbra_models import Account, AnonymousProfile

    account_id = _consume_magic_token(token)
    if not account_id:
        raise HTTPException(
            status_code=400,
            detail="Lien invalide ou expiré. Demandez un nouveau lien."
        )

    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Compte introuvable.")

    # Marquer email vérifié
    if not account.email_verified:
        account.email_verified = True
    account.last_login_at = datetime.utcnow()
    db.commit()

    # Récupérer le profil anonyme si existant
    profile = db.query(AnonymousProfile).filter(
        AnonymousProfile.account_id == account_id
    ).first()

    access  = _create_jwt(account_id, "access")
    refresh = _create_jwt(account_id, "refresh")

    logger.info("auth verified: %s", account_id[:8])
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        account_type=account.account_type.value,
        profile_id=profile.id if profile else None,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(req: RefreshRequest, db: Session = Depends(get_db)):
    """Renouvelle les tokens depuis un refresh token valide."""
    from .db.umbra_models import Account, AnonymousProfile

    payload = _decode_jwt(req.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=400, detail="Refresh token requis.")

    account = db.query(Account).filter(Account.id == payload["sub"]).first()
    if not account or not account.is_active or account.is_suspended:
        raise HTTPException(status_code=401, detail="Compte invalide.")

    profile = db.query(AnonymousProfile).filter(
        AnonymousProfile.account_id == account.id
    ).first()

    return TokenResponse(
        access_token=_create_jwt(account.id, "access"),
        refresh_token=_create_jwt(account.id, "refresh"),
        account_type=account.account_type.value,
        profile_id=profile.id if profile else None,
    )


@router.get("/me")
def me(account=Depends(get_current_account), db: Session = Depends(get_db)):
    """Retourne les infos du compte courant (sans données sensibles)."""
    from .db.umbra_models import AnonymousProfile, TrustScore

    profile = db.query(AnonymousProfile).filter(
        AnonymousProfile.account_id == account.id
    ).first()
    trust = db.query(TrustScore).filter(TrustScore.account_id == account.id).first()

    return {
        "account_id":    account.id,
        "account_type":  account.account_type.value,
        "email_verified": account.email_verified,
        "ide_verified":  account.ide_verified,
        "plan":          account.plan,
        "profile_id":    profile.id if profile else None,
        "profile_complete": profile is not None,
        "trust_score":   trust.score if trust else 3.0,
        "trust_grade":   trust.grade.value if trust else "standard",
    }


# ── EMAIL (stub — brancher Resend en prod) ────────────────────────────────────

def _send_magic_link(email: str, token: str, action: str) -> None:
    """
    Envoie le magic link par email.
    En dev : log le lien. En prod : Resend API.
    """
    base_url = os.getenv("APP_URL", "http://localhost:3000")
    link = f"{base_url}/auth/verify?token={token}"

    if os.getenv("ENV", "dev") == "dev":
        logger.info("🔗 MAGIC LINK [%s] → %s", action, link)
        return

    try:
        import resend
        resend.api_key = os.getenv("RESEND_API_KEY")
        subject = "Votre lien de connexion UMBRA" if action == "login" else "Bienvenue sur UMBRA"
        resend.Emails.send({
            "from":    "UMBRA <auth@umbra.work>",
            "to":      [email],
            "subject": subject,
            "html":    _magic_link_html(link, action),
        })
        logger.info("magic link email sent: %s", email[:3] + "***")
    except Exception as e:
        logger.error("failed to send magic link email: %s", e)


def _magic_link_html(link: str, action: str) -> str:
    label = "Me connecter" if action == "login" else "Activer mon compte"
    return f"""
    <div style="background:#05080e;color:#edeae4;font-family:sans-serif;padding:48px;max-width:480px;margin:0 auto;">
      <div style="font-family:Georgia,serif;font-size:28px;color:#d97b3a;letter-spacing:0.2em;margin-bottom:32px;">UMBRA</div>
      <p style="font-size:16px;line-height:1.7;color:#7a8da8;margin-bottom:32px;">
        Cliquez sur le bouton ci-dessous pour {"vous connecter" if action == "login" else "activer votre compte"}.<br>
        Ce lien est valable <strong style="color:#edeae4;">15 minutes</strong>.
      </p>
      <a href="{link}" style="display:inline-block;background:#d97b3a;color:#05080e;padding:14px 36px;text-decoration:none;font-weight:500;font-size:15px;">{label} →</a>
      <p style="margin-top:32px;font-size:12px;color:#4d5e75;">
        Si vous n'avez pas demandé ce lien, ignorez cet email.<br>
        Votre compte reste sécurisé.
      </p>
    </div>
    """
