# shop/utils.py
from django.conf import settings

def get_currency_for_country(code: str):
    code = (code or "").upper()
    if code == "NG":
        return "NGN"
    if code in getattr(settings, "EU_COUNTRIES", []):
        return "EUR"
    return getattr(settings, "NON_LOCAL_DEFAULT_CURRENCY", "USD")

# shop/utils.py
NIGERIA_STATES = [
    "Abia", "Adamawa", "Akwa Ibom", "Anambra", "Bauchi", "Bayelsa",
    "Benue", "Borno", "Cross River", "Delta", "Ebonyi", "Edo", "Ekiti",
    "Enugu", "Gombe", "Imo", "Jigawa", "Kaduna", "Kano", "Katsina",
    "Kebbi", "Kogi", "Kwara", "Lagos", "Nasarawa", "Niger", "Ogun",
    "Ondo", "Osun", "Oyo", "Plateau", "Rivers", "Sokoto", "Taraba",
    "Yobe", "Zamfara", "FCT"
]

COUNTRY_NAMES = {
    "NG": "Nigeria",
    "US": "United States",
    "GB": "United Kingdom",
    "CA": "Canada",
    "GH": "Ghana",
    "ZA": "South Africa",
    "FR": "France",
    "DE": "Germany",
}

def get_country_name(code):
    """Return readable country name from code."""
    return COUNTRY_NAMES.get(code.upper(), code)

from decimal import Decimal

def calculate_local_shipping(state: str):
    state = (state or "").strip().lower()
    branch_states = ["lagos", "rivers"]

    if state in branch_states:
        return Decimal("6000.00"), "Branch Delivery (Lagos / Rivers)"
    else:
        return Decimal("7500.00"), "Nationwide Delivery"
