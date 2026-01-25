# Production Environment Variables (.env)

Create a `.env` file on your PythonAnywhere server with these settings:

```env
# Django Settings
SECRET_KEY=your-very-secure-secret-key-here-change-this
DEBUG=False
ALLOWED_HOSTS=register.elevatetribelearning.com,www.register.elevatetribelearning.com

# Squad Payment Configuration (Production)
SQUAD_SECRET_KEY=sk_fe6cbc553c2f65e84a93a27012461a4962bcd002
SQUAD_PUBLIC_KEY=pk_fe6cbc553c2f65e83e83a30413570c4c77c0a762
SQUAD_BASE_URL=https://api-d.squadco.com
USD_TO_NGN_RATE=1500.0

# Email Configuration (Production)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=elevatetribeanalytics9@gmail.com
EMAIL_HOST_PASSWORD=rdftfeotvelgtwlo
DEFAULT_FROM_EMAIL=ASPIR Program <noreply@aspirprogram.com>
SUPPORT_EMAIL=info@elevatetribeanalytics.com

# Site URL (for email links)
SITE_URL=https://register.elevatetribelearning.com
```

## Important Notes:

1. **SECRET_KEY**: Generate a new secure key for production:
   ```python
   from django.core.management.utils import get_random_secret_key
   print(get_random_secret_key())
   ```

2. **DEBUG**: Must be `False` in production

3. **ALLOWED_HOSTS**: Include your domain and www subdomain

4. **SQUAD_BASE_URL**: Use production URL `https://api-d.squadco.com` (not sandbox)

5. **SITE_URL**: Used in email templates for generating links
