"""increase password_hash length

Revision ID: increase_password_hash
Revises: add_security_models
Create Date: 2026-01-20 22:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'increase_password_hash'
down_revision = 'add_security_models'
branch_labels = None
depends_on = None


def upgrade():
    # Increase password_hash column length from 128 to 256
    op.alter_column('user', 'password_hash',
                    existing_type=sa.String(length=128),
                    type_=sa.String(length=256),
                    existing_nullable=False)


def downgrade():
    # Revert password_hash column length from 256 to 128
    op.alter_column('user', 'password_hash',
                    existing_type=sa.String(length=256),
                    type_=sa.String(length=128),
                    existing_nullable=False)
