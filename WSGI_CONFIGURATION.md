# PythonAnywhere WSGI Configuration

## Correct WSGI File Content

Replace the entire content of your WSGI file on PythonAnywhere with this:

```python
import os
import sys

# Add your project directory to the Python path
path = '/home/josueadimado/elevate_registration'
if path not in sys.path:
    sys.path.insert(0, path)

# Set the Django settings module
os.environ['DJANGO_SETTINGS_MODULE'] = 'aspir_project.settings'

# Add virtual environment's site-packages to Python path
venv_path = '/home/josueadimado/elevate_registration/venv'
if os.path.exists(venv_path):
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

# Import Django WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

## How to Update on PythonAnywhere

1. Go to **Web** tab
2. Click on the **WSGI configuration file** link (usually shows as `register_elevatetribelearning_com_wsgi.py`)
3. **Delete all the existing content**
4. **Paste the code above**
5. **Important**: Replace `josueadimado` with your actual PythonAnywhere username if different
6. **Important**: Replace `python3.10` with your actual Python version (could be `python3.9`, `python3.11`, etc.)
7. Click **Save**
8. Go back to **Web** tab and click **Reload**

## Finding Your Python Version

To find which Python version your venv uses:

```bash
cd ~/elevate_registration
source venv/bin/activate
python --version
```

Then check which directory exists:
```bash
ls venv/lib/
```

Use that version number in the WSGI file (e.g., `python3.10`, `python3.11`, etc.)
