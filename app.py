import os
from datetime import timedelta, datetime, timezone
from flask import Flask, render_template, request, redirect, url_for, flash, abort, jsonify, send_from_directory
from flask_wtf import CSRFProtect
import bleach
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not found. Using system environment variables only.")
    pass

from models import db, User, Post, Tag, AuthorProfile, NewsletterSubscription, Comment, SearchQuery, Image
from forms import LoginForm, PostForm, ImageUploadForm, CommentForm, CommentModerationForm, BulkCommentModerationForm
from image_handler import ImageHandler
from schedule_manager import ScheduleManager
from about_page_manager import AboutPageManager
from feed_generator import FeedGenerator
from comment_manager import CommentManager
from seo_manager import SEOManager


def get_content_sanitization_config():
    """Get configuration for content sanitization."""
    ALLOWED_TAGS = [
        'a', 'abbr', 'b', 'blockquote', 'br', 'code', 'em', 'i', 'li', 'ol', 'p', 'strong', 'ul', 'h1', 'h2', 'h3', 'h4', 'img'
    ]
    ALLOWED_ATTRIBUTES = {
        'a': ['href', 'title', 'rel', 'target'],
        'img': ['src', 'alt', 'title', 'width', 'height', 'style', 'class']
    }
    return ALLOWED_TAGS, ALLOWED_ATTRIBUTES


def sanitize_content(content):
    """Sanitize HTML content for safe storage."""
    ALLOWED_TAGS, ALLOWED_ATTRIBUTES = get_content_sanitization_config()
    return bleach.clean(
        content or '',
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True
    )


def create_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', f'sqlite:///{os.path.abspath("instance/site.db")}')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Configure upload settings
    app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', 'static/uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    
    # Ensure upload directory exists
    upload_folder = app.config['UPLOAD_FOLDER']
    os.makedirs(upload_folder, exist_ok=True)

    db.init_app(app)

    # Initialize Flask-Migrate
    migrate = Migrate(app, db)

    # CSRF protection for all forms
    csrf = CSRFProtect(app)

    login_manager = LoginManager()
    login_manager.login_view = 'login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Ensure database tables exist and optionally create initial admin
    with app.app_context():
        db.create_all()
        if User.query.count() == 0:
            admin_user = os.environ.get('ADMIN_USER')
            admin_pass = os.environ.get('ADMIN_PASSWORD')
            if admin_user and admin_pass:
                u = User(username=admin_user, is_admin=True)
                u.set_password(admin_pass)
                db.session.add(u)
                db.session.commit()
        
        # Initialize search engine
        from search_engine import SearchEngine
        search_engine = SearchEngine(app)
        try:
            search_engine.create_search_index()
            app.logger.info("Search engine initialized successfully")
        except Exception as e:
            app.logger.error(f"Error initializing search engine: {str(e)}")

    # Initialize and start background scheduler
    scheduler = ScheduleManager(app)
    scheduler.start()
    
    # Initialize SEO Manager
    seo_manager = SEOManager(app)
    
    # Helper function to invalidate sitemap cache when content changes
    def invalidate_sitemap_cache():
        """Invalidate sitemap cache when content changes."""
        # This could be extended to use Redis or other caching mechanisms
        # For now, we rely on ETag-based caching in the sitemap route
        pass

    # Custom template filters
    @app.template_filter('nl2br')
    def nl2br_filter(text):
        """Convert newlines to HTML line breaks."""
        if not text:
            return text
        return text.replace('\n', '<br>\n')

    @app.route('/')
    def index():
        # Show latest published posts for three main site heads/categories
        wealth_posts = Post.query.filter(Post.category.ilike('wealth'), Post.status == 'published').order_by(Post.created_at.desc()).limit(5).all()
        health_posts = Post.query.filter(Post.category.ilike('health'), Post.status == 'published').order_by(Post.created_at.desc()).limit(5).all()
        happiness_posts = Post.query.filter(Post.category.ilike('happiness'), Post.status == 'published').order_by(Post.created_at.desc()).limit(5).all()
        
        # Generate SEO data for homepage
        seo_meta = seo_manager.generate_meta_tags(page_type='website')
        og_tags = seo_manager.generate_open_graph_tags(page_type='website')
        structured_data = seo_manager.generate_structured_data(page_type='WebSite')
        
        return render_template('index.html', 
                             wealth_posts=wealth_posts, 
                             health_posts=health_posts, 
                             happiness_posts=happiness_posts,
                             seo_meta=seo_meta,
                             og_tags=og_tags,
                             structured_data=structured_data)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        form = LoginForm()
        if form.validate_on_submit():
            username = form.username.data.strip()
            password = form.password.data
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                if not user.is_admin:
                    flash('Unauthorized: developer access only', 'danger')
                else:
                    login_user(user)
                    return redirect(request.args.get('next') or url_for('index'))
            else:
                flash('Invalid credentials', 'danger')
        return render_template('login.html', form=form)

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('index'))

    @app.route('/about')
    def about():
        """About page displaying author information and mission."""
        about_manager = AboutPageManager(app)
        profile = about_manager.get_author_profile()
        social_links = about_manager.get_social_links()
        profile_image_url = about_manager.get_profile_image_url()
        
        # Generate SEO data for about page
        seo_meta = seo_manager.generate_meta_tags(page_type='about', content=profile)
        og_tags = seo_manager.generate_open_graph_tags(page_type='profile', content=profile)
        structured_data = seo_manager.generate_structured_data(page_type='Person', content=profile)
        
        return render_template('about.html', 
                             profile=profile, 
                             social_links=social_links,
                             profile_image_url=profile_image_url,
                             seo_meta=seo_meta,
                             og_tags=og_tags,
                             structured_data=structured_data)

    @app.route('/dashboard', methods=['GET', 'POST'])
    @login_required
    def dashboard():
        from post_manager import PostManager
        from datetime import datetime
        
        form = PostForm()
        if form.validate_on_submit():
            title = form.title.data.strip()
            category = (form.category.data or '').strip() or None
            tags_str = (form.tags.data or '').strip()
            summary = (form.summary.data or '').strip() or None
            status = form.status.data
            scheduled_time = form.scheduled_time.data
            
            # Parse tags into list
            tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()] if tags_str else []
            
            # Validate scheduled time for scheduled posts
            if status == 'scheduled' and not scheduled_time:
                flash('Scheduled posts must have a scheduled publication time.', 'danger')
                return render_template('dashboard.html', form=form, posts=PostManager.get_posts_organized_by_status())
            
            # Sanitize content for safe storage
            cleaned_content = sanitize_content(form.content.data)
            
            try:
                # Create post using PostManager
                post = PostManager.create_post(
                    title=title,
                    content=cleaned_content,
                    category=category,
                    summary=summary,
                    status=status,
                    scheduled_time=scheduled_time,
                    tags=tags
                )
                
                # Handle image uploads
                image_handler = ImageHandler()
                uploaded_images = []
                
                if form.images.data:
                    for image_file in form.images.data:
                        if image_file and image_file.filename:
                            success, message, image_record = image_handler.save_image(image_file, post.id)
                            if success:
                                uploaded_images.append(image_record)
                            else:
                                flash(f"Error uploading {image_file.filename}: {message}", 'warning')
                
                # Success message based on status
                status_msg = {
                    'draft': 'saved as draft',
                    'published': 'published successfully',
                    'scheduled': f'scheduled for publication on {scheduled_time.strftime("%Y-%m-%d at %H:%M")}' if scheduled_time else 'scheduled for publication'
                }.get(status, 'created')
                
                if uploaded_images:
                    flash(f"Post {status_msg} with {len(uploaded_images)} image(s) uploaded.", 'success')
                else:
                    flash(f"Post {status_msg}.", 'success')
                    
                return redirect(url_for('post_view', post_id=post.id))
                
            except ValueError as e:
                flash(str(e), 'danger')
                return render_template('dashboard.html', form=form, posts=PostManager.get_posts_organized_by_status())
        
        # Get organized posts for dashboard display
        organized_posts = PostManager.get_posts_organized_by_status()
        return render_template('dashboard.html', form=form, posts=organized_posts)


    @app.route('/dashboard/edit/<int:post_id>', methods=['GET', 'POST'])
    @login_required
    def edit_post(post_id):
        from post_manager import PostManager
        from tag_manager import TagManager
        
        post = Post.query.get_or_404(post_id)
        if not current_user.is_admin:
            abort(403)
        
        form = PostForm()
        if form.validate_on_submit():
            title = form.title.data.strip()
            category = (form.category.data or '').strip() or None
            tags_str = (form.tags.data or '').strip()
            summary = (form.summary.data or '').strip() or None
            status = form.status.data
            scheduled_time = form.scheduled_time.data
            
            # Parse tags into list
            tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()] if tags_str else []
            
            # Validate scheduled time for scheduled posts
            if status == 'scheduled' and not scheduled_time:
                flash('Scheduled posts must have a scheduled publication time.', 'danger')
                return render_template('edit_post.html', form=form, post=post)
            
            # Sanitize content for safe storage
            cleaned_content = sanitize_content(form.content.data)
            
            try:
                # Update post using PostManager
                updated_post = PostManager.update_post(
                    post_id=post.id,
                    title=title,
                    content=cleaned_content,
                    category=category,
                    summary=summary,
                    status=status,
                    scheduled_time=scheduled_time,
                    tags=tags
                )
                
                if not updated_post:
                    flash('Post not found.', 'danger')
                    return redirect(url_for('dashboard'))
                
                # Handle new image uploads
                image_handler = ImageHandler()
                uploaded_images = []
                
                if form.images.data:
                    for image_file in form.images.data:
                        if image_file and image_file.filename:
                            success, message, image_record = image_handler.save_image(image_file, post.id)
                            if success:
                                uploaded_images.append(image_record)
                            else:
                                flash(f"Error uploading {image_file.filename}: {message}", 'warning')
                
                # Success message based on status
                status_msg = {
                    'draft': 'saved as draft',
                    'published': 'published successfully',
                    'scheduled': f'scheduled for publication on {scheduled_time.strftime("%Y-%m-%d at %H:%M")}' if scheduled_time else 'scheduled for publication'
                }.get(status, 'updated')
                
                if uploaded_images:
                    flash(f"Post {status_msg} with {len(uploaded_images)} new image(s) uploaded.", 'success')
                else:
                    flash(f"Post {status_msg}.", 'success')
                    
                return redirect(url_for('post_view', post_id=post.id))
                
            except ValueError as e:
                flash(str(e), 'danger')
                return render_template('edit_post.html', form=form, post=post)
        
        # Pre-fill the form fields for GET
        if request.method == 'GET':
            form.title.data = post.title
            form.category.data = post.category or ''
            form.content.data = post.content or ''
            form.summary.data = post.summary or ''
            form.status.data = post.status or 'draft'
            form.scheduled_time.data = post.scheduled_publish_at
            
            # Get tags as comma-separated string
            if hasattr(post, 'tag_relationships') and post.tag_relationships:
                tag_names = [rel.tag.name for rel in post.tag_relationships]
                form.tags.data = ', '.join(tag_names)
            else:
                # Fallback to legacy tags field
                form.tags.data = post.tags or ''
                
        return render_template('edit_post.html', form=form, post=post)


    @app.route('/dashboard/delete/<int:post_id>', methods=['POST'])
    @login_required
    def delete_post(post_id):
        post = Post.query.get_or_404(post_id)
        if not current_user.is_admin:
            abort(403)
        
        # Use no_autoflush to prevent premature flushes
        with db.session.no_autoflush:
            # First delete all comments associated with this post
            comments_to_delete = Comment.query.filter_by(post_id=post_id).all()
            for comment in comments_to_delete:
                db.session.delete(comment)
            
            # Then delete the post
            db.session.delete(post)
        
        try:
            db.session.commit()
            flash('Post and associated comments deleted successfully', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error deleting post: {str(e)}', 'danger')
        
        return redirect(url_for('dashboard'))

    @app.route('/dashboard/bulk-action', methods=['POST'])
    @login_required
    def bulk_action():
        """Handle bulk actions on multiple posts."""
        from post_manager import PostManager
        
        if not current_user.is_admin:
            abort(403)
        
        action = request.form.get('action')
        post_ids = request.form.getlist('post_ids')
        
        if not action or not post_ids:
            flash('No action or posts selected.', 'warning')
            return redirect(url_for('dashboard'))
        
        try:
            post_ids = [int(pid) for pid in post_ids]
        except ValueError:
            flash('Invalid post selection.', 'danger')
            return redirect(url_for('dashboard'))
        
        if action == 'delete':
            # Delete selected posts and their associated comments
            deleted_count = 0
            
            # Use no_autoflush to prevent premature flushes
            with db.session.no_autoflush:
                for post_id in post_ids:
                    post = db.session.get(Post, post_id)
                    if post:
                        # First delete all comments associated with this post
                        comments_to_delete = Comment.query.filter_by(post_id=post_id).all()
                        for comment in comments_to_delete:
                            db.session.delete(comment)
                        
                        # Then delete the post
                        db.session.delete(post)
                        deleted_count += 1
            
            try:
                db.session.commit()
                flash(f'Successfully deleted {deleted_count} post(s) and their associated comments.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error deleting posts: {str(e)}', 'danger')
        
        elif action in ['draft', 'published', 'scheduled']:
            # Bulk status change
            result = PostManager.bulk_update_status(post_ids, action)
            
            if result['success']:
                flash(f'Successfully updated {result["updated_count"]} post(s) to {action}.', 'success')
            else:
                flash(f'Updated {result["updated_count"]} post(s). Errors: {"; ".join(result["errors"])}', 'warning')
        
        else:
            flash('Invalid bulk action.', 'danger')
        
        return redirect(url_for('dashboard'))

    @app.route('/dashboard/author-profile', methods=['GET', 'POST'])
    @login_required
    def author_profile_management():
        """Author profile management interface."""
        if not current_user.is_admin:
            abort(403)
        
        from forms import AuthorProfileForm
        
        about_manager = AboutPageManager(app)
        profile = about_manager.get_author_profile()
        
        form = AuthorProfileForm()
        
        if form.validate_on_submit():
            # Handle profile image upload
            profile_image_uploaded = False
            if form.profile_image.data:
                success, message, filename = about_manager.upload_profile_image(form.profile_image.data)
                if success:
                    profile_image_uploaded = True
                    flash(f'Profile image updated: {message}', 'success')
                else:
                    flash(f'Image upload failed: {message}', 'warning')
            
            # Update profile data
            expertise_areas = form.expertise_areas.data
            success, message, updated_profile = about_manager.update_author_profile(
                name=form.name.data,
                bio=form.bio.data,
                mission_statement=form.mission_statement.data,
                expertise_areas=expertise_areas,
                email=form.email.data,
                twitter_handle=form.twitter_handle.data,
                linkedin_url=form.linkedin_url.data,
                github_url=form.github_url.data,
                website_url=form.website_url.data
            )
            
            if success:
                if profile_image_uploaded:
                    flash('Profile updated successfully with new image!', 'success')
                else:
                    flash('Profile updated successfully!', 'success')
                return redirect(url_for('author_profile_management'))
            else:
                flash(f'Error updating profile: {message}', 'danger')
        
        # Pre-fill form with current data
        if request.method == 'GET':
            form.name.data = profile.name
            form.bio.data = profile.bio
            form.mission_statement.data = profile.mission_statement
            form.email.data = profile.email
            form.twitter_handle.data = profile.twitter_handle or ''
            form.linkedin_url.data = profile.linkedin_url or ''
            form.github_url.data = profile.github_url or ''
            form.website_url.data = profile.website_url or ''
            
            # Convert expertise areas list to comma-separated string
            expertise_areas = profile.get_expertise_areas()
            form.expertise_areas.data = ', '.join(expertise_areas) if expertise_areas else ''
        
        # Get additional data for template
        social_links = about_manager.get_social_links()
        profile_image_url = about_manager.get_profile_image_url()
        profile_stats = about_manager.get_profile_stats()
        
        return render_template('author_profile_management.html',
                             form=form,
                             profile=profile,
                             social_links=social_links,
                             profile_image_url=profile_image_url,
                             profile_stats=profile_stats)

    @app.route('/dashboard/author-profile/delete-image', methods=['POST'])
    @login_required
    def delete_profile_image():
        """Delete current profile image."""
        if not current_user.is_admin:
            abort(403)
        
        about_manager = AboutPageManager(app)
        success, message = about_manager.delete_profile_image()
        
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
        
        return redirect(url_for('author_profile_management'))

    @app.route('/dashboard/author-profile/cleanup-files', methods=['POST'])
    @login_required
    def cleanup_profile_files():
        """Clean up orphaned profile image files."""
        if not current_user.is_admin:
            abort(403)
        
        about_manager = AboutPageManager(app)
        success, message, count = about_manager.cleanup_orphaned_files()
        
        if success:
            flash(f"{message}", 'success')
        else:
            flash(message, 'danger')
        
        return redirect(url_for('author_profile_management'))

    @app.route('/api/upload-editor-image', methods=['POST'])
    @login_required
    def upload_editor_image():
        """Upload image for use in post editor."""
        if not current_user.is_admin:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No image file provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        try:
            image_handler = ImageHandler()
            success, message, image_record = image_handler.save_image(file)
            
            if success:
                return jsonify({
                    'success': True,
                    'url': f'/images/{image_record.filename}',
                    'filename': image_record.filename,
                    'message': message
                })
            else:
                return jsonify({'success': False, 'error': message}), 400
                
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/editor-images')
    @login_required
    def get_editor_images():
        """Get list of available images for editor."""
        if not current_user.is_admin:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        try:
            from models import Image as ImageModel
            images = ImageModel.query.order_by(ImageModel.upload_date.desc()).limit(20).all()
            
            image_list = []
            for img in images:
                image_list.append({
                    'id': img.id,
                    'filename': img.filename,
                    'original_name': img.original_name,
                    'url': f'/images/{img.filename}',
                    'upload_date': img.upload_date.isoformat(),
                    'file_size': img.file_size,
                    'mime_type': img.mime_type
                })
            
            return jsonify({'success': True, 'images': image_list})
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/post/<int:post_id>', methods=['GET', 'POST'])
    def post_view(post_id):
        post = Post.query.get_or_404(post_id)
        
        # Only allow comments on published posts
        # Allow admins to view draft posts for preview
        if post.status != 'published':
            if not (current_user.is_authenticated and current_user.is_admin):
                abort(404)
        
        # Get author profile for author bio section
        about_manager = AboutPageManager(app)
        author_profile = about_manager.get_author_profile()
        social_links = about_manager.get_social_links()
        
        # Initialize comment manager
        comment_manager = CommentManager(app)
        
        # Handle comment submission
        comment_form = CommentForm()
        if comment_form.validate_on_submit() and post.status == 'published':
            # Get client IP and user agent for spam detection
            ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR'))
            user_agent = request.headers.get('User-Agent')
            
            success, message, comment = comment_manager.submit_comment(
                post_id=post.id,
                author_name=comment_form.author_name.data,
                author_email=comment_form.author_email.data,
                content=comment_form.content.data,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            if success:
                flash(message, 'success')
            else:
                flash(message, 'danger')
            
            return redirect(url_for('post_view', post_id=post.id))
        
        # Get approved comments for display
        comments = comment_manager.get_comment_tree(post.id)
        
        # Generate SEO data for post page
        seo_meta = seo_manager.generate_meta_tags(page_type='post', content=post)
        og_tags = seo_manager.generate_open_graph_tags(page_type='article', content=post)
        structured_data = seo_manager.generate_structured_data(page_type='BlogPosting', content=post)
        
        return render_template('post.html', 
                             post=post, 
                             author_profile=author_profile,
                             social_links=social_links,
                             comment_form=comment_form,
                             comments=comments,
                             seo_meta=seo_meta,
                             og_tags=og_tags,
                             structured_data=structured_data)

    @app.route('/explore')
    def explore():
        q = request.args.get('q', '').strip()
        tag = request.args.get('tag', '').strip()
        category = request.args.get('category', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = 10  # Posts per page

        posts = Post.query.filter_by(status='published')  # Only show published posts
        if q:
            like = f"%{q}%"
            posts = posts.filter((Post.title.ilike(like)) | (Post.content.ilike(like)) | (Post.tags.ilike(like)))
        if tag:
            # Use new tag system if available, fallback to legacy
            from models import PostTag
            posts = posts.join(PostTag).join(Tag).filter(Tag.name.ilike(f"%{tag}%"))
        if category:
            posts = posts.filter(Post.category == category)

        # Paginate results
        posts_pagination = posts.order_by(Post.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Get all tags with post counts for the tags section
        from tag_manager import TagManager
        all_tags = TagManager.get_all_tags_with_counts()
        
        # Generate SEO data for explore page
        seo_meta = seo_manager.generate_meta_tags(
            page_type='website',
            title=f"Explore Posts | {app.config.get('SEO_SITE_NAME', 'Smileys Blog')}",
            description="Explore all blog posts about wealth, health, and happiness"
        )
        og_tags = seo_manager.generate_open_graph_tags(page_type='website')
        structured_data = seo_manager.generate_structured_data(page_type='WebSite')
        
        return render_template('explore.html', 
                             posts=posts_pagination.items,
                             pagination=posts_pagination,
                             q=q,
                             tag=tag,
                             category=category,
                             all_tags=all_tags,
                             seo_meta=seo_meta,
                             og_tags=og_tags,
                             structured_data=structured_data)

    @app.route('/tags')
    def tag_list():
        """Redirect to explore page (tags are now integrated there)."""
        return redirect(url_for('explore'))

    @app.route('/tag/<slug>')
    def tag_posts(slug):
        """Show all published posts for a specific tag."""
        from tag_manager import TagManager
        
        # Get tag by slug
        tag = Tag.query.filter_by(slug=slug).first_or_404()
        
        page = request.args.get('page', 1, type=int)
        per_page = 10  # Posts per page
        
        # Get published posts for this tag with pagination
        posts_query = TagManager.get_posts_query_by_tag_name(tag.name, published_only=True)
        posts_pagination = posts_query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Generate SEO data for tag page
        seo_meta = seo_manager.generate_meta_tags(page_type='tag', content=tag)
        og_tags = seo_manager.generate_open_graph_tags(page_type='website')
        structured_data = seo_manager.generate_structured_data(page_type='WebSite')
        
        return render_template('tag_posts.html', 
                             tag=tag, 
                             posts=posts_pagination.items,
                             pagination=posts_pagination,
                             seo_meta=seo_meta,
                             og_tags=og_tags,
                             structured_data=structured_data)

    @app.route('/api/tags/search')
    def api_tag_search():
        """API endpoint for tag search/autocomplete."""
        query = request.args.get('q', '').strip()
        
        if not query:
            return jsonify([])
        
        # Search tags by name
        tags = Tag.query.filter(Tag.name.ilike(f'%{query}%')).limit(10).all()
        
        tag_data = []
        for tag in tags:
            tag_data.append({
                'id': tag.id,
                'name': tag.name,
                'slug': tag.slug
            })
        
        return jsonify(tag_data)

    # Search routes and API endpoints
    @app.route('/search')
    def search():
        """Search interface and results display."""
        from search_engine import SearchEngine
        
        query = request.args.get('q', '').strip()
        category = request.args.get('category', '').strip()
        page = request.args.get('page', 1, type=int)
        
        # Generate SEO data for search page
        seo_meta = seo_manager.generate_meta_tags(page_type='search', query=query)
        og_tags = seo_manager.generate_open_graph_tags(page_type='website')
        structured_data = seo_manager.generate_structured_data(page_type='WebSite')
        
        if not query:
            return render_template('search_results.html', 
                                 results=None, 
                                 query='', 
                                 category=category,
                                 seo_meta=seo_meta,
                                 og_tags=og_tags,
                                 structured_data=structured_data)
        
        # Initialize search engine
        search_engine = SearchEngine(app)
        
        # Build filters
        filters = {}
        if category:
            filters['category'] = category
        
        # Perform search
        results = search_engine.search_posts(query, filters=filters, page=page)
        
        # Log search query for analytics
        search_engine.log_search_query(
            query=query,
            results_count=results['total_results'],
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return render_template('search_results.html', 
                             results=results, 
                             query=query, 
                             category=category,
                             seo_meta=seo_meta,
                             og_tags=og_tags,
                             structured_data=structured_data)
    
    @app.route('/api/search/autocomplete')
    def api_search_autocomplete():
        """AJAX endpoint for search autocomplete suggestions."""
        from search_engine import SearchEngine
        
        query = request.args.get('q', '').strip()
        limit = request.args.get('limit', 5, type=int)
        
        if not query or len(query) < 2:
            return jsonify([])
        
        try:
            search_engine = SearchEngine(app)
            suggestions = search_engine.get_search_suggestions(query, limit=limit)
            
            return jsonify({
                'success': True,
                'suggestions': suggestions
            })
            
        except Exception as e:
            app.logger.error(f"Error getting search suggestions: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Failed to get suggestions'
            }), 500
    
    @app.route('/api/search/live')
    def api_live_search():
        """AJAX endpoint for live search results."""
        from search_engine import SearchEngine
        
        query = request.args.get('q', '').strip()
        category = request.args.get('category', '').strip()
        limit = request.args.get('limit', 5, type=int)
        
        if not query:
            return jsonify({
                'success': True,
                'results': [],
                'total_results': 0
            })
        
        try:
            search_engine = SearchEngine(app)
            
            # Build filters
            filters = {}
            if category:
                filters['category'] = category
            
            # Perform search with limited results for live search
            results = search_engine.search_posts(query, filters=filters, page=1, per_page=limit)
            
            # Format results for JSON response
            formatted_results = []
            for result in results['posts']:
                post = result['post']
                formatted_results.append({
                    'id': post.id,
                    'title': post.title,
                    'excerpt': result['excerpt'],
                    'category': post.category,
                    'url': url_for('post_view', post_id=post.id),
                    'published_at': post.published_at.isoformat() if post.published_at else None
                })
            
            return jsonify({
                'success': True,
                'results': formatted_results,
                'total_results': results['total_results'],
                'query': query
            })
            
        except Exception as e:
            app.logger.error(f"Error performing live search: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Search failed'
            }), 500
    
    @app.route('/api/search/popular')
    def api_popular_searches():
        """API endpoint for popular search queries."""
        from search_engine import SearchEngine
        
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        
        limit = request.args.get('limit', 10, type=int)
        days = request.args.get('days', 30, type=int)
        
        try:
            search_engine = SearchEngine(app)
            popular_searches = search_engine.get_popular_searches(limit=limit, days=days)
            
            return jsonify({
                'success': True,
                'popular_searches': [{'query': query, 'count': count} for query, count in popular_searches]
            })
            
        except Exception as e:
            app.logger.error(f"Error getting popular searches: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Failed to get popular searches'
            }), 500

    # Image upload and management routes
    @app.route('/upload-image', methods=['POST'])
    @login_required
    def upload_image():
        """AJAX endpoint for uploading images."""
        form = ImageUploadForm()
        
        if form.validate_on_submit():
            image_handler = ImageHandler()
            success, message, image_record = image_handler.save_image(form.image.data)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': message,
                    'image_id': image_record.id,
                    'image_url': image_handler.get_image_url(image_record.filename),
                    'filename': image_record.filename
                })
            else:
                return jsonify({
                    'success': False,
                    'message': message
                }), 400
        else:
            errors = []
            for field, field_errors in form.errors.items():
                errors.extend(field_errors)
            return jsonify({
                'success': False,
                'message': 'Validation failed',
                'errors': errors
            }), 400

    @app.route('/debug/images')
    @login_required
    def debug_images():
        """Debug route to check image database and filesystem."""
        if not current_user.is_admin:
            abort(403)
        
        try:
            from models import Image as ImageModel
            import os
            
            # Get database images
            db_images = ImageModel.query.order_by(ImageModel.upload_date.desc()).limit(10).all()
            
            # Get filesystem images
            image_handler = ImageHandler()
            fs_images = []
            if os.path.exists(image_handler.upload_folder):
                fs_images = [f for f in os.listdir(image_handler.upload_folder) 
                           if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))]
            
            debug_info = {
                'upload_folder': image_handler.upload_folder,
                'upload_folder_exists': os.path.exists(image_handler.upload_folder),
                'database_images': [
                    {
                        'id': img.id,
                        'filename': img.filename,
                        'original_name': img.original_name,
                        'upload_date': img.upload_date.isoformat(),
                        'post_id': img.post_id
                    } for img in db_images
                ],
                'filesystem_images': fs_images[:10],  # First 10
                'db_count': ImageModel.query.count(),
                'fs_count': len(fs_images)
            }
            
            return jsonify(debug_info)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/debug/content-test')
    @login_required
    def debug_content_test():
        """Debug route to test content sanitization."""
        if not current_user.is_admin:
            abort(403)
        
        # Test HTML content with image
        test_content = '''
        <p>This is a test post with an image:</p>
        <img src="/images/test.jpg" alt="Test Image" style="max-width: 100%; height: auto; border-radius: 8px; margin: 1rem 0; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" class="editor-image">
        <p>This should show the image properly.</p>
        '''
        
        sanitized = sanitize_content(test_content)
        
        return f'''
        <h2>Content Sanitization Test</h2>
        <h3>Original:</h3>
        <pre>{test_content}</pre>
        <h3>Sanitized:</h3>
        <pre>{sanitized}</pre>
        <h3>Rendered:</h3>
        <div style="border: 1px solid #ccc; padding: 1rem; margin: 1rem 0;">
        {sanitized}
        </div>
        '''

    @app.route('/debug/profile-image')
    @login_required
    def debug_profile_image():
        """Debug route to check profile image configuration."""
        if not current_user.is_admin:
            abort(403)
            
        about_manager = AboutPageManager(app)
        profile = about_manager.get_author_profile()
        profile_image_url = about_manager.get_profile_image_url()
        
        debug_info = {
            'profile_exists': profile is not None,
            'profile_image_filename': profile.profile_image if profile else None,
            'profile_image_url': profile_image_url,
            'upload_folder': app.config.get('UPLOAD_FOLDER'),
            'upload_folder_exists': os.path.exists(app.config.get('UPLOAD_FOLDER', 'static/uploads')),
        }
        
        if profile and profile.profile_image:
            image_path = os.path.join(app.config.get('UPLOAD_FOLDER', 'static/uploads'), profile.profile_image)
            debug_info['image_file_exists'] = os.path.exists(image_path)
            debug_info['image_file_path'] = image_path
            
            if os.path.exists(image_path):
                debug_info['image_file_size'] = os.path.getsize(image_path)
                
                # Check if file can be accessed (not locked)
                try:
                    with open(image_path, 'rb') as f:
                        f.read(1)
                    debug_info['file_accessible'] = True
                except (OSError, PermissionError):
                    debug_info['file_accessible'] = False
        
        # List all profile files in upload folder
        upload_folder = app.config.get('UPLOAD_FOLDER', 'static/uploads')
        if os.path.exists(upload_folder):
            profile_files = [f for f in os.listdir(upload_folder) if f.startswith('profile_')]
            debug_info['all_profile_files'] = profile_files
            debug_info['orphaned_files'] = [f for f in profile_files if f != (profile.profile_image if profile else None)]
        
        return jsonify(debug_info)

    @app.route('/images/<filename>')
    def serve_image(filename):
        """Serve uploaded images with caching headers."""
        try:
            # Initialize image handler
            image_handler = ImageHandler()
            
            # Log the request for debugging
            app.logger.info(f"Serving image request for: {filename}")
            app.logger.info(f"Upload folder: {image_handler.upload_folder}")
            
            # Check if file exists on filesystem first
            file_path = os.path.join(image_handler.upload_folder, filename)
            app.logger.info(f"Looking for file at: {file_path}")
            
            if not os.path.exists(file_path):
                app.logger.error(f"Image file not found on filesystem: {file_path}")
                abort(404)
            
            # Check if it's a profile image first
            profile = AuthorProfile.query.filter_by(profile_image=filename).first()
            
            if profile:
                # It's a profile image, serve it directly
                try:
                    app.logger.info(f"Serving profile image: {filename}")
                    response = send_from_directory(image_handler.upload_folder, filename)
                    # Add caching headers for images (1 year cache)
                    response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
                    response.headers['ETag'] = f'"{filename}-{profile.updated_at.timestamp()}"'
                    response.headers['Expires'] = (datetime.now(timezone.utc) + timedelta(days=365)).strftime('%a, %d %b %Y %H:%M:%S GMT')
                    return response
                except Exception as e:
                    app.logger.error(f"Error serving profile image {filename}: {str(e)}")
                    abort(500)
            
            # Check if it's a regular post image
            image_record = Image.query.filter_by(filename=filename).first()
            
            if not image_record:
                # If not in database, serve it anyway (for development/orphaned files)
                app.logger.warning(f"Serving image {filename} that's not in database")
                try:
                    response = send_from_directory(image_handler.upload_folder, filename)
                    response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
                    return response
                except Exception as e:
                    app.logger.error(f"Error serving orphaned image {filename}: {str(e)}")
                    abort(500)
            
            # Serve the file with caching headers
            try:
                app.logger.info(f"Serving database image: {filename}")
                response = send_from_directory(image_handler.upload_folder, filename)
                # Add caching headers for images (1 year cache)
                response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
                response.headers['ETag'] = f'"{filename}-{image_record.upload_date.timestamp()}"'
                response.headers['Expires'] = (datetime.now(timezone.utc) + timedelta(days=365)).strftime('%a, %d %b %Y %H:%M:%S GMT')
                return response
            except Exception as e:
                app.logger.error(f"Error serving image {filename}: {str(e)}")
                abort(500)
                
        except Exception as e:
            app.logger.error(f"Unexpected error in serve_image for {filename}: {str(e)}")
            import traceback
            app.logger.error(f"Traceback: {traceback.format_exc()}")
            abort(500)
    
    @app.route('/static/<path:filename>')
    def serve_static_with_cache(filename):
        """Serve static files with appropriate caching headers."""
        response = send_from_directory(app.static_folder, filename)
        
        # Determine cache duration based on file type
        if filename.endswith(('.css', '.js')):
            # CSS and JS files - cache for 1 week
            response.headers['Cache-Control'] = 'public, max-age=604800'
            response.headers['ETag'] = f'"{filename}-{os.path.getmtime(os.path.join(app.static_folder, filename))}"'
        elif filename.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico')):
            # Image files - cache for 1 month
            response.headers['Cache-Control'] = 'public, max-age=2592000'
            response.headers['ETag'] = f'"{filename}-{os.path.getmtime(os.path.join(app.static_folder, filename))}"'
        elif filename.endswith(('.woff', '.woff2', '.ttf', '.eot')):
            # Font files - cache for 1 year
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
            response.headers['ETag'] = f'"{filename}-{os.path.getmtime(os.path.join(app.static_folder, filename))}"'
        else:
            # Other files - cache for 1 day
            response.headers['Cache-Control'] = 'public, max-age=86400'
        
        return response

    @app.route('/delete-image/<int:image_id>', methods=['POST'])
    @login_required
    def delete_image(image_id):
        """Delete an uploaded image."""
        image_handler = ImageHandler()
        success, message = image_handler.delete_image(image_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400

    @app.route('/images/post/<int:post_id>')
    @login_required
    def get_post_images(post_id):
        """Get all images for a specific post."""
        image_handler = ImageHandler()
        images = image_handler.get_images_by_post(post_id)
        
        image_data = []
        for image in images:
            image_data.append({
                'id': image.id,
                'filename': image.filename,
                'original_name': image.original_name,
                'url': image_handler.get_image_url(image.filename),
                'file_size': image.file_size,
                'upload_date': image.upload_date.isoformat()
            })
        
        return jsonify({
            'success': True,
            'images': image_data
        })

    @app.route('/media-library')
    @login_required
    def media_library():
        """Media library interface for managing uploaded images."""
        from models import Image as ImageModel
        
        if not current_user.is_admin:
            abort(403)
        
        # Get all images with post information
        images = db.session.query(ImageModel).order_by(ImageModel.upload_date.desc()).all()
        
        image_handler = ImageHandler()
        image_data = []
        
        for image in images:
            # Get associated post if any
            post = None
            if image.post_id:
                post = db.session.get(Post, image.post_id)
            
            image_data.append({
                'id': image.id,
                'filename': image.filename,
                'original_name': image.original_name,
                'url': image_handler.get_image_url(image.filename),
                'file_size': image.file_size,
                'upload_date': image.upload_date,
                'post': post,
                'mime_type': image.mime_type
            })
        
        return render_template('media_library.html', images=image_data)

    # RSS/Atom Feed Routes
    @app.route('/feed.xml')
    @app.route('/rss.xml')
    def rss_feed():
        """Generate RSS 2.0 feed."""
        try:
            feed_generator = FeedGenerator(app)
            rss_content = feed_generator.generate_rss_feed()
            
            response = app.response_class(
                rss_content,
                mimetype='application/rss+xml'
            )
            
            # Add caching headers
            response.headers['Cache-Control'] = 'public, max-age=3600'  # 1 hour
            response.headers['ETag'] = f'"{hash(rss_content)}"'
            
            return response
            
        except Exception as e:
            # Log error and return 500
            app.logger.error(f"Error generating RSS feed: {str(e)}")
            abort(500)
    
    @app.route('/atom.xml')
    def atom_feed():
        """Generate Atom 1.0 feed."""
        try:
            feed_generator = FeedGenerator(app)
            atom_content = feed_generator.generate_atom_feed()
            
            response = app.response_class(
                atom_content,
                mimetype='application/atom+xml'
            )
            
            # Add caching headers
            response.headers['Cache-Control'] = 'public, max-age=3600'  # 1 hour
            response.headers['ETag'] = f'"{hash(atom_content)}"'
            
            return response
            
        except Exception as e:
            # Log error and return 500
            app.logger.error(f"Error generating Atom feed: {str(e)}")
            abort(500)
    
    @app.route('/feed-info')
    def feed_info():
        """Display feed information for debugging/admin purposes."""
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        
        try:
            feed_generator = FeedGenerator(app)
            metadata = feed_generator.get_feed_metadata()
            
            return jsonify({
                'success': True,
                'metadata': metadata
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # Newsletter subscription routes
    @app.route('/newsletter/subscribe', methods=['GET', 'POST'])
    def newsletter_subscribe():
        """Newsletter subscription page."""
        from newsletter_manager import NewsletterManager
        from forms import NewsletterSubscriptionForm
        
        form = NewsletterSubscriptionForm()
        
        if form.validate_on_submit():
            newsletter_manager = NewsletterManager(app)
            
            success, message, subscription = newsletter_manager.subscribe_email(
                email=form.email.data,
                frequency=form.frequency.data,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
            
            if success:
                flash(message, 'success')
                return redirect(url_for('newsletter_subscribe'))
            else:
                flash(message, 'danger')
        
        return render_template('newsletter_subscribe.html', form=form)
    
    @app.route('/newsletter/confirm/<token>')
    def confirm_subscription(token):
        """Confirm newsletter subscription."""
        from newsletter_manager import NewsletterManager
        
        newsletter_manager = NewsletterManager(app)
        success, message, subscription = newsletter_manager.confirm_subscription(token)
        
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
        
        return redirect(url_for('index'))
    
    @app.route('/newsletter/unsubscribe/<token>', methods=['GET', 'POST'])
    def unsubscribe_newsletter(token):
        """Unsubscribe from newsletter."""
        from newsletter_manager import NewsletterManager
        from forms import NewsletterUnsubscribeForm
        
        newsletter_manager = NewsletterManager(app)
        form = NewsletterUnsubscribeForm()
        
        # Get subscription info for display
        subscription = NewsletterSubscription.query.filter_by(unsubscribe_token=token).first()
        
        if form.validate_on_submit():
            if form.confirm.data == 'yes':
                success, message, _ = newsletter_manager.unsubscribe_email(token)
                if success:
                    flash(message, 'success')
                    return redirect(url_for('index'))
                else:
                    flash(message, 'danger')
            else:
                flash('You remain subscribed to our newsletter.', 'info')
                return redirect(url_for('index'))
        
        return render_template('newsletter_unsubscribe.html', form=form, subscription=subscription)
    
    @app.route('/api/newsletter/subscribe', methods=['POST'])
    def api_newsletter_subscribe():
        """AJAX endpoint for newsletter subscription."""
        from newsletter_manager import NewsletterManager
        
        email = request.json.get('email', '').strip()
        frequency = request.json.get('frequency', 'weekly')
        
        if not email:
            return jsonify({
                'success': False,
                'message': 'Email address is required'
            }), 400
        
        newsletter_manager = NewsletterManager(app)
        success, message, subscription = newsletter_manager.subscribe_email(
            email=email,
            frequency=frequency,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return jsonify({
            'success': success,
            'message': message
        }), 200 if success else 400

    @app.route('/dashboard/newsletter', methods=['GET', 'POST'])
    @login_required
    def newsletter_management():
        """Newsletter management interface."""
        if not current_user.is_admin:
            abort(403)
        
        from newsletter_manager import NewsletterManager
        
        newsletter_manager = NewsletterManager(app)
        
        # Handle digest sending
        if request.method == 'POST':
            action = request.form.get('action')
            frequency = request.form.get('frequency', 'weekly')
            
            if action == 'send_digest':
                success, message, stats = newsletter_manager.send_digest_to_subscribers(frequency)
                if success:
                    flash(f"Digest sent successfully: {message}", 'success')
                else:
                    flash(f"Error sending digest: {message}", 'danger')
            elif action == 'preview_digest':
                success, message, digest_data = newsletter_manager.generate_digest(frequency)
                if success:
                    return render_template('newsletter_digest_preview.html', 
                                         digest_data=digest_data, 
                                         frequency=frequency)
                else:
                    flash(f"Error generating preview: {message}", 'danger')
        
        # Get newsletter statistics
        stats = newsletter_manager.get_subscription_stats()
        
        # Get recent subscriptions
        recent_subscriptions = NewsletterSubscription.query.filter_by(
            is_confirmed=True
        ).order_by(NewsletterSubscription.confirmed_at.desc()).limit(10).all()
        
        return render_template('newsletter_management.html', 
                             stats=stats, 
                             recent_subscriptions=recent_subscriptions)
    
    @app.route('/api/newsletter/stats')
    @login_required
    def api_newsletter_stats():
        """API endpoint for newsletter statistics."""
        if not current_user.is_admin:
            abort(403)
        
        from newsletter_manager import NewsletterManager
        
        newsletter_manager = NewsletterManager(app)
        stats = newsletter_manager.get_subscription_stats()
        
        return jsonify({
            'success': True,
            'stats': stats
        })

    # Comment moderation routes
    @app.route('/dashboard/comments', methods=['GET', 'POST'])
    @login_required
    def comment_moderation():
        """Comment moderation interface."""
        if not current_user.is_admin:
            abort(403)
        
        comment_manager = CommentManager(app)
        
        # Handle bulk actions
        bulk_form = BulkCommentModerationForm()
        if bulk_form.validate_on_submit() and request.form.get('selected_comments'):
            selected_ids = [int(id) for id in request.form.getlist('selected_comments')]
            action = bulk_form.action.data
            
            if action == 'approve':
                successful, failed = comment_manager.bulk_approve_comments(selected_ids, current_user.id)
                flash(f'Approved {successful} comments. {failed} failed.', 'success' if failed == 0 else 'warning')
            elif action == 'reject':
                successful, failed = comment_manager.bulk_reject_comments(selected_ids, current_user.id, mark_as_spam=False)
                flash(f'Rejected {successful} comments. {failed} failed.', 'success' if failed == 0 else 'warning')
            elif action == 'spam':
                successful, failed = comment_manager.bulk_reject_comments(selected_ids, current_user.id, mark_as_spam=True)
                flash(f'Marked {successful} comments as spam. {failed} failed.', 'success' if failed == 0 else 'warning')
            elif action == 'delete':
                successful = 0
                failed = 0
                for comment_id in selected_ids:
                    success, _ = comment_manager.delete_comment(comment_id, current_user.id)
                    if success:
                        successful += 1
                    else:
                        failed += 1
                flash(f'Deleted {successful} comments. {failed} failed.', 'success' if failed == 0 else 'warning')
            
            return redirect(url_for('comment_moderation'))
        
        # Get pending comments and statistics
        pending_comments = comment_manager.get_pending_comments()
        stats = comment_manager.get_comment_stats()
        
        return render_template('comment_moderation.html',
                             pending_comments=pending_comments,
                             stats=stats,
                             bulk_form=bulk_form)
    
    @app.route('/api/comment/moderate/<int:comment_id>', methods=['POST'])
    @login_required
    def api_moderate_comment(comment_id):
        """API endpoint for individual comment moderation."""
        if not current_user.is_admin:
            abort(403)
        
        comment_manager = CommentManager(app)
        action = request.json.get('action')
        
        if action == 'approve':
            success, message = comment_manager.approve_comment(comment_id, current_user.id)
        elif action == 'reject':
            success, message = comment_manager.reject_comment(comment_id, current_user.id, mark_as_spam=False)
        elif action == 'spam':
            success, message = comment_manager.reject_comment(comment_id, current_user.id, mark_as_spam=True)
        elif action == 'delete':
            success, message = comment_manager.delete_comment(comment_id, current_user.id)
        else:
            return jsonify({'success': False, 'message': 'Invalid action'}), 400
        
        return jsonify({
            'success': success,
            'message': message
        }), 200 if success else 400
    
    @app.route('/api/comment/stats')
    @login_required
    def api_comment_stats():
        """API endpoint for comment statistics."""
        if not current_user.is_admin:
            abort(403)
        
        comment_manager = CommentManager(app)
        stats = comment_manager.get_comment_stats()
        
        return jsonify({
            'success': True,
            'stats': stats
        })

    # SEO and Sitemap routes
    @app.route('/sitemap.xml')
    def sitemap():
        """Generate and serve XML sitemap."""
        try:
            sitemap_xml = seo_manager.generate_sitemap()
            
            response = app.response_class(
                sitemap_xml,
                mimetype='application/xml'
            )
            
            # Add caching headers
            response.headers['Cache-Control'] = 'public, max-age=86400'  # 24 hours
            response.headers['ETag'] = f'"{hash(sitemap_xml)}"'
            
            return response
            
        except Exception as e:
            # Log error and return 500
            app.logger.error(f"Error generating sitemap: {str(e)}")
            abort(500)

    @app.route('/sitemap')
    def sitemap_html():
        """Generate and serve HTML sitemap with clickable links."""
        try:
            # Get all published posts
            published_posts = Post.query.filter_by(status='published').order_by(Post.created_at.desc()).all()
            
            # Get all tags that have posts (simplified query to avoid potential issues)
            try:
                from models import Tag
                tags_with_posts = db.session.query(Tag).join(Tag.posts).filter(Post.status == 'published').distinct().all()
            except Exception:
                # Fallback if tag query fails
                tags_with_posts = []
            
            # Organize posts by category
            posts_by_category = {}
            for post in published_posts:
                category = post.category or 'Uncategorized'
                if category not in posts_by_category:
                    posts_by_category[category] = []
                posts_by_category[category].append(post)
            
            # Generate SEO data for sitemap page (with fallbacks)
            try:
                seo_meta = seo_manager.generate_meta_tags(page_type='website')
                og_tags = seo_manager.generate_open_graph_tags(page_type='website')
                structured_data = seo_manager.generate_structured_data(page_type='WebSite')
            except Exception:
                # Fallback SEO data
                seo_meta = {'title': 'Site Map', 'description': 'Browse all content on this site'}
                og_tags = {}
                structured_data = {}
            
            return render_template('sitemap.html',
                                 posts_by_category=posts_by_category,
                                 tags=tags_with_posts,
                                 total_posts=len(published_posts),
                                 seo_meta=seo_meta,
                                 og_tags=og_tags,
                                 structured_data=structured_data)
            
        except Exception as e:
            # Log error and return 500
            app.logger.error(f"Error generating HTML sitemap: {str(e)}")
            import traceback
            app.logger.error(traceback.format_exc())
            abort(500)
    
    # System Health and Monitoring routes
    @app.route('/health')
    def health_check():
        """Public health check endpoint."""
        from system_health_monitor import SystemHealthMonitor
        
        health_monitor = SystemHealthMonitor(app)
        health_data, status_code = health_monitor.run_health_check_endpoint()
        
        # Return simplified health data for public endpoint
        public_health = {
            'status': health_data['overall_status'],
            'timestamp': health_data['check_timestamp'],
            'components': {
                name: {'status': component['status'], 'message': component['message']}
                for name, component in health_data['components'].items()
            }
        }
        
        response = jsonify(public_health)
        response.status_code = status_code
        return response
    
    @app.route('/api/system/health')
    @login_required
    def api_system_health():
        """Detailed system health API for admin dashboard."""
        if not current_user.is_admin:
            abort(403)
        
        from system_health_monitor import SystemHealthMonitor
        
        health_monitor = SystemHealthMonitor(app)
        health_data = health_monitor.get_overall_health()
        
        return jsonify({
            'success': True,
            'health': health_data
        })
    
    @app.route('/api/system/health/<component>')
    @login_required
    def api_component_health(component):
        """Get health status for a specific component."""
        if not current_user.is_admin:
            abort(403)
        
        from system_health_monitor import SystemHealthMonitor
        
        health_monitor = SystemHealthMonitor(app)
        
        # Map component names to health check methods
        component_checks = {
            'database': health_monitor.check_database_health,
            'search': health_monitor.check_search_index_health,
            'email': health_monitor.check_email_service_health,
            'feeds': health_monitor.check_feed_generation_health,
            'filesystem': health_monitor.check_file_system_health,
            'performance': health_monitor.check_performance_metrics
        }
        
        if component not in component_checks:
            return jsonify({
                'success': False,
                'error': 'Invalid component'
            }), 400
        
        try:
            component_health = component_checks[component]()
            return jsonify({
                'success': True,
                'component': component,
                'health': component_health
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # Analytics and Reporting routes
    @app.route('/api/analytics/comprehensive')
    @login_required
    def api_comprehensive_analytics():
        """Get comprehensive analytics across all system components."""
        if not current_user.is_admin:
            abort(403)
        
        from analytics_manager import AnalyticsManager
        
        days = request.args.get('days', 30, type=int)
        
        analytics_manager = AnalyticsManager(app)
        analytics = analytics_manager.get_comprehensive_analytics(days)
        
        return jsonify({
            'success': True,
            'analytics': analytics
        })
    
    @app.route('/api/analytics/dashboard')
    @login_required
    def api_dashboard_analytics():
        """Get dashboard summary analytics."""
        if not current_user.is_admin:
            abort(403)
        
        from analytics_manager import AnalyticsManager
        
        analytics_manager = AnalyticsManager(app)
        summary = analytics_manager.get_dashboard_summary()
        
        return jsonify({
            'success': True,
            'summary': summary
        })
    
    @app.route('/api/analytics/content')
    @login_required
    def api_content_analytics():
        """Get content-specific analytics."""
        if not current_user.is_admin:
            abort(403)
        
        from analytics_manager import AnalyticsManager
        from datetime import datetime, timezone, timedelta
        
        days = request.args.get('days', 30, type=int)
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        analytics_manager = AnalyticsManager(app)
        content_analytics = analytics_manager.get_content_analytics(start_date, end_date)
        
        return jsonify({
            'success': True,
            'content_analytics': content_analytics,
            'period': {
                'days': days,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            }
        })
    
    @app.route('/api/analytics/engagement')
    @login_required
    def api_engagement_analytics():
        """Get engagement-specific analytics."""
        if not current_user.is_admin:
            abort(403)
        
        from analytics_manager import AnalyticsManager
        from datetime import datetime, timezone, timedelta
        
        days = request.args.get('days', 30, type=int)
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        analytics_manager = AnalyticsManager(app)
        engagement_analytics = analytics_manager.get_engagement_analytics(start_date, end_date)
        
        return jsonify({
            'success': True,
            'engagement_analytics': engagement_analytics,
            'period': {
                'days': days,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            }
        })
    
    @app.route('/api/analytics/growth')
    @login_required
    def api_growth_analytics():
        """Get growth metrics analytics."""
        if not current_user.is_admin:
            abort(403)
        
        from analytics_manager import AnalyticsManager
        
        days = request.args.get('days', 90, type=int)
        
        analytics_manager = AnalyticsManager(app)
        growth_metrics = analytics_manager.get_growth_metrics(days)
        
        return jsonify({
            'success': True,
            'growth_metrics': growth_metrics
        })
    
    @app.route('/api/analytics/export')
    @login_required
    def api_export_analytics():
        """Export analytics report."""
        if not current_user.is_admin:
            abort(403)
        
        from analytics_manager import AnalyticsManager
        
        days = request.args.get('days', 30, type=int)
        format_type = request.args.get('format', 'json')
        
        analytics_manager = AnalyticsManager(app)
        report = analytics_manager.export_analytics_report(days, format_type)
        
        if format_type.lower() == 'json':
            response = app.response_class(
                report,
                mimetype='application/json'
            )
            response.headers['Content-Disposition'] = f'attachment; filename=analytics_report_{days}days.json'
        else:
            response = app.response_class(
                report,
                mimetype='text/plain'
            )
            response.headers['Content-Disposition'] = f'attachment; filename=analytics_report_{days}days.txt'
        
        return response

    @app.route('/robots.txt')
    def robots_txt():
        """Generate robots.txt file."""
        site_url = app.config.get('SEO_SITE_URL', 'https://smileys-blog.com')
        
        robots_content = f"""User-agent: *
Allow: /

# Sitemaps
Sitemap: {site_url}/sitemap.xml

# Disallow admin and API endpoints
Disallow: /dashboard
Disallow: /api/
Disallow: /login
Disallow: /logout
Disallow: /upload-image
Disallow: /delete-image
Disallow: /images/post/

# Allow feed discovery
Allow: /feed.xml
Allow: /atom.xml
Allow: /rss.xml
"""
        
        response = app.response_class(
            robots_content,
            mimetype='text/plain'
        )
        
        # Add caching headers
        response.headers['Cache-Control'] = 'public, max-age=86400'  # 24 hours
        
        return response

    @app.route('/favicon.ico')
    def favicon():
        """Serve favicon.ico to prevent 404 errors."""
        # Return a simple 1x1 transparent PNG as favicon
        # This prevents 404 errors when browsers automatically request favicon.ico
        import base64
        
        # 1x1 transparent PNG encoded as base64
        transparent_png = base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI9jU77zgAAAABJRU5ErkJggg=='
        )
        
        response = app.response_class(
            transparent_png,
            mimetype='image/png'
        )
        
        # Add caching headers
        response.headers['Cache-Control'] = 'public, max-age=31536000'  # 1 year
        
        return response

    return app


if __name__ == '__main__':
    app = create_app()
    
    # Production configuration
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    app.run(host='0.0.0.0', port=port, debug=debug)
