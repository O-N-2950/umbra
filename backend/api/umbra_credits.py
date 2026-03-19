"""
UMBRA — Credits Router
Gestion des crédits d'annonces (achats Stripe + solde + historique).

© 2026 PEP's Swiss SA — UMBRA
"""

import os
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel

from db.session import get_db
from auth.jwt_utils import get_current_account

logger = logging.getLogger("umbra.credits")

router = APIRouter(prefix="/credits", tags=["credits"])


# ── SCHEMAS ──────────────────────────────────────────────────────────────────

class BalanceResponse(BaseModel):
    account_id: str
    balance: int
    total_bought: int
    total_spent: int
    total_refunded: int


class CheckoutRequest(BaseModel):
    quantity: int  # nombre de crédits à acheter


class CheckoutResponse(BaseModel):
    checkout_url: str
    price_chf: float
    credits: int


# ── PRIX ─────────────────────────────────────────────────────────────────────

CREDIT_PRICE_CHF = 5.0  # 5 CHF / crédit d'annonce (prix public)

# FLAG_FACTURATION — activer après 10 embauches documentées
# Voir CONTEXT.md § Décisions Stratégiques
FLAG_FACTURATION = os.getenv("FLAG_FACTURATION", "false").lower() == "true"


# ── ROUTES ───────────────────────────────────────────────────────────────────

@router.get("/balance", response_model=BalanceResponse)
def get_balance(
    account=Depends(get_current_account),
    db: Session = Depends(get_db),
):
    """Solde de crédits du compte courant."""
    try:
        from db.umbra_models import CreditBalance
        balance = db.query(CreditBalance).filter(
            CreditBalance.account_id == account.id
        ).first()

        if not balance:
            # Créer le solde initial (5 crédits offerts)
            balance = CreditBalance(
                account_id=account.id,
                balance=5,
                total_bought=0,
                total_spent=0,
                total_refunded=0,
            )
            db.add(balance)
            db.commit()
            db.refresh(balance)

        return BalanceResponse(
            account_id=balance.account_id,
            balance=balance.balance,
            total_bought=balance.total_bought,
            total_spent=balance.total_spent,
            total_refunded=balance.total_refunded,
        )
    except Exception as e:
        logger.error("get_balance error: %s", e)
        raise HTTPException(status_code=500, detail="Erreur solde crédits")


@router.get("/pricing")
def get_pricing():
    """
    Retourne le modèle de facturation actuel.
    Phase lancement : analyses CV gratuites.
    Phase post-10-embauches : bundlées dans l'annonce.
    """
    if not FLAG_FACTURATION:
        return {
            "model": "free_launch",
            "cv_analysis_price_chf": 0,
            "message": "Analyses CV gratuites pendant la phase de lancement.",
            "note": "Les analyses seront incluses dans l'annonce après 10 embauches documentées.",
        }
    else:
        return {
            "model": "bundled",
            "cv_analysis_price_chf": 0,
            "message": "Analyses CV illimitées incluses dans votre annonce active.",
            "credit_price_chf": CREDIT_PRICE_CHF,
        }


@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout(
    body: CheckoutRequest,
    account=Depends(get_current_account),
    db: Session = Depends(get_db),
):
    """
    Crée une session Stripe Checkout pour acheter des crédits.
    Désactivé en phase de lancement (FLAG_FACTURATION=false).
    """
    if not FLAG_FACTURATION:
        raise HTTPException(
            status_code=403,
            detail="Achats de crédits non disponibles — phase de lancement gratuit."
        )

    if body.quantity < 1 or body.quantity > 100:
        raise HTTPException(status_code=400, detail="Quantité invalide (1–100)")

    try:
        import stripe
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

        price_cents = int(body.quantity * CREDIT_PRICE_CHF * 100)
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "chf",
                    "unit_amount": int(CREDIT_PRICE_CHF * 100),
                    "product_data": {
                        "name": f"UMBRA — Crédit annonce",
                        "description": "1 crédit = 1 annonce UMBRA (validité 90 jours)",
                    },
                },
                "quantity": body.quantity,
            }],
            mode="payment",
            metadata={
                "app": "umbra",
                "account_id": str(account.id),
                "credits": str(body.quantity),
            },
            success_url=f"{os.getenv('APP_URL', 'http://localhost:3000')}/credits?success=1",
            cancel_url=f"{os.getenv('APP_URL', 'http://localhost:3000')}/credits",
        )

        return CheckoutResponse(
            checkout_url=session.url,
            price_chf=body.quantity * CREDIT_PRICE_CHF,
            credits=body.quantity,
        )
    except Exception as e:
        logger.error("Stripe checkout error: %s", e)
        raise HTTPException(status_code=500, detail="Erreur paiement Stripe")


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Webhook Stripe — crédite le compte après paiement réussi.
    Configure dans Stripe Dashboard → Webhooks → checkout.session.completed
    """
    import stripe
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET_UMBRA", "")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except Exception as e:
        logger.error("Webhook signature error: %s", e)
        raise HTTPException(status_code=400, detail="Signature invalide")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        meta = session.get("metadata", {})

        if meta.get("app") != "umbra":
            return {"received": True}

        account_id = meta.get("account_id")
        credits = int(meta.get("credits", 0))

        if account_id and credits > 0:
            try:
                from db.umbra_models import CreditBalance, CreditTransaction
                balance = db.query(CreditBalance).filter(
                    CreditBalance.account_id == account_id
                ).first()
                if balance:
                    balance.balance += credits
                    balance.total_bought += credits
                    db.add(CreditTransaction(
                        account_id=account_id,
                        amount=credits,
                        type="purchase",
                        stripe_pi_id=session.get("payment_intent"),
                        note=f"Achat {credits} crédit(s) Stripe",
                    ))
                    db.commit()
                    logger.info("✅ %d crédits crédités → %s", credits, account_id)
            except Exception as e:
                logger.error("Credit update error: %s", e)
                db.rollback()

    return {"received": True}
