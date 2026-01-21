# 🎨 Website Assets Guide

## 📁 Folder Structure

Your permanent website assets are organized in `static/assets/`:

```
static/assets/
├── logos/          # Site logos (main, light, dark, small)
├── branding/       # Brand images, hero images, backgrounds
├── icons/          # Favicons and app icons
└── README.md       # Detailed documentation
```

## 🖼️ Adding Your Logo

### 1. Prepare Your Logo Files

Create these versions of your logo:
- **logo.png** - Main logo (400x100px recommended)
- **logo-small.png** - Compact version for mobile (200x50px)
- **logo-square.png** - Square version for social media (200x200px)

### 2. Add to Project

Place your logo files in `static/assets/logos/`

### 3. Use in Templates

Update `templates/base.html` to use your logo:

```html
<!-- In the navigation -->
<div class="site-title">
    <h1>
        <a href="{{ url_for('index') }}">
            <img src="{{ url_for('static', filename='assets/logos/logo.png') }}" 
                 alt="Your Site Name" 
                 style="height: 40px;">
        </a>
    </h1>
</div>
```

## 🎯 Adding Favicons

### 1. Generate Favicons

Use a tool like [favicon.io](https://favicon.io) or [realfavicongenerator.net](https://realfavicongenerator.net) to generate:
- favicon.ico
- favicon-16x16.png
- favicon-32x32.png
- apple-touch-icon.png (180x180)
- android-chrome-192x192.png
- android-chrome-512x512.png

### 2. Add to Project

Place all favicon files in `static/assets/icons/`

### 3. Add to HTML Head

Update `templates/base.html` in the `<head>` section:

```html
<head>
    <!-- Favicons -->
    <link rel="icon" type="image/x-icon" href="{{ url_for('static', filename='assets/icons/favicon.ico') }}">
    <link rel="icon" type="image/png" sizes="16x16" href="{{ url_for('static', filename='assets/icons/favicon-16x16.png') }}">
    <link rel="icon" type="image/png" sizes="32x32" href="{{ url_for('static', filename='assets/icons/favicon-32x32.png') }}">
    <link rel="apple-touch-icon" sizes="180x180" href="{{ url_for('static', filename='assets/icons/apple-touch-icon.png') }}">
    
    <!-- Android -->
    <link rel="icon" type="image/png" sizes="192x192" href="{{ url_for('static', filename='assets/icons/android-chrome-192x192.png') }}">
    <link rel="icon" type="image/png" sizes="512x512" href="{{ url_for('static', filename='assets/icons/android-chrome-512x512.png') }}">
</head>
```

## 🎨 Adding Hero/Background Images

### 1. Prepare Images

- Optimize for web (compress to <200KB)
- Recommended size: 1920x600px for hero images
- Use JPG for photos, PNG for graphics with transparency

### 2. Add to Project

Place images in `static/assets/branding/`

### 3. Use in Templates

```html
<!-- Hero section background -->
<header class="site-hero" style="background-image: url('{{ url_for('static', filename='assets/branding/hero-bg.jpg') }}');">
    <div class="hero-content">
        <h2>Welcome to My Blog</h2>
    </div>
</header>
```

## 📱 Mobile Considerations

For responsive logos, use CSS:

```css
/* In your CSS */
.site-logo {
    height: 40px;
    width: auto;
}

@media (max-width: 768px) {
    .site-logo {
        height: 30px;
    }
}
```

## 🚀 Deployment

These assets will be deployed with your application:

1. **Commit to Git:**
   ```bash
   git add static/assets/
   git commit -m "Add site logos and branding assets"
   git push
   ```

2. **Railway will automatically deploy** these files with your app

## 📊 File Size Recommendations

| Asset Type | Max Size | Format |
|------------|----------|--------|
| Logo | 50KB | PNG (with transparency) |
| Favicon | 10KB | ICO or PNG |
| Hero Image | 200KB | JPG (compressed) |
| Background | 100KB | JPG or PNG |
| Icons | 20KB | PNG |

## 🔧 Quick Setup Checklist

- [ ] Add main logo to `static/assets/logos/logo.png`
- [ ] Add small logo to `static/assets/logos/logo-small.png`
- [ ] Generate and add favicons to `static/assets/icons/`
- [ ] Update `templates/base.html` with logo
- [ ] Update `templates/base.html` with favicon links
- [ ] Add hero/background images to `static/assets/branding/`
- [ ] Test on desktop and mobile
- [ ] Commit and push to deploy

## 💡 Tips

1. **Use SVG for logos** when possible (scales perfectly)
2. **Compress images** before uploading (use TinyPNG or similar)
3. **Test favicons** on different browsers and devices
4. **Keep backups** of original high-res files
5. **Use descriptive filenames** (e.g., `logo-christmas-2024.png`)

## 🆚 Assets vs Uploads

| `static/assets/` | `static/uploads/` |
|------------------|-------------------|
| Permanent site assets | User-uploaded content |
| Logos, favicons, branding | Blog post images |
| Committed to git | NOT in git (.gitignore) |
| Deployed with app | Managed separately |
| Designer/developer managed | User/admin managed |

Your permanent assets are now organized and ready to use! 🎉
