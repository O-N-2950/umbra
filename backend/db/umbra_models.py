"""
UMBRA — Database Models
Architecture anonymat-first pour la plateforme de recrutement.

Tables clés :
  accounts           → Compte réel (email, téléphone, vérification IDE)
  anonymous_profiles → Profil anonyme dissocié du compte — JAMAIS de FK directe visible
  skills / sectors   → Référentiel compétences
  culture_profiles   → Vecteur culturel (5 dimensions quiz)
  matches            → Correspondances calculées par l'algorithme
  interest_signals   → Signaux d'intérêt (anonymes jusqu'à double confirmation)
  trust_events       → Événements qui modifient le score de confiance
  credits            → Système de crédits contacts
  questions          → Entretien inversé (candidat → entreprise)
  offboarding        → Module off-boarding structuré

© 2026 PEP's Swiss SA — UMBRA
"""

import uuid
import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, JSON,
    DateTime, ForeignKey, Enum, UniqueConstraint, Index,
    SmallInteger,
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func


def PgEnum(enum_cls, **kw):
    """
    Enum SQLAlchemy qui persiste la VALEUR de l'enum (ex: "candidate"), pas son
    NOM (ex: "CANDIDATE"). Sans cela, SQLAlchemy stocke le nom, que l'enum
    PostgreSQL (strict) rejette — alors que SQLite (tolérant) l'accepte, d'où des
    500 en prod invisibles en dev. values_callable garantit le même comportement
    sur les deux moteurs.
    """
    return Enum(
        enum_cls,
        values_callable=lambda e: [member.value for member in e],
        **kw,
    )


Base = declarative_base()


# ── ENUMS ──────────────────────────────────────────────────────────────────────

class AccountType(str, enum.Enum):
    CANDIDATE = "candidate"
    COMPANY   = "company"

class ProfileMode(str, enum.Enum):
    SHADOW = "shadow"
    ACTIVE = "active"

class CompanyMode(str, enum.Enum):
    DISCREET = "discreet"
    PUBLIC   = "public"

class ContractType(str, enum.Enum):
    CDI    = "cdi"
    CDD    = "cdd"
    STAGE  = "stage"
    MISSION = "mission"

class TrustGrade(str, enum.Enum):
    PLATINUM   = "platinum"   # > 4.5
    GOLD       = "gold"       # > 4.0
    STANDARD   = "standard"   # > 3.0
    RESTRICTED = "restricted" # > 2.0
    SUSPENDED  = "suspended"  # <= 2.0

class TrustEventType(str, enum.Enum):
    CONTACT_INITIATED    = "contact_initiated"
    INTERVIEW_DONE       = "interview_done"
    OFFER_MADE           = "offer_made"
    HIRE_CONFIRMED       = "hire_confirmed"
    CONTACT_NO_FOLLOWUP  = "contact_no_followup"
    REPORTED_ABUSE       = "reported_abuse"
    GHOST_PROFILE        = "ghost_profile"
    DELAY_EXCEEDED       = "delay_exceeded"
    VERIFICATION_PASSED  = "verification_passed"

class RevealStatus(str, enum.Enum):
    PENDING   = "pending"
    MUTUAL    = "mutual"
    EXPIRED   = "expired"
    WITHDRAWN = "withdrawn"

class TransportMode(str, enum.Enum):
    CAR    = "car"
    PUBLIC = "public"
    BIKE   = "bike"
    REMOTE = "remote"


# ── HELPERS ────────────────────────────────────────────────────────────────────

def gen_uuid() -> str:
    return str(uuid.uuid4())

def gen_anon_id() -> str:
    import random, string
    return "U-" + "".join(random.choices(string.digits, k=4))


# ══════════════════════════════════════════════════════════════════════════════
# COMPTES RÉELS
# ══════════════════════════════════════════════════════════════════════════════

class Account(Base):
    """
    Compte réel — stocke l'identité vérifiée.
    JAMAIS exposé dans l'API de matching.
    La dissociation avec anonymous_profile est la garantie centrale de l'anonymat.
    """
    __tablename__ = "accounts"

    id             = Column(String(36), primary_key=True, default=gen_uuid)
    account_type   = Column(PgEnum(AccountType), nullable=False)

    email          = Column(String(200), unique=True, nullable=False, index=True)
    phone          = Column(String(30))
    email_verified = Column(Boolean, default=False)
    phone_verified = Column(Boolean, default=False)

    # Identité chiffrée AES-256 en prod
    identity_encrypted = Column(Text)

    # IDE entreprise (vérifié via Zefix API)
    ide_number     = Column(String(15), index=True)
    ide_verified   = Column(Boolean, default=False)
    ide_verified_at = Column(DateTime)

    plan           = Column(String(20), default="free")
    stripe_customer_id = Column(String(50))

    # Employeurs à exclure des matchs (protection candidat)
    employer_block_list = Column(JSON, default=list)

    # Employeur ACTUEL du candidat (IDE). Injecté automatiquement dans la block-list
    # à chaque matching : protège d'office le candidat contre un faux poste publié par
    # son propre patron pour le débusquer en veille. C'est LE garde-fou anti-désanonymisation.
    current_employer_ide = Column(String(15))

    is_active      = Column(Boolean, default=True)
    is_suspended   = Column(Boolean, default=False)
    suspended_at   = Column(DateTime)
    suspension_reason = Column(String(200))

    created_at     = Column(DateTime, default=func.now())
    updated_at     = Column(DateTime, default=func.now(), onupdate=func.now())
    last_login_at  = Column(DateTime)

    anonymous_profile = relationship("AnonymousProfile", back_populates="account", uselist=False)
    credits           = relationship("CreditBalance", back_populates="account", uselist=False)
    trust_events      = relationship("TrustEvent", back_populates="account")

    __table_args__ = (
        Index("ix_accounts_type_active", "account_type", "is_active"),
    )


# ══════════════════════════════════════════════════════════════════════════════
# PROFILS ANONYMES
# ══════════════════════════════════════════════════════════════════════════════

class AnonymousProfile(Base):
    """
    Seule entité visible dans le système de matching.
    FK vers account jamais exposée en API.
    Règle : aucune donnée ici ne doit permettre d'identifier le compte sans accès DB.
    """
    __tablename__ = "anonymous_profiles"

    id           = Column(String(36), primary_key=True, default=gen_uuid)
    display_id   = Column(String(10), unique=True, default=gen_anon_id)
    account_id   = Column(String(36), ForeignKey("accounts.id"), nullable=False, unique=True)

    profile_type = Column(PgEnum(AccountType), nullable=False)
    mode         = Column(PgEnum(ProfileMode), default=ProfileMode.SHADOW)
    company_mode = Column(PgEnum(CompanyMode), default=CompanyMode.DISCREET)

    # Zone géographique (jamais adresse exacte — centroïde + décalage aléatoire 2-5km)
    postal_zone  = Column(String(4))
    region_label = Column(String(100))
    mobility_km  = Column(Integer, default=50)
    transport_mode = Column(PgEnum(TransportMode), default=TransportMode.CAR)
    geo_lat      = Column(Float)
    geo_lon      = Column(Float)

    sector_id    = Column(String(36), ForeignKey("sectors.id"))

    contract_types  = Column(JSON, default=list)
    work_rate_min   = Column(SmallInteger, default=100)
    work_rate_max   = Column(SmallInteger, default=100)

    # Salaire jamais affiché brut — compatibilité ±10% calculée backend
    salary_min      = Column(Integer)
    salary_max      = Column(Integer)
    salary_currency = Column(String(3), default="CHF")

    notice_days  = Column(Integer, default=0)
    notice_label = Column(String(30))

    # Recommandations anonymes reçues
    anonymous_recommendations = Column(JSON, default=list)

    is_visible   = Column(Boolean, default=False)
    last_active_at = Column(DateTime)
    shadow_alert_threshold = Column(Integer, default=85)

    created_at   = Column(DateTime, default=func.now())
    updated_at   = Column(DateTime, default=func.now(), onupdate=func.now())

    account        = relationship("Account", back_populates="anonymous_profile")
    sector         = relationship("Sector")
    profile_skills = relationship("ProfileSkill", back_populates="profile", cascade="all, delete-orphan")
    culture_profile = relationship("CultureProfile", back_populates="profile", uselist=False)
    matches_as_a   = relationship("Match", foreign_keys="Match.profile_a_id", back_populates="profile_a")
    matches_as_b   = relationship("Match", foreign_keys="Match.profile_b_id", back_populates="profile_b")
    sent_signals   = relationship("InterestSignal", foreign_keys="InterestSignal.sender_id")
    received_signals = relationship("InterestSignal", foreign_keys="InterestSignal.receiver_id")

    __table_args__ = (
        Index("ix_profiles_type_visible", "profile_type", "is_visible"),
        Index("ix_profiles_sector", "sector_id"),
    )


# ══════════════════════════════════════════════════════════════════════════════
# RÉFÉRENTIEL COMPÉTENCES
# ══════════════════════════════════════════════════════════════════════════════

class Sector(Base):
    __tablename__ = "sectors"

    id        = Column(String(36), primary_key=True, default=gen_uuid)
    slug      = Column(String(50), unique=True, nullable=False)
    label     = Column(String(100), nullable=False)
    symbol    = Column(String(5))
    color     = Column(String(10))
    order     = Column(SmallInteger, default=0)
    is_active = Column(Boolean, default=True)


class Skill(Base):
    __tablename__ = "skills"

    id        = Column(String(36), primary_key=True, default=gen_uuid)
    sector_id = Column(String(36), ForeignKey("sectors.id"), nullable=False)
    label     = Column(String(150), nullable=False)
    slug      = Column(String(100))
    category  = Column(String(50))
    is_active = Column(Boolean, default=True)

    sector = relationship("Sector")

    __table_args__ = (
        UniqueConstraint("sector_id", "label", name="uq_skill_sector_label"),
        Index("ix_skills_sector", "sector_id"),
    )


class ProfileSkill(Base):
    __tablename__ = "profile_skills"

    id         = Column(String(36), primary_key=True, default=gen_uuid)
    profile_id = Column(String(36), ForeignKey("anonymous_profiles.id"), nullable=False)
    skill_id   = Column(String(36), ForeignKey("skills.id"), nullable=False)
    level      = Column(SmallInteger, default=2)  # 1=débutant 2=autonome 3=expert
    verified   = Column(Boolean, default=False)
    verified_at = Column(DateTime)

    profile = relationship("AnonymousProfile", back_populates="profile_skills")
    skill   = relationship("Skill")

    __table_args__ = (
        UniqueConstraint("profile_id", "skill_id", name="uq_profile_skill"),
    )


# ══════════════════════════════════════════════════════════════════════════════
# EMPREINTE CULTURELLE
# ══════════════════════════════════════════════════════════════════════════════

class CultureProfile(Base):
    """Vecteur culturel 6 dimensions [0.0-1.0] calculé depuis le quiz 5 questions."""
    __tablename__ = "culture_profiles"

    id         = Column(String(36), primary_key=True, default=gen_uuid)
    profile_id = Column(String(36), ForeignKey("anonymous_profiles.id"), nullable=False, unique=True)

    quiz_answers = Column(JSON)
    quiz_dims    = Column(JSON)

    dim_autonomie     = Column(Float, default=0.5)
    dim_structure     = Column(Float, default=0.5)
    dim_collaboration = Column(Float, default=0.5)
    dim_remote        = Column(Float, default=0.5)
    dim_croissance    = Column(Float, default=0.5)
    dim_stabilite     = Column(Float, default=0.5)

    work_style   = Column(String(50))
    environment  = Column(String(50))
    motivation   = Column(String(50))

    completed    = Column(Boolean, default=False)
    completed_at = Column(DateTime)

    profile = relationship("AnonymousProfile", back_populates="culture_profile")

    def as_vector(self) -> list:
        return [
            self.dim_autonomie, self.dim_structure,
            self.dim_collaboration, self.dim_remote,
            self.dim_croissance, self.dim_stabilite,
        ]


# ══════════════════════════════════════════════════════════════════════════════
# MATCHING
# ══════════════════════════════════════════════════════════════════════════════

class Match(Base):
    """
    Correspondance entre profil CANDIDATE (a) et COMPANY (b).
    Score composite pondéré :
      compétences 40% + culture 20% + géo 20% + salary 15% + durabilité 5%
    """
    __tablename__ = "matches"

    id           = Column(String(36), primary_key=True, default=gen_uuid)
    display_id   = Column(String(10), unique=True, default=gen_anon_id)
    profile_a_id = Column(String(36), ForeignKey("anonymous_profiles.id"), nullable=False)
    profile_b_id = Column(String(36), ForeignKey("anonymous_profiles.id"), nullable=False)

    score_total      = Column(Float, nullable=False)
    score_skills     = Column(Float)
    score_culture    = Column(Float)
    score_geo        = Column(Float)
    score_salary     = Column(Float)
    score_durability = Column(Float)

    distance_km        = Column(Float)
    salary_compatible  = Column(Boolean, default=False)
    matched_skill_ids  = Column(JSON, default=list)
    culture_similarity = Column(Float)

    market_tension_pct = Column(Float)
    market_intel_label = Column(String(200))

    is_active    = Column(Boolean, default=True)
    ignored_by_a = Column(Boolean, default=False)
    ignored_by_b = Column(Boolean, default=False)

    computed_at  = Column(DateTime, default=func.now())
    expires_at   = Column(DateTime)

    profile_a = relationship("AnonymousProfile", foreign_keys=[profile_a_id], back_populates="matches_as_a")
    profile_b = relationship("AnonymousProfile", foreign_keys=[profile_b_id], back_populates="matches_as_b")
    signals   = relationship("InterestSignal", back_populates="match")
    questions = relationship("InverseQuestion", back_populates="match")

    __table_args__ = (
        UniqueConstraint("profile_a_id", "profile_b_id", name="uq_match_pair"),
        Index("ix_matches_score", "score_total"),
        Index("ix_matches_active", "is_active"),
    )


# ══════════════════════════════════════════════════════════════════════════════
# SIGNAUX D'INTÉRÊT & RÉVÉLATION MUTUELLE
# ══════════════════════════════════════════════════════════════════════════════

class InterestSignal(Base):
    """
    Révélation ne se déclenche QUE si les deux signaux existent pour le même match.
    Cœur du protocole de confidentialité.
    """
    __tablename__ = "interest_signals"

    id          = Column(String(36), primary_key=True, default=gen_uuid)
    match_id    = Column(String(36), ForeignKey("matches.id"), nullable=False)
    sender_id   = Column(String(36), ForeignKey("anonymous_profiles.id"), nullable=False)
    receiver_id = Column(String(36), ForeignKey("anonymous_profiles.id"), nullable=False)

    status     = Column(PgEnum(RevealStatus), default=RevealStatus.PENDING)
    sent_at    = Column(DateTime, default=func.now())
    expires_at = Column(DateTime)

    revealed_at  = Column(DateTime)
    reveal_token = Column(String(64))

    match    = relationship("Match", back_populates="signals")
    sender   = relationship("AnonymousProfile", foreign_keys=[sender_id], back_populates="sent_signals")
    receiver = relationship("AnonymousProfile", foreign_keys=[receiver_id], back_populates="received_signals")

    __table_args__ = (
        UniqueConstraint("match_id", "sender_id", name="uq_signal_match_sender"),
        Index("ix_signals_match", "match_id"),
    )


# ══════════════════════════════════════════════════════════════════════════════
# ENTRETIEN INVERSÉ
# ══════════════════════════════════════════════════════════════════════════════

class InverseQuestion(Base):
    """Max 3 questions par match. Candidat interroge l'entreprise avant révélation."""
    __tablename__ = "inverse_questions"

    id        = Column(String(36), primary_key=True, default=gen_uuid)
    match_id  = Column(String(36), ForeignKey("matches.id"), nullable=False)
    asker_id  = Column(String(36), ForeignKey("anonymous_profiles.id"), nullable=False)
    order_num = Column(SmallInteger, default=1)

    question    = Column(Text, nullable=False)
    answer      = Column(Text)
    asked_at    = Column(DateTime, default=func.now())
    answered_at = Column(DateTime)

    match = relationship("Match", back_populates="questions")
    asker = relationship("AnonymousProfile", foreign_keys=[asker_id])

    __table_args__ = (Index("ix_questions_match", "match_id"),)


# ══════════════════════════════════════════════════════════════════════════════
# SYSTÈME DE CONFIANCE — EVENT SOURCING
# ══════════════════════════════════════════════════════════════════════════════

class TrustEvent(Base):
    """Score courant = somme de tous les événements. Immuable."""
    __tablename__ = "trust_events"

    id           = Column(String(36), primary_key=True, default=gen_uuid)
    account_id   = Column(String(36), ForeignKey("accounts.id"), nullable=False)
    event_type   = Column(PgEnum(TrustEventType), nullable=False)
    points_delta = Column(Float, nullable=False)
    reference_id = Column(String(36))
    note         = Column(String(300))
    created_at   = Column(DateTime, default=func.now())

    account = relationship("Account", back_populates="trust_events")

    __table_args__ = (
        Index("ix_trust_account", "account_id"),
        Index("ix_trust_created", "created_at"),
    )


class TrustScore(Base):
    """Score dénormalisé pour performance — recalculé après chaque TrustEvent."""
    __tablename__ = "trust_scores"

    account_id = Column(String(36), ForeignKey("accounts.id"), primary_key=True)
    score      = Column(Float, default=3.0)
    grade      = Column(PgEnum(TrustGrade), default=TrustGrade.STANDARD)

    contacts_total   = Column(Integer, default=0)
    interviews_total = Column(Integer, default=0)
    offers_total     = Column(Integer, default=0)
    hires_confirmed  = Column(Integer, default=0)
    reports_received = Column(Integer, default=0)
    hire_rate_pct    = Column(Float, default=0.0)

    consecutive_no_followup = Column(Integer, default=0)
    suspension_watch        = Column(Boolean, default=False)

    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    account = relationship("Account", foreign_keys=[account_id])


# ══════════════════════════════════════════════════════════════════════════════
# CRÉDITS CONTACTS
# ══════════════════════════════════════════════════════════════════════════════

class CreditBalance(Base):
    __tablename__ = "credit_balances"

    account_id     = Column(String(36), ForeignKey("accounts.id"), primary_key=True)
    balance        = Column(Integer, default=5)
    total_bought   = Column(Integer, default=0)
    total_spent    = Column(Integer, default=0)
    total_refunded = Column(Integer, default=0)
    updated_at     = Column(DateTime, default=func.now(), onupdate=func.now())

    account = relationship("Account", back_populates="credits")


class CreditTransaction(Base):
    __tablename__ = "credit_transactions"

    id           = Column(String(36), primary_key=True, default=gen_uuid)
    account_id   = Column(String(36), ForeignKey("accounts.id"), nullable=False)
    amount       = Column(Integer, nullable=False)
    type         = Column(String(30))
    reference_id = Column(String(36))
    stripe_pi_id = Column(String(50))
    note         = Column(String(200))
    created_at   = Column(DateTime, default=func.now())

    __table_args__ = (Index("ix_credits_account", "account_id"),)


# ══════════════════════════════════════════════════════════════════════════════
# OFFBOARDING
# ══════════════════════════════════════════════════════════════════════════════

class Offboarding(Base):
    """Départ structuré = réactivation automatique du profil candidat à end_date."""
    __tablename__ = "offboardings"

    id                   = Column(String(36), primary_key=True, default=gen_uuid)
    candidate_account_id = Column(String(36), ForeignKey("accounts.id"), nullable=False)
    company_account_id   = Column(String(36), ForeignKey("accounts.id"), nullable=False)

    end_date        = Column(DateTime)
    actual_end_date = Column(DateTime)

    company_recommendation   = Column(Text)
    candidate_recommendation = Column(Text)
    mutual_consent_reveal    = Column(Boolean, default=False)

    reactivation_date   = Column(DateTime)
    reactivated         = Column(Boolean, default=False)
    reactivated_at      = Column(DateTime)

    managed_well         = Column(Boolean)
    trust_bonus_applied  = Column(Boolean, default=False)

    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index("ix_offboarding_candidate", "candidate_account_id"),
        Index("ix_offboarding_reactivation", "reactivation_date", "reactivated"),
    )


# ══════════════════════════════════════════════════════════════════════════════
# INTELLIGENCE MARCHÉ
# ══════════════════════════════════════════════════════════════════════════════

class MarketSnapshot(Base):
    """Snapshot mensuel agrégé et anonymisé par secteur × région."""
    __tablename__ = "market_snapshots"

    id             = Column(String(36), primary_key=True, default=gen_uuid)
    sector_id      = Column(String(36), ForeignKey("sectors.id"), nullable=False)
    region_code    = Column(String(10), nullable=False)
    snapshot_month = Column(String(7), nullable=False)

    salary_median     = Column(Integer)
    salary_p25        = Column(Integer)
    salary_p75        = Column(Integer)
    sample_size       = Column(Integer, default=0)

    demand_count      = Column(Integer, default=0)
    supply_count      = Column(Integer, default=0)
    tension_pct       = Column(Float, default=0.0)
    median_response_days = Column(Float)

    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        UniqueConstraint("sector_id", "region_code", "snapshot_month", name="uq_snapshot"),
        Index("ix_snapshot_sector_region", "sector_id", "region_code"),
    )


class SalaryBenchmark(Base):
    """Benchmark salarial par rôle × région × expérience avec prédictions IA."""
    __tablename__ = "salary_benchmarks"

    id            = Column(String(36), primary_key=True, default=gen_uuid)
    sector_id     = Column(String(36), ForeignKey("sectors.id"), nullable=False)
    role_label    = Column(String(150), nullable=False)
    region_code   = Column(String(10))
    experience_years_min = Column(SmallInteger, default=0)
    experience_years_max = Column(SmallInteger)

    salary_min    = Column(Integer)
    salary_median = Column(Integer)
    salary_max    = Column(Integer)
    currency      = Column(String(3), default="CHF")

    demand_index  = Column(Float, default=50.0)
    trend_6m_pct  = Column(Float, default=0.0)
    ai_prediction_18m_pct = Column(Float)

    valid_from    = Column(DateTime, default=func.now())
    valid_until   = Column(DateTime)

    __table_args__ = (Index("ix_benchmark_sector", "sector_id"),)


# ══════════════════════════════════════════════════════════════════════════════
# AUDIT LOG — IMMUABLE
# ══════════════════════════════════════════════════════════════════════════════

class AuditLog(Base):
    """Toutes les actions sensibles. Jamais de UPDATE ni DELETE."""
    __tablename__ = "audit_logs"

    id           = Column(String(36), primary_key=True, default=gen_uuid)
    account_id   = Column(String(36), ForeignKey("accounts.id"))
    action       = Column(String(100), nullable=False)
    resource     = Column(String(50))
    resource_id  = Column(String(36))
    ip_hash      = Column(String(64))
    user_agent_hash = Column(String(64))
    meta         = Column(JSON, default=dict)
    created_at   = Column(DateTime, default=func.now())

    __table_args__ = (
        Index("ix_audit_account", "account_id"),
        Index("ix_audit_created", "created_at"),
        Index("ix_audit_action", "action"),
    )
