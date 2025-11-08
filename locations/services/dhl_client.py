import requests
from django.conf import settings

def fetch_dhl_countries():
    url = f"{settings.DHL_API_BASE_URL}/shipping/v1/capabilities/countries"
    headers = {
        "DHL-API-Key": settings.DHL_API_KEY,
        "Accept": "application/json"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def fetch_dhl_cities(country_code):
    url = f"{settings.DHL_API_BASE_URL}/shipping/v1/capabilities/countries/{country_code}/cities"
    headers = {
        "DHL-API-Key": settings.DHL_API_KEY,
        "Accept": "application/json"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()
