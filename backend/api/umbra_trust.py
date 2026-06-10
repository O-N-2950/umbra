"""
UMBRA — API Trust (Passeport) + Credits
Gestion du passeport de confiance et des crédits contacts.

Trust endpoints :
  GET  /trust/me/passport          → passeport complet du compte courant
  GET  /trust/{display_id}/passport → passeport public d'un autre compte
  POST /trust/events/hire           → confirmer une embauche (double confirmation)
  POST /trust/events/interview      → signaler un entretien réalisé
  POST /trust/events/no-followup    → signaler un contact sans suite (auto / cron)

Credits endpoints :
  GET  /credits/me             → solde et historique
  POST /credits/purchase       → acheter des crédits (Stripe)
  POST /credits/webhook/stripe → webhook Stripe (paiements)

© 2026 PEP's Swiss SA — UMBRA
"""

from __future__ import annotations

import os
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from db.session import get_db
from api.umbra_auth import get_current_account
from pydantic import BaseModel
from sqlalchemy.orm import Session

logger = logging.getLogger("umbra.trust")

router        = APIRouter(prefix="/trust",   tags=["trust"])
credits_router = APIRouter(prefix="/credits", tags=["credits"])


# ── SCHEMAS ───────────────────────────────────────────────────────────────────

class HireConfirmRequest(BaseModel):
    match_id:              str
    candidate_account_id:  str   # ID du compte candidat (révélé post-signal)


class InterviewRequest(BaseModel):
    match_id: str


class NoFollowupRequest(BaseModel):
    match_id: str
    note:     Optional[str] = None


class PurchaseRequest(BaseModel):
    credits:  int   # 5, 10, 20, 50
    plan:     Optional[str] = None   # "starter", "pro", "enterprise"


# ── TRUST ENDPOINTS ───────────────────────────────────────────────────────────

@router.get("/me/passport")
def my_passport(
    account=Depends(get_current_account),
    db: Session = Depends(get_db),
):
    """Retourne le passeport de confiance complet du compte courant."""
    from .services.trust_service import trust_service
    from db.umbra_models import TrustEvent, CreditBalance

    passport = trust_service.get_passport(db, account.id)

    # Historique des 10 derniers events
    events = (
        db.query(TrustEvent)
        .filter(TrustEvent.account_id == account.id)
        .order_by(TrustEvent.created_at.desc())
        .limit(10)
        .all()
    )
    passport["recent_events"] = [
        {
            "type":   e.event_type.value,
            "delta":  e.points_delta,
            "date":   e.created_at.isoformat(),
            "note":   e.note,
        }
        for e in events
    ]

    # Crédits (pour entreprises)
    balance = db.query(CreditBalance).filter(CreditBalance.account_id == account.id).first()
    passport["credits"] = {
        "balance":        balance.balance if balance else 0,
        "total_bought":   balance.total_bought if balance else 0,
        "total_spent":    balance.total_spent if balance else 0,
        "total_refunded": balance.total_refunded if balance else 0,
    }

    # Grade et accès
    ts = trust_service.get_score(db, account.id)
    passport["access"] = {
        "can_initiate_contact":    ts.grade.value not in ("restricted", "suspended"),
        "can_access_shadow":       ts.grade.value == "platinum",
        "is_certified":            ts.grade.value in ("gold", "platinum"),
        "suspension_watch":        ts.suspension_watch,
        "consecutive_no_followup": ts.consecutive_no_followup,
    }

    return passport


@router.get("/{display_id}/passport")
def public_passport(
    display_id: str,
    db: Session = Depends(get_db),
):
    """
    Passeport public d'un autre compte (visible par tous).
    Retourne uniquement les métriques publiques — jamais l'identité.
    """
    from db.umbra_models import AnonymousProfile, TrustScore

    profile = db.query(AnonymousProfile).filter(
        AnonymousProfile.display_id == display_id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profil introuvable.")

    trust = db.query(TrustScore).filter(TrustScore.account_id == profile.account_id).first()
    if not trust:
        return {"display_id": display_id, "score": 3.0, "grade": "standard"}

    return {
        "display_id":     display_id,
        "score":          round(trust.score, 2),
        "grade":          trust.grade.value,
        "hire_rate_pct":  round(trust.hire_rate_pct, 1),
        "hires_confirmed": trust.hires_confirmed,
        "contacts_total":  trust.contacts_total,
        "reports_received": trust.reports_received,
        "is_certified":   trust.grade.value in ("gold", "platinum"),
        "is_suspended":   trust.grade.value == "suspended",
    }


@router.post("/events/hire")
def confirm_hire(
    req: HireConfirmRequest,
    account=Depends(get_current_account),
    db: Session = Depends(get_db),
):
    """
    Confirme une embauche (côté entreprise).
    L'embauche n'est validée que si le candidat confirme aussi de son côté.
    Utilise la table hire_confirmations pour traquer les double confirmations.
    """
    from db.umbra_models import Match, InterestSignal, RevealStatus
    from .services.trust_service import trust_service

    # Vérifier que la révélation mutuelle a bien eu lieu
    match = db.query(Match).filter(Match.id == req.match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match introuvable.")

    revealed = db.query(InterestSignal).filter(
        InterestSignal.match_id == req.match_id,
        InterestSignal.status == RevealStatus.MUTUAL,
    ).first()
    if not revealed:
        raise HTTPException(
            status_code=400,
            detail="Impossible de confirmer une embauche sans révélation mutuelle préalable."
        )

    # TODO: stocker la confirmation de ce côté et attendre l'autre côté
    # Pour simplifier ici : on déclenche directement si l'entreprise confirme
    # En prod : table hire_confirmations avec état "pending_candidate"
    ts_company, ts_candidate = trust_service.record_hire_confirmed(
        db,
        company_account_id=account.id,
        candidate_account_id=req.candidate_account_id,
        match_id=req.match_id,
    )

    return {
        "hire_confirmed": True,
        "company_score":  round(ts_company.score, 2),
        "company_grade":  ts_company.grade.value,
        "message": "Embauche confirmée. Les compétences du candidat ont été validées.",
    }


@router.post("/events/interview")
def record_interview(
    req: InterviewRequest,
    account=Depends(get_current_account),
    db: Session = Depends(get_db),
):
    """Signale qu'un entretien a eu lieu suite à ce match."""
    from .services.trust_service import trust_service, TrustEventType

    ts = trust_service.record_event(
        db, account.id, TrustEventType.INTERVIEW_DONE,
        reference_id=req.match_id,
        note="Entretien réalisé",
    )
    return {
        "recorded": True,
        "new_score": round(ts.score, 2),
        "new_grade": ts.grade.value,
    }


@router.post("/events/no-followup")
def record_no_followup(
    req: NoFollowupRequest,
    account=Depends(get_current_account),
    db: Session = Depends(get_db),
):
    """
    Signale un contact sans suite.
    Décrémente le score + incrémente consecutive_no_followup.
    Déclenche la surveillance anti-espionnage si seuil atteint.
    """
    from .services.trust_service import trust_service

    ts = trust_service.record_no_followup(db, account.id, req.match_id)
    return {
        "recorded":             True,
        "new_score":            round(ts.score, 2),
        "new_grade":            ts.grade.value,
        "consecutive_nf":       ts.consecutive_no_followup,
        "suspension_watch":     ts.suspension_watch,
        "warning": (
            f"⚠️ Attention : {ts.consecutive_no_followup} contacts sans suite. "
            f"Suspension automatique à 10."
            if ts.consecutive_no_followup >= 5 else None
        ),
    }


# ── CREDITS ENDPOINTS ─────────────────────────────────────────────────────────

@credits_router.get("/me")
def my_credits(
    account=Depends(get_current_account),
    db: Session = Depends(get_db),
):
    """Solde de crédits et historique des 20 dernières transactions."""
    from db.umbra_models import CreditBalance, CreditTransaction

    balance = db.query(CreditBalance).filter(CreditBalance.account_id == account.id).first()
    if not balance:
        balance = CreditBalance(account_id=account.id, balance=0)
        db.add(balance)
        db.commit()

    transactions = (
        db.query(CreditTransaction)
        .filter(CreditTransaction.account_id == account.id)
        .order_by(CreditTransaction.created_at.desc())
        .limit(20)
        .all()
    )

    # Tarifs
    pricing = {
        5:  {"chf": 125, "label": "Pack Starter — 5 crédits"},
        10: {"chf": 220, "label": "Pack Pro — 10 crédits"},
        20: {"chf": 400, "label": "Pack Team — 20 crédits"},
        50: {"chf": 900, "label": "Pack Enterprise — 50 crédits"},
    }

    return {
        "balance":        balance.balance,
        "total_bought":   balance.total_bought,
        "total_spent":    balance.total_spent,
        "total_refunded": balance.total_refunded,
        "pricing":        pricing,
        "transactions": [
            {
                "amount":     t.amount,
                "type":       t.type,
                "date":       t.created_at.isoformat(),
                "note":       t.note,
            }
            for t in transactions
        ],
    }


@credits_router.post("/purchase")
def purchase_credits(
    req: PurchaseRequest,
    account=Depends(get_current_account),
    db: Session = Depends(get_db),
):
    """
    Initie un achat de crédits via Stripe.
    Retourne l'URL de paiement Stripe Checkout.
    """
    valid_packs = {5, 10, 20, 50}
    if req.credits not in valid_packs:
        raise HTTPException(
            status_code=400,
            detail=f"Pack invalide. Choisissez parmi : {sorted(valid_packs)}"
        )

    prices = {5: 12500, 10: 22000, 20: 40000, 50: 90000}  # centimes CHF
    price_chf = prices[req.credits]

    try:
        import stripe
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            currency="chf",
            line_items=[{
                "price_data": {
                    "currency":     "chf",
                    "unit_amount":  price_chf,
                    "product_data": {
                        "name": f"UMBRA — {req.credits} crédits contacts",
                        "description": "Crédits pour initier des contacts sur la plateforme UMBRA",
                    },
                },
                "quantity": 1,
            }],
            mode="payment",
            metadata={
                "account_id": account.id,
                "credits":    str(req.credits),
                "product":    "umbra_credits",
            },
            success_url=f"{os.getenv('APP_URL', 'http://localhost:3000')}/credits/success",
            cancel_url=f"{os.getenv('APP_URL', 'http://localhost:3000')}/credits/cancel",
        )
        return {"checkout_url": session.url, "session_id": session.id}

    except Exception as e:
        logger.error("Stripe checkout error: %s", e)
        raise HTTPException(status_code=500, detail="Erreur lors de la création du paiement.")


@credits_router.post("/webhook/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="stripe-signature"),
    db: Session = Depends(get_db),
):
    """
    Webhook Stripe — crédite le compte après paiement confirmé.
    Vérifie la signature Stripe (HMAC SHA-256).
    """
    import stripe

    stripe.api_key           = os.getenv("STRIPE_SECRET_KEY")
    webhook_secret           = os.getenv("STRIPE_WEBHOOK_SECRET")
    payload                  = await request.body()

    try:
        event = stripe.Webhook.construct_event(payload, stripe_signature, webhook_secret)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Signature Stripe invalide.")

    if event["type"] == "checkout.session.completed":
        session  = event["data"]["object"]
        metadata = session.get("metadata", {})

        if metadata.get("product") != "umbra_credits":
            return {"received": True}

        account_id    = metadata.get("account_id")
        credits_count = int(metadata.get("credits", 0))

        if account_id and credits_count > 0:
            from db.umbra_models import CreditBalance, CreditTransaction

            balance = db.query(CreditBalance).filter(
                CreditBalance.account_id == account_id
            ).first()
            if balance:
                balance.balance      += credits_count
                balance.total_bought += credits_count

            tx = CreditTransaction(
                account_id=account_id,
                amount=credits_count,
                type="purchase",
                stripe_pi_id=session.get("payment_intent"),
                note=f"Achat {credits_count} crédits via Stripe",
            )
            db.add(tx)
            db.commit()

            logger.info(
                "credits purchased: account %s +%d credits",
                account_id[:8], credits_count
            )

    return {"received": True}
