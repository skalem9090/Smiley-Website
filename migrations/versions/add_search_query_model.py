"""Add SearchQuery model for search analytics

Revision ID: add_search_query_model
Revises: add_comment_model
Create Date: 2026-01-17 16:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_search_query_model'
down_revision = 'add_comment_model'
branch_labels = None
depends_on = None


def upgrade():
    # Create SearchQuery table
    op.create_table('search_query',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('query_text', sa.String(length=255), nullable=False),
        sa.Column('results_count', sa.Integer(), nullable=False),
        sa.Column('clicked_result_id', sa.Integer(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['clicked_result_id'], ['post.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    # Drop SearchQuery table
    op.drop_table('search_query')