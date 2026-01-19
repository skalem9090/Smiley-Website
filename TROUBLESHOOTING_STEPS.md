# Troubleshooting: Feature Toolbar Not Visible

## Issue
The feature toolbar buttons are not visible or not working on the dashboard page.

## Step-by-Step Troubleshooting

### Step 1: Hard Refresh Your Browser
**This is the most common issue - browser cache!**

- **Chrome/Edge**: Press `Ctrl + Shift + R` or `Ctrl + F5`
- **Firefox**: Press `Ctrl + Shift + R` or `Ctrl + F5`
- **Safari**: Press `Cmd + Shift + R`

### Step 2: Restart Flask Server
If you're running the Flask development server, restart it:

1. Stop the server (Ctrl+C in terminal)
2. Start it again: `python app.py` or `flask run`
3. Reload the page in your browser

### Step 3: Check Browser Console
Open browser developer tools (F12) and check the Console tab for errors:

1. Press `F12` to open Developer Tools
2. Click on the "Console" tab
3. Look for any red error messages
4. Take a screenshot if you see errors

### Step 4: Inspect the Toolbar Element
Check if the toolbar exists in the DOM:

1. Press `F12` to open Developer Tools
2. Click on the "Elements" or "Inspector" tab
3. Press `Ctrl+F` to search
4. Search for: `editor-feature-toolbar`
5. Check if the element exists and is visible

### Step 5: Check if Functions Exist
In the browser console, type these commands to verify functions are loaded:

```javascript
typeof togglePreview
typeof openExportDialog
typeof validateContent
typeof openTemplateDialog
```

Each should return `"function"`. If they return `"undefined"`, the JavaScript didn't load.

### Step 6: Verify Toolbar Visibility
In the browser console, run:

```javascript
const toolbar = document.querySelector('.editor-feature-toolbar');
console.log('Toolbar exists:', !!toolbar);
console.log('Toolbar display:', toolbar ? toolbar.style.display : 'not found');
console.log('Toolbar visible:', toolbar ? toolbar.offsetHeight > 0 : false);
```

### Step 7: Check Advanced Editor Initialization
In the browser console, run:

```javascript
console.log('AdvancedEditor available:', typeof window.AdvancedEditor);
console.log('advancedEditor instance:', typeof advancedEditor);
```

### Step 8: Force Show Toolbar
If the toolbar exists but isn't visible, try forcing it to show:

```javascript
const toolbar = document.querySelector('.editor-feature-toolbar');
if (toolbar) {
    toolbar.style.display = 'flex';
    toolbar.style.visibility = 'visible';
    toolbar.style.opacity = '1';
    toolbar.style.zIndex = '1000';
    console.log('Toolbar forced visible');
}
```

### Step 9: Test Button Click
Try clicking a button programmatically:

```javascript
const exportBtn = document.querySelector('.editor-feature-toolbar button');
if (exportBtn) {
    console.log('Button found, onclick:', exportBtn.onclick);
    exportBtn.click();
} else {
    console.log('Button not found');
}
```

## Common Issues and Solutions

### Issue: "Nothing changed"
**Solution**: Hard refresh the browser (Ctrl+Shift+R). Browser cache is very aggressive.

### Issue: Toolbar not visible
**Possible causes**:
1. Advanced editor CSS is hiding it (z-index issue)
2. Browser cache showing old version
3. Flask server needs restart

**Solution**: 
- Added `z-index: 10` and `!important` to toolbar display
- Added visible border to make it obvious
- Hard refresh browser

### Issue: Functions not defined
**Possible causes**:
1. JavaScript error preventing script execution
2. Script tag not closed properly
3. Browser cache

**Solution**:
- Check browser console for errors
- Hard refresh browser
- Restart Flask server

### Issue: Buttons don't do anything
**Possible causes**:
1. Functions defined but `advancedEditor` not initialized
2. JavaScript errors
3. onclick handlers not attached

**Solution**:
- Check console for errors
- Verify `advancedEditor` exists: `console.log(advancedEditor)`
- Try clicking after page fully loads

## What I Changed

### 1. Added Missing JavaScript Functions
Added ~500 lines of JavaScript to `templates/dashboard.html`:
- `togglePreview()`
- `openExportDialog()`
- `exportContent(format)`
- `openTemplateDialog()`
- `applyTemplate(templateName)`
- `validateContent()`
- `showValidationResults()`
- `convertHtmlToMarkdown()`

### 2. Enhanced Toolbar Visibility
Updated toolbar styling to ensure it's always visible:
- Added `display: flex !important`
- Added `z-index: 10`
- Added `position: relative`
- Added visible border: `border: 2px solid var(--ink-accent)`
- Added shadow for depth

## Expected Behavior

When you load the dashboard page, you should see:

1. **Feature Toolbar** - A horizontal bar with 4 buttons above the editor:
   - 📤 Export
   - 📋 Templates
   - ✓ Validate
   - 👁️ Preview

2. **Toolbar Appearance**:
   - Light beige/aged paper background
   - Brown border (2px solid)
   - Subtle shadow
   - Buttons with hover effects

3. **Button Functionality**:
   - **Export**: Opens modal with HTML/Markdown/JSON options
   - **Templates**: Opens modal with 4 template choices
   - **Validate**: Checks content and shows results
   - **Preview**: Toggles preview pane below editor

## If Nothing Works

If you've tried all the above and still see nothing:

1. **Take a screenshot** of the dashboard page
2. **Open browser console** (F12) and take a screenshot of any errors
3. **Check the HTML source**: Right-click page → "View Page Source"
4. **Search for**: `editor-feature-toolbar` in the source
5. **Verify the file was saved**: Check the timestamp on `templates/dashboard.html`

## Quick Test

Run this in the browser console to test everything at once:

```javascript
console.log('=== TOOLBAR DIAGNOSTIC ===');
console.log('1. Toolbar element:', !!document.querySelector('.editor-feature-toolbar'));
console.log('2. togglePreview function:', typeof togglePreview);
console.log('3. openExportDialog function:', typeof openExportDialog);
console.log('4. validateContent function:', typeof validateContent);
console.log('5. AdvancedEditor class:', typeof window.AdvancedEditor);
console.log('6. advancedEditor instance:', typeof advancedEditor);

const toolbar = document.querySelector('.editor-feature-toolbar');
if (toolbar) {
    console.log('7. Toolbar display:', toolbar.style.display);
    console.log('8. Toolbar visible height:', toolbar.offsetHeight);
    console.log('9. Toolbar buttons:', toolbar.querySelectorAll('button').length);
}
console.log('=== END DIAGNOSTIC ===');
```

Copy the output and share it if you need help debugging further.
