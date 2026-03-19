"""
UMBRA — Migration Alembic initiale
Création de toutes les tables UMBRA.

Revision: 0001_umbra_init
Branche: umbra (séparée du schéma MATCHO existant)

Pour appliquer :
    alembic upgrade head

Pour rollback :
    alembic downgrade base

© 2026 PEP's Swiss SA — UMBRA
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# ── REVISION ──────────────────────────────────────────────────────────────────

revision = "0001_umbra_init"
down_revision = "001_initial"
branch_labels = None
depends_on = None


# ── UPGRADE ───────────────────────────────────────────────────────────────────

def upgrade() -> None:

    # ── ENUMs ─────────────────────────────────────────────────────────────────

    account_type_enum = sa.Enum(
        "candidate", "company",
        name="accounttype"
    )
    profile_mode_enum = sa.Enum(
        "shadow", "active",
        name="profilemode"
    )
    company_mode_enum = sa.Enum(
        "discreet", "public",
        name="companymode"
    )
    transport_mode_enum = sa.Enum(
        "car", "public", "bike", "remote",
        name="transportmode"
    )
    trust_grade_enum = sa.Enum(
        "platinum", "gold", "standard", "restricted", "suspended",
        name="trustgrade"
    )
    trust_event_type_enum = sa.Enum(
        "contact_initiated", "interview_done", "offer_made", "hire_confirmed",
        "contact_no_followup", "reported_abuse", "ghost_profile",
        "delay_exceeded", "verification_passed",
        name="trusteventtype"
    )
    reveal_status_enum = sa.Enum(
        "pending", "mutual", "expired", "withdrawn",
        name="revealstatus"
    )

    # ── SECTORS ───────────────────────────────────────────────────────────────

    op.create_table(
        "sectors",
        sa.Column("id",        sa.String(36), primary_key=True),
        sa.Column("slug",      sa.String(50),  nullable=False, unique=True),
        sa.Column("label",     sa.String(100), nullable=False),
        sa.Column("symbol",    sa.String(5)),
        sa.Column("color",     sa.String(10)),
        sa.Column("order",     sa.SmallInteger, default=0),
        sa.Column("is_active", sa.Boolean, default=True),
    )

    # ── SKILLS ────────────────────────────────────────────────────────────────

    op.create_table(
        "skills",
        sa.Column("id",        sa.String(36), primary_key=True),
        sa.Column("sector_id", sa.String(36), sa.ForeignKey("sectors.id"), nullable=False),
        sa.Column("label",     sa.String(150), nullable=False),
        sa.Column("slug",      sa.String(100)),
        sa.Column("category",  sa.String(50)),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.UniqueConstraint("sector_id", "label", name="uq_skill_sector_label"),
    )
    op.create_index("ix_skills_sector", "skills", ["sector_id"])

    # ── ACCOUNTS ──────────────────────────────────────────────────────────────

    op.create_table(
        "accounts",
        sa.Column("id",                 sa.String(36), primary_key=True),
        sa.Column("account_type",       account_type_enum, nullable=False),
        sa.Column("email",              sa.String(200), nullable=False, unique=True),
        sa.Column("phone",              sa.String(30)),
        sa.Column("email_verified",     sa.Boolean, default=False),
        sa.Column("phone_verified",     sa.Boolean, default=False),
        sa.Column("identity_encrypted", sa.Text),
        sa.Column("ide_number",         sa.String(15)),
        sa.Column("ide_verified",       sa.Boolean, default=False),
        sa.Column("ide_verified_at",    sa.DateTime),
        sa.Column("plan",               sa.String(20), default="free"),
        sa.Column("stripe_customer_id", sa.String(50)),
        sa.Column("employer_block_list",sa.JSON, default=list),
        sa.Column("is_active",          sa.Boolean, default=True),
        sa.Column("is_suspended",       sa.Boolean, default=False),
        sa.Column("suspended_at",       sa.DateTime),
        sa.Column("suspension_reason",  sa.String(200)),
        sa.Column("created_at",         sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at",         sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("last_login_at",      sa.DateTime),
    )
    op.create_index("ix_accounts_email", "accounts", ["email"])
    op.create_index("ix_accounts_type_active", "accounts", ["account_type", "is_active"])
    op.create_index("ix_accounts_ide", "accounts", ["ide_number"])

    # ── ANONYMOUS PROFILES ────────────────────────────────────────────────────

    op.create_table(
        "anonymous_profiles",
        sa.Column("id",             sa.String(36), primary_key=True),
        sa.Column("display_id",     sa.String(10),  unique=True),
        sa.Column("account_id",     sa.String(36), sa.ForeignKey("accounts.id"), nullable=False, unique=True),
        sa.Column("profile_type",   account_type_enum, nullable=False),
        sa.Column("mode",           profile_mode_enum, default="shadow"),
        sa.Column("company_mode",   company_mode_enum, default="discreet"),
        sa.Column("postal_zone",    sa.String(4)),
        sa.Column("region_label",   sa.String(100)),
        sa.Column("mobility_km",    sa.Integer, default=50),
        sa.Column("transport_mode", transport_mode_enum, default="car"),
        sa.Column("geo_lat",        sa.Float),
        sa.Column("geo_lon",        sa.Float),
        sa.Column("sector_id",      sa.String(36), sa.ForeignKey("sectors.id")),
        sa.Column("contract_types", sa.JSON, default=list),
        sa.Column("work_rate_min",  sa.SmallInteger, default=100),
        sa.Column("work_rate_max",  sa.SmallInteger, default=100),
        sa.Column("salary_min",     sa.Integer),
        sa.Column("salary_max",     sa.Integer),
        sa.Column("salary_currency",sa.String(3), default="CHF"),
        sa.Column("notice_days",    sa.Integer, default=0),
        sa.Column("notice_label",   sa.String(30)),
        sa.Column("anonymous_recommendations", sa.JSON, default=list),
        sa.Column("is_visible",     sa.Boolean, default=False),
        sa.Column("last_active_at", sa.DateTime),
        sa.Column("shadow_alert_threshold", sa.Integer, default=85),
        sa.Column("created_at",     sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at",     sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_profiles_type_visible", "anonymous_profiles", ["profile_type", "is_visible"])
    op.create_index("ix_profiles_sector",       "anonymous_profiles", ["sector_id"])
    op.create_index("ix_profiles_account",      "anonymous_profiles", ["account_id"])

    # ── PROFILE SKILLS ────────────────────────────────────────────────────────

    op.create_table(
        "profile_skills",
        sa.Column("id",         sa.String(36), primary_key=True),
        sa.Column("profile_id", sa.String(36), sa.ForeignKey("anonymous_profiles.id"), nullable=False),
        sa.Column("skill_id",   sa.String(36), sa.ForeignKey("skills.id"), nullable=False),
        sa.Column("level",      sa.SmallInteger, default=2),
        sa.Column("verified",   sa.Boolean, default=False),
        sa.Column("verified_at",sa.DateTime),
        sa.UniqueConstraint("profile_id", "skill_id", name="uq_profile_skill"),
    )
    op.create_index("ix_profile_skills_profile", "profile_skills", ["profile_id"])

    # ── CULTURE PROFILES ──────────────────────────────────────────────────────

    op.create_table(
        "culture_profiles",
        sa.Column("id",               sa.String(36), primary_key=True),
        sa.Column("profile_id",       sa.String(36), sa.ForeignKey("anonymous_profiles.id"), nullable=False, unique=True),
        sa.Column("quiz_answers",     sa.JSON),
        sa.Column("quiz_dims",        sa.JSON),
        sa.Column("dim_autonomie",    sa.Float, default=0.5),
        sa.Column("dim_structure",    sa.Float, default=0.5),
        sa.Column("dim_collaboration",sa.Float, default=0.5),
        sa.Column("dim_remote",       sa.Float, default=0.5),
        sa.Column("dim_croissance",   sa.Float, default=0.5),
        sa.Column("dim_stabilite",    sa.Float, default=0.5),
        sa.Column("work_style",       sa.String(50)),
        sa.Column("environment",      sa.String(50)),
        sa.Column("motivation",       sa.String(50)),
        sa.Column("completed",        sa.Boolean, default=False),
        sa.Column("completed_at",     sa.DateTime),
    )

    # ── MATCHES ───────────────────────────────────────────────────────────────

    op.create_table(
        "matches",
        sa.Column("id",                 sa.String(36), primary_key=True),
        sa.Column("display_id",         sa.String(10),  unique=True),
        sa.Column("profile_a_id",       sa.String(36), sa.ForeignKey("anonymous_profiles.id"), nullable=False),
        sa.Column("profile_b_id",       sa.String(36), sa.ForeignKey("anonymous_profiles.id"), nullable=False),
        sa.Column("score_total",        sa.Float, nullable=False),
        sa.Column("score_skills",       sa.Float),
        sa.Column("score_culture",      sa.Float),
        sa.Column("score_geo",          sa.Float),
        sa.Column("score_salary",       sa.Float),
        sa.Column("score_durability",   sa.Float),
        sa.Column("distance_km",        sa.Float),
        sa.Column("salary_compatible",  sa.Boolean, default=False),
        sa.Column("matched_skill_ids",  sa.JSON, default=list),
        sa.Column("culture_similarity", sa.Float),
        sa.Column("market_tension_pct", sa.Float),
        sa.Column("market_intel_label", sa.String(200)),
        sa.Column("is_active",          sa.Boolean, default=True),
        sa.Column("ignored_by_a",       sa.Boolean, default=False),
        sa.Column("ignored_by_b",       sa.Boolean, default=False),
        sa.Column("computed_at",        sa.DateTime, server_default=sa.func.now()),
        sa.Column("expires_at",         sa.DateTime),
        sa.UniqueConstraint("profile_a_id", "profile_b_id", name="uq_match_pair"),
    )
    op.create_index("ix_matches_score",  "matches", ["score_total"])
    op.create_index("ix_matches_active", "matches", ["is_active"])
    op.create_index("ix_matches_a",      "matches", ["profile_a_id"])
    op.create_index("ix_matches_b",      "matches", ["profile_b_id"])

    # ── INTEREST SIGNALS ──────────────────────────────────────────────────────

    op.create_table(
        "interest_signals",
        sa.Column("id",          sa.String(36), primary_key=True),
        sa.Column("match_id",    sa.String(36), sa.ForeignKey("matches.id"), nullable=False),
        sa.Column("sender_id",   sa.String(36), sa.ForeignKey("anonymous_profiles.id"), nullable=False),
        sa.Column("receiver_id", sa.String(36), sa.ForeignKey("anonymous_profiles.id"), nullable=False),
        sa.Column("status",      reveal_status_enum, default="pending"),
        sa.Column("sent_at",     sa.DateTime, server_default=sa.func.now()),
        sa.Column("expires_at",  sa.DateTime),
        sa.Column("revealed_at", sa.DateTime),
        sa.Column("reveal_token",sa.String(64)),
        sa.UniqueConstraint("match_id", "sender_id", name="uq_signal_match_sender"),
    )
    op.create_index("ix_signals_match",  "interest_signals", ["match_id"])
    op.create_index("ix_signals_sender", "interest_signals", ["sender_id"])

    # ── INVERSE QUESTIONS ─────────────────────────────────────────────────────

    op.create_table(
        "inverse_questions",
        sa.Column("id",          sa.String(36), primary_key=True),
        sa.Column("match_id",    sa.String(36), sa.ForeignKey("matches.id"), nullable=False),
        sa.Column("asker_id",    sa.String(36), sa.ForeignKey("anonymous_profiles.id"), nullable=False),
        sa.Column("order_num",   sa.SmallInteger, default=1),
        sa.Column("question",    sa.Text, nullable=False),
        sa.Column("answer",      sa.Text),
        sa.Column("asked_at",    sa.DateTime, server_default=sa.func.now()),
        sa.Column("answered_at", sa.DateTime),
    )
    op.create_index("ix_questions_match", "inverse_questions", ["match_id"])

    # ── TRUST EVENTS ──────────────────────────────────────────────────────────

    op.create_table(
        "trust_events",
        sa.Column("id",           sa.String(36), primary_key=True),
        sa.Column("account_id",   sa.String(36), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("event_type",   trust_event_type_enum, nullable=False),
        sa.Column("points_delta", sa.Float, nullable=False),
        sa.Column("reference_id", sa.String(36)),
        sa.Column("note",         sa.String(300)),
        sa.Column("created_at",   sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_trust_account", "trust_events", ["account_id"])
    op.create_index("ix_trust_created", "trust_events", ["created_at"])

    # ── TRUST SCORES ──────────────────────────────────────────────────────────

    op.create_table(
        "trust_scores",
        sa.Column("account_id",               sa.String(36), sa.ForeignKey("accounts.id"), primary_key=True),
        sa.Column("score",                     sa.Float, default=3.0),
        sa.Column("grade",                     trust_grade_enum, default="standard"),
        sa.Column("contacts_total",            sa.Integer, default=0),
        sa.Column("interviews_total",          sa.Integer, default=0),
        sa.Column("offers_total",              sa.Integer, default=0),
        sa.Column("hires_confirmed",           sa.Integer, default=0),
        sa.Column("reports_received",          sa.Integer, default=0),
        sa.Column("hire_rate_pct",             sa.Float, default=0.0),
        sa.Column("consecutive_no_followup",   sa.Integer, default=0),
        sa.Column("suspension_watch",          sa.Boolean, default=False),
        sa.Column("updated_at",                sa.DateTime, server_default=sa.func.now()),
    )

    # ── CREDITS ───────────────────────────────────────────────────────────────

    op.create_table(
        "credit_balances",
        sa.Column("account_id",     sa.String(36), sa.ForeignKey("accounts.id"), primary_key=True),
        sa.Column("balance",        sa.Integer, default=5),
        sa.Column("total_bought",   sa.Integer, default=0),
        sa.Column("total_spent",    sa.Integer, default=0),
        sa.Column("total_refunded", sa.Integer, default=0),
        sa.Column("updated_at",     sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "credit_transactions",
        sa.Column("id",           sa.String(36), primary_key=True),
        sa.Column("account_id",   sa.String(36), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("amount",       sa.Integer, nullable=False),
        sa.Column("type",         sa.String(30)),
        sa.Column("reference_id", sa.String(36)),
        sa.Column("stripe_pi_id", sa.String(50)),
        sa.Column("note",         sa.String(200)),
        sa.Column("created_at",   sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_credits_account", "credit_transactions", ["account_id"])

    # ── OFFBOARDINGS ──────────────────────────────────────────────────────────

    op.create_table(
        "offboardings",
        sa.Column("id",                    sa.String(36), primary_key=True),
        sa.Column("candidate_account_id",  sa.String(36), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("company_account_id",    sa.String(36), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("end_date",              sa.DateTime),
        sa.Column("actual_end_date",       sa.DateTime),
        sa.Column("company_recommendation",   sa.Text),
        sa.Column("candidate_recommendation", sa.Text),
        sa.Column("mutual_consent_reveal",    sa.Boolean, default=False),
        sa.Column("reactivation_date",     sa.DateTime),
        sa.Column("reactivated",           sa.Boolean, default=False),
        sa.Column("reactivated_at",        sa.DateTime),
        sa.Column("managed_well",          sa.Boolean),
        sa.Column("trust_bonus_applied",   sa.Boolean, default=False),
        sa.Column("created_at",            sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_offboarding_candidate",    "offboardings", ["candidate_account_id"])
    op.create_index("ix_offboarding_reactivation", "offboardings", ["reactivation_date", "reactivated"])

    # ── MARKET DATA ───────────────────────────────────────────────────────────

    op.create_table(
        "market_snapshots",
        sa.Column("id",              sa.String(36), primary_key=True),
        sa.Column("sector_id",       sa.String(36), sa.ForeignKey("sectors.id"), nullable=False),
        sa.Column("region_code",     sa.String(10), nullable=False),
        sa.Column("snapshot_month",  sa.String(7),  nullable=False),
        sa.Column("salary_median",   sa.Integer),
        sa.Column("salary_p25",      sa.Integer),
        sa.Column("salary_p75",      sa.Integer),
        sa.Column("sample_size",     sa.Integer, default=0),
        sa.Column("demand_count",    sa.Integer, default=0),
        sa.Column("supply_count",    sa.Integer, default=0),
        sa.Column("tension_pct",     sa.Float, default=0.0),
        sa.Column("median_response_days", sa.Float),
        sa.Column("created_at",      sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("sector_id", "region_code", "snapshot_month", name="uq_snapshot"),
    )
    op.create_index("ix_snapshot_sector_region", "market_snapshots", ["sector_id", "region_code"])

    op.create_table(
        "salary_benchmarks",
        sa.Column("id",               sa.String(36), primary_key=True),
        sa.Column("sector_id",        sa.String(36), sa.ForeignKey("sectors.id"), nullable=False),
        sa.Column("role_label",       sa.String(150), nullable=False),
        sa.Column("region_code",      sa.String(10)),
        sa.Column("experience_years_min", sa.SmallInteger, default=0),
        sa.Column("experience_years_max", sa.SmallInteger),
        sa.Column("salary_min",       sa.Integer),
        sa.Column("salary_median",    sa.Integer),
        sa.Column("salary_max",       sa.Integer),
        sa.Column("currency",         sa.String(3), default="CHF"),
        sa.Column("demand_index",     sa.Float, default=50.0),
        sa.Column("trend_6m_pct",     sa.Float, default=0.0),
        sa.Column("ai_prediction_18m_pct", sa.Float),
        sa.Column("valid_from",       sa.DateTime, server_default=sa.func.now()),
        sa.Column("valid_until",      sa.DateTime),
    )
    op.create_index("ix_benchmark_sector", "salary_benchmarks", ["sector_id"])

    # ── AUDIT LOG ─────────────────────────────────────────────────────────────

    op.create_table(
        "audit_logs",
        sa.Column("id",              sa.String(36), primary_key=True),
        sa.Column("account_id",      sa.String(36), sa.ForeignKey("accounts.id")),
        sa.Column("action",          sa.String(100), nullable=False),
        sa.Column("resource",        sa.String(50)),
        sa.Column("resource_id",     sa.String(36)),
        sa.Column("ip_hash",         sa.String(64)),
        sa.Column("user_agent_hash", sa.String(64)),
        sa.Column("metadata",        sa.JSON, default=dict),
        sa.Column("created_at",      sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_audit_account", "audit_logs", ["account_id"])
    op.create_index("ix_audit_created", "audit_logs", ["created_at"])
    op.create_index("ix_audit_action",  "audit_logs", ["action"])


# ── DOWNGRADE ─────────────────────────────────────────────────────────────────

def downgrade() -> None:
    tables = [
        "audit_logs", "salary_benchmarks", "market_snapshots",
        "offboardings", "credit_transactions", "credit_balances",
        "trust_scores", "trust_events", "inverse_questions",
        "interest_signals", "matches", "culture_profiles",
        "profile_skills", "anonymous_profiles", "accounts",
        "skills", "sectors",
    ]
    for table in tables:
        op.drop_table(table)

    enums = [
        "accounttype", "profilemode", "companymode", "transportmode",
        "trustgrade", "trusteventtype", "revealstatus",
    ]
    for enum in enums:
        sa.Enum(name=enum).drop(op.get_bind(), checkfirst=True)
