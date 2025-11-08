# shop/templatetags/currency.py
from django import template
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

try:
    from luchi_addiction.utils.currency import convert_price, format_price
except Exception as e:
    # If import fails, provide no-op fallbacks to avoid template crashes.
    logger.exception("currency utils import failed: %s", e)

    def convert_price(amount, from_c, to_c):
        return amount

    def format_price(amount, currency):
        try:
            return f"{amount:.2f}"
        except Exception:
            return str(amount)

register = template.Library()

@register.filter
def as_currency(amount, currency=None):
    # Currency may be None (session missing). Use app default.
    if not currency:
        currency = getattr(settings, "DEFAULT_DISPLAY_CURRENCY", None) or \
                   (getattr(settings, "SUPPORTED_CURRENCIES", ["USD"])[0])
    try:
        converted = convert_price(amount, "USD", currency)
        return format_price(converted, currency)
    except Exception as e:
        logger.exception("as_currency filter failed: %s", e)
        # fallback: show raw amount as USD
        try:
            return format_price(amount, "USD")
        except Exception:
            return str(amount)
