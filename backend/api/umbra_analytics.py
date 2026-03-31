"""
UMBRA — Route analytics côté serveur
POST /api/v1/analytics/track — events frontend → PostHog backend
Évite d'exposer la clé PostHog dans le JS client.
© 2026 PEP's Swiss SA — UMBRA
"""

import os
import logging
from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any

from monitoring.analytics import track, UmbraEvent

logger = logging.getLogger("umbra.analytics_route")
router = APIRouter(prefix="/analytics", tags=["analytics"])

ALLOWED_EVENTS = {
    UmbraEvent.LANDING_VUE,
    UmbraEvent.INSCRIPTION_DEMARREE,
    UmbraEvent.PROFIL_CANDIDAT_CREE,
    UmbraEvent.OFFRE_PUBLIEE,
    UmbraEvent.MATCHING_DECLENCHE,
    UmbraEvent.CONTACT_INITIE,
    UmbraEvent.CHECKOUT_LANCE,
    UmbraEvent.ABONNEMENT_ACTIVE,
    UmbraEvent.CV_ANALYSE,
    UmbraEvent.REVELATION_MUTUELLE,
    UmbraEvent.PROFIL_VU,
    UmbraEvent.ENTRETIEN_INVERSE_POSE,
}


class TrackRequest(BaseModel):
    event: str
    distinct_id: str           # account_id hashé côté client
    user_type: Optional[str] = None  # "candidat" | "employeur"
    properties: Optional[Dict[str, Any]] = {}


@router.post("/track")
async def track_event(body: TrackRequest, request: Request):
    """
    Proxy PostHog côté serveur.
    La clé API ne quitte jamais le backend.
    """
    if body.event not in ALLOWED_EVENTS:
        return {"ok": False, "reason": "event non autorisé"}

    # Enrichir avec IP anonymisée (premiers 2 octets) pour geo sans PII
    ip = request.client.host if request.client else "0.0.0.0"
    ip_anon = ".".join(ip.split(".")[:2] + ["0", "0"])

    track(
        event=body.event,
        distinct_id=body.distinct_id,
        user_type=body.user_type,
        properties={
            **(body.properties or {}),
            "ip_anon": ip_anon,
            "source": "server_proxy",
        }
    )
    return {"ok": True}


@router.get("/events")
def list_events():
    """Liste les événements trackés par UMBRA (doc interne)."""
    return {
        "events": sorted(ALLOWED_EVENTS),
        "user_types": ["candidat", "employeur"],
        "posthog_active": bool(os.getenv("POSTHOG_API_KEY")),
        "sentry_active": bool(os.getenv("SENTRY_DSN")),
    }
