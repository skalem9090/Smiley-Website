"""Add Comment model for comment system with moderation

Revision ID: add_comment_model
Revises: add_newsletter_subscription
Create Date: 2026-01-17 16:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_comment_model'
down_revision = 'add_newsletter_subscription'
branch_labels = None
depends_on = None


def upgrade():
    # Create Comment table
    op.create_table('comment',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('author_name', sa.String(length=100), nullable=False),
        sa.Column('author_email', sa.String(length=120), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_approved', sa.Boolean(), nullable=True),
        sa.Column('is_spam', sa.Boolean(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('approved_by', sa.Integer(), nullable=True),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['approved_by'], ['user.id'], ),
        sa.ForeignKeyConstraint(['parent_id'], ['comment.id'], ),
        sa.ForeignKeyConstraint(['post_id'], ['post.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    # Drop Comment table
    op.drop_table('comment')