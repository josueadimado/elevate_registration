"""
Email sending functions for registration confirmations and payment notifications.
"""
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)


def send_registration_confirmation_email(registration):
    """
    Send registration confirmation email after registration fee payment.
    
    Args:
        registration: Registration instance
    """
    try:
        # Get exchange rate for display
        from .utils import get_usd_to_ngn_rate
        exchange_rate = get_usd_to_ngn_rate()
        
        # Calculate NGN amounts
        reg_fee_ngn = round(float(registration.registration_fee_amount or registration.get_registration_fee()) * exchange_rate, 0)
        course_fee_ngn = round(float(registration.course_fee_amount or registration.get_course_fee()) * exchange_rate, 0)
        total_ngn = round(float(registration.amount) * exchange_rate, 0)
        remaining_ngn = round(float(registration.get_remaining_balance()) * exchange_rate, 0)
        
        # Get the site URL for links
        site_url = getattr(settings, 'SITE_URL', 'https://elevatetribeanalytics.com')
        
        context = {
            'registration': registration,
            'exchange_rate': exchange_rate,
            'reg_fee_ngn': reg_fee_ngn,
            'course_fee_ngn': course_fee_ngn,
            'total_ngn': total_ngn,
            'remaining_ngn': remaining_ngn,
            'support_email': getattr(settings, 'SUPPORT_EMAIL', 'info@elevatetribeanalytics.com'),
            'site_url': site_url,
            'check_status_url': f"{site_url}/check-status/",
        }
        
        # Render email templates
        subject = f'Registration Confirmed - ASPIR Mentorship Program'
        html_message = render_to_string('registrations/emails/registration_confirmation.html', context)
        plain_message = strip_tags(html_message)
        
        # Send email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[registration.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Registration confirmation email sent to {registration.email} for registration {registration.id}")
        
    except Exception as e:
        logger.error(f"Failed to send registration confirmation email: {str(e)}")
        # Don't raise exception - email failure shouldn't break the payment flow


def send_payment_complete_email(registration):
    """
    Send payment complete email when full payment is made (both fees paid).
    
    Args:
        registration: Registration instance
    """
    try:
        # Get exchange rate for display
        from .utils import get_usd_to_ngn_rate
        exchange_rate = get_usd_to_ngn_rate()
        
        # Calculate NGN amounts
        reg_fee_ngn = round(float(registration.registration_fee_amount or registration.get_registration_fee()) * exchange_rate, 0)
        course_fee_ngn = round(float(registration.course_fee_amount or registration.get_course_fee()) * exchange_rate, 0)
        total_ngn = round(float(registration.amount) * exchange_rate, 0)
        
        # Get the site URL for links
        site_url = getattr(settings, 'SITE_URL', 'https://elevatetribeanalytics.com')
        
        context = {
            'registration': registration,
            'exchange_rate': exchange_rate,
            'reg_fee_ngn': reg_fee_ngn,
            'course_fee_ngn': course_fee_ngn,
            'total_ngn': total_ngn,
            'support_email': getattr(settings, 'SUPPORT_EMAIL', 'info@elevatetribeanalytics.com'),
            'site_url': site_url,
            'check_status_url': f"{site_url}/check-status/",
        }
        
        # Render email templates
        subject = f'Payment Complete - Welcome to ASPIR Mentorship Program!'
        html_message = render_to_string('registrations/emails/payment_complete.html', context)
        plain_message = strip_tags(html_message)
        
        # Send email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[registration.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Payment complete email sent to {registration.email} for registration {registration.id}")
        
    except Exception as e:
        logger.error(f"Failed to send payment complete email: {str(e)}")


def send_course_fee_payment_email(registration):
    """
    Send email when course fee is paid (partial payment completion).
    
    Args:
        registration: Registration instance
    """
    try:
        # Get exchange rate for display
        from .utils import get_usd_to_ngn_rate
        exchange_rate = get_usd_to_ngn_rate()
        
        # Calculate NGN amounts
        course_fee_ngn = round(float(registration.course_fee_amount or registration.get_course_fee()) * exchange_rate, 0)
        
        # Get the site URL for links
        site_url = getattr(settings, 'SITE_URL', 'https://elevatetribeanalytics.com')
        
        context = {
            'registration': registration,
            'exchange_rate': exchange_rate,
            'course_fee_ngn': course_fee_ngn,
            'support_email': getattr(settings, 'SUPPORT_EMAIL', 'info@elevatetribeanalytics.com'),
            'site_url': site_url,
            'check_status_url': f"{site_url}/check-status/",
        }
        
        # Render email templates
        subject = f'Course Fee Payment Received - ASPIR Program'
        html_message = render_to_string('registrations/emails/course_fee_paid.html', context)
        plain_message = strip_tags(html_message)
        
        # Send email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[registration.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Course fee payment email sent to {registration.email} for registration {registration.id}")
        
    except Exception as e:
        logger.error(f"Failed to send course fee payment email: {str(e)}")
