# shop/context_processors.py
from django.conf import settings

def country_context(request):
    country = request.session.get("detected_country", "ZZ")
    # currency map
    if country == "NG":
        currency = "NGN"
    elif country in getattr(settings, "EU_COUNTRIES", []):
        currency = "EUR"
    else:
        currency = request.session.get("currency") or settings.DEFAULT_CURRENCY

    detected_country_name = country  # optional: map code->name if you want names

    return {
        "detected_country": country,
        "detected_country_name": detected_country_name,
        "country_source": request.session.get("country_source", "unknown"),
        "site_currency": currency,
        "show_country_popup": request.session.pop("show_country_popup", False),
        "dhl_supported_countries": getattr(settings, "DHL_SUPPORTED_COUNTRIES", []),
    }
