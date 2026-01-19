from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, PasswordField, TextAreaField, SelectField, MultipleFileField, DateTimeLocalField
from wtforms.validators import DataRequired, Length, Optional, Email, Regexp
import re

# Custom email validator that doesn't require external dependencies
def simple_email_validator(form, field):
    """Simple email validation without external dependencies."""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, field.data):
        raise ValueError('Please enter a valid email address')


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(max=80)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6, max=128)])


class ImageUploadForm(FlaskForm):
    """Form for uploading images with validation."""
    image = FileField('Image', validators=[
        FileRequired(message='Please select an image file'),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 
                   message='Only JPEG, PNG, and GIF files are allowed')
    ])


class AuthorProfileForm(FlaskForm):
    """Form for managing author profile information."""
    name = StringField('Name', validators=[
        DataRequired(message='Name is required'), 
        Length(min=1, max=100, message='Name must be between 1 and 100 characters')
    ])
    bio = TextAreaField('Bio', validators=[
        DataRequired(message='Bio is required'),
        Length(min=10, max=1000, message='Bio must be between 10 and 1000 characters')
    ], description='Tell visitors about yourself and your background.')
    mission_statement = TextAreaField('Mission Statement', validators=[
        DataRequired(message='Mission statement is required'),
        Length(min=10, max=1000, message='Mission statement must be between 10 and 1000 characters')
    ], description='Describe your mission and what you hope to achieve with your blog.')
    expertise_areas = StringField('Areas of Expertise', validators=[
        Optional(),
        Length(max=500, message='Expertise areas cannot exceed 500 characters')
    ], description='Comma-separated list of your areas of expertise (e.g., Technology, Writing, Health)')
    email = StringField('Email', validators=[
        DataRequired(message='Email is required'),
        simple_email_validator,
        Length(max=120, message='Email cannot exceed 120 characters')
    ])
    twitter_handle = StringField('Twitter Handle', validators=[
        Optional(),
        Length(max=50, message='Twitter handle cannot exceed 50 characters')
    ], description='Your Twitter username (with or without @)')
    linkedin_url = StringField('LinkedIn URL', validators=[
        Optional(),
        Length(max=255, message='LinkedIn URL cannot exceed 255 characters')
    ], description='Full URL to your LinkedIn profile')
    github_url = StringField('GitHub URL', validators=[
        Optional(),
        Length(max=255, message='GitHub URL cannot exceed 255 characters')
    ], description='Full URL to your GitHub profile')
    website_url = StringField('Website URL', validators=[
        Optional(),
        Length(max=255, message='Website URL cannot exceed 255 characters')
    ], description='Full URL to your personal website')
    profile_image = FileField('Profile Image', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 
                   message='Only JPEG, PNG, and GIF files are allowed')
    ], description='Upload a profile photo (max 5MB)')


class PostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=200)])
    category = SelectField('Category', choices=[('wealth', 'Wealth'), ('health', 'Health'), ('happiness', 'Happiness')], validators=[DataRequired()])
    tags = StringField('Tags', validators=[Length(max=200)])
    content = TextAreaField('Content', validators=[DataRequired(), Length(min=1)])
    summary = TextAreaField('Summary', validators=[
        Optional(), 
        Length(max=200, message='Summary cannot exceed 200 characters')
    ], description='Optional summary or excerpt. If left blank, one will be generated automatically from the content.')
    status = SelectField('Status', choices=[
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('scheduled', 'Scheduled')
    ], default='draft', validators=[DataRequired()])
    scheduled_time = DateTimeLocalField('Scheduled Publication Time', validators=[
        Optional()
    ], description='Required when status is set to "Scheduled"')
    images = MultipleFileField('Images', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 
                   message='Only JPEG, PNG, and GIF files are allowed')
    ])


class NewsletterSubscriptionForm(FlaskForm):
    """Form for newsletter subscription."""
    email = StringField('Email Address', validators=[
        DataRequired(message='Email address is required'),
        simple_email_validator,
        Length(max=120, message='Email address cannot exceed 120 characters')
    ])
    frequency = SelectField('Frequency', choices=[
        ('weekly', 'Weekly'),
        ('bi-weekly', 'Bi-weekly'),
        ('monthly', 'Monthly')
    ], default='weekly', validators=[DataRequired()])


class NewsletterUnsubscribeForm(FlaskForm):
    """Form for newsletter unsubscription confirmation."""
    confirm = SelectField('Confirm Unsubscription', choices=[
        ('no', 'No, keep me subscribed'),
        ('yes', 'Yes, unsubscribe me')
    ], default='no', validators=[DataRequired()])


class NewsletterFrequencyUpdateForm(FlaskForm):
    """Form for updating newsletter frequency."""
    frequency = SelectField('Email Frequency', choices=[
        ('weekly', 'Weekly'),
        ('bi-weekly', 'Bi-weekly'),
        ('monthly', 'Monthly')
    ], validators=[DataRequired()])


class CommentForm(FlaskForm):
    """Form for submitting comments on blog posts."""
    author_name = StringField('Name', validators=[
        DataRequired(message='Name is required'),
        Length(min=1, max=100, message='Name must be between 1 and 100 characters')
    ])
    author_email = StringField('Email', validators=[
        DataRequired(message='Email is required'),
        simple_email_validator,
        Length(max=120, message='Email cannot exceed 120 characters')
    ], description='Your email will not be published')
    content = TextAreaField('Comment', validators=[
        DataRequired(message='Comment content is required'),
        Length(min=1, max=2000, message='Comment must be between 1 and 2000 characters')
    ], description='Share your thoughts on this post')


class CommentModerationForm(FlaskForm):
    """Form for moderating comments in the dashboard."""
    action = SelectField('Action', choices=[
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('spam', 'Mark as Spam'),
        ('delete', 'Delete')
    ], validators=[DataRequired()])


class BulkCommentModerationForm(FlaskForm):
    """Form for bulk comment moderation actions."""
    action = SelectField('Bulk Action', choices=[
        ('', 'Select Action'),
        ('approve', 'Approve Selected'),
        ('reject', 'Reject Selected'),
        ('spam', 'Mark as Spam'),
        ('delete', 'Delete Selected')
    ], validators=[DataRequired(message='Please select an action')])