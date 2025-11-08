from django.urls import path
from . import views

urlpatterns = [
    path("api/dhl/countries/", views.api_countries, name="api_countries"),
    path("api/dhl/cities/", views.api_cities, name="api_cities"),
]
