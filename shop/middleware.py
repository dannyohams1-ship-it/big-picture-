from django.conf import settings

class CurrencyMiddleware:
    """
    Ensures every session always has a currency set.
    Falls back to BASE_CURRENCY if not.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        base_currency = getattr(settings, "BASE_CURRENCY", "USD")
        supported = getattr(settings, "SUPPORTED_CURRENCIES", ["USD", "EUR", "NGN"])

        # If no currency in session, set it
        if "currency" not in request.session:
            request.session["currency"] = base_currency

        # If an invalid currency somehow sneaks in, reset it
        if request.session["currency"] not in supported:
            request.session["currency"] = base_currency

        return self.get_response(request)
