"""
Views for the ASPIR registration landing page and payment processing.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.urls import reverse
from .forms import RegistrationForm
from .models import (
    Registration, Cohort, Dimension, PricingConfig, ProgramSettings
)
from .utils import get_usd_to_ngn_rate
from .emails import send_registration_confirmation_email, send_payment_complete_email, send_course_fee_payment_email
import requests
import json
import hmac
import hashlib


def home(request):
    """
    Home page view.
    """
    cohorts = Cohort.objects.filter(is_active=True).order_by('name')
    dimensions = Dimension.objects.filter(is_active=True).order_by('code')
    
    # Get pricing for display
    pricing = {}
    all_pricing = PricingConfig.objects.filter(is_active=True)
    for p in all_pricing:
        pricing[p.enrollment_type] = {
            'registration_fee': float(p.registration_fee),
            'course_fee': float(p.course_fee),
            'total': float(p.total_amount),
        }
    
    context = {
        'cohorts': cohorts,
        'dimensions': dimensions,
        'pricing': pricing,
    }
    return render(request, 'registrations/home.html', context)


def register(request):
    """
    Registration form view.
    """
    cohorts = Cohort.objects.filter(is_active=True).order_by('name')
    dimensions = Dimension.objects.filter(is_active=True).order_by('code')
    
    # Get current pricing config (default to NEW enrollment type)
    try:
        pricing_config = PricingConfig.objects.get(enrollment_type='NEW', is_active=True)
    except PricingConfig.DoesNotExist:
        pricing_config = None
    
    # Get all pricing for JavaScript
    all_pricing = {}
    pricing_ngn = {}
    exchange_rate = get_usd_to_ngn_rate()
    
    for p in PricingConfig.objects.filter(is_active=True):
        all_pricing[p.enrollment_type] = {
            'registration_fee': float(p.registration_fee),
            'course_fee': float(p.course_fee),
            'total': float(p.total_amount),
        }
        # Calculate NGN equivalents
        pricing_ngn[p.enrollment_type] = {
            'registration_fee': round(float(p.registration_fee) * exchange_rate, 0),
            'course_fee': round(float(p.course_fee) * exchange_rate, 0),
            'total': round(float(p.total_amount) * exchange_rate, 0),
        }
    
    # Calculate current NGN amounts for display
    if pricing_config:
        current_reg_fee_ngn = round(float(pricing_config.registration_fee) * exchange_rate, 0)
        current_course_fee_ngn = round(float(pricing_config.course_fee) * exchange_rate, 0)
        current_total_ngn = round(float(pricing_config.total_amount) * exchange_rate, 0)
    else:
        current_reg_fee_ngn = 0
        current_course_fee_ngn = 0
        current_total_ngn = 0
    
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            registration = form.save(commit=False)
            # Calculate total amount
            registration.amount = registration.calculate_amount()
            registration.save()
            return redirect('success', reference=registration.squad_reference or registration.paystack_reference)
    else:
        form = RegistrationForm()
    
    context = {
        'form': form,
        'cohorts': cohorts,
        'dimensions': dimensions,
        'pricing_config': pricing_config,
        'all_pricing': all_pricing,
        'pricing_ngn': pricing_ngn,
        'exchange_rate': exchange_rate,
        'current_reg_fee_ngn': current_reg_fee_ngn,
        'current_course_fee_ngn': current_course_fee_ngn,
        'current_total_ngn': current_total_ngn,
    }
    return render(request, 'registrations/register.html', context)


def success(request):
    """
    Payment success confirmation page.
    """
    reference = request.GET.get('reference', '')
    
    if reference:
        try:
            # Handle ASPIR-REG-{id}, ASPIR-COURSE-{id}, and ASPIR-FULL-{id} formats
            if reference.startswith('ASPIR-REG-'):
                # Extract registration ID from reference (everything after "ASPIR-REG-")
                registration_id = reference[len('ASPIR-REG-'):]
                registration = Registration.objects.get(id=registration_id)
            elif reference.startswith('ASPIR-COURSE-'):
                # Extract registration ID from reference (everything after "ASPIR-COURSE-")
                registration_id = reference[len('ASPIR-COURSE-'):]
                registration = Registration.objects.get(id=registration_id)
            elif reference.startswith('ASPIR-FULL-'):
                # Extract registration ID from reference (everything after "ASPIR-FULL-")
                registration_id = reference[len('ASPIR-FULL-'):]
                registration = Registration.objects.get(id=registration_id)
            else:
                # Try squad_reference first, fallback to paystack_reference for backward compatibility
                try:
                    registration = Registration.objects.get(squad_reference=reference)
                except Registration.DoesNotExist:
                    registration = Registration.objects.get(paystack_reference=reference)
            
            # Get exchange rate for display
            exchange_rate = get_usd_to_ngn_rate()
            
            # Calculate NGN amounts for display
            reg_fee_ngn = round(float(registration.registration_fee_amount or registration.get_registration_fee()) * exchange_rate, 0)
            course_fee_ngn = round(float(registration.course_fee_amount or registration.get_course_fee()) * exchange_rate, 0)
            total_amount_ngn = round(float(registration.amount) * exchange_rate, 0)
            
            context = {
                'registration': registration,
                'reference': reference,
                'exchange_rate': exchange_rate,
                'reg_fee_ngn': reg_fee_ngn,
                'course_fee_ngn': course_fee_ngn,
                'total_amount_ngn': total_amount_ngn,
            }
            return render(request, 'registrations/success.html', context)
        except Registration.DoesNotExist:
            messages.error(request, 'Registration not found.')
    
    return redirect('home')


@csrf_exempt
@require_http_methods(["POST"])
def initialize_payment(request):
    """
    Initialize payment with Squad payment gateway.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    form = RegistrationForm(request.POST)
    if not form.is_valid():
        return JsonResponse({
            'error': 'Form validation failed',
            'errors': form.errors
        }, status=400)
    
    registration = form.save(commit=False)
    registration.amount = registration.calculate_amount()
    
    # Get pricing config to save fee amounts
    try:
        pricing = PricingConfig.objects.get(
            enrollment_type=registration.enrollment_type,
            is_active=True
        )
        registration.registration_fee_amount = pricing.registration_fee
        registration.course_fee_amount = pricing.course_fee
    except PricingConfig.DoesNotExist:
        # Fallback to default values
        registration.registration_fee_amount = 50.00 if registration.enrollment_type == 'NEW' else 20.00
        registration.course_fee_amount = 100.00
    
    registration.save()
    
    # Get payment option from form data
    payment_option = request.POST.get('payment_option', 'partial')  # Default to partial
    
    # Determine payment amount and reference based on option
    if payment_option == 'full':
        # Full payment - charge total amount
        payment_amount = float(registration.amount)
        reference = f"ASPIR-FULL-{registration.id}"
        payment_type = 'full_payment'
    else:
        # Partial payment - charge only registration fee
        payment_amount = float(registration.registration_fee_amount)
        reference = f"ASPIR-REG-{registration.id}"
        payment_type = 'registration_fee'
    
    registration.squad_reference = reference
    registration.save()
    
    # Initialize Squad transaction
    url = f"{settings.SQUAD_BASE_URL}/transaction/initiate"
    
    auth_key = settings.SQUAD_SECRET_KEY.strip()
    if not auth_key:
        return JsonResponse({
            'error': 'Squad API key not configured',
            'message': 'Please set SQUAD_SECRET_KEY in your .env file'
        }, status=500)
    
    if not auth_key.startswith('Bearer '):
        auth_key = f'Bearer {auth_key}'
    
    headers = {
        'Authorization': auth_key,
        'Content-Type': 'application/json',
    }
    
    # Convert amount from USD to NGN to kobo
    exchange_rate = get_usd_to_ngn_rate()
    amount_in_ngn = payment_amount * exchange_rate
    amount_in_kobo = int(amount_in_ngn * 100)
    
    payload = {
        'email': registration.email,
        'amount': str(amount_in_kobo),
        'currency': 'NGN',
        'initiate_type': 'inline',
        'transaction_ref': reference,
        'customer_name': registration.full_name,
        'callback_url': request.build_absolute_uri(f'/success/?reference={reference}'),
        'payment_channels': ['card', 'bank', 'ussd', 'transfer'],
        'metadata': {
            'student_name': registration.full_name,
            'cohort': registration.cohort.name if registration.cohort else (registration.cohort_code or 'N/A'),
            'group': registration.get_group_display(),
            'dimension': registration.dimension.name if registration.dimension else (registration.dimension_code or 'N/A'),
            'enrollment_type': registration.get_enrollment_type_display(),
            'payment_type': payment_type,
            'original_amount_usd': str(payment_amount),
            'registration_fee': str(registration.registration_fee_amount),
            'course_fee': str(registration.course_fee_amount),
            'total_amount': str(registration.amount),
            'exchange_rate': str(exchange_rate),
        },
        'pass_charge': False,
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        data = response.json()
        
        if data.get('status') == 200 and data.get('data'):
            checkout_url = data['data'].get('checkout_url')
            if checkout_url:
                return JsonResponse({
                    'status': 'success',
                    'authorization_url': checkout_url,
                    'reference': reference,
                })
            else:
                error_message = data.get('message', 'No checkout URL returned')
                return JsonResponse({
                    'error': 'Failed to initialize payment',
                    'message': error_message,
                    'squad_response': data,
                    'status_code': response.status_code
                }, status=400)
        else:
            error_message = data.get('message', 'Unknown error')
            return JsonResponse({
                'error': 'Failed to initialize payment',
                'message': error_message,
                'squad_response': data,
                'status_code': response.status_code
            }, status=400)
    
    except Exception as e:
        return JsonResponse({
            'error': 'Payment initialization failed',
            'message': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def pay_registration_fee(request, registration_id):
    """
    Initialize payment for registration fee (for existing registrations).
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        registration = Registration.objects.get(id=registration_id)
    except Registration.DoesNotExist:
        return JsonResponse({'error': 'Registration not found'}, status=404)
    
    # Check if registration fee is already paid
    if registration.registration_fee_paid:
        return JsonResponse({'error': 'Registration fee already paid'}, status=400)
    
    # Generate unique reference for registration fee payment
    reference = f"ASPIR-REG-{registration.id}"
    
    # Initialize Squad transaction
    url = f"{settings.SQUAD_BASE_URL}/transaction/initiate"
    
    auth_key = settings.SQUAD_SECRET_KEY.strip()
    if not auth_key:
        return JsonResponse({
            'error': 'Squad API key not configured',
            'message': 'Please set SQUAD_SECRET_KEY in your .env file'
        }, status=500)
    
    if not auth_key.startswith('Bearer '):
        auth_key = f'Bearer {auth_key}'
    
    headers = {
        'Authorization': auth_key,
        'Content-Type': 'application/json',
    }
    
    # Convert registration fee from USD to NGN to kobo
    exchange_rate = get_usd_to_ngn_rate()
    reg_fee_amount = float(registration.registration_fee_amount or registration.get_registration_fee())
    amount_in_ngn = reg_fee_amount * exchange_rate
    amount_in_kobo = int(amount_in_ngn * 100)
    
    payload = {
        'email': registration.email,
        'amount': str(amount_in_kobo),
        'currency': 'NGN',
        'initiate_type': 'inline',
        'transaction_ref': reference,
        'customer_name': registration.full_name,
        'callback_url': request.build_absolute_uri(f'/success/?reference={reference}'),
        'payment_channels': ['card', 'bank', 'ussd', 'transfer'],
        'metadata': {
            'student_name': registration.full_name,
            'cohort': registration.cohort.name if registration.cohort else (registration.cohort_code or 'N/A'),
            'group': registration.get_group_display(),
            'dimension': registration.dimension.name if registration.dimension else (registration.dimension_code or 'N/A'),
            'enrollment_type': registration.get_enrollment_type_display(),
            'payment_type': 'registration_fee',
            'original_amount_usd': str(reg_fee_amount),
            'registration_fee': str(registration.registration_fee_amount),
            'course_fee': str(registration.course_fee_amount),
            'total_amount': str(registration.amount),
            'exchange_rate': str(exchange_rate),
        },
        'pass_charge': False,
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        data = response.json()
        
        if data.get('status') == 200 and data.get('data'):
            checkout_url = data['data'].get('checkout_url')
            if checkout_url:
                # Update registration with the reference
                registration.squad_reference = reference
                registration.save()
                
                return JsonResponse({
                    'status': 'success',
                    'authorization_url': checkout_url,
                    'reference': reference,
                })
            else:
                return JsonResponse({
                    'error': 'Failed to initialize payment',
                    'message': 'No checkout URL returned',
                    'squad_response': data
                }, status=400)
        else:
            return JsonResponse({
                'error': 'Failed to initialize payment',
                'message': data.get('message', 'Unknown error'),
                'squad_response': data
            }, status=400)
    
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error initializing registration fee payment: {str(e)}")
        return JsonResponse({
            'error': 'Payment initialization failed',
            'message': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def pay_course_fee(request, registration_id):
    """
    Initialize payment for remaining course fee.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        registration = Registration.objects.get(id=registration_id)
    except Registration.DoesNotExist:
        return JsonResponse({'error': 'Registration not found'}, status=404)
    
    # Check if course fee is already paid
    if registration.course_fee_paid:
        return JsonResponse({'error': 'Course fee already paid'}, status=400)
    
    # Check if registration fee is paid
    if not registration.registration_fee_paid:
        return JsonResponse({'error': 'Registration fee must be paid first'}, status=400)
    
    # Generate unique reference for course fee payment
    reference = f"ASPIR-COURSE-{registration.id}"
    
    # Initialize Squad transaction
    url = f"{settings.SQUAD_BASE_URL}/transaction/initiate"
    
    auth_key = settings.SQUAD_SECRET_KEY.strip()
    if not auth_key:
        return JsonResponse({
            'error': 'Squad API key not configured',
            'message': 'Please set SQUAD_SECRET_KEY in your .env file'
        }, status=500)
    
    if not auth_key.startswith('Bearer '):
        auth_key = f'Bearer {auth_key}'
    
    headers = {
        'Authorization': auth_key,
        'Content-Type': 'application/json',
    }
    
    # Convert course fee from USD to NGN to kobo
    exchange_rate = get_usd_to_ngn_rate()
    course_fee_amount = float(registration.course_fee_amount or registration.get_course_fee())
    amount_in_ngn = course_fee_amount * exchange_rate
    amount_in_kobo = int(amount_in_ngn * 100)
    
    payload = {
        'email': registration.email,
        'amount': str(amount_in_kobo),
        'currency': 'NGN',
        'initiate_type': 'inline',
        'transaction_ref': reference,
        'customer_name': registration.full_name,
        'callback_url': request.build_absolute_uri(f'/success/?reference={reference}'),
        'payment_channels': ['card', 'bank', 'ussd', 'transfer'],
        'metadata': {
            'student_name': registration.full_name,
            'cohort': registration.cohort.name if registration.cohort else (registration.cohort_code or 'N/A'),
            'group': registration.get_group_display(),
            'dimension': registration.dimension.name if registration.dimension else (registration.dimension_code or 'N/A'),
            'enrollment_type': registration.get_enrollment_type_display(),
            'payment_type': 'course_fee',
            'original_amount_usd': str(course_fee_amount),
            'registration_fee': str(registration.registration_fee_amount),
            'course_fee': str(registration.course_fee_amount),
            'total_amount': str(registration.amount),
            'exchange_rate': str(exchange_rate),
        },
        'pass_charge': False,
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        data = response.json()
        
        if data.get('status') == 200 and data.get('data'):
            checkout_url = data['data'].get('checkout_url')
            if checkout_url:
                return JsonResponse({
                    'status': 'success',
                    'authorization_url': checkout_url,
                    'reference': reference,
                })
            else:
                return JsonResponse({
                    'error': 'Failed to initialize payment',
                    'message': 'No checkout URL returned',
                    'squad_response': data
                }, status=400)
        else:
            return JsonResponse({
                'error': 'Failed to initialize payment',
                'message': data.get('message', 'Unknown error'),
                'squad_response': data
            }, status=400)
    
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error initializing course fee payment: {str(e)}")
        return JsonResponse({
            'error': 'Payment initialization failed',
            'message': str(e)
        }, status=500)


def verify_payment(request):
    """
    Verify payment status with Squad.
    """
    reference = request.GET.get('reference', '')
    
    if not reference:
        return JsonResponse({'error': 'Reference is required'}, status=400)
    
    try:
        # Handle ASPIR-REG-{id}, ASPIR-COURSE-{id}, and ASPIR-FULL-{id} formats
        if reference.startswith('ASPIR-REG-'):
            registration_id = reference[len('ASPIR-REG-'):]
            registration = Registration.objects.get(id=registration_id)
        elif reference.startswith('ASPIR-COURSE-'):
            registration_id = reference[len('ASPIR-COURSE-'):]
            registration = Registration.objects.get(id=registration_id)
        elif reference.startswith('ASPIR-FULL-'):
            registration_id = reference[len('ASPIR-FULL-'):]
            registration = Registration.objects.get(id=registration_id)
        else:
            registration = Registration.objects.get(squad_reference=reference)
        
        # Verify with Squad API
        url = f"{settings.SQUAD_BASE_URL}/transaction"
        
        # Format authorization header - Squad requires Bearer token
        auth_key = settings.SQUAD_SECRET_KEY.strip()
        if not auth_key.startswith('Bearer '):
            auth_key = f'Bearer {auth_key}'
        
        headers = {
            'Authorization': auth_key,
            'Content-Type': 'application/json',
        }
        
        params = {
            'reference': reference,
            'currency': 'NGN',
        }
        
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        
        if data.get('status') == 200 and data.get('success'):
            transactions = data.get('data', [])
            if transactions:
                transaction = transactions[0]
                if transaction.get('transaction_status', '').lower() == 'success':
                    registration.status = 'PAID'
                    registration.save()
                    return JsonResponse({
                        'status': 'success',
                        'message': 'Payment verified successfully',
                        'registration': {
                            'name': registration.full_name,
                            'cohort': registration.cohort.name if registration.cohort else 'N/A',
                            'group': registration.get_group_display(),
                            'dimension': registration.dimension.name if registration.dimension else 'N/A',
                        }
                    })
        
        return JsonResponse({
            'status': 'failed',
            'message': 'Payment verification failed',
            'squad_response': data
        })
    
    except Registration.DoesNotExist:
        return JsonResponse({'error': 'Registration not found'}, status=404)
    except Exception as e:
        return JsonResponse({
            'error': 'Verification failed',
            'message': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def squad_webhook(request):
    """
    Handle Squad webhook notifications.
    Updates registration status based on payment events.
    """
    # Parse webhook data
    try:
        payload = json.loads(request.body)
        event = payload.get('Event')
        body = payload.get('Body', {})
        
        if event == 'charge_successful':
            transaction_ref = body.get('transaction_ref') or payload.get('TransactionRef')
            
            if not transaction_ref:
                return HttpResponse('Missing transaction reference', status=400)
            
            try:
                # Try to find registration by reference (could be registration fee, course fee, or full payment)
                # Handle ASPIR-REG-{id}, ASPIR-COURSE-{id}, and ASPIR-FULL-{id} formats
                if transaction_ref.startswith('ASPIR-REG-'):
                    # Extract registration ID from reference (everything after "ASPIR-REG-")
                    registration_id = transaction_ref[len('ASPIR-REG-'):]
                    registration = Registration.objects.get(id=registration_id)
                elif transaction_ref.startswith('ASPIR-COURSE-'):
                    # Extract registration ID from reference (everything after "ASPIR-COURSE-")
                    registration_id = transaction_ref[len('ASPIR-COURSE-'):]
                    registration = Registration.objects.get(id=registration_id)
                elif transaction_ref.startswith('ASPIR-FULL-'):
                    # Extract registration ID from reference (everything after "ASPIR-FULL-")
                    registration_id = transaction_ref[len('ASPIR-FULL-'):]
                    registration = Registration.objects.get(id=registration_id)
                else:
                    # Legacy format: try direct lookup
                    registration = Registration.objects.get(squad_reference=transaction_ref)
                
                # Update registration status
                transaction_status = body.get('transaction_status', '').lower()
                if transaction_status == 'success':
                    # Check payment type from metadata
                    metadata = body.get('meta', {}) or payload.get('metadata', {})
                    payment_type = metadata.get('payment_type', 'registration_fee')
                    
                    # Track previous payment status to determine which email to send
                    was_fully_paid_before = registration.is_fully_paid()
                    
                    if payment_type == 'full_payment' or transaction_ref.startswith('ASPIR-FULL-'):
                        # Full payment - mark both fees as paid
                        registration.registration_fee_paid = True
                        registration.course_fee_paid = True
                        registration.status = 'PAID'
                    elif payment_type == 'registration_fee' or transaction_ref.startswith('ASPIR-REG-'):
                        registration.registration_fee_paid = True
                        registration.status = 'PENDING'  # Still pending course fee
                    elif payment_type == 'course_fee' or transaction_ref.startswith('ASPIR-COURSE-'):
                        registration.course_fee_paid = True
                        # Check if fully paid
                        if registration.registration_fee_paid and registration.course_fee_paid:
                            registration.status = 'PAID'
                        else:
                            registration.status = 'PENDING'
                    else:
                        # Legacy: assume full payment
                        registration.registration_fee_paid = True
                        registration.course_fee_paid = True
                        registration.status = 'PAID'
                    
                    registration.save()
                    
                    # Send appropriate email based on payment type
                    try:
                        if payment_type == 'full_payment' or transaction_ref.startswith('ASPIR-FULL-'):
                            # Full payment - send payment complete email
                            send_payment_complete_email(registration)
                        elif payment_type == 'registration_fee' or transaction_ref.startswith('ASPIR-REG-'):
                            # Registration fee paid - send registration confirmation
                            send_registration_confirmation_email(registration)
                        elif payment_type == 'course_fee' or transaction_ref.startswith('ASPIR-COURSE-'):
                            # Course fee paid - check if fully paid now
                            if registration.is_fully_paid():
                                # Just became fully paid - send payment complete email
                                send_payment_complete_email(registration)
                            else:
                                # Only course fee paid (registration fee was already paid) - send course fee confirmation
                                send_course_fee_payment_email(registration)
                        else:
                            # Legacy: assume full payment
                            send_payment_complete_email(registration)
                    except Exception as email_error:
                        # Log email error but don't fail the webhook
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"Failed to send email for registration {registration.id}: {str(email_error)}")
                    
                    # Create transaction record
                    from .models import Transaction
                    from django.utils.dateparse import parse_datetime
                    
                    # Convert amount from kobo to NGN, then back to USD for storage
                    # Get the exchange rate used (from metadata if available, otherwise fetch current)
                    exchange_rate = float(body.get('meta', {}).get('exchange_rate', 0))
                    if not exchange_rate:
                        exchange_rate = get_usd_to_ngn_rate()
                    
                    amount_in_kobo = float(body.get('amount', 0))
                    amount_in_ngn = amount_in_kobo / 100
                    amount_in_usd = amount_in_ngn / exchange_rate
                    
                    paid_at_str = body.get('created_at')
                    paid_at = None
                    if paid_at_str:
                        try:
                            paid_at = parse_datetime(paid_at_str)
                        except:
                            from django.utils import timezone
                            paid_at = timezone.now()
                    
                    Transaction.objects.create(
                        registration=registration,
                        reference=transaction_ref,
                        amount=amount_in_usd,  # Store in USD
                        currency='USD',
                        paid_at=paid_at,
                        channel=body.get('transaction_type', ''),
                        raw_payload=body
                    )
                    
                    return HttpResponse('Webhook processed successfully', status=200)
                else:
                    registration.status = 'FAILED'
                    registration.save()
                    return HttpResponse('Transaction failed', status=200)
            
            except Registration.DoesNotExist:
                return HttpResponse('Registration not found', status=404)
        
        return HttpResponse('Event not handled', status=200)
    
    except json.JSONDecodeError:
        return HttpResponse('Invalid JSON', status=400)
    except Exception as e:
        return HttpResponse(f'Error: {str(e)}', status=500)


def check_status(request):
    """
    Allow users to check their registration status by email or reference.
    """
    registration = None
    error_message = None
    email = ''
    reference = ''
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        reference = request.POST.get('reference', '').strip()
        
        if email:
            try:
                # Find registration by email (most recent one)
                registration = Registration.objects.filter(email__iexact=email).order_by('-created_at').first()
                if not registration:
                    error_message = 'No registration found with this email address.'
            except Exception as e:
                error_message = 'An error occurred. Please try again.'
        elif reference:
            try:
                # Handle ASPIR-REG-{id}, ASPIR-COURSE-{id}, and ASPIR-FULL-{id} formats
                if reference.startswith('ASPIR-REG-'):
                    registration_id = reference[len('ASPIR-REG-'):]
                    registration = Registration.objects.get(id=registration_id)
                elif reference.startswith('ASPIR-COURSE-'):
                    registration_id = reference[len('ASPIR-COURSE-'):]
                    registration = Registration.objects.get(id=registration_id)
                elif reference.startswith('ASPIR-FULL-'):
                    registration_id = reference[len('ASPIR-FULL-'):]
                    registration = Registration.objects.get(id=registration_id)
                else:
                    # Try squad_reference first, fallback to paystack_reference
                    try:
                        registration = Registration.objects.get(squad_reference=reference)
                    except Registration.DoesNotExist:
                        registration = Registration.objects.get(paystack_reference=reference)
            except Registration.DoesNotExist:
                error_message = 'No registration found with this reference number.'
            except Exception as e:
                error_message = 'An error occurred. Please try again.'
        else:
            error_message = 'Please enter either your email address or reference number.'
    
    # If registration found, redirect to success page with reference
    if registration:
        # Use the registration ID to create a reference for the success page
        if registration.squad_reference:
            ref = registration.squad_reference
        elif registration.paystack_reference:
            ref = registration.paystack_reference
        else:
            # Create a reference from registration ID
            ref = f"ASPIR-REG-{registration.id}"
        
        return redirect(f"{reverse('success')}?reference={ref}")
    
    context = {
        'error_message': error_message,
        'email': email,
        'reference': reference,
    }
    return render(request, 'registrations/check_status.html', context)
