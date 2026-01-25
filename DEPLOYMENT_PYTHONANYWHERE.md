# Deploying ASPIR Registration System to PythonAnywhere

This guide will help you deploy your Django application to PythonAnywhere.

## Prerequisites

1. A PythonAnywhere account (free or paid)
2. Your GitHub repository URL: `https://github.com/josueadimado/elevate_registration.git`
3. All your environment variables from `.env` file

## Step 1: Clone Your Repository

1. Open a **Bash console** on PythonAnywhere
2. Navigate to your home directory:
   ```bash
   cd ~
   ```
3. Clone your repository:
   ```bash
   git clone https://github.com/josueadimado/elevate_registration.git
   ```
4. Navigate into the project:
   ```bash
   cd elevate_registration
   ```

## Step 2: Set Up Virtual Environment

1. Create a virtual environment:
   ```bash
   python3.10 -m venv venv
   ```
   (Use `python3.9` or `python3.11` if 3.10 is not available)

2. Activate the virtual environment:
   ```bash
   source venv/bin/activate
   ```

3. Upgrade pip:
   ```bash
   pip install --upgrade pip
   ```

## Step 3: Install Dependencies

1. Install all required packages:
   ```bash
   pip install -r requirements.txt
   ```

2. Also install `python-decouple` if not already in requirements:
   ```bash
   pip install python-decouple
   ```

## Step 4: Set Up Environment Variables

1. Create a `.env` file in your project root:
   ```bash
   nano .env
   ```

2. Add all your environment variables (copy from your local `.env` file):
   ```env
   # Django Settings
   SECRET_KEY=your-secret-key-here
   DEBUG=False
   ALLOWED_HOSTS=yourusername.pythonanywhere.com,www.yourdomain.com

   # Squad Configuration
   SQUAD_SECRET_KEY=your-squad-secret-key
   SQUAD_PUBLIC_KEY=your-squad-public-key
   SQUAD_BASE_URL=https://api-d.squadco.com
   USD_TO_NGN_RATE=1500.0

   # Email Configuration
   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_HOST_USER=your-email@gmail.com
   EMAIL_HOST_PASSWORD=your-app-password
   DEFAULT_FROM_EMAIL=ASPIR Program <noreply@aspirprogram.com>
   SUPPORT_EMAIL=info@elevatetribeanalytics.com

   # Database (if using PostgreSQL)
   # DB_NAME=your_db_name
   # DB_USER=your_db_user
   # DB_PASSWORD=your_db_password
   # DB_HOST=yourusername.mysql.pythonanywhere-services.com
   # DB_PORT=3306
   ```

3. Save and exit (Ctrl+X, then Y, then Enter)

## Step 5: Set Up Database

1. Run migrations:
   ```bash
   python manage.py migrate
   ```

2. Create a superuser (for admin access):
   ```bash
   python manage.py createsuperuser
   ```

3. (Optional) Load initial data:
   ```bash
   python manage.py setup_initial_data
   ```

## Step 6: Collect Static Files

1. Collect all static files:
   ```bash
   python manage.py collectstatic --noinput
   ```

## Step 7: Configure Web App on PythonAnywhere

1. Go to the **Web** tab on PythonAnywhere dashboard
2. Click **Add a new web app**
3. Choose **Manual configuration** (not "Django")
4. Select Python version (3.10 or 3.11)

### Configure WSGI File

1. Click on the WSGI configuration file link
2. Replace the entire content with:

```python
import os
import sys

# Add your project directory to the Python path
path = '/home/yourusername/elevate_registration'
if path not in sys.path:
    sys.path.insert(0, path)

# Set the Django settings module
os.environ['DJANGO_SETTINGS_MODULE'] = 'aspir_project.settings'

# Add virtual environment's site-packages to Python path
venv_path = '/home/yourusername/elevate_registration/venv'
if os.path.exists(venv_path):
    # Try python3.10 first
    venv_site_packages = os.path.join(venv_path, 'lib', 'python3.10', 'site-packages')
    if os.path.exists(venv_site_packages):
        if venv_site_packages not in sys.path:
            sys.path.insert(0, venv_site_packages)
    # Try python3.11 if 3.10 doesn't exist
    else:
        venv_site_packages = os.path.join(venv_path, 'lib', 'python3.11', 'site-packages')
        if os.path.exists(venv_site_packages):
            if venv_site_packages not in sys.path:
                sys.path.insert(0, venv_site_packages)
    # Try python3.9 if neither exists
    else:
        venv_site_packages = os.path.join(venv_path, 'lib', 'python3.9', 'site-packages')
        if os.path.exists(venv_site_packages):
            if venv_site_packages not in sys.path:
                sys.path.insert(0, venv_site_packages)

# Import Django WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

**Important:** 
- Replace `yourusername` with your actual PythonAnywhere username!
- The code will automatically detect your Python version (3.9, 3.10, or 3.11)

### Configure Static Files

1. In the **Web** tab, scroll down to **Static files**
2. Add these mappings:

| URL | Directory |
|-----|-----------|
| `/static/` | `/home/yourusername/elevate_registration/staticfiles/` |
| `/media/` | `/home/yourusername/elevate_registration/media/` |

### Configure Source Code

1. In the **Web** tab, under **Source code**:
   - **Working directory**: `/home/yourusername/elevate_registration`

## Step 8: Update Django Settings

1. Edit your `settings.py` file:
   ```bash
   nano aspir_project/settings.py
   ```

2. Make sure these settings are correct:

```python
# At the top, after imports
from decouple import config

# Debug mode - MUST be False in production
DEBUG = config('DEBUG', default=False, cast=bool)

# Allowed hosts - add your PythonAnywhere domain
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Media files (if needed)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
```

## Step 9: Reload Web App

1. Go to the **Web** tab
2. Click the big green **Reload** button
3. Your site should now be live!

## Step 10: Test Your Deployment

1. Visit your site: `https://yourusername.pythonanywhere.com`
2. Test the registration form
3. Test the admin panel: `https://yourusername.pythonanywhere.com/admin-panel/`
4. Test email sending (check your email inbox)

## Troubleshooting

### Common Issues:

1. **500 Error**: Check the error log in the **Web** tab
2. **Static files not loading**: Make sure `collectstatic` ran successfully
3. **Database errors**: Check your database configuration in settings.py
4. **Email not sending**: Verify your email credentials in `.env`
5. **Module not found**: Make sure virtual environment is activated and dependencies are installed

### Viewing Logs:

- **Error log**: Web tab → Error log
- **Server log**: Web tab → Server log

## Security Checklist

- [ ] `DEBUG = False` in production
- [ ] `SECRET_KEY` is set and secure
- [ ] `ALLOWED_HOSTS` includes your domain
- [ ] `.env` file is not in version control (already in `.gitignore`)
- [ ] Database credentials are secure
- [ ] Email credentials are secure

## Custom Domain Setup (Optional)

If you have a custom domain:

1. Go to **Web** tab → **Static files**
2. Add your domain to `ALLOWED_HOSTS` in `.env`
3. Point your domain's DNS to PythonAnywhere's IP
4. Add domain in PythonAnywhere **Web** tab → **Domains**

## Updating Your Site

When you make changes:

1. Pull latest code:
   ```bash
   cd ~/elevate_registration
   git pull origin main
   ```

2. Activate virtual environment:
   ```bash
   source venv/bin/activate
   ```

3. Install new dependencies (if any):
   ```bash
   pip install -r requirements.txt
   ```

4. Run migrations (if any):
   ```bash
   python manage.py migrate
   ```

5. Collect static files:
   ```bash
   python manage.py collectstatic --noinput
   ```

6. Reload web app in PythonAnywhere dashboard

## Need Help?

- PythonAnywhere Docs: https://help.pythonanywhere.com/
- Django Deployment: https://docs.djangoproject.com/en/stable/howto/deployment/
