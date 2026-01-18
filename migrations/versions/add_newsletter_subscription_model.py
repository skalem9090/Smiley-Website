"""Add NewsletterSubscription model for email subscription system

Revision ID: add_newsletter_subscription
Revises: add_author_profile
Create Date: 2026-01-17 16:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_newsletter_subscription'
down_revision = 'add_author_profile'
branch_labels = None
depends_on = None


def upgrade():
    # Create NewsletterSubscription table
    op.create_table('newsletter_subscription',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('is_confirmed', sa.Boolean(), nullable=True),
        sa.Column('confirmation_token', sa.String(length=100), nullable=True),
        sa.Column('frequency', sa.String(length=20), nullable=True),
        sa.Column('subscribed_at', sa.DateTime(), nullable=True),
        sa.Column('confirmed_at', sa.DateTime(), nullable=True),
        sa.Column('last_email_sent', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('unsubscribe_token', sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('confirmation_token'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('unsubscribe_token')
    )


def downgrade():
    # Drop NewsletterSubscription table
    op.drop_table('newsletter_subscription')