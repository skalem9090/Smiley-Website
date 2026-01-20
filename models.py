from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import json
import secrets

db = SQLAlchemy()

class SearchQuery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    query_text = db.Column(db.String(255), nullable=False)
    results_count = db.Column(db.Integer, nullable=False)
    clicked_result_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationship
    clicked_post = db.relationship('Post', backref='search_clicks')

    def __repr__(self):
        return f"<SearchQuery {self.id} '{self.query_text}'>"


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id', ondelete='CASCADE'), nullable=False)
    author_name = db.Column(db.String(100), nullable=False)
    author_email = db.Column(db.String(120), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_approved = db.Column(db.Boolean, default=False)
    is_spam = db.Column(db.Boolean, default=False)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    approved_at = db.Column(db.DateTime, nullable=True)
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Optional threading support
    parent_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=True)
    replies = db.relationship('Comment', backref=db.backref('parent', remote_side=[id]))
    
    # Relationships
    post = db.relationship('Post', backref=db.backref('comments', cascade='all, delete-orphan'))
    moderator = db.relationship('User', backref='moderated_comments')

    def __repr__(self):
        return f"<Comment {self.id} by {self.author_name}>"


class NewsletterSubscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    is_confirmed = db.Column(db.Boolean, default=False)
    confirmation_token = db.Column(db.String(100), unique=True, nullable=True)
    frequency = db.Column(db.String(20), default='weekly')  # weekly, biweekly, monthly
    subscribed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    confirmed_at = db.Column(db.DateTime, nullable=True)
    last_email_sent = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    unsubscribe_token = db.Column(db.String(100), unique=True, nullable=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.unsubscribe_token:
            self.unsubscribe_token = secrets.token_urlsafe(32)
        if not self.confirmation_token:
            self.confirmation_token = secrets.token_urlsafe(32)

    def generate_confirmation_token(self):
        """Generate a new confirmation token."""
        self.confirmation_token = secrets.token_urlsafe(32)
        return self.confirmation_token

    def generate_unsubscribe_token(self):
        """Generate a new unsubscribe token."""
        self.unsubscribe_token = secrets.token_urlsafe(32)
        return self.unsubscribe_token

    def __repr__(self):
        return f"<NewsletterSubscription {self.id} {self.email}>"


class AuthorProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    bio = db.Column(db.Text, nullable=False)
    mission_statement = db.Column(db.Text, nullable=False)
    expertise_areas = db.Column(db.Text, nullable=False)  # JSON array
    profile_image = db.Column(db.String(255), nullable=True)
    email = db.Column(db.String(120), nullable=False)
    twitter_handle = db.Column(db.String(50), nullable=True)
    linkedin_url = db.Column(db.String(255), nullable=True)
    github_url = db.Column(db.String(255), nullable=True)
    website_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def get_expertise_areas(self):
        """Get expertise areas as a list."""
        try:
            return json.loads(self.expertise_areas) if self.expertise_areas else []
        except (json.JSONDecodeError, TypeError):
            return []

    def set_expertise_areas(self, areas_list):
        """Set expertise areas from a list."""
        self.expertise_areas = json.dumps(areas_list) if areas_list else '[]'

    def __repr__(self):
        return f"<AuthorProfile {self.id} {self.name}>"


# Association table for many-to-many relationship between Post and Tag
post_tags = db.Table('post_tags',
    db.Column('post_id', db.Integer, db.ForeignKey('post.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)


class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Tag {self.id} {self.name}>"


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)  # Increased from 128 to 256 for scrypt hashes
    is_admin = db.Column(db.Boolean, default=False)
    
    # Security fields for account lockout
    failed_login_attempts = db.Column(db.Integer, nullable=False, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    last_login_at = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_locked(self) -> bool:
        """Check if account is currently locked"""
        if self.locked_until is None:
            return False
        # Ensure both datetimes are timezone-aware for comparison
        now = datetime.now(timezone.utc)
        locked_until = self.locked_until
        if locked_until.tzinfo is None:
            # If locked_until is naive, assume it's UTC
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        return now < locked_until
    
    def reset_failed_attempts(self) -> None:
        """Reset failed login attempt counter"""
        self.failed_login_attempts = 0
        self.locked_until = None
    
    @property
    def two_factor_enabled(self) -> bool:
        """Check if two-factor authentication is enabled for this user"""
        return self.two_factor_auth is not None and self.two_factor_auth.enabled
    
    @property
    def backup_codes_remaining(self) -> int:
        """Get the number of remaining backup codes"""
        if not self.two_factor_auth or not self.two_factor_auth.backup_codes:
            return 0
        try:
            import json
            codes = json.loads(self.two_factor_auth.backup_codes)
            return len(codes) if isinstance(codes, list) else 0
        except (json.JSONDecodeError, TypeError):
            return 0


class LoginAttempt(db.Model):
    """Records login attempts for security monitoring"""
    
    __tablename__ = 'login_attempts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    username = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(45), nullable=False)  # IPv6 compatible
    success = db.Column(db.Boolean, nullable=False)
    failure_reason = db.Column(db.String(200), nullable=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # Relationship
    user = db.relationship('User', backref='login_attempts')
    
    # Indexes for query performance
    __table_args__ = (
        db.Index('idx_login_attempts_timestamp', 'timestamp'),
        db.Index('idx_login_attempts_username', 'username'),
        db.Index('idx_login_attempts_ip', 'ip_address'),
    )
    
    def __repr__(self):
        return f"<LoginAttempt {self.id} {self.username} {'success' if self.success else 'failed'}>"


class AuditLog(db.Model):
    """Records administrative actions for compliance"""
    
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    username = db.Column(db.String(100), nullable=False)
    action_type = db.Column(db.String(50), nullable=False)
    details = db.Column(db.Text, nullable=True)  # JSON string
    ip_address = db.Column(db.String(45), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # Relationship
    user = db.relationship('User', backref='audit_logs')
    
    # Indexes for query performance
    __table_args__ = (
        db.Index('idx_audit_logs_timestamp', 'timestamp'),
        db.Index('idx_audit_logs_user', 'user_id'),
        db.Index('idx_audit_logs_action', 'action_type'),
    )
    
    def __repr__(self):
        return f"<AuditLog {self.id} {self.username} {self.action_type}>"


class TwoFactorAuth(db.Model):
    """Stores two-factor authentication data"""
    
    __tablename__ = 'two_factor_auth'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    secret = db.Column(db.String(32), nullable=False)  # Base32 encoded
    enabled = db.Column(db.Boolean, nullable=False, default=False)
    backup_codes = db.Column(db.Text, nullable=True)  # JSON array of hashed codes
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    last_used = db.Column(db.DateTime, nullable=True)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('two_factor_auth', uselist=False))
    
    def __repr__(self):
        return f"<TwoFactorAuth {self.id} user_id={self.user_id} enabled={self.enabled}>"


class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    mime_type = db.Column(db.String(50), nullable=False)
    upload_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=True)

    def __repr__(self):
        return f"<Image {self.id} {self.filename}>"


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text, nullable=True)  # New: Manual or auto-generated excerpt
    category = db.Column(db.String(50), nullable=True)
    tags = db.Column(db.String(200), nullable=True)  # Legacy: comma-separated tags (to be migrated)
    status = db.Column(db.String(20), default='draft', nullable=False)  # New: draft, published, scheduled
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    published_at = db.Column(db.DateTime, nullable=True)  # New: Actual publication timestamp
    scheduled_publish_at = db.Column(db.DateTime, nullable=True)  # New: Scheduled publication time
    
    # Relationships
    tag_relationships = db.relationship('Tag', secondary=post_tags, backref='posts')
    images = db.relationship('Image', backref='post', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Post {self.id} {self.title}>"
