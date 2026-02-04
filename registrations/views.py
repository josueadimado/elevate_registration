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
import time


def _unique_ref(prefix, registration_id):
    """Generate a unique transaction reference per attempt to avoid 'Duplicate Transaction Reference'."""
    return f"{prefix}{registration_id}-{int(time.time())}"


def _registration_id_from_ref(reference, prefix):
    """Extract registration ID from reference (e.g. ASPIR-REG-{uuid}-{timestamp} -> uuid). UUID is 36 chars."""
    if not reference.startswith(prefix):
        return None
    rest = reference[len(prefix):]
    return rest[:36] if len(rest) >= 36 else rest


def _registration_from_ref(reference):
    """Resolve a reference (with optional attempt suffix) to a Registration. Raises Registration.DoesNotExist."""
    if reference.startswith('ASPIR-REG-'):
        rid = _registration_id_from_ref(reference, 'ASPIR-REG-')
        if rid:
            return Registration.objects.get(id=rid)
    if reference.startswith('ASPIR-COURSE-'):
        rid = _registration_id_from_ref(reference, 'ASPIR-COURSE-')
        if rid:
            return Registration.objects.get(id=rid)
    if reference.startswith('ASPIR-FULL-'):
        rid = _registration_id_from_ref(reference, 'ASPIR-FULL-')
        if rid:
            return Registration.objects.get(id=rid)
    try:
        return Registration.objects.get(squad_reference=reference)
    except Registration.DoesNotExist:
        return Registration.objects.get(paystack_reference=reference)


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
        # If this email is already registered, send them to the payment page instead of creating a duplicate
        email = (request.POST.get('email') or '').strip()
        if email:
            existing = (
                Registration.objects.filter(email__iexact=email)
                .order_by('-created_at')
                .first()
            )
            if existing:
                ref = f'ASPIR-REG-{existing.id}'
                return redirect(reverse('success') + f'?reference={ref}')
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


def check_email(request):
    """
    API: Check if an email is already registered. Used on the register page
    to show "Complete your payment" when the user enters an existing email.
    """
    email = (request.GET.get('email') or request.POST.get('email') or '').strip()
    if not email:
        return JsonResponse({'exists': False, 'redirect_url': None})
    existing = (
        Registration.objects.filter(email__iexact=email)
        .order_by('-created_at')
        .first()
    )
    if existing:
        ref = f'ASPIR-REG-{existing.id}'
        redirect_url = request.build_absolute_uri(
            reverse('success') + f'?reference={ref}'
        )
        return JsonResponse({'exists': True, 'redirect_url': redirect_url})
    return JsonResponse({'exists': False, 'redirect_url': None})


def success(request):
    """
    Payment success confirmation page.
    """
    reference = request.GET.get('reference', '')
    
    if reference:
        try:
            registration = _registration_from_ref(reference)
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
    
    # If this email is already registered, tell the frontend to redirect to the payment page
    email = (request.POST.get('email') or '').strip()
    if email:
        existing = (
            Registration.objects.filter(email__iexact=email)
            .order_by('-created_at')
            .first()
        )
        if existing:
            ref = f'ASPIR-REG-{existing.id}'
            redirect_url = request.build_absolute_uri(
                reverse('success') + f'?reference={ref}'
            )
            return JsonResponse({
                'status': 'already_registered',
                'redirect_url': redirect_url,
                'message': 'This email is already registered. Redirecting you to complete your payment.',
            })
    
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
    
    # Get payment option and gateway from form data (all payments in USD)
    body = _parse_body_json(request)
    payment_option = (body.get('payment_option') or request.POST.get('payment_option') or 'partial').lower()
    payment_option = 'full' if payment_option == 'full' else 'partial'
    payment_gateway = (body.get('payment_gateway') or request.POST.get('payment_gateway') or 'squad').lower()
    
    # Determine payment amount and reference based on option (unique ref per attempt to avoid Duplicate Transaction Reference)
    if payment_option == 'full':
        payment_amount = float(registration.amount)
        reference = _unique_ref("ASPIR-FULL-", str(registration.id))
        payment_type = 'full_payment'
    else:
        payment_amount = float(registration.registration_fee_amount)
        reference = _unique_ref("ASPIR-REG-", str(registration.id))
        payment_type = 'registration_fee'
    
    exchange_rate = get_usd_to_ngn_rate()
    amount_subunit = int(round(payment_amount * 100))  # USD cents (all payments in USD)
    callback_url = request.build_absolute_uri(f'/success/?reference={reference}')
    metadata = {
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
    }
    
    # Branch by payment gateway
    if payment_gateway == 'paystack' and getattr(settings, 'PAYSTACK_SECRET_KEY', None):
        registration.paystack_reference = reference
        registration.save()
        try:
            url = f"{settings.PAYSTACK_BASE_URL}/transaction/initialize"
            headers = {
                'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY.strip()}',
                'Content-Type': 'application/json',
            }
            payload = {
                'email': registration.email,
                'amount': amount_subunit,
                'reference': reference,
                'callback_url': callback_url,
                'metadata': metadata,
                'currency': 'USD',
            }
            response = requests.post(url, headers=headers, json=payload)
            data = response.json()
            if data.get('status') and data.get('data', {}).get('authorization_url'):
                return JsonResponse({
                    'status': 'success',
                    'authorization_url': data['data']['authorization_url'],
                    'reference': reference,
                })
            return JsonResponse({
                'error': 'Paystack initialization failed',
                'message': data.get('message', 'Unknown error'),
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'error': 'Payment initialization failed',
                'message': str(e),
            }, status=500)
    
    # Squad: Initiate Payment — all in USD
    registration.squad_reference = reference
    registration.save()
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
    payload = {
        'email': registration.email,
        'amount': str(amount_subunit),
        'currency': 'USD',
        'initiate_type': 'inline',
        'transaction_ref': reference,
        'customer_name': registration.full_name,
        'callback_url': callback_url,
        'payment_channels': ['card', 'bank', 'ussd', 'transfer'],
        'metadata': metadata,
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
            return JsonResponse({
                'error': 'Failed to initialize payment',
                'message': data.get('message', 'No checkout URL returned'),
                'squad_response': data,
            }, status=400)
        return JsonResponse({
            'error': 'Failed to initialize payment',
            'message': data.get('message', 'Unknown error'),
            'squad_response': data,
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': 'Payment initialization failed',
            'message': str(e),
        }, status=500)


def _parse_gateway(request):
    """Read payment_gateway from POST body (JSON or form). Default 'squad'."""
    gateway = 'squad'
    if request.content_type and 'application/json' in request.content_type:
        try:
            body = json.loads(request.body)
            gateway = (body.get('payment_gateway') or body.get('gateway') or 'squad').lower()
        except (json.JSONDecodeError, TypeError):
            pass
    else:
        gateway = (request.POST.get('payment_gateway') or request.POST.get('gateway') or 'squad').lower()
    return gateway if gateway in ('squad', 'paystack') else 'squad'


def _parse_body_json(request):
    """Read JSON body and return dict. Return {} if not JSON or invalid."""
    if request.content_type and 'application/json' in request.content_type:
        try:
            return json.loads(request.body)
        except (json.JSONDecodeError, TypeError):
            pass
    return {}


@csrf_exempt
@require_http_methods(["POST"])
def pay_registration_fee(request, registration_id):
    """
    Initialize payment for registration fee OR full amount (for existing registrations).
    Accepts optional JSON body: { "payment_gateway": "squad" | "paystack", "payment_option": "partial" | "full" }.
    - partial: pay registration fee only (default)
    - full: pay full amount (registration + course) in one go
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        registration = Registration.objects.get(id=registration_id)
    except Registration.DoesNotExist:
        return JsonResponse({'error': 'Registration not found'}, status=404)
    
    if registration.registration_fee_paid:
        return JsonResponse({'error': 'Registration fee already paid'}, status=400)
    
    body = _parse_body_json(request)
    payment_option = (body.get('payment_option') or request.POST.get('payment_option') or 'partial').lower()
    payment_option = 'full' if payment_option == 'full' else 'partial'
    
    if payment_option == 'full':
        reference = _unique_ref("ASPIR-FULL-", str(registration.id))
        payment_amount = float(registration.amount)
        payment_type = 'full_payment'
    else:
        reference = _unique_ref("ASPIR-REG-", str(registration.id))
        payment_amount = float(registration.registration_fee_amount or registration.get_registration_fee())
        payment_type = 'registration_fee'
    
    exchange_rate = get_usd_to_ngn_rate()
    amount_subunit = int(round(payment_amount * 100))  # USD cents (all payments in USD)
    callback_url = request.build_absolute_uri(f'/success/?reference={reference}')
    metadata = {
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
    }
    gateway = _parse_gateway(request)
    
    if gateway == 'paystack' and getattr(settings, 'PAYSTACK_SECRET_KEY', None):
        registration.paystack_reference = reference
        registration.save()
        try:
            url = f"{settings.PAYSTACK_BASE_URL}/transaction/initialize"
            headers = {
                'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY.strip()}',
                'Content-Type': 'application/json',
            }
            payload = {
                'email': registration.email,
                'amount': amount_subunit,
                'reference': reference,
                'callback_url': callback_url,
                'metadata': metadata,
                'currency': 'USD',
            }
            response = requests.post(url, headers=headers, json=payload)
            data = response.json()
            if data.get('status') and data.get('data', {}).get('authorization_url'):
                return JsonResponse({
                    'status': 'success',
                    'authorization_url': data['data']['authorization_url'],
                    'reference': reference,
                })
            return JsonResponse({
                'error': 'Paystack initialization failed',
                'message': data.get('message', 'Unknown error'),
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'error': 'Payment initialization failed',
                'message': str(e),
            }, status=500)
    
    # Squad — all in USD
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
    payload = {
        'email': registration.email,
        'amount': str(amount_subunit),
        'currency': 'USD',
        'initiate_type': 'inline',
        'transaction_ref': reference,
        'customer_name': registration.full_name,
        'callback_url': callback_url,
        'payment_channels': ['card', 'bank', 'ussd', 'transfer'],
        'metadata': metadata,
        'pass_charge': False,
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        data = response.json()
        if data.get('status') == 200 and data.get('data'):
            checkout_url = data['data'].get('checkout_url')
            if checkout_url:
                registration.squad_reference = reference
                registration.save()
                return JsonResponse({
                    'status': 'success',
                    'authorization_url': checkout_url,
                    'reference': reference,
                })
            return JsonResponse({
                'error': 'Failed to initialize payment',
                'message': 'No checkout URL returned',
                'squad_response': data
            }, status=400)
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
    Accepts optional JSON body: { "payment_gateway": "squad" | "paystack" }.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        registration = Registration.objects.get(id=registration_id)
    except Registration.DoesNotExist:
        return JsonResponse({'error': 'Registration not found'}, status=404)
    
    if registration.course_fee_paid:
        return JsonResponse({'error': 'Course fee already paid'}, status=400)
    if not registration.registration_fee_paid:
        return JsonResponse({'error': 'Registration fee must be paid first'}, status=400)
    
    body = _parse_body_json(request)
    reference = _unique_ref("ASPIR-COURSE-", str(registration.id))
    exchange_rate = get_usd_to_ngn_rate()
    course_fee_amount = float(registration.course_fee_amount or registration.get_course_fee())
    amount_subunit = int(round(course_fee_amount * 100))  # USD cents (all payments in USD)
    callback_url = request.build_absolute_uri(f'/success/?reference={reference}')
    metadata = {
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
    }
    gateway = _parse_gateway(request)
    
    if gateway == 'paystack' and getattr(settings, 'PAYSTACK_SECRET_KEY', None):
        registration.paystack_reference = reference
        registration.save()
        try:
            url = f"{settings.PAYSTACK_BASE_URL}/transaction/initialize"
            headers = {
                'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY.strip()}',
                'Content-Type': 'application/json',
            }
            payload = {
                'email': registration.email,
                'amount': amount_subunit,
                'reference': reference,
                'callback_url': callback_url,
                'metadata': metadata,
                'currency': 'USD',
            }
            response = requests.post(url, headers=headers, json=payload)
            data = response.json()
            if data.get('status') and data.get('data', {}).get('authorization_url'):
                return JsonResponse({
                    'status': 'success',
                    'authorization_url': data['data']['authorization_url'],
                    'reference': reference,
                })
            return JsonResponse({
                'error': 'Paystack initialization failed',
                'message': data.get('message', 'Unknown error'),
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'error': 'Payment initialization failed',
                'message': str(e),
            }, status=500)
    
    # Squad — all in USD
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
    payload = {
        'email': registration.email,
        'amount': str(amount_subunit),
        'currency': 'USD',
        'initiate_type': 'inline',
        'transaction_ref': reference,
        'customer_name': registration.full_name,
        'callback_url': callback_url,
        'payment_channels': ['card', 'bank', 'ussd', 'transfer'],
        'metadata': metadata,
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
            return JsonResponse({
                'error': 'Failed to initialize payment',
                'message': 'No checkout URL returned',
                'squad_response': data
            }, status=400)
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
        registration = _registration_from_ref(reference)
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
                registration = _registration_from_ref(transaction_ref)
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


@csrf_exempt
@require_http_methods(["POST"])
def paystack_webhook(request):
    """
    Handle Paystack webhook notifications (charge.success).
    Updates registration status and sends emails.
    """
    from .models import Transaction
    from django.utils.dateparse import parse_datetime
    from django.utils import timezone as tz

    raw_body = request.body
    signature = request.headers.get('X-Paystack-Signature', '')
    secret = getattr(settings, 'PAYSTACK_WEBHOOK_SECRET', None)
    if secret:
        computed = hmac.new(
            secret.encode('utf-8'),
            raw_body,
            hashlib.sha512
        ).hexdigest()
        if not hmac.compare_digest(computed, signature):
            return HttpResponse('Invalid signature', status=401)

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        return HttpResponse('Invalid JSON', status=400)

    event = payload.get('event')
    if event != 'charge.success':
        return HttpResponse('Event not handled', status=200)

    data = payload.get('data', {})
    reference = data.get('reference')
    if not reference:
        return HttpResponse('Missing reference', status=400)

    try:
        registration = _registration_from_ref(reference)
    except Registration.DoesNotExist:
        return HttpResponse('Registration not found', status=404)

    metadata = data.get('metadata', {}) or {}
    payment_type = metadata.get('payment_type', '')
    if reference.startswith('ASPIR-FULL-'):
        payment_type = 'full_payment'
    elif reference.startswith('ASPIR-REG-'):
        payment_type = 'registration_fee'
    elif reference.startswith('ASPIR-COURSE-'):
        payment_type = 'course_fee'

    if payment_type == 'full_payment' or reference.startswith('ASPIR-FULL-'):
        registration.registration_fee_paid = True
        registration.course_fee_paid = True
        registration.status = 'PAID'
    elif payment_type == 'registration_fee' or reference.startswith('ASPIR-REG-'):
        registration.registration_fee_paid = True
        registration.status = 'PENDING'
    elif payment_type == 'course_fee' or reference.startswith('ASPIR-COURSE-'):
        registration.course_fee_paid = True
        registration.status = 'PAID' if registration.registration_fee_paid else 'PENDING'
    else:
        registration.registration_fee_paid = True
        registration.course_fee_paid = True
        registration.status = 'PAID'
    registration.save()

    try:
        if payment_type == 'full_payment' or reference.startswith('ASPIR-FULL-'):
            send_payment_complete_email(registration)
        elif payment_type == 'registration_fee' or reference.startswith('ASPIR-REG-'):
            send_registration_confirmation_email(registration)
        elif payment_type == 'course_fee' or reference.startswith('ASPIR-COURSE-'):
            if registration.is_fully_paid():
                send_payment_complete_email(registration)
            else:
                send_course_fee_payment_email(registration)
        else:
            send_payment_complete_email(registration)
    except Exception as email_error:
        import logging
        logging.getLogger(__name__).error(f"Paystack webhook email error: {email_error}")

    exchange_rate = float(metadata.get('exchange_rate', 0)) or get_usd_to_ngn_rate()
    amount_in_kobo = float(data.get('amount', 0))
    amount_in_ngn = amount_in_kobo / 100
    amount_in_usd = amount_in_ngn / exchange_rate
    paid_at = None
    if data.get('paid_at'):
        try:
            paid_at = parse_datetime(data['paid_at'])
        except Exception:
            paid_at = tz.now()
    else:
        paid_at = tz.now()

    Transaction.objects.create(
        registration=registration,
        reference=reference,
        amount=amount_in_usd,
        currency='USD',
        paid_at=paid_at,
        channel=data.get('channel', '') or 'paystack',
        raw_payload=data,
    )
    return HttpResponse('OK', status=200)


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
                registration = _registration_from_ref(reference)
            except Registration.DoesNotExist:
                error_message = 'No registration found with this reference number.'
            except Exception:
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
