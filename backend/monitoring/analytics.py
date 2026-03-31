"""
UMBRA — Analytics & Observabilité
PostHog (product analytics) + Sentry (erreurs) côté backend.

Events PostHog prioritaires :
  landing_vue, inscription_démarrée, profil_candidat_créé,
  offre_publiée, matching_déclenché, contact_initié,
  checkout_lancé, abonnement_activé

© 2026 PEP's Swiss SA — UMBRA
"""

import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("umbra.analytics")

# ── Sentry ────────────────────────────────────────────────────────────────────

_sentry_initialized = False

def init_sentry() -> bool:
    """Initialise Sentry SDK. No-op si SENTRY_DSN absent."""
    global _sentry_initialized
    if _sentry_initialized:
        return True
    dsn = os.getenv("SENTRY_DSN", "")
    if not dsn:
        logger.info("[Analytics] Sentry désactivé (SENTRY_DSN manquant)")
        return False
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        sentry_sdk.init(
            dsn=dsn,
            environment=os.getenv("ENVIRONMENT", "production"),
            release=f"umbra@{os.getenv('APP_VERSION', '1.0.0')}",
            traces_sample_rate=0.1,       # 10% des transactions
            profiles_sample_rate=0.05,    # 5% de profiling
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
            ],
            # Ne pas envoyer les données personnelles en clair
            send_default_pii=False,
            before_send=_scrub_pii,
        )
        _sentry_initialized = True
        logger.info("[Analytics] ✅ Sentry initialisé")
        return True
    except ImportError:
        logger.warning("[Analytics] sentry-sdk non installé — pip install sentry-sdk")
        return False
    except Exception as e:
        logger.error("[Analytics] Sentry init failed: %s", e)
        return False


def _scrub_pii(event, hint):
    """Supprimer PII avant envoi à Sentry (conformité LPD/RGPD)."""
    # Masquer emails dans les exceptions
    if "exception" in event:
        for exc in event.get("exception", {}).get("values", []):
            if exc.get("value") and "@" in str(exc["value"]):
                exc["value"] = "[email masqué]"
    # Supprimer headers sensibles
    for req in (event.get("request") or {}).get("headers", {}).copy():
        if req.lower() in ("authorization", "cookie", "x-api-key"):
            event["request"]["headers"][req] = "[masqué]"
    return event


def capture_exception(exc: Exception, context: Dict = None):
    """Envoyer une exception à Sentry si initialisé."""
    try:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            if context:
                for k, v in context.items():
                    scope.set_extra(k, v)
            sentry_sdk.capture_exception(exc)
    except Exception:
        pass  # Ne jamais crasher à cause de Sentry


# ── PostHog ───────────────────────────────────────────────────────────────────

_posthog = None

def get_posthog():
    """Retourne le client PostHog, initialisé lazily."""
    global _posthog
    if _posthog is not None:
        return _posthog
    api_key = os.getenv("POSTHOG_API_KEY", "")
    if not api_key:
        return None
    try:
        from posthog import Posthog
        _posthog = Posthog(
            project_api_key=api_key,
            host=os.getenv("POSTHOG_HOST", "https://eu.i.posthog.com"),  # EU pour conformité
            disabled=os.getenv("ENVIRONMENT", "production") == "dev",
        )
        logger.info("[Analytics] ✅ PostHog initialisé")
        return _posthog
    except ImportError:
        logger.warning("[Analytics] posthog non installé — pip install posthog")
        return None
    except Exception as e:
        logger.error("[Analytics] PostHog init failed: %s", e)
        return None


# ── Events UMBRA ──────────────────────────────────────────────────────────────

class UmbraEvent:
    """Constantes d'événements PostHog. Candidats vs Employeurs."""
    LANDING_VUE            = "landing_vue"
    INSCRIPTION_DEMARREE   = "inscription_démarrée"
    PROFIL_CANDIDAT_CREE   = "profil_candidat_créé"
    OFFRE_PUBLIEE          = "offre_publiée"
    MATCHING_DECLENCHE     = "matching_déclenché"
    CONTACT_INITIE         = "contact_initié"
    CHECKOUT_LANCE         = "checkout_lancé"
    ABONNEMENT_ACTIVE      = "abonnement_activé"
    # Supplémentaires
    CV_ANALYSE             = "cv_analysé"
    REVELATION_MUTUELLE    = "révélation_mutuelle"
    PROFIL_VU              = "profil_vu"
    ENTRETIEN_INVERSE_POSE = "entretien_inversé_posé"


def track(
    event: str,
    distinct_id: str,
    properties: Optional[Dict[str, Any]] = None,
    user_type: Optional[str] = None,  # "candidat" | "employeur"
) -> None:
    """
    Envoyer un événement PostHog.
    distinct_id : account_id (jamais l'email en clair)
    user_type   : "candidat" | "employeur"
    """
    ph = get_posthog()
    if not ph:
        return
    try:
        props = {
            "platform": "umbra",
            "env": os.getenv("ENVIRONMENT", "production"),
            **({"user_type": user_type} if user_type else {}),
            **(properties or {}),
        }
        ph.capture(distinct_id=distinct_id, event=event, properties=props)
        logger.debug("[Analytics] Event: %s | %s | %s", event, distinct_id[:8], user_type)
    except Exception as e:
        logger.error("[Analytics] track failed: %s", e)


def identify(
    distinct_id: str,
    user_type: str,
    plan: str = "free",
    region: Optional[str] = None,
) -> None:
    """
    Identifier un utilisateur dans PostHog.
    Jamais d'email ou de nom en clair — seulement des métadonnées anonymes.
    """
    ph = get_posthog()
    if not ph:
        return
    try:
        ph.identify(
            distinct_id=distinct_id,
            properties={
                "user_type": user_type,
                "plan": plan,
                **({"region": region} if region else {}),
            }
        )
    except Exception as e:
        logger.error("[Analytics] identify failed: %s", e)
