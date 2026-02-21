"""
Utility functions for the registrations app.
"""
import requests
from django.core.cache import cache
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def get_usd_to_ngn_rate():
    """
    Fetch live USD to NGN exchange rate from API.
    Uses caching to avoid excessive API calls.
    Falls back to configured rate if API fails.
    
    Returns:
        float: USD to NGN exchange rate
    """
    # Check cache first (cache for 1 hour)
    cached_rate = cache.get('usd_to_ngn_rate')
    if cached_rate:
        return float(cached_rate)
    
    # Try to fetch from API
    try:
        # Using exchangerate-api.com (free tier: 1,500 requests/month)
        # Alternative: You can use other APIs like fixer.io, currencylayer, etc.
        api_url = 'https://api.exchangerate-api.com/v4/latest/USD'
        
        response = requests.get(api_url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        ngn_rate = data.get('rates', {}).get('NGN')
        
        if ngn_rate:
            # Cache for 1 hour (3600 seconds)
            cache.set('usd_to_ngn_rate', ngn_rate, 3600)
            logger.info(f"Fetched live USD to NGN rate: {ngn_rate}")
            return float(ngn_rate)
        else:
            logger.warning("NGN rate not found in API response")
            
    except requests.exceptions.RequestException as e:
        logger.warning(f"Failed to fetch exchange rate from API: {str(e)}")
    except (KeyError, ValueError) as e:
        logger.warning(f"Error parsing exchange rate API response: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error fetching exchange rate: {str(e)}")
    
    # Fallback to configured rate
    fallback_rate = getattr(settings, 'USD_TO_NGN_RATE', 1500.0)
    logger.info(f"Using fallback USD to NGN rate: {fallback_rate}")
    return float(fallback_rate)


def get_usd_to_ngn_rate_alternative():
    """
    Alternative method using a different API (fixer.io or currencylayer).
    Uncomment and configure if you prefer a different provider.
    """
    try:
        # Option 1: Using fixer.io (requires API key)
        # api_key = getattr(settings, 'FIXER_API_KEY', '')
        # if api_key:
        #     api_url = f'http://data.fixer.io/api/latest?access_key={api_key}&symbols=NGN&base=USD'
        #     response = requests.get(api_url, timeout=5)
        #     data = response.json()
        #     if data.get('success'):
        #         return float(data['rates']['NGN'])
        
        # Option 2: Using currencylayer (requires API key)
        # api_key = getattr(settings, 'CURRENCYLAYER_API_KEY', '')
        # if api_key:
        #     api_url = f'http://api.currencylayer.com/live?access_key={api_key}&currencies=NGN&source=USD'
        #     response = requests.get(api_url, timeout=5)
        #     data = response.json()
        #     if data.get('success'):
        #         return float(data['quotes']['USDNGN'])
        
        pass
    except Exception as e:
        logger.error(f"Error in alternative exchange rate fetch: {str(e)}")
    
    return None


# Canonical participant ID format: ET/ASPIR/{cohort}/NNN (e.g. ET/ASPIR/C1/003)
# Cohort is C1 or C2; sequence is exactly 3 digits: 001, 002, 003, ...
PARTICIPANT_ID_FORMAT = "ET/ASPIR/{cohort}/{seq:03d}"


def format_participant_id_canonical(cohort_code, sequence):
    """
    Return participant ID in canonical form: ET/ASPIR/C1/003.
    cohort_code: e.g. C1, C2 (will be uppercased).
    sequence: integer (1, 2, 3, ...); will be zero-padded to 3 digits.
    """
    c = str(cohort_code).strip().upper()
    try:
        seq = int(sequence)
    except (TypeError, ValueError):
        seq = 1
    return f"ET/ASPIR/{c}/{seq:03d}"


def get_next_available_sequence(cohort_code):
    """
    Return the next available sequence number (integer) for participant IDs
    in the given cohort (e.g. C1, C2). Used when normalizing IDs to avoid duplicates.
    """
    from .models import Registration
    c = str(cohort_code).strip().upper()
    prefix = f"ET/ASPIR/{c}/"
    existing = Registration.objects.filter(
        participant_id__startswith=prefix
    ).exclude(participant_id__isnull=True).exclude(participant_id="")
    next_seq = 1
    for r in existing:
        try:
            part = (r.participant_id or "").split("/")[-1]
            if part.isdigit():
                next_seq = max(next_seq, int(part) + 1)
        except (ValueError, IndexError):
            pass
    return next_seq


def parse_participant_id_to_canonical(participant_id):
    """
    Parse a participant_id string (from file or DB) into canonical form ET/ASPIR/C1/003.
    Accepts ET/ASPIR/C1/003, ET/ASPIR/C1/3, ET/ASPIR/C1/0001, etc.
    Returns canonical string or None if invalid.
    """
    if not participant_id or not isinstance(participant_id, str):
        return None
    # Normalize slashes
    s = participant_id.strip().replace("\\", "/").replace("／", "/")
    parts = [p.strip() for p in s.split("/") if p.strip()]
    if len(parts) < 3:
        return None
    # Find cohort (C1 or C2) and the numeric segment
    cohort_code = None
    seq_num = None
    for i, p in enumerate(parts):
        if p.upper() in ("C1", "C2"):
            cohort_code = p.upper()
            # Next part after cohort is usually the sequence (or there might be dimension in old format)
            for j in range(i + 1, len(parts)):
                if parts[j].isdigit():
                    seq_num = int(parts[j])
                    break
            break
    if not cohort_code or seq_num is None:
        return None
    return format_participant_id_canonical(cohort_code, seq_num)


def generate_participant_id(registration):
    """
    Generate and assign a unique participant ID for a registration.
    Format: ET/ASPIR/{cohort_code}/{sequence} with 3-digit sequence: 001, 002, 003, ...

    Call when the participant is fully registered (e.g. when payment is complete).
    Returns the assigned participant_id, or None if cohort missing.
    """
    from .models import Registration
    from django.db import transaction

    if getattr(registration, 'participant_id', None):
        return registration.participant_id
    if not registration.cohort:
        return None

    cohort_code = registration.cohort.code.strip().upper()
    if not cohort_code:
        return None

    cohort_prefix = f"ET/ASPIR/{cohort_code}/"

    with transaction.atomic():
        Registration.objects.select_for_update().filter(
            cohort_id=registration.cohort_id
        ).exists()

        existing = Registration.objects.filter(
            participant_id__startswith=cohort_prefix
        ).exclude(participant_id__isnull=True).exclude(participant_id="")

        next_seq = 1
        for r in existing:
            try:
                part = (r.participant_id or "").split("/")[-1]
                if part.isdigit():
                    next_seq = max(next_seq, int(part) + 1)
            except (ValueError, IndexError):
                pass

        new_id = format_participant_id_canonical(cohort_code, next_seq)
        registration.participant_id = new_id
        registration.save(update_fields=["participant_id"])
        logger.info(f"Generated participant_id {new_id} for registration {registration.id}")
        return new_id
