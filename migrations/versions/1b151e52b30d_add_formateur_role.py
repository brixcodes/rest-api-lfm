"""add_formateur_role

Revision ID: 1b151e52b30d
Revises: 4ce22dc309ec
Create Date: 2025-08-30 11:44:02.621390

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1b151e52b30d'
down_revision: Union[str, Sequence[str], None] = '4ce22dc309ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Ajouter le rôle FORMATEUR à l'enum roleenum
    op.execute("ALTER TYPE roleenum ADD VALUE 'FORMATEUR'")


def downgrade() -> None:
    """Downgrade schema."""
    # Note: PostgreSQL ne permet pas de supprimer des valeurs d'enum
    # Cette opération ne peut pas être annulée
    pass
