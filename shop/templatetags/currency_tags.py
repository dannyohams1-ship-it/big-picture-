from django import template
from django.conf import settings
from decimal import Decimal
from luchi_addiction.utils.currency import convert_price, format_price
import logging

register = template.Library()
logger = logging.getLogger(__name__)

@register.filter(name="as_currency")
def as_currency(amount, currency_code=None):
    """
    Convert and format price into the chosen currency.
    Usage: {{ product.price|as_currency:request.session.currency }}
    """
    if amount is None:
        return ""

    # Ensure Decimal safety
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))

    base_currency = getattr(settings, "BASE_CURRENCY", "NGN")  # default base
    target_currency = currency_code or base_currency

    # Ensure target is supported
    supported = getattr(settings, "SUPPORTED_CURRENCIES", [base_currency])
    if target_currency not in supported:
        logger.warning(f"Unsupported currency '{target_currency}', falling back to {base_currency}")
        target_currency = base_currency

    converted = convert_price(
        amount,
        from_currency=base_currency,
        to_currency=target_currency
    )
    return format_price(converted, currency=target_currency)
