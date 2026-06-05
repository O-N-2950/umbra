"""
UMBRA — Migration: add magic_tokens table
Revision: 0002_magic_tokens
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_magic_tokens"
down_revision = "0001_umbra_init"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "magic_tokens",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("account_id", sa.String(36), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("used", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_magic_tokens_account_id", "magic_tokens", ["account_id"])
    op.create_index("ix_magic_tokens_expires_at", "magic_tokens", ["expires_at"])

def downgrade():
    op.drop_table("magic_tokens")
