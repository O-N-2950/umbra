"""
UMBRA — Trust Service
Event-sourcing du score de confiance.

Principe :
  - Chaque action génère un TrustEvent immuable
  - TrustScore est dénormalisé (recalculé à chaque event) pour performance
  - Le score détermine l'accès (grade) et les actions autorisées
  - L'anti-espionnage surveille les contacts sans suite consécutifs

Points par événement :
  hire_confirmed       +15   (double confirmation obligatoire)
  verification_passed  +10   (IDE Zefix validé)
  offer_made           +8
  interview_done       +5
  contact_initiated    +2
  delay_exceeded       -4
  ghost_profile        -5
  contact_no_followup  -3
  reported_abuse       -10

© 2026 PEP's Swiss SA — UMBRA
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from ..db.umbra_models import (
    Account, TrustEvent, TrustScore, TrustGrade, TrustEventType,
    AuditLog, CreditBalance, CreditTransaction,
)

logger = logging.getLogger("umbra.trust")

# ── POINTS ────────────────────────────────────────────────────────────────────

EVENT_POINTS: dict[TrustEventType, float] = {
    TrustEventType.HIRE_CONFIRMED:       +15.0,
    TrustEventType.VERIFICATION_PASSED:  +10.0,
    TrustEventType.OFFER_MADE:           +8.0,
    TrustEventType.INTERVIEW_DONE:       +5.0,
    TrustEventType.CONTACT_INITIATED:    +2.0,
    TrustEventType.DELAY_EXCEEDED:       -4.0,
    TrustEventType.GHOST_PROFILE:        -5.0,
    TrustEventType.CONTACT_NO_FOLLOWUP:  -3.0,
    TrustEventType.REPORTED_ABUSE:       -10.0,
}

# Seuils des grades
GRADE_THRESHOLDS = {
    TrustGrade.PLATINUM:   4.5,
    TrustGrade.GOLD:       4.0,
    TrustGrade.STANDARD:   3.0,
    TrustGrade.RESTRICTED: 2.0,
    # SUSPENDED : < 2.0
}

# Anti-espionnage : nb max contacts sans suite avant suspension_watch
SUSPICIOUS_NO_FOLLOWUP_THRESHOLD = 5
SUSPENSION_NO_FOLLOWUP_THRESHOLD = 10


# ── HELPERS ───────────────────────────────────────────────────────────────────

def _score_to_grade(score: float) -> TrustGrade:
    if score >= GRADE_THRESHOLDS[TrustGrade.PLATINUM]:
        return TrustGrade.PLATINUM
    if score >= GRADE_THRESHOLDS[TrustGrade.GOLD]:
        return TrustGrade.GOLD
    if score >= GRADE_THRESHOLDS[TrustGrade.STANDARD]:
        return TrustGrade.STANDARD
    if score >= GRADE_THRESHOLDS[TrustGrade.RESTRICTED]:
        return TrustGrade.RESTRICTED
    return TrustGrade.SUSPENDED


def _clamp(value: float, min_v: float = 0.0, max_v: float = 5.0) -> float:
    return max(min_v, min(max_v, value))


# ── SERVICE ───────────────────────────────────────────────────────────────────

class TrustService:
    """
    Service de gestion du score de confiance.
    
    Toutes les mutations passent ici — jamais de modification directe
    de TrustScore sans passer par record_event().
    """

    # ── LECTURE ───────────────────────────────────────────────────────────────

    def get_score(self, db: Session, account_id: str) -> TrustScore:
        """Retourne ou crée le TrustScore d'un compte."""
        ts = db.query(TrustScore).filter(TrustScore.account_id == account_id).first()
        if not ts:
            ts = TrustScore(account_id=account_id)
            db.add(ts)
            db.commit()
            db.refresh(ts)
        return ts

    def get_passport(self, db: Session, account_id: str) -> dict:
        """Retourne les données publiques du Passeport de Confiance."""
        ts = self.get_score(db, account_id)
        return {
            "score":            round(ts.score, 2),
            "grade":            ts.grade.value,
            "contacts_total":   ts.contacts_total,
            "interviews_total": ts.interviews_total,
            "offers_total":     ts.offers_total,
            "hires_confirmed":  ts.hires_confirmed,
            "reports_received": ts.reports_received,
            "hire_rate_pct":    round(ts.hire_rate_pct, 1),
            "is_suspended":     ts.grade == TrustGrade.SUSPENDED,
            "is_certified":     ts.grade in (TrustGrade.PLATINUM, TrustGrade.GOLD),
        }

    def can_initiate_contact(self, db: Session, account_id: str) -> tuple[bool, str]:
        """Vérifie si un compte peut initier un contact."""
        ts = self.get_score(db, account_id)
        if ts.grade == TrustGrade.SUSPENDED:
            return False, "Compte suspendu suite à des abus répétés."
        if ts.grade == TrustGrade.RESTRICTED:
            return False, "Accès restreint — score insuffisant. Réception uniquement."
        return True, "ok"

    def can_access_shadow_profiles(self, db: Session, account_id: str) -> bool:
        """Seuls PLATINUM peuvent accéder aux profils en mode veille passive."""
        ts = self.get_score(db, account_id)
        return ts.grade == TrustGrade.PLATINUM

    # ── MUTATIONS ─────────────────────────────────────────────────────────────

    def record_event(
        self,
        db: Session,
        account_id: str,
        event_type: TrustEventType,
        reference_id: Optional[str] = None,
        note: Optional[str] = None,
    ) -> TrustScore:
        """
        Enregistre un événement et recalcule le TrustScore.
        C'est la SEULE méthode qui doit modifier le score.
        """
        points = EVENT_POINTS.get(event_type, 0.0)

        # 1. Créer l'event immuable
        event = TrustEvent(
            account_id=account_id,
            event_type=event_type,
            points_delta=points,
            reference_id=reference_id,
            note=note,
        )
        db.add(event)

        # 2. Mettre à jour le score dénormalisé
        ts = self.get_score(db, account_id)
        new_score = _clamp(ts.score + points)
        ts.score = new_score
        ts.grade = _score_to_grade(new_score)
        ts.updated_at = datetime.utcnow()

        # 3. Mettre à jour les compteurs
        self._update_counters(ts, event_type)

        # 4. Recalculer le taux d'embauche
        if ts.contacts_total > 0:
            ts.hire_rate_pct = (ts.hires_confirmed / ts.contacts_total) * 100

        # 5. Logique anti-espionnage
        self._check_anti_spy(db, ts, event_type, account_id)

        db.commit()
        db.refresh(ts)

        logger.info(
            "trust_event recorded",
            extra={
                "account": account_id, "event": event_type.value,
                "delta": points, "new_score": new_score, "grade": ts.grade.value,
            }
        )
        return ts

    def record_contact_initiated(self, db: Session, account_id: str, match_id: str) -> TrustScore:
        """Appeler quand une entreprise initie un contact (débit crédit inclus)."""
        # Débit 1 crédit
        self._debit_credit(db, account_id, match_id)
        return self.record_event(
            db, account_id, TrustEventType.CONTACT_INITIATED,
            reference_id=match_id, note="Contact initié sur match"
        )

    def record_hire_confirmed(
        self, db: Session,
        company_account_id: str,
        candidate_account_id: str,
        match_id: str,
    ) -> tuple[TrustScore, TrustScore]:
        """
        Double confirmation d'embauche.
        Valide uniquement si les deux profils ont déjà confirmé (vérifier avant d'appeler).
        
        Retourne (trust_score_company, trust_score_candidate)
        """
        # Compétences du candidat deviennent "verified"
        self._verify_candidate_skills(db, candidate_account_id, match_id)

        # Événements des deux côtés
        ts_company = self.record_event(
            db, company_account_id, TrustEventType.HIRE_CONFIRMED,
            reference_id=match_id, note="Embauche confirmée (double)"
        )
        ts_candidate = self.record_event(
            db, candidate_account_id, TrustEventType.HIRE_CONFIRMED,
            reference_id=match_id, note="Embauche confirmée (double)"
        )

        # Remboursement partiel du crédit contact
        self._refund_credit(db, company_account_id, match_id, amount=1)

        self._audit(db, company_account_id, "hire_confirmed", "match", match_id)
        return ts_company, ts_candidate

    def record_no_followup(self, db: Session, account_id: str, match_id: str) -> TrustScore:
        """
        Contact sans suite (délai dépassé sans entretien ni offre).
        Décrémente le score + incrémente consecutive_no_followup.
        """
        return self.record_event(
            db, account_id, TrustEventType.CONTACT_NO_FOLLOWUP,
            reference_id=match_id, note="Contact sans suivi dans les délais"
        )

    def check_and_run_suspensions(self, db: Session) -> list[str]:
        """
        Cron job : vérifie tous les comptes en suspension_watch.
        Suspend automatiquement si seuil atteint.
        Retourne la liste des account_id suspendus.
        """
        suspended = []
        watches = (
            db.query(TrustScore)
            .filter(TrustScore.suspension_watch == True)
            .all()
        )
        for ts in watches:
            if ts.consecutive_no_followup >= SUSPENSION_NO_FOLLOWUP_THRESHOLD:
                self._suspend(db, ts)
                suspended.append(ts.account_id)
                logger.warning("account auto-suspended: %s", ts.account_id)

        if suspended:
            db.commit()
        return suspended

    # ── PRIVÉ ─────────────────────────────────────────────────────────────────

    def _update_counters(self, ts: TrustScore, event_type: TrustEventType) -> None:
        """Met à jour les compteurs du passeport."""
        if event_type == TrustEventType.CONTACT_INITIATED:
            ts.contacts_total += 1
        elif event_type == TrustEventType.INTERVIEW_DONE:
            ts.interviews_total += 1
        elif event_type == TrustEventType.OFFER_MADE:
            ts.offers_total += 1
        elif event_type == TrustEventType.HIRE_CONFIRMED:
            ts.hires_confirmed += 1
            ts.consecutive_no_followup = 0  # reset après embauche
        elif event_type == TrustEventType.REPORTED_ABUSE:
            ts.reports_received += 1
        elif event_type == TrustEventType.CONTACT_NO_FOLLOWUP:
            ts.consecutive_no_followup += 1

    def _check_anti_spy(
        self,
        db: Session,
        ts: TrustScore,
        event_type: TrustEventType,
        account_id: str,
    ) -> None:
        """
        Logique anti-espionnage :
        - >= 5 contacts sans suite → suspension_watch activé
        - >= 10 contacts sans suite → suspension automatique au prochain event
        """
        if ts.consecutive_no_followup >= SUSPICIOUS_NO_FOLLOWUP_THRESHOLD:
            ts.suspension_watch = True
            self._audit(db, account_id, "suspension_watch_activated", "account", account_id,
                        {"consecutive": ts.consecutive_no_followup})
            logger.warning("suspension_watch activated for %s (%d no-followups)",
                           account_id, ts.consecutive_no_followup)

        if ts.consecutive_no_followup >= SUSPENSION_NO_FOLLOWUP_THRESHOLD:
            self._suspend(db, ts)

    def _suspend(self, db: Session, ts: TrustScore) -> None:
        """
        Suspend le compte et masque définitivement les profils consultés.
        Cette action est IRRÉVERSIBLE sans intervention manuelle.
        """
        ts.score = min(ts.score, 1.9)  # force sous le seuil SUSPENDED
        ts.grade = TrustGrade.SUSPENDED

        account = db.query(Account).filter(Account.id == ts.account_id).first()
        if account:
            account.is_suspended = True
            account.suspended_at = datetime.utcnow()
            account.suspension_reason = "Anti-espionnage : contacts répétés sans embauche"

        self._audit(db, ts.account_id, "account_auto_suspended", "account", ts.account_id,
                    {"consecutive_no_followup": ts.consecutive_no_followup})

    def _debit_credit(self, db: Session, account_id: str, match_id: str) -> None:
        """Débite 1 crédit pour initiation de contact."""
        balance = db.query(CreditBalance).filter(CreditBalance.account_id == account_id).first()
        if balance:
            balance.balance = max(0, balance.balance - 1)
            balance.total_spent += 1
        tx = CreditTransaction(
            account_id=account_id, amount=-1,
            type="contact_debit", reference_id=match_id,
            note="Contact initié",
        )
        db.add(tx)

    def _refund_credit(self, db: Session, account_id: str, match_id: str, amount: int = 1) -> None:
        """Rembourse partiellement un crédit après embauche confirmée."""
        balance = db.query(CreditBalance).filter(CreditBalance.account_id == account_id).first()
        if balance:
            balance.balance += amount
            balance.total_refunded += amount
        tx = CreditTransaction(
            account_id=account_id, amount=amount,
            type="hire_refund", reference_id=match_id,
            note="Remboursement partiel après embauche confirmée",
        )
        db.add(tx)

    def _verify_candidate_skills(self, db: Session, candidate_account_id: str, match_id: str) -> None:
        """
        Après embauche confirmée, les compétences matchées du candidat
        passent à verified=True (validées en conditions réelles).
        """
        from ..db.umbra_models import AnonymousProfile, ProfileSkill, Match, InterestSignal

        # Retrouver le match
        match = db.query(Match).filter(Match.id == match_id).first()
        if not match:
            return

        # Profil du candidat
        profile = db.query(AnonymousProfile).filter(
            AnonymousProfile.account_id == candidate_account_id
        ).first()
        if not profile:
            return

        # Marquer les compétences matchées comme vérifiées
        for skill_id in (match.matched_skill_ids or []):
            ps = db.query(ProfileSkill).filter(
                ProfileSkill.profile_id == profile.id,
                ProfileSkill.skill_id == skill_id,
            ).first()
            if ps and not ps.verified:
                ps.verified = True
                ps.verified_at = datetime.utcnow()

    def _audit(
        self, db: Session, account_id: str, action: str,
        resource: str, resource_id: str, metadata: dict = None
    ) -> None:
        """Écrit une entrée dans le journal d'audit immuable."""
        entry = AuditLog(
            account_id=account_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            metadata=metadata or {},
        )
        db.add(entry)


# ── INSTANCE SINGLETON ────────────────────────────────────────────────────────

trust_service = TrustService()
