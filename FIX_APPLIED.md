# Fix Applied: advancedEditor Scope Issue

## Problem
The feature toolbar buttons were throwing errors:
```
Uncaught ReferenceError: advancedEditor is not defined
```

## Root Cause
The `advancedEditor` variable was declared inside an IIFE (Immediately Invoked Function Expression) with `var`, making it local scope only. The feature toolbar functions (which are global) couldn't access it.

## Solution Applied
Made `advancedEditor` globally accessible by:

1. **Added global reference**: `window.advancedEditor = null;`
2. **Updated assignment**: `advancedEditor = window.advancedEditor = new window.AdvancedEditor({...})`
3. **Updated all function references**: Changed `advancedEditor` to `window.advancedEditor` in:
   - `openExportDialog()`
   - `exportContent()`
   - `openTemplateDialog()`
   - `applyTemplate()`
   - `validateContent()`

## Changes Made

### File: `templates/dashboard.html`

**Line ~254**: Added global reference
```javascript
// Make advancedEditor global so feature toolbar functions can access it
window.advancedEditor = null;
var advancedEditor = null;
```

**Line ~316**: Updated assignment
```javascript
advancedEditor = window.advancedEditor = new window.AdvancedEditor({
```

**All feature functions**: Updated to use `window.advancedEditor`
```javascript
if (!window.advancedEditor) {
  alert('Editor is still loading. Please wait a moment and try again.');
  return;
}
```

## Testing

After applying this fix:

1. **Hard refresh your browser**: `Ctrl + Shift + R`
2. **Restart Flask server** (if needed)
3. **Test each button**:
   - Click "Export" → Should open export modal
   - Click "Templates" → Should open template modal  
   - Click "Validate" → Should validate content
   - Click "Preview" → Should toggle preview pane

## Expected Behavior

✅ **No more "advancedEditor is not defined" errors**
✅ **All buttons should work** (may show "Editor is still loading" if clicked too quickly)
✅ **Functions wait for editor** to be ready before executing

## If Still Not Working

Run this in browser console to verify:
```javascript
console.log('advancedEditor global:', typeof window.advancedEditor);
console.log('advancedEditor value:', window.advancedEditor);
```

Should show:
- `advancedEditor global: object` (after editor loads)
- `advancedEditor value: AdvancedEditor {config: {...}, ...}`

If it shows `undefined`, the editor hasn't initialized yet. Wait a moment and try again.
