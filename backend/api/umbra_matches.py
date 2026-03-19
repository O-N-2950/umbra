"""
UMBRA — API Matches + Signals + Questions
Le cœur du protocole de matching et de révélation mutuelle.

Endpoints Matches :
  GET  /matches/            → liste mes matchs (triés par score)
  GET  /matches/{id}        → détail d'un match
  POST /matches/{id}/ignore → ignorer un match
  GET  /matches/run         → déclencher le calcul (admin/cron)

Endpoints Signals (Intérêt + Révélation) :
  POST /matches/{id}/signal         → signaler mon intérêt
  GET  /matches/{id}/signal-status  → état du protocole de révélation
  DELETE /matches/{id}/signal       → retirer mon intérêt

Endpoints Questions (Entretien Inversé) :
  GET  /matches/{id}/questions            → voir les questions/réponses
  POST /matches/{id}/questions            → poser une question (candidat)
  PUT  /matches/{id}/questions/{qid}      → répondre (entreprise)

© 2026 PEP's Swiss SA — UMBRA
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

logger = logging.getLogger("umbra.matches")

router_matches   = APIRouter(prefix="/matches",   tags=["matches"])
router_signals   = APIRouter(prefix="/matches",   tags=["signals"])
router_questions = APIRouter(prefix="/matches",   tags=["questions"])


# ── SCHEMAS ───────────────────────────────────────────────────────────────────

class IgnoreRequest(BaseModel):
    reason: Optional[str] = None


class SignalRequest(BaseModel):
    message: Optional[str] = None   # message optionnel (jamais visible avant révélation)


class QuestionCreate(BaseModel):
    question: str


class QuestionAnswer(BaseModel):
    answer: str


# ── HELPERS ───────────────────────────────────────────────────────────────────

def _serialize_match(match, viewer_profile_id: str, trust_scores: dict = None) -> dict:
    """
    Sérialise un Match pour l'API.
    Ne révèle JAMAIS l'identity de l'autre côté avant révélation mutuelle.
    """
    is_a = (match.profile_a_id == viewer_profile_id)
    other_id = match.profile_b_id if is_a else match.profile_a_id

    # Vérifier si révélation mutuelle déjà faite
    revealed = any(
        s.status.value == "mutual" for s in (match.signals or [])
    )

    other_ts = (trust_scores or {}).get(other_id, {})

    base = {
        "id":           match.id,
        "display_id":   match.display_id,
        "score_total":  match.score_total,
        "score_skills": match.score_skills,
        "score_culture": match.score_culture,
        "score_geo":    match.score_geo,
        "score_salary": match.score_salary,
        "score_durability": match.score_durability,
        "distance_km":  match.distance_km,
        "salary_compatible": match.salary_compatible,
        "culture_similarity": match.culture_similarity,
        "market_intel": match.market_intel_label,
        "market_tension_pct": match.market_tension_pct,
        "computed_at":  match.computed_at.isoformat() if match.computed_at else None,
        "expires_at":   match.expires_at.isoformat() if match.expires_at else None,
        # État du signal courant
        "my_signal":    None,
        "revealed":     revealed,
        # Trust de l'autre côté (toujours public)
        "other_trust": other_ts,
    }

    # Compétences matchées (IDs → labels si relations chargées)
    base["matched_skill_ids"] = match.matched_skill_ids or []

    # Identité de l'autre côté : visible UNIQUEMENT si révélation mutuelle
    if revealed:
        other = match.profile_b if is_a else match.profile_a
        if other:
            base["other_profile"] = {
                "display_id":   other.display_id,
                "region_label": other.region_label,
                "sector_id":    other.sector_id,
                # Ne pas révéler geo_lat/lon même post-révélation
            }
    else:
        base["other_profile"] = {
            "display_id": "ANONYME",
            "region_label": _anonymize_region(
                (match.profile_b if is_a else match.profile_a)
            ),
        }

    # Signal courant de ce viewer
    my_signal = next(
        (s for s in (match.signals or []) if s.sender_id == viewer_profile_id),
        None
    )
    if my_signal:
        base["my_signal"] = {
            "status":   my_signal.status.value,
            "sent_at":  my_signal.sent_at.isoformat(),
            "expires_at": my_signal.expires_at.isoformat() if my_signal.expires_at else None,
        }

    return base


def _anonymize_region(profile) -> str:
    """Donne une indication de région sans révéler le lieu exact."""
    if not profile or not profile.region_label:
        return "Suisse"
    # Retourner seulement le canton/région, pas la ville
    parts = profile.region_label.split(" ")
    return parts[-1] if len(parts) > 1 else profile.region_label


def _check_mutual_signal(db: Session, match_id: str) -> bool:
    """
    Vérifie si les deux profils ont signalé leur intérêt pour ce match.
    Si oui → déclenche la révélation.
    Retourne True si révélation déclenchée.
    """
    from .db.umbra_models import InterestSignal, RevealStatus, Match

    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        return False

    signals = db.query(InterestSignal).filter(
        InterestSignal.match_id == match_id,
        InterestSignal.status == RevealStatus.PENDING,
    ).all()

    # Vérifier signal des deux côtés
    senders = {s.sender_id for s in signals}
    if match.profile_a_id in senders and match.profile_b_id in senders:
        # Déclencher la révélation mutuelle
        reveal_token = secrets.token_urlsafe(48)
        for s in signals:
            s.status = RevealStatus.MUTUAL
            s.revealed_at = datetime.utcnow()
            s.reveal_token = reveal_token
        db.commit()
        logger.info("reveal triggered: match %s", match_id[:8])
        return True
    return False


def _notify_interest(account_id: str, match_display_id: str) -> None:
    """Notifie l'autre partie qu'elle a reçu un signal d'intérêt (anonyme)."""
    # TODO: email + push notification
    logger.info("interest notification → account %s (match %s)", account_id[:8], match_display_id)


# ── ENDPOINTS MATCHES ─────────────────────────────────────────────────────────

@router_matches.get("/")
def list_matches(
    limit: int = 20,
    offset: int = 0,
    min_score: float = 0,
    account=Depends(lambda: None),
    db: Session = Depends(lambda: None),
):
    """Retourne les matchs du profil courant, triés par score décroissant."""
    from .db.umbra_models import AnonymousProfile, Match, TrustScore

    profile = db.query(AnonymousProfile).filter(
        AnonymousProfile.account_id == account.id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profil non trouvé.")

    q = db.query(Match).filter(
        Match.is_active == True,
        ((Match.profile_a_id == profile.id) | (Match.profile_b_id == profile.id)),
        Match.score_total >= min_score,
    )
    # Profil en shadow : uniquement matchs > threshold
    if profile.mode.value == "shadow":
        q = q.filter(Match.score_total >= profile.shadow_alert_threshold)

    total = q.count()
    matches = q.order_by(Match.score_total.desc()).offset(offset).limit(limit).all()

    # Précharger trust scores des "autres" profils
    other_ids = []
    for m in matches:
        other_ids.append(m.profile_b_id if m.profile_a_id == profile.id else m.profile_a_id)

    trust_map = {}
    if other_ids:
        # Résoudre profile → account → trust_score
        # (simplifié ici — à optimiser avec JOIN en prod)
        pass

    return {
        "total":   total,
        "matches": [_serialize_match(m, profile.id, trust_map) for m in matches],
        "limit":   limit,
        "offset":  offset,
    }


@router_matches.get("/{match_id}")
def get_match(
    match_id: str,
    account=Depends(lambda: None),
    db: Session = Depends(lambda: None),
):
    from .db.umbra_models import AnonymousProfile, Match

    profile = db.query(AnonymousProfile).filter(
        AnonymousProfile.account_id == account.id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profil non trouvé.")

    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match introuvable.")

    # Vérifier que ce profil est bien partie prenante
    if profile.id not in (match.profile_a_id, match.profile_b_id):
        raise HTTPException(status_code=403, detail="Accès refusé.")

    return _serialize_match(match, profile.id)


@router_matches.post("/{match_id}/ignore", status_code=204)
def ignore_match(
    match_id: str,
    req: IgnoreRequest,
    account=Depends(lambda: None),
    db: Session = Depends(lambda: None),
):
    from .db.umbra_models import AnonymousProfile, Match

    profile = db.query(AnonymousProfile).filter(
        AnonymousProfile.account_id == account.id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profil non trouvé.")

    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match introuvable.")
    if profile.id not in (match.profile_a_id, match.profile_b_id):
        raise HTTPException(status_code=403, detail="Accès refusé.")

    if match.profile_a_id == profile.id:
        match.ignored_by_a = True
    else:
        match.ignored_by_b = True

    db.commit()


@router_matches.post("/run")
def run_matching(
    background_tasks: BackgroundTasks,
    account=Depends(lambda: None),
    db: Session = Depends(lambda: None),
):
    """
    Déclenche le calcul de matching pour le profil courant.
    Asynchrone — retourne immédiatement, calcul en arrière-plan.
    """
    from .db.umbra_models import AnonymousProfile

    profile = db.query(AnonymousProfile).filter(
        AnonymousProfile.account_id == account.id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profil non trouvé.")

    background_tasks.add_task(_run_matching_task, profile.id, db)
    return {"message": "Matching lancé en arrière-plan.", "profile_id": profile.id}


def _run_matching_task(profile_id: str, db: Session) -> None:
    """Tâche de matching en arrière-plan."""
    from .db.umbra_models import (
        AnonymousProfile, Match, TrustScore, AccountType
    )
    from .services.matching_engine import engine, profile_to_input, MIN_SCORE_THRESHOLD

    profile = db.query(AnonymousProfile).filter(AnonymousProfile.id == profile_id).first()
    if not profile:
        return

    account = profile.account
    trust   = db.query(TrustScore).filter(TrustScore.account_id == account.id).first()

    # Type opposé pour matcher
    opposite_type = AccountType.COMPANY if profile.profile_type == AccountType.CANDIDATE else AccountType.CANDIDATE

    # Charger les profils opposés actifs (ou shadow si PLATINUM)
    q = db.query(AnonymousProfile).filter(
        AnonymousProfile.profile_type == opposite_type,
        AnonymousProfile.sector_id == profile.sector_id,
    )
    if profile.profile_type == AccountType.COMPANY:
        # Entreprises voient les profils actifs + shadow si elles sont PLATINUM
        if trust and trust.grade.value == "platinum":
            pass  # tous profils
        else:
            q = q.filter(AnonymousProfile.is_visible == True)

    opposites = q.limit(500).all()

    current_input = profile_to_input(profile, account, trust)

    new_matches = 0
    for opp in opposites:
        opp_account = opp.account
        opp_trust   = db.query(TrustScore).filter(TrustScore.account_id == opp_account.id).first()
        opp_input   = profile_to_input(opp, opp_account, opp_trust)

        # Toujours candidate=a, company=b
        a, b = (current_input, opp_input) if profile.profile_type == AccountType.CANDIDATE else (opp_input, current_input)
        a_id = profile.id if profile.profile_type == AccountType.CANDIDATE else opp.id
        b_id = opp.id if profile.profile_type == AccountType.CANDIDATE else profile.id

        result = engine.compute(a, b)
        if result.disqualified or result.total < MIN_SCORE_THRESHOLD:
            continue

        # Upsert match
        existing = db.query(Match).filter(
            Match.profile_a_id == a_id,
            Match.profile_b_id == b_id,
        ).first()

        if existing:
            existing.score_total      = result.total
            existing.score_skills     = result.skills
            existing.score_culture    = result.culture
            existing.score_geo        = result.geo
            existing.score_salary     = result.salary
            existing.score_durability = result.durability
            existing.distance_km      = result.distance_km
            existing.matched_skill_ids = result.matched_skill_ids
            existing.culture_similarity = result.culture_similarity
            existing.market_intel_label = result.market_intel
            existing.market_tension_pct = result.market_tension_pct
            existing.computed_at      = datetime.utcnow()
            existing.expires_at       = datetime.utcnow() + timedelta(days=30)
        else:
            match = Match(
                profile_a_id=a_id,
                profile_b_id=b_id,
                score_total=result.total,
                score_skills=result.skills,
                score_culture=result.culture,
                score_geo=result.geo,
                score_salary=result.salary,
                score_durability=result.durability,
                distance_km=result.distance_km,
                salary_compatible=result.salary_compatible,
                matched_skill_ids=result.matched_skill_ids,
                culture_similarity=result.culture_similarity,
                market_intel_label=result.market_intel,
                market_tension_pct=result.market_tension_pct,
                expires_at=datetime.utcnow() + timedelta(days=30),
            )
            db.add(match)
            new_matches += 1

    db.commit()
    logger.info("matching complete: %s — %d new matches", profile_id[:8], new_matches)


# ── ENDPOINTS SIGNALS ─────────────────────────────────────────────────────────

@router_signals.post("/{match_id}/signal", status_code=201)
def send_signal(
    match_id: str,
    req: SignalRequest,
    background_tasks: BackgroundTasks,
    account=Depends(lambda: None),
    db: Session = Depends(lambda: None),
):
    """
    Signale l'intérêt pour ce match.
    Si l'autre partie a déjà signalé → révélation déclenchée immédiatement.
    Si pas de crédits pour les entreprises → erreur.
    """
    from .db.umbra_models import (
        AnonymousProfile, Match, InterestSignal, RevealStatus,
        AccountType, CreditBalance, TrustScore
    )
    from .services.trust_service import trust_service

    profile = db.query(AnonymousProfile).filter(
        AnonymousProfile.account_id == account.id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profil non trouvé.")

    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match introuvable.")
    if profile.id not in (match.profile_a_id, match.profile_b_id):
        raise HTTPException(status_code=403, detail="Accès refusé.")

    # Vérifier signal existant
    existing_signal = db.query(InterestSignal).filter(
        InterestSignal.match_id == match_id,
        InterestSignal.sender_id == profile.id,
    ).first()
    if existing_signal:
        raise HTTPException(status_code=409, detail="Signal déjà envoyé pour ce match.")

    # Pour les entreprises : vérifier crédits + trust
    if profile.profile_type == AccountType.COMPANY:
        can, reason = trust_service.can_initiate_contact(db, account.id)
        if not can:
            raise HTTPException(status_code=403, detail=reason)

        balance = db.query(CreditBalance).filter(CreditBalance.account_id == account.id).first()
        if not balance or balance.balance < 1:
            raise HTTPException(
                status_code=402,
                detail="Crédits insuffisants. Rechargez votre compte."
            )

        # Débit crédit + event trust
        trust_service.record_contact_initiated(db, account.id, match_id)

    # Créer le signal
    receiver_id = match.profile_b_id if profile.id == match.profile_a_id else match.profile_a_id
    signal = InterestSignal(
        match_id=match_id,
        sender_id=profile.id,
        receiver_id=receiver_id,
        status=RevealStatus.PENDING,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(signal)
    db.commit()

    # Vérifier si révélation mutuelle
    revealed = _check_mutual_signal(db, match_id)

    # Notifier l'autre partie (en arrière-plan)
    receiver_account_id = None
    receiver_profile = db.query(AnonymousProfile).filter(AnonymousProfile.id == receiver_id).first()
    if receiver_profile:
        receiver_account_id = receiver_profile.account_id
    if receiver_account_id:
        background_tasks.add_task(_notify_interest, receiver_account_id, match.display_id)

    return {
        "signal_sent": True,
        "revealed":    revealed,
        "message": (
            "🎉 Révélation mutuelle déclenchée ! Les identités sont maintenant visibles."
            if revealed else
            "Signal envoyé. En attente de la confirmation de l'autre partie (max 7 jours)."
        ),
    }


@router_signals.get("/{match_id}/signal-status")
def get_signal_status(
    match_id: str,
    account=Depends(lambda: None),
    db: Session = Depends(lambda: None),
):
    """Retourne l'état du protocole de révélation pour ce match."""
    from .db.umbra_models import AnonymousProfile, Match, InterestSignal

    profile = db.query(AnonymousProfile).filter(
        AnonymousProfile.account_id == account.id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profil non trouvé.")

    match = db.query(Match).filter(Match.id == match_id).first()
    if not match or profile.id not in (match.profile_a_id, match.profile_b_id):
        raise HTTPException(status_code=404, detail="Match introuvable.")

    signals = db.query(InterestSignal).filter(InterestSignal.match_id == match_id).all()
    my_signal    = next((s for s in signals if s.sender_id == profile.id), None)
    other_signal = next((s for s in signals if s.sender_id != profile.id), None)

    revealed = any(s.status.value == "mutual" for s in signals)

    return {
        "match_id":     match_id,
        "revealed":     revealed,
        "i_signaled":   my_signal is not None,
        "other_signaled": other_signal is not None,
        "my_signal_status":    my_signal.status.value if my_signal else None,
        "my_signal_expires":   my_signal.expires_at.isoformat() if my_signal and my_signal.expires_at else None,
        "reveal_token":        my_signal.reveal_token if revealed and my_signal else None,
    }


@router_signals.delete("/{match_id}/signal", status_code=204)
def withdraw_signal(
    match_id: str,
    account=Depends(lambda: None),
    db: Session = Depends(lambda: None),
):
    """Retire le signal d'intérêt (uniquement si pas encore de révélation mutuelle)."""
    from .db.umbra_models import AnonymousProfile, InterestSignal, RevealStatus

    profile = db.query(AnonymousProfile).filter(
        AnonymousProfile.account_id == account.id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profil non trouvé.")

    signal = db.query(InterestSignal).filter(
        InterestSignal.match_id == match_id,
        InterestSignal.sender_id == profile.id,
    ).first()
    if not signal:
        raise HTTPException(status_code=404, detail="Signal introuvable.")
    if signal.status == RevealStatus.MUTUAL:
        raise HTTPException(
            status_code=409,
            detail="Impossible de retirer — révélation mutuelle déjà effectuée."
        )

    signal.status = RevealStatus.WITHDRAWN
    db.commit()


# ── ENDPOINTS QUESTIONS (ENTRETIEN INVERSÉ) ───────────────────────────────────

@router_questions.get("/{match_id}/questions")
def list_questions(
    match_id: str,
    account=Depends(lambda: None),
    db: Session = Depends(lambda: None),
):
    from .db.umbra_models import AnonymousProfile, Match, InverseQuestion

    profile = db.query(AnonymousProfile).filter(
        AnonymousProfile.account_id == account.id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profil non trouvé.")

    match = db.query(Match).filter(Match.id == match_id).first()
    if not match or profile.id not in (match.profile_a_id, match.profile_b_id):
        raise HTTPException(status_code=403, detail="Accès refusé.")

    questions = db.query(InverseQuestion).filter(
        InverseQuestion.match_id == match_id
    ).order_by(InverseQuestion.order_num).all()

    return {
        "questions": [
            {
                "id":         q.id,
                "order":      q.order_num,
                "question":   q.question,
                "answer":     q.answer,
                "asked_at":   q.asked_at.isoformat(),
                "answered_at": q.answered_at.isoformat() if q.answered_at else None,
            }
            for q in questions
        ],
        "count":     len(questions),
        "remaining": max(0, 3 - len(questions)),
    }


@router_questions.post("/{match_id}/questions", status_code=201)
def ask_question(
    match_id: str,
    req: QuestionCreate,
    account=Depends(lambda: None),
    db: Session = Depends(lambda: None),
):
    """
    Le candidat pose une question anonyme à l'entreprise.
    Maximum 3 questions par match.
    Uniquement avant la révélation mutuelle.
    """
    from .db.umbra_models import (
        AnonymousProfile, Match, InverseQuestion, AccountType, RevealStatus, InterestSignal
    )

    profile = db.query(AnonymousProfile).filter(
        AnonymousProfile.account_id == account.id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profil non trouvé.")

    if profile.profile_type != AccountType.CANDIDATE:
        raise HTTPException(
            status_code=403,
            detail="Seul le candidat peut poser des questions dans l'entretien inversé."
        )

    match = db.query(Match).filter(Match.id == match_id).first()
    if not match or profile.id != match.profile_a_id:
        raise HTTPException(status_code=403, detail="Accès refusé.")

    # Vérifier révélation pas encore faite
    signals = db.query(InterestSignal).filter(
        InterestSignal.match_id == match_id,
        InterestSignal.status == RevealStatus.MUTUAL,
    ).first()
    if signals:
        raise HTTPException(
            status_code=409,
            detail="La révélation mutuelle a déjà eu lieu — contactez l'entreprise directement."
        )

    # Vérifier quota
    count = db.query(InverseQuestion).filter(InverseQuestion.match_id == match_id).count()
    if count >= 3:
        raise HTTPException(status_code=400, detail="Maximum 3 questions par match atteint.")

    q = InverseQuestion(
        match_id=match_id,
        asker_id=profile.id,
        order_num=count + 1,
        question=req.question.strip(),
    )
    db.add(q)
    db.commit()
    db.refresh(q)

    logger.info("question asked: match %s (#%d)", match_id[:8], q.order_num)
    return {
        "question_id": q.id,
        "order":       q.order_num,
        "remaining":   max(0, 3 - (count + 1)),
    }


@router_questions.put("/{match_id}/questions/{question_id}")
def answer_question(
    match_id: str,
    question_id: str,
    req: QuestionAnswer,
    account=Depends(lambda: None),
    db: Session = Depends(lambda: None),
):
    """L'entreprise répond à une question du candidat."""
    from .db.umbra_models import AnonymousProfile, Match, InverseQuestion, AccountType

    profile = db.query(AnonymousProfile).filter(
        AnonymousProfile.account_id == account.id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profil non trouvé.")

    if profile.profile_type != AccountType.COMPANY:
        raise HTTPException(status_code=403, detail="Seule l'entreprise peut répondre.")

    match = db.query(Match).filter(Match.id == match_id).first()
    if not match or profile.id != match.profile_b_id:
        raise HTTPException(status_code=403, detail="Accès refusé.")

    question = db.query(InverseQuestion).filter(
        InverseQuestion.id == question_id,
        InverseQuestion.match_id == match_id,
    ).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question introuvable.")
    if question.answer:
        raise HTTPException(status_code=409, detail="Question déjà répondue.")

    question.answer      = req.answer.strip()
    question.answered_at = datetime.utcnow()
    db.commit()

    logger.info("question answered: %s", question_id[:8])
    return {"answered": True, "question_id": question_id}
