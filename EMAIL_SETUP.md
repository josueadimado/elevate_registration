# Email Setup Guide

This guide explains how to configure email sending for the ASPIR Program registration system.

## 🧪 Development Mode (Current Setup)

**For testing and development, emails will print to your terminal/console.**

This is already configured in your `.env` file:
```
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

**How it works:**
- When someone makes a payment, the email content will appear in your terminal
- No email account setup is needed
- Perfect for testing the email templates and content
- You can see exactly what emails would be sent

**To test:**
1. Make a test registration and payment
2. Check your terminal/console where you ran `python manage.py runserver`
3. You'll see the email content printed there

---

## 📧 Production Mode (Gmail Setup)

When you're ready to send real emails, follow these steps:

### Step 1: Enable 2-Factor Authentication on Gmail

1. **Go to your Google Account:**
   - Visit: https://myaccount.google.com/
   - Sign in with your Gmail account

2. **Navigate to Security:**
   - Click on "Security" in the left sidebar
   - Or go directly to: https://myaccount.google.com/security

3. **Enable 2-Step Verification:**
   - Find "2-Step Verification" section
   - Click "Get started" or "Turn on"
   - Follow the prompts to set it up
   - You'll need your phone to verify

**Why is this needed?**
- Gmail requires 2-factor authentication to generate App Passwords
- This is a security requirement from Google

---

### Step 2: Generate an App Password

1. **Go back to Security settings:**
   - Visit: https://myaccount.google.com/security

2. **Find "App passwords":**
   - Scroll down to "2-Step Verification" section
   - Click on "App passwords"
   - If you don't see it, make sure 2-Step Verification is enabled first

3. **Create the App Password:**
   - Select "Mail" as the app type
   - Select "Other (Custom name)" as the device
   - Type: "ASPIR Program Django"
   - Click "Generate"

4. **Copy the App Password:**
   - Google will show you a 16-character password
   - It looks like: `abcd efgh ijkl mnop`
   - **Copy this password immediately** (you won't see it again!)
   - Remove the spaces when using it: `abcdefghijklmnop`

**Important Notes:**
- This is NOT your regular Gmail password
- This is a special password just for your Django app
- You can create multiple app passwords for different apps
- If you lose it, just generate a new one

---

### Step 3: Update Your .env File

1. **Open your `.env` file** in the project root

2. **Comment out the console backend** (add `#` at the start):
   ```env
   # EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
   ```

3. **Uncomment and fill in the SMTP settings:**
   ```env
   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_HOST_USER=your-actual-email@gmail.com
   EMAIL_HOST_PASSWORD=abcdefghijklmnop
   DEFAULT_FROM_EMAIL=ASPIR Program <your-email@gmail.com>
   SUPPORT_EMAIL=info@elevatetribeanalytics.com
   ```

4. **Replace these values:**
   - `your-actual-email@gmail.com` → Your actual Gmail address
   - `abcdefghijklmnop` → The App Password you generated (no spaces)
   - Update `DEFAULT_FROM_EMAIL` with your email if needed

5. **Save the file**

6. **Restart your Django server:**
   ```bash
   # Stop the server (Ctrl+C)
   # Then start it again
   python manage.py runserver
   ```

---

### Step 4: Test Email Sending

1. **Make a test registration and payment**
2. **Check the recipient's email inbox** (including spam folder)
3. **Check your terminal** for any error messages

---

## 🔍 Troubleshooting

### "Authentication failed" error:
- Make sure you're using the **App Password**, not your regular Gmail password
- Verify 2-Step Verification is enabled
- Check that the App Password has no spaces

### "Connection refused" error:
- Check your internet connection
- Verify `EMAIL_HOST=smtp.gmail.com` is correct
- Make sure `EMAIL_PORT=587` and `EMAIL_USE_TLS=True`

### Emails going to spam:
- This is normal for new email setups
- Ask recipients to mark as "Not Spam"
- Over time, as you send more emails, this improves

### Still seeing emails in console:
- Make sure you restarted the Django server after changing `.env`
- Check that `EMAIL_BACKEND` is set to `smtp.EmailBackend` (not `console`)

---

## 📝 Quick Reference

**Development (Console):**
```env
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

**Production (Gmail SMTP):**
```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-16-char-app-password
DEFAULT_FROM_EMAIL=ASPIR Program <your-email@gmail.com>
SUPPORT_EMAIL=info@elevatetribeanalytics.com
```

---

## 🎯 Current Status

✅ **You're currently set up for DEVELOPMENT mode**
- Emails will print to your console/terminal
- No Gmail setup needed right now
- Perfect for testing!

When you're ready for production, follow the Gmail setup steps above.
