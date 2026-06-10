"""
UMBRA — Migration: add accounts.current_employer_ide
Revision: 0003_current_employer_ide
Down: 0002_magic_tokens

Ajoute le champ `current_employer_ide` sur accounts. Cet IDE (employeur actuel
déclaré par le candidat) est injecté automatiquement dans la block-list de matching,
garantissant qu'un employeur ne peut jamais débusquer ses propres salariés en veille
via un faux poste. Garde-fou anti-désanonymisation (engagement légal UMBRA).
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_current_employer_ide"
down_revision = "0002_magic_tokens"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "accounts",
        sa.Column("current_employer_ide", sa.String(length=15), nullable=True),
    )


def downgrade():
    op.drop_column("accounts", "current_employer_ide")
