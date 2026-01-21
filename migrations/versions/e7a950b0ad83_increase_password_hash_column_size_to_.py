"""Increase password_hash column size to 256

Revision ID: e7a950b0ad83
Revises: increase_password_hash
Create Date: 2026-01-21 12:42:17.653666

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e7a950b0ad83'
down_revision = 'increase_password_hash'
branch_labels = None
depends_on = None


def upgrade():
    # Increase password_hash column size from 128 to 256
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('password_hash',
                              existing_type=sa.String(length=128),
                              type_=sa.String(length=256),
                              existing_nullable=False)


def downgrade():
    # Revert password_hash column size back to 128
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('password_hash',
                              existing_type=sa.String(length=256),
                              type_=sa.String(length=128),
                              existing_nullable=False)
