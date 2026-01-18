from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, PasswordField, TextAreaField, SelectField, MultipleFileField, DateTimeLocalField
from wtforms.validators import DataRequired, Length, Optional, Email


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
        Email(message='Please enter a valid email address'),
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
