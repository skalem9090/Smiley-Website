"""Add security models for hardening

Revision ID: add_security_models
Revises: fd8c8a944542
Create Date: 2026-01-20

This migration adds security-related tables and fields:
- LoginAttempt table for tracking login attempts
- AuditLog table for tracking administrative actions
- TwoFactorAuth table for 2FA support
- User model extensions for account lockout
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_security_models'
down_revision = 'fd8c8a944542'
branch_labels = None
depends_on = None


def upgrade():
    # Add fields to User table
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('locked_until', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('last_login_at', sa.DateTime(), nullable=True))
    
    # Create LoginAttempt table
    op.create_table('login_attempts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('failure_reason', sa.String(length=200), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_login_attempts_timestamp', 'login_attempts', ['timestamp'], unique=False)
    op.create_index('idx_login_attempts_username', 'login_attempts', ['username'], unique=False)
    op.create_index('idx_login_attempts_ip', 'login_attempts', ['ip_address'], unique=False)
    
    # Create AuditLog table
    op.create_table('audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('action_type', sa.String(length=50), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_audit_logs_timestamp', 'audit_logs', ['timestamp'], unique=False)
    op.create_index('idx_audit_logs_user', 'audit_logs', ['user_id'], unique=False)
    op.create_index('idx_audit_logs_action', 'audit_logs', ['action_type'], unique=False)
    
    # Create TwoFactorAuth table
    op.create_table('two_factor_auth',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('secret', sa.String(length=32), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('backup_codes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_used', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )


def downgrade():
    # Drop TwoFactorAuth table
    op.drop_table('two_factor_auth')
    
    # Drop AuditLog table
    op.drop_index('idx_audit_logs_action', table_name='audit_logs')
    op.drop_index('idx_audit_logs_user', table_name='audit_logs')
    op.drop_index('idx_audit_logs_timestamp', table_name='audit_logs')
    op.drop_table('audit_logs')
    
    # Drop LoginAttempt table
    op.drop_index('idx_login_attempts_ip', table_name='login_attempts')
    op.drop_index('idx_login_attempts_username', table_name='login_attempts')
    op.drop_index('idx_login_attempts_timestamp', table_name='login_attempts')
    op.drop_table('login_attempts')
    
    # Remove fields from User table
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('last_login_at')
        batch_op.drop_column('locked_until')
        batch_op.drop_column('failed_login_attempts')
