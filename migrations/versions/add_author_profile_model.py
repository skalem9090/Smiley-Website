"""Add AuthorProfile model for about page and author information

Revision ID: add_author_profile
Revises: f3e711160b2c
Create Date: 2026-01-17 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_author_profile'
down_revision = 'f3e711160b2c'
branch_labels = None
depends_on = None


def upgrade():
    # Create AuthorProfile table
    op.create_table('author_profile',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('bio', sa.Text(), nullable=False),
        sa.Column('mission_statement', sa.Text(), nullable=False),
        sa.Column('expertise_areas', sa.Text(), nullable=False),
        sa.Column('profile_image', sa.String(length=255), nullable=True),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('twitter_handle', sa.String(length=50), nullable=True),
        sa.Column('linkedin_url', sa.String(length=255), nullable=True),
        sa.Column('github_url', sa.String(length=255), nullable=True),
        sa.Column('website_url', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    # Drop AuthorProfile table
    op.drop_table('author_profile')