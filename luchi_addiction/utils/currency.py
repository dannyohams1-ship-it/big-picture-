# luchi_addiction/utils/currency.py
import logging
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from datetime import datetime

import requests
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)

# === Configuration (all overridable from settings) ===
API_BASE_URL = getattr(settings, "EXCHANGE_RATE_API_URL", "https://open.er-api.com/v6/latest/USD")
CACHE_KEY = getattr(settings, "EXCHANGE_RATES_CACHE_KEY", "exchange_rates")
CACHE_TTL = getattr(settings, "EXCHANGE_RATES_CACHE_TTL", 60 * 60 * 24)  # default 24h
API_TIMEOUT = getattr(settings, "EXCHANGE_RATE_API_TIMEOUT", 10)

BASE_CURRENCY = getattr(settings, "BASE_CURRENCY", "NGN")
SUPPORTED_CURRENCIES = getattr(settings, "SUPPORTED_CURRENCIES", ["NGN", "USD", "EUR"])

_SYMBOLS = getattr(settings, "CURRENCY_SYMBOLS", {"USD": "$", "EUR": "€", "NGN": "₦"})
_LOCALE_MAP = getattr(settings, "CURRENCY_LOCALES", {"USD": "en_US", "EUR": "de_DE", "NGN": "en_NG"})


# === Helpers ===
def _to_decimal(value: object) -> Decimal:
    """Safely convert any value to Decimal; return Decimal('0') on invalid input."""
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as e:
        logger.debug("Failed to convert %r to Decimal: %s", value, e)
        return Decimal("0")


def _fetch_rates_from_api():
    """Fetch latest exchange rates from external API (expected base = USD)."""
    try:
        resp = requests.get(API_BASE_URL, timeout=API_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        # open.er-api: expects {"result": "success", "rates": {...}}
        if data.get("result") != "success":
            logger.warning("Exchange API returned non-success: %s", data.get("result"))
            return None

        rates = data.get("rates", {}) or {}
        rates["USD"] = 1.0  # ensure USD present
        rates = {k: _to_decimal(v) for k, v in rates.items()}
        return {"rates": rates, "fetched_at": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.warning("Failed to fetch exchange rates from %s: %s", API_BASE_URL, e)
        return None


# === Public API ===
def get_exchange_rates(force_refresh: bool = False):
    if not force_refresh:
        cached = cache.get(CACHE_KEY)
        if cached:
            return cached

    fresh = _fetch_rates_from_api()
    if fresh:
        rates = fresh["rates"]

        # normalize so NGN = 1
        ngn_rate = rates.get("NGN")
        if ngn_rate and ngn_rate != 0:
            normalized = {cur: (rate / ngn_rate) for cur, rate in rates.items()}
            fresh["rates"] = normalized

        cache.set(CACHE_KEY, fresh, CACHE_TTL)
        return fresh

    # try to return cached even after failed fetch
    cached = cache.get(CACHE_KEY)
    if cached:
        return cached

    # final fallback to DEFAULT_EXCHANGE_RATES from settings
    default_rates = getattr(
        settings,
        "DEFAULT_EXCHANGE_RATES",
        {
            "NGN": "1",
            "USD": "0.0006705",
            "EUR": "0.0005693",
        },
    )
    rates = {k: _to_decimal(v) for k, v in default_rates.items()}
    return {"rates": rates, "fetched_at": datetime.utcnow().isoformat()}



def _is_supported(currency: str) -> bool:
    return currency in SUPPORTED_CURRENCIES

def convert_price(amount, from_currency=BASE_CURRENCY, to_currency=None, request=None):
    if request:
        to_currency = request.session.get("currency", BASE_CURRENCY)
    if not to_currency:
        to_currency = BASE_CURRENCY

    amount_dec = _to_decimal(amount)
    if from_currency == to_currency:
        return amount_dec.quantize(Decimal("0.00"), rounding=ROUND_HALF_UP)

    rates = get_exchange_rates().get("rates", {})
    from_rate = rates.get(from_currency)
    to_rate = rates.get(to_currency)

    if not from_rate or not to_rate:
        return amount_dec.quantize(Decimal("0.00"), rounding=ROUND_HALF_UP)

    return (amount_dec / from_rate * to_rate).quantize(Decimal("0.00"), rounding=ROUND_HALF_UP)

def format_price(amount, currency: str = BASE_CURRENCY, locale: str | None = None) -> str:

    try:
        from babel.numbers import format_currency

        if not locale:
            locale = _LOCALE_MAP.get(currency, "en_US")

        # ensure Decimal for consistent formatting
        if not isinstance(amount, Decimal):
            amount = _to_decimal(amount)

        return format_currency(amount, currency, locale=locale)
    except Exception as e:
        logger.debug("Babel formatting failed for %r %s: %s", amount, currency, e)
        symbol = _SYMBOLS.get(currency, currency + " ")
        try:
            if not isinstance(amount, Decimal):
                amount = _to_decimal(amount)
            return f"{symbol}{amount:,.2f}"
        except Exception:
            # ultimate fallback
            return f"{symbol}0.00"



def get_current_currency(request):
    return request.session.get("currency", BASE_CURRENCY)

