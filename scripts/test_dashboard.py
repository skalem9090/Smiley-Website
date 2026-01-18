import requests

s = requests.Session()
base = 'http://127.0.0.1:5000'
# Get login page to fetch csrf token if present
r = s.get(base + '/login')
if r.status_code != 200:
    print('GET /login ->', r.status_code)
    raise SystemExit

# Extract CSRF token from the login page
import re
m = re.search(r'name="csrf_token" type="hidden" value="([^"]+)"', r.text)
csrf = m.group(1) if m else ''
payload = {'username':'admin','password':'devpass','csrf_token':csrf}
r = s.post(base + '/login', data=payload, allow_redirects=True)
print('POST /login ->', r.status_code)
# Try to access dashboard
r = s.get(base + '/dashboard')
print('/dashboard status', r.status_code)
html = r.text
print('--- DASHBOARD HTML INFO ---')
print('length=', len(html))
print('contains cdn:', 'cdn.ckeditor.com' in html)
print('contains local ckeditor fallback:', '/static/ckeditor/ckeditor.js' in html)
print('contains preview element:', 'id="preview"' in html)
print('--- DASHBOARD HTML TAIL ---')
print(html[-800:])
print('--- END ---')
