import os
from flask import Flask, render_template, request, redirect, url_for, flash, abort, jsonify, send_from_directory
from flask_wtf import CSRFProtect
import bleach
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate

from models import db, User, Post, Tag, AuthorProfile, NewsletterSubscription, Comment, SearchQuery
from forms import LoginForm, PostForm, ImageUploadForm
from image_handler import ImageHandler
from schedule_manager import ScheduleManager
from about_page_manager import AboutPageManager
from feed_generator import FeedGenerator


def create_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', f'sqlite:///{os.path.abspath("instance/site.db")}')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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

    # Initialize and start background scheduler
    scheduler = ScheduleManager(app)
    scheduler.start()

    @app.route('/')
    def index():
        # Show latest published posts for three main site heads/categories
        wealth_posts = Post.query.filter(Post.category.ilike('wealth'), Post.status == 'published').order_by(Post.created_at.desc()).limit(5).all()
        health_posts = Post.query.filter(Post.category.ilike('health'), Post.status == 'published').order_by(Post.created_at.desc()).limit(5).all()
        happiness_posts = Post.query.filter(Post.category.ilike('happiness'), Post.status == 'published').order_by(Post.created_at.desc()).limit(5).all()
        return render_template('index.html', wealth_posts=wealth_posts, health_posts=health_posts, happiness_posts=happiness_posts)

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
        
        return render_template('about.html', 
                             profile=profile, 
                             social_links=social_links,
                             profile_image_url=profile_image_url)

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
            
            # sanitize content: allow basic formatting tags and safe attributes
            ALLOWED_TAGS = [
                'a', 'abbr', 'b', 'blockquote', 'br', 'code', 'em', 'i', 'li', 'ol', 'p', 'strong', 'ul', 'h1', 'h2', 'h3', 'h4', 'img'
            ]
            ALLOWED_ATTRIBUTES = {
                'a': ['href', 'title', 'rel', 'target'],
                'img': ['src', 'alt', 'title', 'width', 'height']
            }
            cleaned_content = bleach.clean(
                form.content.data or '',
                tags=ALLOWED_TAGS,
                attributes=ALLOWED_ATTRIBUTES,
                strip=True
            )
            
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
                    'scheduled': f'scheduled for publication on {scheduled_time.strftime("%Y-%m-%d at %H:%M")}'
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
            
            # sanitize content: allow basic formatting tags and safe attributes
            ALLOWED_TAGS = [
                'a', 'abbr', 'b', 'blockquote', 'br', 'code', 'em', 'i', 'li', 'ol', 'p', 'strong', 'ul', 'h1', 'h2', 'h3', 'h4', 'img'
            ]
            ALLOWED_ATTRIBUTES = {
                'a': ['href', 'title', 'rel', 'target'],
                'img': ['src', 'alt', 'title', 'width', 'height']
            }
            cleaned_content = bleach.clean(
                form.content.data or '',
                tags=ALLOWED_TAGS,
                attributes=ALLOWED_ATTRIBUTES,
                strip=True
            )
            
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
                    'scheduled': f'scheduled for publication on {scheduled_time.strftime("%Y-%m-%d at %H:%M")}'
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
        db.session.delete(post)
        db.session.commit()
        flash('Post deleted', 'success')
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
            # Delete selected posts
            deleted_count = 0
            for post_id in post_ids:
                post = db.session.get(Post, post_id)
                if post:
                    db.session.delete(post)
                    deleted_count += 1
            
            try:
                db.session.commit()
                flash(f'Successfully deleted {deleted_count} post(s).', 'success')
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

    @app.route('/post/<int:post_id>')
    def post_view(post_id):
        post = Post.query.get_or_404(post_id)
        
        # Get author profile for author bio section
        about_manager = AboutPageManager(app)
        author_profile = about_manager.get_author_profile()
        social_links = about_manager.get_social_links()
        
        return render_template('post.html', 
                             post=post, 
                             author_profile=author_profile,
                             social_links=social_links)

    @app.route('/explore')
    def explore():
        q = request.args.get('q', '').strip()
        tag = request.args.get('tag', '').strip()
        category = request.args.get('category', '').strip()

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

        posts = posts.order_by(Post.created_at.desc()).all()
        return render_template('explore.html', posts=posts, q=q)

    @app.route('/tags')
    def tag_list():
        """List all tags with post counts."""
        from tag_manager import TagManager
        
        # Get all tags with their post counts
        tags_with_counts = TagManager.get_all_tags_with_counts()
        
        return render_template('tag_list.html', tags=tags_with_counts)

    @app.route('/tag/<slug>')
    def tag_posts(slug):
        """Show all published posts for a specific tag."""
        from tag_manager import TagManager
        
        # Get tag by slug
        tag = Tag.query.filter_by(slug=slug).first_or_404()
        
        # Get published posts for this tag
        posts = TagManager.get_posts_by_tag_name(tag.name, published_only=True)
        
        return render_template('tag_posts.html', tag=tag, posts=posts)

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

    @app.route('/images/<filename>')
    def serve_image(filename):
        """Serve uploaded images with caching headers."""
        image_handler = ImageHandler()
        
        # Verify the image exists in database for security
        from models import Image as ImageModel
        image_record = ImageModel.query.filter_by(filename=filename).first()
        if not image_record:
            abort(404)
        
        # Serve the file with caching headers
        response = send_from_directory(image_handler.upload_folder, filename)
        
        # Add caching headers
        response.headers['Cache-Control'] = 'public, max-age=31536000'  # 1 year
        response.headers['ETag'] = f'"{filename}"'
        
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

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
