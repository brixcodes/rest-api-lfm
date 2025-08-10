"""add user contact and address fields

Revision ID: 8b3a1c4d6e7f
Revises: 2a7a2092a0ce
Create Date: 2025-08-10

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '8b3a1c4d6e7f'
down_revision = '2a7a2092a0ce'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('utilisateurs', sa.Column('telephone', sa.String(length=30), nullable=True))
    op.add_column('utilisateurs', sa.Column('nationalite', sa.String(length=100), nullable=True))
    op.add_column('utilisateurs', sa.Column('pays', sa.String(length=100), nullable=True))
    op.add_column('utilisateurs', sa.Column('region', sa.String(length=100), nullable=True))
    op.add_column('utilisateurs', sa.Column('ville', sa.String(length=100), nullable=True))
    op.add_column('utilisateurs', sa.Column('adresse', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('utilisateurs', 'adresse')
    op.drop_column('utilisateurs', 'ville')
    op.drop_column('utilisateurs', 'region')
    op.drop_column('utilisateurs', 'pays')
    op.drop_column('utilisateurs', 'nationalite')
    op.drop_column('utilisateurs', 'telephone')

