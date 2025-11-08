from django.contrib import admin
from .models import Country, Region, City, PostalCode


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("name", "iso2", "iso3")
    search_fields = ("name", "iso2", "iso3")


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("name", "country", "code")
    search_fields = ("name", "code")
    list_filter = ("country",)


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "country", "region", "population")
    search_fields = ("name", "region__name")
    list_filter = ("country", "region")


@admin.register(PostalCode)
class PostalCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "country", "city")
    search_fields = ("code", "city__name")
    list_filter = ("country",)
