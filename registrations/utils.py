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
