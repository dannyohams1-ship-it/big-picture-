# views.py
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from services.dhl_client import fetch_dhl_countries, fetch_dhl_cities


@require_GET
def api_countries(request):
    """
    Get DHL-available countries.
    Example: /api/dhl/countries/
    """
    try:
        data = fetch_dhl_countries()
        return JsonResponse({"countries": data})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def api_cities(request):
    """
    Get DHL-available cities for a given country.
    Example: /api/dhl/cities/?country=NG
    """
    country = request.GET.get("country")
    if not country:
        return JsonResponse({"error": "country required"}, status=400)

    try:
        data = fetch_dhl_cities(country)
        return JsonResponse({"cities": data})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
