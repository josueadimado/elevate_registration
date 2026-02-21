"""
Custom admin dashboard views for managing registrations and program settings.
"""
import csv
import io
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages, auth
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
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
from .utils import generate_participant_id, parse_participant_id_to_canonical
from .emails import (
    send_registration_confirmation_email,
    send_payment_complete_email,
    send_course_fee_payment_email,
    send_staff_payment_notification_email,
    send_participant_id_email,
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
    Custom admin dashboard with overview statistics and payment status (full/half/pending).
    """
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    
    base = Registration.objects.all()
    total_registrations = base.count()
    # Payment status by fees paid (aligned with registrations list)
    full_paid_count = base.filter(registration_fee_paid=True, course_fee_paid=True).count()
    half_paid_count = base.filter(
        Q(registration_fee_paid=True, course_fee_paid=False) |
        Q(registration_fee_paid=False, course_fee_paid=True)
    ).count()
    pending_count = base.filter(registration_fee_paid=False, course_fee_paid=False).count()
    failed_registrations = base.filter(status='FAILED').count()
    
    # Revenue statistics
    total_revenue = Transaction.objects.aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    # Recent registrations (last 7 days) with payment status
    seven_days_ago = timezone.now() - timedelta(days=7)
    recent_registrations = Registration.objects.select_related(
        'cohort', 'dimension'
    ).filter(
        created_at__gte=seven_days_ago
    ).order_by('-created_at')[:10]
    
    # Registrations by status (for any legacy use)
    registrations_by_status = Registration.objects.values('status').annotate(
        count=Count('id')
    )
    registrations_by_cohort = Registration.objects.values(
        'cohort__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')
    registrations_by_dimension = Registration.objects.values(
        'dimension__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')
    
    recent_transactions = Transaction.objects.select_related(
        'registration'
    ).order_by('-created_at')[:10]
    
    active_cohorts = Cohort.objects.filter(is_active=True).count()
    active_dimensions = Dimension.objects.filter(is_active=True).count()
    
    context = {
        'total_registrations': total_registrations,
        'full_paid_count': full_paid_count,
        'half_paid_count': half_paid_count,
        'pending_count': pending_count,
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


PAGINATE_BY = 25


@login_required
def admin_registrations(request):
    """
    View all registrations with filtering, search, and pagination.
    Shows payment type: Full paid, Half paid, Pending, and summary counts.
    """
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    registrations_qs = _get_filtered_registrations_queryset(request)
    status_filter = request.GET.get('status', '')
    cohort_filter = request.GET.get('cohort', '')
    dimension_filter = request.GET.get('dimension', '')
    search_query = request.GET.get('search', '')
    cohorts = Cohort.objects.filter(is_active=True)
    dimensions = Dimension.objects.filter(is_active=True)
    # Payment summary counts (all registrations, no filters)
    base = Registration.objects.all()
    count_full_paid = base.filter(registration_fee_paid=True, course_fee_paid=True).count()
    count_half_paid = base.filter(
        Q(registration_fee_paid=True, course_fee_paid=False) |
        Q(registration_fee_paid=False, course_fee_paid=True)
    ).count()
    count_pending = base.filter(registration_fee_paid=False, course_fee_paid=False).count()
    count_failed = base.filter(status='FAILED').count()
    # Paginate
    paginator = Paginator(registrations_qs, PAGINATE_BY)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    # Query string for pagination links (preserve filters, exclude page)
    q = request.GET.copy()
    q.pop('page', None)
    query_string = q.urlencode()
    context = {
        'page_obj': page_obj,
        'registrations': page_obj.object_list,
        'query_string': query_string,
        'cohorts': cohorts,
        'dimensions': dimensions,
        'status_filter': status_filter,
        'cohort_filter': cohort_filter,
        'dimension_filter': dimension_filter,
        'search_query': search_query,
        'count_full_paid': count_full_paid,
        'count_half_paid': count_half_paid,
        'count_pending': count_pending,
        'count_failed': count_failed,
    }
    return render(request, 'registrations/admin/registrations.html', context)


def _get_filtered_registrations_queryset(request):
    """
    Returns the same filtered registrations queryset used on the list page.
    Used by admin_registrations and export_registrations.
    Status filter: PAID (full), PENDING (no payment), HALF (half paid), FAILED.
    """
    registrations = Registration.objects.select_related(
        'cohort', 'dimension'
    ).order_by('-created_at')
    status_filter = request.GET.get('status', '')
    cohort_filter = request.GET.get('cohort', '')
    dimension_filter = request.GET.get('dimension', '')
    search_query = request.GET.get('search', '')
    if status_filter == 'PAID':
        registrations = registrations.filter(registration_fee_paid=True, course_fee_paid=True)
    elif status_filter == 'PENDING':
        registrations = registrations.filter(registration_fee_paid=False, course_fee_paid=False)
    elif status_filter == 'HALF':
        registrations = registrations.filter(
            Q(registration_fee_paid=True, course_fee_paid=False) |
            Q(registration_fee_paid=False, course_fee_paid=True)
        )
    elif status_filter == 'FAILED':
        registrations = registrations.filter(status='FAILED')
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
        'Participant ID', 'Enrollment Type', 'Amount', 'Currency', 'Status', 'Registration Fee Paid',
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
            r.participant_id or '',
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


# CSV template columns for manual registration import (must match import logic)
REGISTRATION_CSV_HEADERS = [
    'full_name', 'email', 'phone', 'country', 'age', 'group', 'cohort', 'dimension',
    'enrollment_type', 'amount', 'currency', 'guardian_name', 'guardian_phone', 'referral_source',
]


@login_required
def download_registrations_template(request):
    """
    Download a CSV template for manual registration import.
    Fill the rows and upload via Import (CSV) to create registrations.
    """
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        'attachment; filename="aspir_registrations_template.csv"'
    )
    writer = csv.writer(response)
    writer.writerow(REGISTRATION_CSV_HEADERS)
    # One example row (commented in instructions - we add a real example so format is clear)
    writer.writerow([
        'Jane Doe',
        'jane@example.com',
        '+233201234567',
        'Ghana',
        '14',
        'G1',
        'C1',
        'S',
        'RETURNING',
        '120',
        'USD',
        'John Doe',
        '+233209876543',
        'Word of mouth',
    ])
    return response


def _normalize_name(s):
    """Normalize name for matching: strip, collapse spaces, lower."""
    if not s or not isinstance(s, str):
        return ''
    return ' '.join(s.strip().split()).lower()


def _normalize_participant_id(raw_id):
    """
    Normalize participant ID from file: ensure string, strip, unify slashes and spaces.
    Excel may use backslash, full-width slash, or extra spaces. Returns normalized string or ''.
    """
    if raw_id is None:
        return ''
    s = str(raw_id).strip()
    if not s:
        return ''
    # Unify path-like separators to /
    for char in ('\\', '／', '∕', '\u2044'):
        s = s.replace(char, '/')
    # Collapse multiple slashes and trim
    s = '/'.join(p.strip() for p in s.split('/') if p.strip())
    return s


def _looks_like_participant_id(val):
    """True if string looks like ET/ASPIR/C1/003 or C1/003 style ID."""
    if val is None:
        return False
    s = _normalize_participant_id(val)
    if not s:
        return False
    parts = [p.strip().upper() for p in s.split('/') if p.strip()]
    if not parts:
        return False
    if 'ET' in parts and 'ASPIR' in parts:
        return True
    if any(p in ('C1', 'C2') for p in parts):
        return True
    return False


def _looks_like_name(val):
    """True if string looks like a person name (letters, spaces, maybe hyphen/apostrophe)."""
    if not val or not isinstance(val, str):
        return False
    s = str(val).strip()
    if len(s) < 2:
        return False
    # Should not be mostly digits or contain ET/ASPIR
    if 'ET' in s.upper() and 'ASPIR' in s.upper():
        return False
    if s.replace(' ', '').replace('-', '').replace("'", '').replace('.', '').isnumeric():
        return False
    # Allow letters, spaces, hyphen, apostrophe, period
    allowed = set(' abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-\'.')
    return all(c in allowed for c in s)


def _extract_cohort_code_from_participant_id(participant_id):
    """
    Extract cohort code from participant_id string.
    e.g. ET/ASPIR/C1/003 -> C1, ET/ASPIR/C2/001 -> C2, ET/ASPIR/C1/S/0016 -> C1.
    Accepts normalized or raw ID (slashes unified by _normalize_participant_id).
    Returns None if not in expected format.
    """
    if not participant_id:
        return None
    s = _normalize_participant_id(participant_id)
    if not s:
        return None
    parts = s.split('/')
    for p in parts:
        if p and p.upper() in ('C1', 'C2'):
            return p.upper()
    return None


def _resolve_cohort(cohort_value):
    """Resolve cohort from CSV value: C1, C2, or cohort name. Returns Cohort or None."""
    if not cohort_value or not str(cohort_value).strip():
        return None
    v = str(cohort_value).strip().upper()
    # Try by code first
    cohort = Cohort.objects.filter(code__iexact=v, is_active=True).first()
    if cohort:
        return cohort
    # Try by name (e.g. "Cohort 1")
    cohort = Cohort.objects.filter(name__icontains=v.replace('COHORT ', 'Cohort '), is_active=True).first()
    if cohort:
        return cohort
    return Cohort.objects.filter(name__icontains=cohort_value.strip(), is_active=True).first()


def _resolve_dimension(dim_value):
    """Resolve dimension from CSV value: A, S, P, I, R. Returns Dimension or None."""
    if not dim_value or not str(dim_value).strip():
        return None
    code = str(dim_value).strip().upper()[0]
    return Dimension.objects.filter(code=code, is_active=True).first()


@login_required
def import_registrations(request):
    """
    Upload a CSV file to create or update registrations (e.g. offline sign-ups).
    Rows are matched by email (case-insensitive): if a registration with that email
    exists, it is updated; otherwise a new registration is created.
    CSV must have headers matching REGISTRATION_CSV_HEADERS.
    """
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')

    if request.method == 'POST' and request.FILES.get('csv_file'):
        uploaded = request.FILES['csv_file']
        if not uploaded.name.lower().endswith('.csv'):
            messages.error(request, 'Please upload a CSV file.')
            return redirect('admin_import_registrations')

        try:
            content = uploaded.read().decode('utf-8-sig').strip()
        except UnicodeDecodeError:
            try:
                content = uploaded.read().decode('latin-1').strip()
            except Exception:
                messages.error(request, 'Could not read the file. Use UTF-8 or Latin-1 encoding.')
                return redirect('admin_import_registrations')

        reader = csv.DictReader(io.StringIO(content))
        created = 0
        updated = 0
        errors = []
        for row_num, row in enumerate(reader, start=2):
            if not row:
                continue
            # Normalize keys (strip spaces)
            row = {k.strip(): v for k, v in row.items() if k}
            full_name = (row.get('full_name') or '').strip()
            email = (row.get('email') or '').strip()
            if not full_name or not email:
                errors.append(f'Row {row_num}: full_name and email are required.')
                continue

            phone = (row.get('phone') or '').strip() or ''
            country = (row.get('country') or '').strip() or ''
            try:
                age = int((row.get('age') or '0').strip() or 0)
            except ValueError:
                age = 0
            if age < 10 or age > 22:
                errors.append(f'Row {row_num}: age must be between 10 and 22.')
                continue

            group = (row.get('group') or '').strip().upper()
            if group not in ('G1', 'G2'):
                group = 'G1' if age <= 15 else 'G2'
            cohort_val = (row.get('cohort') or '').strip()
            dimension_val = (row.get('dimension') or '').strip()
            enrollment_type = (row.get('enrollment_type') or '').strip().upper()
            if enrollment_type not in ('NEW', 'RETURNING'):
                enrollment_type = 'NEW'
            try:
                amount = float((row.get('amount') or '0').strip().replace(',', '') or 0)
            except ValueError:
                amount = 0
            currency = (row.get('currency') or 'USD').strip().upper() or 'USD'
            guardian_name = (row.get('guardian_name') or '').strip() or None
            guardian_phone = (row.get('guardian_phone') or '').strip() or None
            referral_source = (row.get('referral_source') or '').strip() or None

            cohort = _resolve_cohort(cohort_val)
            dimension = _resolve_dimension(dimension_val)
            if not cohort:
                errors.append(f'Row {row_num}: cohort "{cohort_val}" not found. Use C1, C2 or exact cohort name.')
                continue
            if not dimension:
                errors.append(f'Row {row_num}: dimension "{dimension_val}" not found. Use A, S, P, I, or R.')
                continue

            if amount <= 0:
                try:
                    pricing = PricingConfig.objects.get(enrollment_type=enrollment_type, is_active=True)
                    amount = float(pricing.total_amount)
                except PricingConfig.DoesNotExist:
                    amount = 150.00 if enrollment_type == 'NEW' else 120.00

            # Match by email (case-insensitive): update if exists, otherwise create
            existing = Registration.objects.filter(email__iexact=email).first()
            try:
                if existing:
                    existing.full_name = full_name
                    existing.phone = phone
                    existing.country = country
                    existing.age = age
                    existing.group = group
                    existing.cohort = cohort
                    existing.dimension = dimension
                    existing.cohort_code = cohort.code
                    existing.dimension_code = dimension.code
                    existing.enrollment_type = enrollment_type
                    existing.amount = amount
                    existing.currency = currency
                    existing.guardian_name = guardian_name
                    existing.guardian_phone = guardian_phone
                    existing.referral_source = referral_source
                    existing.save()
                    updated += 1
                else:
                    Registration.objects.create(
                        full_name=full_name,
                        email=email,
                        phone=phone,
                        country=country,
                        age=age,
                        group=group,
                        cohort=cohort,
                        dimension=dimension,
                        cohort_code=cohort.code,
                        dimension_code=dimension.code,
                        enrollment_type=enrollment_type,
                        amount=amount,
                        currency=currency,
                        status='PENDING',
                        guardian_name=guardian_name,
                        guardian_phone=guardian_phone,
                        referral_source=referral_source,
                    )
                    created += 1
            except Exception as e:
                errors.append(f'Row {row_num}: {str(e)}')

        if errors:
            for err in errors[:20]:
                messages.error(request, err)
            if len(errors) > 20:
                messages.error(request, f'... and {len(errors) - 20} more errors.')
        if created or updated:
            parts = []
            if created:
                parts.append(f'{created} created')
            if updated:
                parts.append(f'{updated} updated')
            messages.success(request, f'Import complete: {", ".join(parts)}. You can mark offline payments as full/half in Edit Registration.')
        if created == 0 and updated == 0 and not errors:
            messages.warning(request, 'No rows were imported. Check that the CSV has a header row and data rows with full_name and email.')
        return redirect('admin_registrations')

    return render(request, 'registrations/admin/import_registrations.html', {})


def _parse_id_file_rows(uploaded):
    """
    Parse CSV or Excel file into list of dicts with keys 'name', 'participant_id'.
    CSV: expects headers 'Name' and 'Participant ID' (or 'ID').
    Excel: first sheet; column A = name, B = participant ID; or use first row as headers if it looks like headers.
    """
    name_key = None
    id_key = None
    rows = []

    if uploaded.name.lower().endswith('.csv'):
        try:
            content = uploaded.read().decode('utf-8-sig').strip()
        except UnicodeDecodeError:
            content = uploaded.read().decode('latin-1').strip()
        reader = csv.DictReader(io.StringIO(content))
        for row in reader:
            row = {k.strip(): v for k, v in row.items() if k}
            if name_key is None:
                for k in row:
                    if k and 'name' in k.lower():
                        name_key = k
                    if k and ('participant' in k.lower() or k.lower() == 'id'):
                        id_key = k
                if not name_key:
                    name_key = 'Name'
                if not id_key:
                    id_key = 'Participant ID'
            name = (row.get(name_key) or '').strip()
            pid = _normalize_participant_id(row.get(id_key))
            if name or pid:
                rows.append({'name': name, 'participant_id': pid})
        return rows

    if uploaded.name.lower().endswith(('.xlsx', '.xls')):
        try:
            import openpyxl
        except ImportError:
            return None  # caller will show "install openpyxl" message
        uploaded.seek(0)
        wb = openpyxl.load_workbook(uploaded, read_only=True, data_only=True)
        ws = wb.active
        data = list(ws.iter_rows(values_only=True))
        wb.close()
        if not data:
            return []
        # Convert first row to strings for header detection
        first = []
        for c in data[0]:
            if c is None:
                first.append('')
            elif isinstance(c, float) and c == int(c):
                first.append(str(int(c)))
            else:
                first.append(str(c).strip())
        # Check if first row looks like headers
        if first[0] and 'name' in first[0].lower() and (len(first) < 2 or 'participant' in (first[1] or '').lower() or (first[1] or '').strip().upper() == 'ID'):
            # Header row
            name_col = 0
            id_col = 1 if len(first) > 1 else 0
            for i, cell in enumerate(first):
                if cell and 'name' in cell.lower():
                    name_col = i
                if cell and ('participant' in cell.lower() or cell.strip().upper() == 'ID'):
                    id_col = i
            for row in data[1:]:
                row = list(row) if row else []
                name = (row[name_col] if name_col < len(row) else None) or ''
                name = str(name).strip()
                raw_pid = row[id_col] if id_col < len(row) else None
                pid = _normalize_participant_id(raw_pid)
                if name or pid:
                    rows.append({'name': name, 'participant_id': pid})
        else:
            # No header: detect column order from first data row (or first row)
            name_col, id_col = 0, 1
            if len(data) > 0:
                r0 = list(data[0]) if data[0] else []
                c0 = (r0[0] if len(r0) > 0 else None)
                c1 = (r0[1] if len(r0) > 1 else None)
                str0 = str(c0).strip() if c0 is not None else ''
                str1 = str(c1).strip() if c1 is not None else ''
                if _looks_like_participant_id(str0) and _looks_like_name(str1):
                    id_col, name_col = 0, 1
                elif _looks_like_name(str0) and _looks_like_participant_id(str1):
                    name_col, id_col = 0, 1
            for row in data:
                row = list(row) if row else []
                name = (row[name_col] if name_col < len(row) else None) or ''
                name = str(name).strip()
                raw_pid = row[id_col] if id_col < len(row) else None
                pid = _normalize_participant_id(raw_pid)
                if name or pid:
                    rows.append({'name': name, 'participant_id': pid})
        return rows

    return None


@login_required
def update_participant_ids_from_file(request):
    """
    Upload a file (CSV or Excel) with columns Name and Participant ID (e.g. from "New Elevate Tribe ID #s").
    Matches rows to registrations by name and optionally cohort from the ID; updates participant_id and cohort.
    """
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')

    if request.method == 'POST' and request.FILES.get('id_file'):
        uploaded = request.FILES['id_file']
        if not uploaded.name.lower().endswith(('.csv', '.xlsx', '.xls')):
            messages.error(request, 'Please upload a CSV or Excel (.xlsx) file.')
            return redirect('admin_update_participant_ids_from_file')

        rows = _parse_id_file_rows(uploaded)
        if rows is None:
            messages.error(request, 'Excel support requires openpyxl. Install it with: pip install openpyxl')
            return redirect('admin_update_participant_ids_from_file')
        if not rows:
            messages.warning(request, 'No rows found in the file. CSV needs headers "Name" and "Participant ID".')
            return redirect('admin_update_participant_ids_from_file')

        updated_count = 0
        skipped_no_match = []
        skipped_multiple = []
        skipped_invalid_id = []
        errors = []

        for item in rows:
            name = item.get('name') or ''
            participant_id = _normalize_participant_id(item.get('participant_id'))
            if not participant_id:
                continue
            # Skip rows where ID doesn't look like ET/ASPIR/C1/003 (e.g. Excel gave us just a number)
            if not _looks_like_participant_id(participant_id):
                skipped_invalid_id.append(f'{name or "(no name)"}: "{participant_id}"')
                continue
            cohort_code = _extract_cohort_code_from_participant_id(participant_id)
            cohort = _resolve_cohort(cohort_code) if cohort_code else None

            norm_name = _normalize_name(name)
            if not norm_name:
                continue

            # Find registration(s) with matching name (exact normalized match)
            candidates = list(
                Registration.objects.filter(
                    full_name__iexact=name
                ).select_related('cohort')
            )
            if not candidates:
                # Try normalized: registration full_name normalized equals norm_name
                all_regs = Registration.objects.all().select_related('cohort')
                candidates = [r for r in all_regs if _normalize_name(r.full_name) == norm_name]
            if not candidates:
                # Fallback: registration full_name contains name or name in full_name (e.g. "Nana Ama Kwartemah" vs "Nana Ama Kwartemah Agyei")
                all_regs = Registration.objects.all().select_related('cohort')
                candidates = [r for r in all_regs if (
                    norm_name in _normalize_name(r.full_name) or _normalize_name(r.full_name) in norm_name
                )]

            if not candidates:
                skipped_no_match.append(name)
                continue
            if len(candidates) > 1 and cohort:
                candidates = [r for r in candidates if r.cohort and r.cohort.code == cohort_code]
            if len(candidates) > 1:
                skipped_multiple.append(name)
                continue
            reg = candidates[0]
            # Store in canonical form: ET/ASPIR/C1/003 (3-digit sequence)
            canonical_id = parse_participant_id_to_canonical(participant_id)
            reg.participant_id = canonical_id if canonical_id else participant_id
            if cohort:
                reg.cohort = cohort
                reg.cohort_code = cohort.code
            reg.save(update_fields=['participant_id', 'cohort', 'cohort_code', 'updated_at'])
            updated_count += 1

        if updated_count:
            messages.success(request, f'Updated participant ID and cohort for {updated_count} registration(s).')
        if skipped_no_match:
            messages.warning(
                request,
                f'No match in registrations for: {", ".join(skipped_no_match[:15])}' +
                (f' ... and {len(skipped_no_match) - 15} more' if len(skipped_no_match) > 15 else '')
            )
        if skipped_multiple:
            messages.warning(
                request,
                f'Multiple registrations with same name (could not pick one): {", ".join(skipped_multiple[:10])}' +
                (f' ... and {len(skipped_multiple) - 10} more' if len(skipped_multiple) > 10 else '')
            )
        if skipped_invalid_id:
            messages.warning(
                request,
                f'Unrecognized ID format (expected e.g. ET/ASPIR/C1/003): {"; ".join(skipped_invalid_id[:5])}' +
                (f' ... and {len(skipped_invalid_id) - 5} more' if len(skipped_invalid_id) > 5 else '')
            )
        if errors:
            for err in errors[:10]:
                messages.error(request, err)
        return redirect('admin_registrations')

    return render(request, 'registrations/admin/update_participant_ids_from_file.html', {})


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
        # Send appropriate email to the participant
        try:
            if payment_type == 'full_payment' or reference.startswith('ASPIR-FULL-'):
                generate_participant_id(registration)
                send_payment_complete_email(registration)
            elif payment_type == 'registration_fee' or reference.startswith('ASPIR-REG-'):
                send_registration_confirmation_email(registration)
            elif payment_type == 'course_fee' or reference.startswith('ASPIR-COURSE-'):
                if registration.is_fully_paid():
                    generate_participant_id(registration)
                    send_payment_complete_email(registration)
                else:
                    send_course_fee_payment_email(registration)
        except Exception:
            pass
        # Notify staff (elevatetribeanalytics9, amosbenita7) – full vs partial
        try:
            send_staff_payment_notification_email(
                registration, payment_type, amount_in_usd, reference=reference
            )
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
def bulk_generate_participant_ids_view(request):
    """
    Generate participant IDs for all registrations that have a cohort but no ID yet.
    POST only. Redirects back to registrations list with count of generated IDs.
    """
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    if request.method != 'POST':
        return redirect('admin_registrations')

    # Registrations that can get an ID: have cohort, no participant_id yet (dimension not required for ID)
    from django.db.models import Q
    without_id = Registration.objects.filter(
        cohort__isnull=False,
    ).filter(Q(participant_id__isnull=True) | Q(participant_id=''))
    generated = 0
    for reg in without_id:
        if generate_participant_id(reg):
            generated += 1
    if generated:
        messages.success(
            request,
            f'Generated participant IDs for {generated} registration(s). Their numbers now appear in the list and in Export CSV.'
        )
    else:
        messages.info(request, 'No registrations needed an ID. All with a cohort already have one.')
    return redirect('admin_registrations')


@login_required
def generate_participant_id_view(request, registration_id):
    """
    Generate participant ID only (no email). POST only.
    Redirects back to view_registration with the new ID in the message.
    """
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    if request.method != 'POST':
        return redirect('view_registration', registration_id=registration_id)

    registration = get_object_or_404(
        Registration.objects.select_related('cohort', 'dimension'),
        id=registration_id
    )
    if not registration.cohort:
        messages.error(
            request,
            'Assign a Cohort first, then generate the participant ID.'
        )
        return redirect('view_registration', registration_id=registration_id)
    new_id = generate_participant_id(registration)
    if new_id:
        messages.success(request, f'Participant ID generated: {new_id}. You can send it by email or export from the list.')
    else:
        messages.error(request, 'Could not generate participant ID. Check that a cohort is assigned.')
    return redirect('view_registration', registration_id=registration_id)


@login_required
def send_participant_id_email_view(request, registration_id):
    """
    Generate participant ID if missing and send it by email to the participant.
    POST only. Redirects back to view_registration with success or error message.
    """
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    if request.method != 'POST':
        return redirect('view_registration', registration_id=registration_id)

    registration = get_object_or_404(
        Registration.objects.select_related('cohort', 'dimension'),
        id=registration_id
    )
    had_id_before = bool(registration.participant_id)
    if send_participant_id_email(registration):
        msg = 'Participant ID generated and sent' if not had_id_before else 'Participant ID sent'
        messages.success(request, f'{msg} to {registration.email}.')
    else:
        messages.error(
            request,
            'Could not send participant ID. Ensure the registration has a cohort assigned.'
        )
    return redirect('view_registration', registration_id=registration_id)


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
            # Reload so we see participant_id if it was auto-generated
            registration.refresh_from_db()
            msg = f'Registration for {registration.full_name} has been updated.'
            if registration.participant_id:
                msg += f' Participant ID: {registration.participant_id}'
            messages.success(request, msg)
            return redirect('view_registration', registration_id=registration.id)
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
