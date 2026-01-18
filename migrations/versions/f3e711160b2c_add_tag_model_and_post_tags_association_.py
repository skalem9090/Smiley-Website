"""Add Tag model and post_tags association table

Revision ID: f3e711160b2c
Revises: 2cbdb1f2cfa3
Create Date: 2026-01-17 14:36:09.105906

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f3e711160b2c'
down_revision = '2cbdb1f2cfa3'
branch_labels = None
depends_on = None


def upgrade():
    # Create Tag table
    op.create_table('tag',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('slug', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('slug')
    )
    
    # Create post_tags association table
    op.create_table('post_tags',
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('tag_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['post_id'], ['post.id'], ),
        sa.ForeignKeyConstraint(['tag_id'], ['tag.id'], ),
        sa.PrimaryKeyConstraint('post_id', 'tag_id')
    )


def downgrade():
    # Drop post_tags association table
    op.drop_table('post_tags')
    
    # Drop Tag table
    op.drop_table('tag')
