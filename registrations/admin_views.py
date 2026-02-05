"""
Custom admin dashboard views for managing registrations and program settings.
"""
import csv
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages, auth
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q
from django.utils import timezone
from django.conf import settings as django_settings
from django.http import JsonResponse, HttpResponse
from datetime import timedelta
from .models import (
    Registration, Transaction, PaymentActivity, Cohort, Dimension, 
    PricingConfig, ProgramSettings
)
from .views import _registration_from_ref
from .emails import (
    send_registration_confirmation_email,
    send_payment_complete_email,
    send_course_fee_payment_email,
)
from .admin_forms import (
    AdminEditRegistrationForm, AdminEditCohortForm,
    AdminEditDimensionForm, AdminEditPricingForm,
    AdminEditProgramSettingsForm
)


def admin_login(request):
    """
    Custom admin login page.
    """
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = auth.authenticate(request, username=username, password=password)
        if user is not None and user.is_staff:
            auth.login(request, user)
            next_url = request.GET.get('next', '/admin-panel/dashboard/')
            # Handle both URL names and paths
            if next_url.startswith('/'):
                return redirect(next_url)
            else:
                return redirect(next_url)
        else:
            messages.error(request, 'Invalid credentials or you do not have admin access.')
    
    return render(request, 'registrations/admin/login.html')


@login_required
def admin_logout(request):
    """
    Custom admin logout.
    """
    auth.logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('admin_login')


@login_required
def admin_dashboard(request):
    """
    Custom admin dashboard with overview statistics and management tools.
    """
    # Calculate statistics
    total_registrations = Registration.objects.count()
    paid_registrations = Registration.objects.filter(status='PAID').count()
    pending_registrations = Registration.objects.filter(status='PENDING').count()
    failed_registrations = Registration.objects.filter(status='FAILED').count()
    
    # Revenue statistics
    total_revenue = Transaction.objects.aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    # Recent registrations (last 7 days)
    seven_days_ago = timezone.now() - timedelta(days=7)
    recent_registrations = Registration.objects.filter(
        created_at__gte=seven_days_ago
    ).order_by('-created_at')[:10]
    
    # Registrations by status
    registrations_by_status = Registration.objects.values('status').annotate(
        count=Count('id')
    )
    
    # Registrations by cohort
    registrations_by_cohort = Registration.objects.values(
        'cohort__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Registrations by dimension
    registrations_by_dimension = Registration.objects.values(
        'dimension__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Recent transactions
    recent_transactions = Transaction.objects.select_related(
        'registration'
    ).order_by('-created_at')[:10]
    
    # Active cohorts and dimensions
    active_cohorts = Cohort.objects.filter(is_active=True).count()
    active_dimensions = Dimension.objects.filter(is_active=True).count()
    
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    
    context = {
        'total_registrations': total_registrations,
        'paid_registrations': paid_registrations,
        'pending_registrations': pending_registrations,
        'failed_registrations': failed_registrations,
        'total_revenue': total_revenue,
        'recent_registrations': recent_registrations,
        'registrations_by_status': registrations_by_status,
        'registrations_by_cohort': registrations_by_cohort,
        'registrations_by_dimension': registrations_by_dimension,
        'recent_transactions': recent_transactions,
        'active_cohorts': active_cohorts,
        'active_dimensions': active_dimensions,
    }
    
    return render(request, 'registrations/admin/dashboard.html', context)


@login_required
def admin_registrations(request):
    """
    View all registrations with filtering and search.
    """
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    registrations = _get_filtered_registrations_queryset(request)
    status_filter = request.GET.get('status', '')
    cohort_filter = request.GET.get('cohort', '')
    dimension_filter = request.GET.get('dimension', '')
    search_query = request.GET.get('search', '')
    cohorts = Cohort.objects.filter(is_active=True)
    dimensions = Dimension.objects.filter(is_active=True)
    context = {
        'registrations': registrations,
        'cohorts': cohorts,
        'dimensions': dimensions,
        'status_filter': status_filter,
        'cohort_filter': cohort_filter,
        'dimension_filter': dimension_filter,
        'search_query': search_query,
    }
    return render(request, 'registrations/admin/registrations.html', context)


def _get_filtered_registrations_queryset(request):
    """
    Returns the same filtered registrations queryset used on the list page.
    Used by admin_registrations and export_registrations.
    """
    registrations = Registration.objects.select_related(
        'cohort', 'dimension'
    ).order_by('-created_at')
    status_filter = request.GET.get('status', '')
    cohort_filter = request.GET.get('cohort', '')
    dimension_filter = request.GET.get('dimension', '')
    search_query = request.GET.get('search', '')
    if status_filter:
        registrations = registrations.filter(status=status_filter)
    if cohort_filter:
        registrations = registrations.filter(cohort_id=cohort_filter)
    if dimension_filter:
        registrations = registrations.filter(dimension_id=dimension_filter)
    if search_query:
        registrations = registrations.filter(
            Q(full_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(squad_reference__icontains=search_query) |
            Q(paystack_reference__icontains=search_query)
        )
    return registrations


@login_required
def export_registrations(request):
    """
    Export the registrations list as CSV, respecting current filters.
    """
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    registrations = _get_filtered_registrations_queryset(request)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        'attachment; filename="registrations_%s.csv"' % timezone.now().strftime('%Y-%m-%d_%H-%M')
    )
    writer = csv.writer(response)
    # Header row
    writer.writerow([
        'Name', 'Email', 'Phone', 'Country', 'Age', 'Group', 'Cohort', 'Dimension',
        'Enrollment Type', 'Amount', 'Currency', 'Status', 'Registration Fee Paid',
        'Course Fee Paid', 'Reference (Squad)', 'Reference (Paystack)', 'Guardian Name',
        'Guardian Phone', 'Referral Source', 'Created At'
    ])
    for r in registrations:
        writer.writerow([
            r.full_name or '',
            r.email or '',
            r.phone or '',
            r.country or '',
            r.age or '',
            r.get_group_display() if r.group else '',
            r.cohort.name if r.cohort else '',
            r.dimension.name if r.dimension else (r.dimension_code or ''),
            r.get_enrollment_type_display() if r.enrollment_type else '',
            r.amount or '',
            r.currency or '',
            r.status or '',
            'Yes' if r.registration_fee_paid else 'No',
            'Yes' if r.course_fee_paid else 'No',
            r.squad_reference or (r.paystack_reference or ''),
            r.paystack_reference or '',
            r.guardian_name or '',
            r.guardian_phone or '',
            r.referral_source or '',
            r.created_at.strftime('%Y-%m-%d %H:%M') if r.created_at else '',
        ])
    return response


@login_required
def admin_transactions(request):
    """
    View all successful transactions.
    """
    transactions = Transaction.objects.select_related(
        'registration'
    ).order_by('-created_at')
    
    # Filtering
    search_query = request.GET.get('search', '')
    
    if search_query:
        transactions = transactions.filter(
            Q(reference__icontains=search_query) |
            Q(registration__full_name__icontains=search_query) |
            Q(registration__email__icontains=search_query)
        )
    
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    
    context = {
        'transactions': transactions,
        'search_query': search_query,
    }
    
    return render(request, 'registrations/admin/transactions.html', context)


@login_required
def admin_payment_activity(request):
    """
    View all payment activity: initiated, success, failed (every event).
    """
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    
    activities = PaymentActivity.objects.select_related(
        'registration'
    ).order_by('-created_at')
    
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    if search_query:
        activities = activities.filter(
            Q(reference__icontains=search_query) |
            Q(registration__full_name__icontains=search_query) |
            Q(registration__email__icontains=search_query)
        )
    if status_filter:
        activities = activities.filter(status=status_filter)
    
    context = {
        'activities': activities,
        'search_query': search_query,
        'status_filter': status_filter,
    }
    
    return render(request, 'registrations/admin/payment_activity.html', context)


@login_required
def admin_reconcile_payment(request):
    """
    Reconcile a payment by reference when the webhook was missed.
    Verifies with Squad API and then updates registration, creates Transaction, logs activity, sends email.
    """
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    
    if request.method == 'POST':
        reference = (request.POST.get('reference') or '').strip()
        if not reference:
            messages.error(request, 'Please enter a payment reference.')
            return redirect('admin_reconcile_payment')
        
        try:
            registration = _registration_from_ref(reference)
        except Registration.DoesNotExist:
            messages.error(request, f'No registration found for reference: {reference}')
            return redirect('admin_reconcile_payment')
        
        # Already have a Transaction for this reference?
        if Transaction.objects.filter(reference=reference).exists():
            messages.warning(
                request,
                f'This payment is already recorded (reference: {reference}). Registration and Transaction are up to date.'
            )
            return redirect('view_registration', registration_id=registration.id)
        
        # Verify with Squad API: GET /transaction/verify/{transaction_ref}
        base_url = (getattr(django_settings, 'SQUAD_BASE_URL') or '').rstrip('/')
        url = f"{base_url}/transaction/verify/{reference}"
        auth_key = (getattr(django_settings, 'SQUAD_SECRET_KEY') or '').strip()
        if not auth_key.startswith('Bearer '):
            auth_key = f'Bearer {auth_key}'
        headers = {'Authorization': auth_key, 'Content-Type': 'application/json'}
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            data = response.json()
        except Exception as e:
            messages.error(request, f'Could not reach Squad API: {e}')
            return redirect('admin_reconcile_payment')
        
        if response.status_code == 400 or not (data.get('status') == 200 and data.get('success')):
            msg = data.get('message') or data.get('error') or f'Status {data.get("status", response.status_code)}'
            messages.error(
                request,
                f'Squad returned an error: {msg}. Check that the reference is correct and exists in Squad (live vs sandbox).'
            )
            return redirect('admin_reconcile_payment')
        
        txn = data.get('data')
        if not txn:
            messages.error(request, 'Squad did not return transaction data for this reference.')
            return redirect('admin_reconcile_payment')
        
        if (txn.get('transaction_status') or '').lower() != 'success':
            messages.error(request, f'Payment was not successful on Squad (status: {txn.get("transaction_status")}).')
            return redirect('admin_reconcile_payment')
        
        # Determine payment type from reference prefix
        if reference.startswith('ASPIR-FULL-'):
            payment_type = 'full_payment'
        elif reference.startswith('ASPIR-COURSE-'):
            payment_type = 'course_fee'
        elif reference.startswith('ASPIR-REG-'):
            payment_type = 'registration_fee'
        else:
            payment_type = (txn.get('meta') or {}).get('payment_type') or 'registration_fee'
        
        # Amount: Squad verify returns transaction_amount (in smallest unit: cents for USD, kobo for NGN)
        amount_subunit = float(txn.get('transaction_amount', 0))
        currency = (txn.get('transaction_currency_id') or txn.get('currency') or 'USD').upper()
        if currency == 'USD':
            amount_in_usd = amount_subunit / 100
        else:
            from .utils import get_usd_to_ngn_rate
            rate = get_usd_to_ngn_rate()
            amount_in_usd = (amount_subunit / 100) / rate
        paid_at = timezone.now()
        if txn.get('created_at'):
            try:
                from django.utils.dateparse import parse_datetime
                paid_at = parse_datetime(txn['created_at']) or paid_at
            except Exception:
                pass
        
        # Update registration
        if payment_type == 'full_payment' or reference.startswith('ASPIR-FULL-'):
            registration.registration_fee_paid = True
            registration.course_fee_paid = True
            registration.status = 'PAID'
        elif payment_type == 'registration_fee' or reference.startswith('ASPIR-REG-'):
            registration.registration_fee_paid = True
            registration.status = 'PENDING'
        elif payment_type == 'course_fee' or reference.startswith('ASPIR-COURSE-'):
            registration.course_fee_paid = True
            registration.status = 'PAID' if (registration.registration_fee_paid and registration.course_fee_paid) else 'PENDING'
        registration.save()
        
        # Create Transaction record
        Transaction.objects.get_or_create(
            reference=reference,
            defaults={
                'registration': registration,
                'amount': amount_in_usd,
                'currency': 'USD',
                'paid_at': paid_at,
                'channel': txn.get('transaction_type', '') or 'squad',
                'raw_payload': txn,
            }
        )
        # Log success in PaymentActivity
        PaymentActivity.objects.create(
            registration=registration,
            reference=reference,
            status='success',
            payment_type=payment_type,
            amount=amount_in_usd,
            currency='USD',
            gateway='squad',
            message='Reconciled from admin',
        )
        # Send appropriate email
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
        except Exception:
            pass
        messages.success(
            request,
            f'Payment reconciled successfully for {registration.full_name}. Transaction created and registration updated.'
        )
        return redirect('view_registration', registration_id=registration.id)
    
    return render(request, 'registrations/admin/reconcile_payment.html', {})


@login_required
def admin_settings(request):
    """
    Custom settings page for managing cohorts, dimensions, and pricing.
    """
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    
    cohorts = Cohort.objects.all().order_by('-created_at')
    dimensions = Dimension.objects.all().order_by('display_order')
    pricing_configs = PricingConfig.objects.all()
    settings = ProgramSettings.load()
    
    context = {
        'cohorts': cohorts,
        'dimensions': dimensions,
        'pricing_configs': pricing_configs,
        'settings': settings,
    }
    
    return render(request, 'registrations/admin/settings.html', context)


@login_required
def view_registration(request, registration_id):
    """
    View registration details in read-only mode.
    """
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    
    registration = get_object_or_404(
        Registration.objects.select_related('cohort', 'dimension'),
        id=registration_id
    )
    
    # Get related transactions
    from .models import Transaction
    transactions = Transaction.objects.filter(registration=registration).order_by('-paid_at')
    
    # Get exchange rate for display
    from .utils import get_usd_to_ngn_rate
    exchange_rate = get_usd_to_ngn_rate()
    
    # Calculate NGN amounts for display
    reg_fee_ngn = round(float(registration.registration_fee_amount or registration.get_registration_fee()) * exchange_rate, 0)
    course_fee_ngn = round(float(registration.course_fee_amount or registration.get_course_fee()) * exchange_rate, 0)
    total_ngn = round(float(registration.amount) * exchange_rate, 0)
    remaining_ngn = round(float(registration.get_remaining_balance()) * exchange_rate, 0)
    
    context = {
        'registration': registration,
        'transactions': transactions,
        'exchange_rate': exchange_rate,
        'reg_fee_ngn': reg_fee_ngn,
        'course_fee_ngn': course_fee_ngn,
        'total_ngn': total_ngn,
        'remaining_ngn': remaining_ngn,
        'page_title': 'View Registration',
    }
    
    return render(request, 'registrations/admin/view_registration.html', context)


@login_required
def edit_registration(request, registration_id):
    """
    Edit a registration using custom form.
    """
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    
    registration = get_object_or_404(Registration, id=registration_id)
    
    if request.method == 'POST':
        form = AdminEditRegistrationForm(request.POST, instance=registration)
        if form.is_valid():
            form.save()
            messages.success(request, f'Registration for {registration.full_name} has been updated successfully.')
            return redirect('admin_registrations')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = AdminEditRegistrationForm(instance=registration)
    
    context = {
        'form': form,
        'registration': registration,
        'page_title': 'Edit Registration',
    }
    
    return render(request, 'registrations/admin/edit_registration.html', context)


@login_required
def delete_registration(request, registration_id):
    """
    Delete a registration.
    """
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    
    if request.method == 'POST':
        try:
            registration = Registration.objects.get(id=registration_id)
            registration.delete()
            messages.success(request, f'Registration for {registration.full_name} has been deleted successfully.')
        except Registration.DoesNotExist:
            messages.error(request, 'Registration not found.')
        except Exception as e:
            messages.error(request, f'Error deleting registration: {str(e)}')
    
    return redirect('admin_registrations')


@login_required
def toggle_cohort(request, cohort_id):
    """
    Toggle cohort active status.
    """
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    
    try:
        cohort = Cohort.objects.get(id=cohort_id)
        cohort.is_active = not cohort.is_active
        cohort.save()
        status = 'activated' if cohort.is_active else 'deactivated'
        messages.success(request, f'Cohort "{cohort.name}" has been {status}.')
    except Cohort.DoesNotExist:
        messages.error(request, 'Cohort not found.')
    
    return redirect('admin_settings')


@login_required
def toggle_dimension(request, dimension_id):
    """
    Toggle dimension active status.
    """
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    
    try:
        dimension = Dimension.objects.get(id=dimension_id)
        dimension.is_active = not dimension.is_active
        dimension.save()
        status = 'activated' if dimension.is_active else 'deactivated'
        messages.success(request, f'Dimension "{dimension.name}" has been {status}.')
    except Dimension.DoesNotExist:
        messages.error(request, 'Dimension not found.')
    
    return redirect('admin_settings')


@login_required
def toggle_pricing(request, pricing_id):
    """
    Toggle pricing config active status.
    """
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    
    try:
        pricing = PricingConfig.objects.get(id=pricing_id)
        pricing.is_active = not pricing.is_active
        pricing.save()
        status = 'activated' if pricing.is_active else 'deactivated'
        messages.success(request, f'Pricing for {pricing.get_enrollment_type_display()} has been {status}.')
    except PricingConfig.DoesNotExist:
        messages.error(request, 'Pricing configuration not found.')
    
    return redirect('admin_settings')


@login_required
def add_registration(request):
    """
    Add a new registration.
    """
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    
    if request.method == 'POST':
        form = AdminEditRegistrationForm(request.POST)
        if form.is_valid():
            registration = form.save()
            messages.success(request, f'Registration for {registration.full_name} has been created successfully.')
            return redirect('admin_registrations')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = AdminEditRegistrationForm()
    
    context = {
        'form': form,
        'page_title': 'Add New Registration',
    }
    
    return render(request, 'registrations/admin/edit_registration.html', context)


@login_required
def add_cohort(request):
    """
    Add a new cohort.
    """
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    
    if request.method == 'POST':
        form = AdminEditCohortForm(request.POST)
        if form.is_valid():
            cohort = form.save()
            messages.success(request, f'Cohort "{cohort.name}" has been created successfully.')
            return redirect('admin_settings')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = AdminEditCohortForm()
    
    context = {
        'form': form,
        'page_title': 'Add New Cohort',
    }
    
    return render(request, 'registrations/admin/edit_cohort.html', context)


@login_required
def edit_cohort(request, cohort_id):
    """
    Edit a cohort.
    """
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    
    cohort = get_object_or_404(Cohort, id=cohort_id)
    
    if request.method == 'POST':
        form = AdminEditCohortForm(request.POST, instance=cohort)
        if form.is_valid():
            form.save()
            messages.success(request, f'Cohort "{cohort.name}" has been updated successfully.')
            return redirect('admin_settings')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = AdminEditCohortForm(instance=cohort)
    
    context = {
        'form': form,
        'cohort': cohort,
        'page_title': 'Edit Cohort',
    }
    
    return render(request, 'registrations/admin/edit_cohort.html', context)


@login_required
def delete_cohort(request, cohort_id):
    """
    Delete a cohort.
    """
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    
    if request.method == 'POST':
        try:
            cohort = Cohort.objects.get(id=cohort_id)
            cohort_name = cohort.name
            cohort.delete()
            messages.success(request, f'Cohort "{cohort_name}" has been deleted successfully.')
        except Cohort.DoesNotExist:
            messages.error(request, 'Cohort not found.')
        except Exception as e:
            messages.error(request, f'Error deleting cohort: {str(e)}')
    
    return redirect('admin_settings')


@login_required
def add_dimension(request):
    """
    Add a new dimension.
    """
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    
    if request.method == 'POST':
        form = AdminEditDimensionForm(request.POST)
        if form.is_valid():
            dimension = form.save()
            messages.success(request, f'Dimension "{dimension.name}" has been created successfully.')
            return redirect('admin_settings')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = AdminEditDimensionForm()
    
    context = {
        'form': form,
        'page_title': 'Add New Dimension',
    }
    
    return render(request, 'registrations/admin/edit_dimension.html', context)


@login_required
def edit_dimension(request, dimension_id):
    """
    Edit a dimension.
    """
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    
    dimension = get_object_or_404(Dimension, id=dimension_id)
    
    if request.method == 'POST':
        form = AdminEditDimensionForm(request.POST, instance=dimension)
        if form.is_valid():
            form.save()
            messages.success(request, f'Dimension "{dimension.name}" has been updated successfully.')
            return redirect('admin_settings')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = AdminEditDimensionForm(instance=dimension)
    
    context = {
        'form': form,
        'dimension': dimension,
        'page_title': 'Edit Dimension',
    }
    
    return render(request, 'registrations/admin/edit_dimension.html', context)


@login_required
def delete_dimension(request, dimension_id):
    """
    Delete a dimension.
    """
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    
    if request.method == 'POST':
        try:
            dimension = Dimension.objects.get(id=dimension_id)
            dimension_name = dimension.name
            dimension.delete()
            messages.success(request, f'Dimension "{dimension_name}" has been deleted successfully.')
        except Dimension.DoesNotExist:
            messages.error(request, 'Dimension not found.')
        except Exception as e:
            messages.error(request, f'Error deleting dimension: {str(e)}')
    
    return redirect('admin_settings')


@login_required
def add_pricing(request):
    """
    Add a new pricing configuration.
    """
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    
    if request.method == 'POST':
        form = AdminEditPricingForm(request.POST)
        if form.is_valid():
            pricing = form.save()
            messages.success(request, f'Pricing for {pricing.get_enrollment_type_display()} has been created successfully.')
            return redirect('admin_settings')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = AdminEditPricingForm()
    
    context = {
        'form': form,
        'page_title': 'Add New Pricing',
    }
    
    return render(request, 'registrations/admin/edit_pricing.html', context)


@login_required
def edit_pricing(request, pricing_id):
    """
    Edit a pricing configuration.
    """
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    
    pricing = get_object_or_404(PricingConfig, id=pricing_id)
    
    if request.method == 'POST':
        form = AdminEditPricingForm(request.POST, instance=pricing)
        if form.is_valid():
            form.save()
            messages.success(request, f'Pricing for {pricing.get_enrollment_type_display()} has been updated successfully.')
            return redirect('admin_settings')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = AdminEditPricingForm(instance=pricing)
    
    context = {
        'form': form,
        'pricing': pricing,
        'page_title': 'Edit Pricing',
    }
    
    return render(request, 'registrations/admin/edit_pricing.html', context)


@login_required
def delete_pricing(request, pricing_id):
    """
    Delete a pricing configuration.
    """
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    
    if request.method == 'POST':
        try:
            pricing = PricingConfig.objects.get(id=pricing_id)
            pricing_type = pricing.get_enrollment_type_display()
            pricing.delete()
            messages.success(request, f'Pricing for {pricing_type} has been deleted successfully.')
        except PricingConfig.DoesNotExist:
            messages.error(request, 'Pricing configuration not found.')
        except Exception as e:
            messages.error(request, f'Error deleting pricing: {str(e)}')
    
    return redirect('admin_settings')


@login_required
def edit_program_settings(request):
    """
    Edit program settings.
    """
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    
    settings = ProgramSettings.load()
    
    if request.method == 'POST':
        form = AdminEditProgramSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'Program settings have been updated successfully.')
            return redirect('admin_settings')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = AdminEditProgramSettingsForm(instance=settings)
    
    context = {
        'form': form,
        'settings': settings,
        'page_title': 'Edit Program Settings',
    }
    
    return render(request, 'registrations/admin/edit_program_settings.html', context)
