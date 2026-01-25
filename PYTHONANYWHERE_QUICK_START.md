# PythonAnywhere Quick Start Guide

## Quick Setup Steps

### 1. Clone Repository
```bash
cd ~
git clone https://github.com/josueadimado/elevate_registration.git
cd elevate_registration
```

### 2. Create Virtual Environment
```bash
python3.10 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Create .env File
```bash
nano .env
```

Paste your environment variables (from your local .env file) and update:
- `DEBUG=False`
- `ALLOWED_HOSTS=yourusername.pythonanywhere.com`

### 4. Database Setup
```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

### 5. Configure Web App

1. Go to **Web** tab → **Add a new web app**
2. Choose **Manual configuration**
3. Select Python version

### 6. WSGI Configuration

Click on WSGI file and replace with:

```python
import os
import sys

path = '/home/YOURUSERNAME/elevate_registration'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'aspir_project.settings'

activate_this = '/home/YOURUSERNAME/elevate_registration/venv/bin/activate_this.py'
with open(activate_this) as f:
    exec(f.read(), {'__file__': activate_this})

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

**Replace YOURUSERNAME with your actual username!**

### 7. Static Files

In **Web** tab → **Static files**:
- URL: `/static/`
- Directory: `/home/YOURUSERNAME/elevate_registration/staticfiles/`

### 8. Reload

Click the green **Reload** button in the Web tab.

## Your Site URLs

- Home: `https://yourusername.pythonanywhere.com/`
- Register: `https://yourusername.pythonanywhere.com/register/`
- Admin: `https://yourusername.pythonanywhere.com/admin-panel/`
- Check Status: `https://yourusername.pythonanywhere.com/check-status/`

## Important Notes

1. **Free accounts**: Can only use `yourusername.pythonanywhere.com` domain
2. **Paid accounts**: Can use custom domains
3. **Database**: Free accounts use SQLite (included), paid can use MySQL
4. **HTTPS**: Automatically enabled on PythonAnywhere

## Troubleshooting

- **500 Error**: Check Error log in Web tab
- **Static files 404**: Run `collectstatic` again
- **Import errors**: Make sure virtual environment path is correct in WSGI
