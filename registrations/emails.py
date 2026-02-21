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


# Staff addresses to notify when any payment goes through (full or partial)
STAFF_PAYMENT_NOTIFICATION_EMAILS = [
    'elevatetribeanalytics9@gmail.com',
    'amosbenita7@gmail.com',
]


def send_staff_payment_notification_email(registration, payment_type, amount_paid_usd, reference=''):
    """
    Notify staff (elevatetribeanalytics9@gmail.com, amosbenita7@gmail.com) when a
    payment goes through, so they know who paid and whether it was full or partial.
    """
    recipient_list = getattr(
        settings, 'STAFF_PAYMENT_NOTIFICATION_EMAILS', STAFF_PAYMENT_NOTIFICATION_EMAILS
    )
    if not recipient_list:
        return
    try:
        is_full = registration.is_fully_paid()
        payment_type_display = {
            'full_payment': 'Full payment (registration + course fee)',
            'registration_fee': 'Registration fee only',
            'course_fee': 'Course fee only',
        }.get(payment_type, payment_type.replace('_', ' ').title())
        remaining = float(registration.get_remaining_balance()) if not is_full else 0

        context = {
            'registration': registration,
            'is_full_payment': is_full,
            'payment_type_display': payment_type_display,
            'amount_paid_usd': f'{float(amount_paid_usd):.2f}',
            'remaining_balance': f'{remaining:.2f}',
            'reference': reference or getattr(registration, '_last_transaction_ref', ''),
        }
        subject = f'ASPIR: Payment received – {"Full" if is_full else "Partial"} – {registration.full_name}'
        html_message = render_to_string('registrations/emails/staff_payment_notification.html', context)
        plain_message = strip_tags(html_message)

        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=list(recipient_list),
            html_message=html_message,
            fail_silently=True,
        )
        logger.info(f"Staff payment notification sent for registration {registration.id} ({payment_type})")
    except Exception as e:
        logger.error(f"Failed to send staff payment notification: {str(e)}")


def send_participant_id_email(registration):
    """
    Send an email to the participant with their ASPIR participant ID.
    Use when generating/sending ID to existing registrations (e.g. from admin).
    Generates the ID if missing (when cohort is set).
    """
    from .utils import generate_participant_id

    # Ensure ID exists (generate if possible; only cohort is required)
    if not getattr(registration, 'participant_id', None) and registration.cohort:
        generate_participant_id(registration)

    if not registration.participant_id:
        logger.warning(f"Cannot send participant ID email: no participant_id and cannot generate (registration {registration.id})")
        return False

    try:
        site_url = getattr(settings, 'SITE_URL', 'https://elevatetribeanalytics.com')
        context = {
            'registration': registration,
            'support_email': getattr(settings, 'SUPPORT_EMAIL', 'info@elevatetribeanalytics.com'),
            'site_url': site_url,
        }
        subject = 'Your ASPIR Participant ID'
        html_message = render_to_string('registrations/emails/participant_id_email.html', context)
        plain_message = strip_tags(html_message)
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[registration.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Participant ID email sent to {registration.email} for registration {registration.id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send participant ID email: {str(e)}")
        return False
