import json
import requests
from django.conf import settings
from django.utils import timezone
from shop.utils import get_currency_for_country


def _get_client_ip(request):
    """Extract client IP (supports proxies)."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


class CountryDetectionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # --- Skip admin and static paths ---
        if request.path.startswith("/admin") or request.path.startswith(settings.STATIC_URL):
            return self.get_response(request)

        # --- Manual country switcher (from dropdown or AJAX) ---
        if "switch_country" in request.GET:
            code = request.GET["switch_country"].upper()
            request.session["detected_country"] = code
            request.session["detected_country_name"] = code
            request.session["country_source"] = "manual"
            request.session["country_timestamp"] = timezone.now().isoformat()
            request.session["currency"] = get_currency_for_country(code)

            response = self.get_response(request)
            response.set_cookie(
                settings.COUNTRY_COOKIE_NAME,
                json.dumps({
                    "country": code,
                    "country_name": code,
                    "source": "manual",
                    "ts": request.session["country_timestamp"],
                }),
                max_age=settings.COUNTRY_COOKIE_AGE,
                httponly=False,
                samesite="Lax",
            )
            return response

        # --- Debug override (useful in development/testing) ---
        if settings.DEBUG and request.GET.get("force_country"):
            code = request.GET["force_country"].upper()
            request.session["detected_country"] = code
            request.session["detected_country_name"] = code  # fallback name if API not used
            request.session["country_source"] = "forced"
            request.session["country_timestamp"] = timezone.now().isoformat()
            request.session["currency"] = get_currency_for_country(code)

            response = self.get_response(request)
            response.set_cookie(
                settings.COUNTRY_COOKIE_NAME,
                json.dumps({
                    "country": code,
                    "country_name": code,
                    "source": "forced",
                    "ts": request.session["country_timestamp"],
                }),
                max_age=settings.COUNTRY_COOKIE_AGE,
                httponly=False,
                samesite="Lax",
            )
            return response

        # --- Already detected? Ensure currency still exists ---
        if request.session.get("detected_country"):
            if not request.session.get("currency"):
                country = request.session.get("detected_country", "ZZ")
                request.session["currency"] = get_currency_for_country(country)
            return self.get_response(request)

        # --- Default values ---
        country = "ZZ"
        country_name = "Unknown"

        # --- Try GeoIP lookup ---
        ip = _get_client_ip(request)
        try:
            if settings.GEOIP_PROVIDER == "ipapi":
                r = requests.get(f"https://ipapi.co/{ip}/json/", timeout=2)
                if r.status_code == 200:
                    data = r.json()
                    country = data.get("country_code", "ZZ")
                    country_name = data.get("country_name", "Unknown")
        except Exception:
            country, country_name = "ZZ", "Unknown"

        # --- Check supported countries (business logic) ---
        supported_countries = getattr(settings, "DHL_SUPPORTED_COUNTRIES", [])
        if supported_countries and country not in supported_countries:
            # If not supported, fallback to "ZZ" but still store original name
            country = "ZZ"

        # --- Save to session ---
        request.session["detected_country"] = country
        request.session["detected_country_name"] = country_name
        request.session["country_source"] = "geoip"
        request.session["country_timestamp"] = timezone.now().isoformat()
        request.session["currency"] = get_currency_for_country(country)

        # --- Save to cookie (accessible to frontend JS) ---
        response = self.get_response(request)
        response.set_cookie(
            settings.COUNTRY_COOKIE_NAME,
            json.dumps({
                "country": country,
                "country_name": country_name,
                "source": "geoip",
                "ts": request.session["country_timestamp"],
            }),
            max_age=settings.COUNTRY_COOKIE_AGE,
            httponly=False,
            samesite="Lax",
        )
        return response
