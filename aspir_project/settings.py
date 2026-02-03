"""
Django settings for aspir_project project.
"""

from pathlib import Path
from decouple import config
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-this-in-production-12345')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=lambda v: [s.strip() for s in v.split(',')])


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'registrations',  # Our main app
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'aspir_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
            ],
        },
    },
]

WSGI_APPLICATION = 'aspir_project.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'OPTIONS': {
            'timeout': 20,  # Add timeout to prevent hanging
        },
    }
}

# For PostgreSQL (uncomment when ready):
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': config('DB_NAME', default='aspir_db'),
#         'USER': config('DB_USER', default='postgres'),
#         'PASSWORD': config('DB_PASSWORD', default=''),
#         'HOST': config('DB_HOST', default='localhost'),
#         'PORT': config('DB_PORT', default='5432'),
#     }
# }


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

# Authentication settings
LOGIN_URL = '/admin-panel/login/'
LOGIN_REDIRECT_URL = '/admin-panel/dashboard/'
LOGOUT_REDIRECT_URL = '/admin-panel/login/'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files (for user uploads if needed)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Optimize static files finders for faster startup
# Only use necessary finders in development
if DEBUG:
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
else:
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Squad Payment Configuration
SQUAD_SECRET_KEY = config('SQUAD_SECRET_KEY', default='')
SQUAD_PUBLIC_KEY = config('SQUAD_PUBLIC_KEY', default='')
# Use production URL for live site, sandbox for testing.
_squad_base = config('SQUAD_BASE_URL', default='')
if not _squad_base:
    _squad_base = 'https://api-d.squadco.com' if not DEBUG else 'https://sandbox-api-d.squadco.com'
# Safeguard: live host must never use Squad sandbox (fix truncation or wrong env)
if 'elevatetribelearning.com' in str(ALLOWED_HOSTS) or not _squad_base.endswith('.com'):
    _squad_base = 'https://api-d.squadco.com'
SQUAD_BASE_URL = _squad_base

# Paystack Payment Configuration (alternative gateway)
PAYSTACK_SECRET_KEY = config('PAYSTACK_SECRET_KEY', default='')
PAYSTACK_PUBLIC_KEY = config('PAYSTACK_PUBLIC_KEY', default='')
PAYSTACK_WEBHOOK_SECRET = config('PAYSTACK_WEBHOOK_SECRET', default='')
PAYSTACK_BASE_URL = 'https://api.paystack.co'

# USD to NGN exchange rate (fallback if API fails)
USD_TO_NGN_RATE = config('USD_TO_NGN_RATE', default=1500.0, cast=float)  # Fallback rate

# Cache Configuration (for exchange rate caching)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
        'TIMEOUT': 3600,  # 1 hour default timeout
    }
}

# CORS Settings (for API endpoints)
CORS_ALLOWED_ORIGINS = [
    "https://register.elevatetribelearning.com",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Allow all origins in development (for testing)
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True

CORS_ALLOW_CREDENTIALS = True

# Security settings for production
if not DEBUG:
    # HTTPS/SSL Security
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')  # For PythonAnywhere
    
    # HSTS (HTTP Strict Transport Security)
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    
    # Additional security headers
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
else:
    # Development settings - suppress security warnings
    # These warnings are expected in development and safe to ignore
    # They will be properly configured for production
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

# Logging Configuration - Optimized for faster startup
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',  # Reduce logging verbosity
            'propagate': False,
        },
        'registrations': {
            'handlers': ['console'],
            'level': 'INFO',  # Changed from DEBUG to INFO for faster startup
            'propagate': False,
        },
    },
}

# Performance optimizations for development
if DEBUG:
    # Disable some checks that slow down startup
    # Silencing security warnings in development (they're expected)
    SILENCED_SYSTEM_CHECKS = [
        'security.W004',  # HSTS not set (not needed in dev)
        'security.W008',  # SSL redirect not set (not needed in dev)
        'security.W012',  # Session cookie secure (not needed in dev)
        'security.W016',  # CSRF cookie secure (not needed in dev)
        'security.W018',  # DEBUG=True (expected in dev)
    ]

# Email Configuration
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend' if DEBUG else 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=False, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='ASPIR Program <noreply@aspirprogram.com>')
SERVER_EMAIL = config('SERVER_EMAIL', default=DEFAULT_FROM_EMAIL)

# Support email (for contact information)
SUPPORT_EMAIL = config('SUPPORT_EMAIL', default='info@elevatetribeanalytics.com')

# Site URL for email links and absolute URLs
SITE_URL = config('SITE_URL', default='https://register.elevatetribelearning.com' if not DEBUG else 'http://localhost:8000')
