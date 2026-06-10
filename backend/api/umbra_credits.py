"""
UMBRA — Credits Router
Gestion des crédits d'annonces (achats Stripe + solde + historique).

© 2026 PEP's Swiss SA — UMBRA
"""

import os
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel

from db.session import get_db
from api.umbra_auth import get_current_account

logger = logging.getLogger("umbra.credits")

router = APIRouter(prefix="/credits", tags=["credits"])

# FLAG_FACTURATION — activer après 10 embauches documentées
# Voir CONTEXT.md § Décisions Stratégiques (server/routers.ts ligne ~252 pour le frontend)
FLAG_FACTURATION = os.getenv("FLAG_FACTURATION", "false").lower() == "true"
CREDIT_PRICE_CHF = 5.0


# ── Helper auth ───────────────────────────────────────────────────────────────

def _get_current_account():
    """Import différé pour éviter les cycles."""
    from api.umbra_auth import get_current_account
    return get_current_account


# ── Schemas ───────────────────────────────────────────────────────────────────

class BalanceResponse(BaseModel):
    account_id: str
    balance: int
    total_bought: int
    total_spent: int
    total_refunded: int

class CheckoutRequest(BaseModel):
    quantity: int


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/pricing")
def get_pricing():
    """Modèle de facturation actuel."""
    if not FLAG_FACTURATION:
        return {
            "model": "free_launch",
            "cv_analysis_price_chf": 0,
            "message": "Analyses CV gratuites — phase de lancement.",
            "note": "Bundlées dans l'annonce après 10 embauches documentées.",
        }
    return {
        "model": "bundled",
        "cv_analysis_price_chf": 0,
        "message": "Analyses CV illimitées incluses dans votre annonce active.",
        "credit_price_chf": CREDIT_PRICE_CHF,
    }


@router.get("/balance")
def get_balance(
    db: Session = Depends(get_db),
    account=Depends(get_current_account),
):
    """Solde de crédits — route préparée."""
    return {"balance": 5, "model": "free_launch", "flag_facturation": FLAG_FACTURATION}


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Webhook Stripe — reçoit les événements paiement."""
    import stripe
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET_UMBRA", "")

    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig, webhook_secret)
    except Exception as e:
        logger.error("Webhook error: %s", e)
        raise HTTPException(status_code=400, detail="Signature invalide")

    logger.info("Stripe event: %s", event["type"])
    return {"received": True}
