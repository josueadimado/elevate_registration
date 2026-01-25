# ASPIR Mentorship Program - Setup Guide

This guide will help you set up the ASPIR Mentorship Program registration and payment system using Django and Paystack.

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Paystack account (for payment processing)

## Installation Steps

### 1. Create a Virtual Environment (Recommended)

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up Environment Variables

Create a `.env` file in the project root (copy from `.env.example`):

```bash
cp .env.example .env
```

Edit `.env` and add your configuration:

- **SECRET_KEY**: Generate a Django secret key (you can use `python manage.py shell` and run `from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())`)
- **PAYSTACK_SECRET_KEY**: Your Paystack secret key (starts with `sk_test_` for test mode)
- **PAYSTACK_PUBLIC_KEY**: Your Paystack public key (starts with `pk_test_` for test mode)
- **PAYSTACK_WEBHOOK_SECRET**: Your Paystack webhook secret (get this from Paystack dashboard)

### 4. Run Database Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Create a Superuser (for Django Admin)

```bash
python manage.py createsuperuser
```

### 6. Collect Static Files

```bash
python manage.py collectstatic
```

### 7. Run the Development Server

```bash
python manage.py runserver
```

The application will be available at `http://localhost:8000`

## Paystack Configuration

### Getting Your Paystack Keys

1. Sign up/login to [Paystack](https://paystack.com)
2. Go to Settings > API Keys & Webhooks
3. Copy your **Test Secret Key** and **Test Public Key**
4. Set up a webhook URL: `https://yourdomain.com/api/paystack/webhook/`
5. Copy the webhook secret from Paystack

### Testing Payments

- Use Paystack test cards: `4084084084084081` (successful payment)
- Use any future expiry date and CVV
- Use any email address

## Project Structure

```
aspir_model/
├── aspir_project/          # Main Django project
│   ├── settings.py         # Django settings
│   ├── urls.py             # Main URL configuration
│   └── ...
├── registrations/           # Main app
│   ├── models.py           # Database models
│   ├── views.py            # View functions
│   ├── forms.py            # Django forms
│   ├── admin.py            # Admin configuration
│   └── templates/          # HTML templates
├── static/                 # Static files (CSS, JS)
│   └── css/
│       └── styles.css
├── manage.py               # Django management script
├── requirements.txt        # Python dependencies
└── .env                    # Environment variables (create this)
```

## Features

- ✅ One-page landing page with registration form
- ✅ Paystack payment integration
- ✅ Webhook handling for payment verification
- ✅ Django admin for managing registrations
- ✅ CSV export functionality
- ✅ Conditional guardian fields (for age < 16)
- ✅ Auto-calculation of payment amounts
- ✅ Mobile-responsive design

## Admin Access

Access the Django admin at: `http://localhost:8000/admin/`

You can:
- View all registrations
- Filter by status, cohort, group, dimension
- Export registrations as CSV
- View transaction details

## Troubleshooting

### Issue: Static files not loading
- Run `python manage.py collectstatic`
- Check `STATIC_URL` and `STATIC_ROOT` in settings.py

### Issue: Paystack webhook not working
- Ensure your webhook URL is accessible (use ngrok for local testing)
- Verify webhook secret matches in `.env`
- Check Paystack dashboard for webhook logs

### Issue: Form validation errors
- Check browser console for JavaScript errors
- Verify all required fields are filled
- Ensure age is between 10-22

## Production Deployment

Before deploying to production:

1. Set `DEBUG=False` in `.env`
2. Set a strong `SECRET_KEY`
3. Configure `ALLOWED_HOSTS` with your domain
4. Set up PostgreSQL database (update `DATABASES` in settings.py)
5. Configure proper static file serving
6. Set up SSL/HTTPS
7. Update Paystack keys to production keys
8. Configure production webhook URL in Paystack

## Support

For issues or questions, please contact the development team.
