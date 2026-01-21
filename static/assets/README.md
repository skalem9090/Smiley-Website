# Website Assets

This folder contains permanent website assets that are part of the site's design and branding.

## Folder Structure

### `/logos`
Store your site logos here:
- `logo.png` - Main site logo
- `logo-light.png` - Light version for dark backgrounds
- `logo-dark.png` - Dark version for light backgrounds
- `logo-small.png` - Small/compact version for mobile

### `/branding`
Store brand-related images:
- Hero images
- Background patterns
- Brand photography
- Marketing materials

### `/icons`
Store favicons and app icons:
- `favicon.ico` - Browser favicon
- `favicon-16x16.png` - 16x16 favicon
- `favicon-32x32.png` - 32x32 favicon
- `apple-touch-icon.png` - iOS home screen icon (180x180)
- `android-chrome-192x192.png` - Android icon
- `android-chrome-512x512.png` - Android icon (large)

## Usage in Templates

```html
<!-- Logo -->
<img src="{{ url_for('static', filename='assets/logos/logo.png') }}" alt="Site Logo">

<!-- Favicon -->
<link rel="icon" type="image/png" sizes="32x32" href="{{ url_for('static', filename='assets/icons/favicon-32x32.png') }}">

<!-- Branding Image -->
<img src="{{ url_for('static', filename='assets/branding/hero-image.jpg') }}" alt="Hero">
```

## Important Notes

- These files are **permanent** and part of your site's design
- They are **NOT** user-uploaded content
- They should be committed to version control
- They will be deployed with your application
- Separate from `static/uploads/` which is for user content

## Recommended Sizes

### Logos
- Main logo: 400x100px (or proportional)
- Small logo: 200x50px
- Square logo: 200x200px

### Favicons
- favicon.ico: 16x16, 32x32, 48x48 (multi-size)
- PNG favicons: 16x16, 32x32, 96x96
- Apple touch icon: 180x180
- Android icons: 192x192, 512x512

### Hero/Banner Images
- Desktop: 1920x600px
- Mobile: 800x600px
- Optimize for web (compress to <200KB)
