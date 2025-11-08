from django.db import models


class Country(models.Model):
    """Represents a country (ISO codes + full name)."""
    name = models.CharField(max_length=200, unique=True)
    iso2 = models.CharField(
        max_length=2,
        unique=True,
        db_index=True,
        default="XX"   # placeholder until real ISO2 is added
    )
    iso3 = models.CharField(
        max_length=3,
        unique=True,
        db_index=True,
        default="XXX"  # placeholder until real ISO3 is added
    )

    class Meta:
        verbose_name_plural = "Countries"

    def __str__(self):
        return f"{self.name} ({self.iso2})"


class Region(models.Model):
    """Admin1/region-level subdivision (state/province)."""
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="regions")
    code = models.CharField(max_length=20, blank=True, null=True, db_index=True)  # e.g. state code
    name = models.CharField(max_length=200)

    class Meta:
        unique_together = ("country", "code")
        indexes = [
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return f"{self.name}, {self.country.iso2}"


class City(models.Model):
    """City or town within a region/country."""
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="cities")
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True, related_name="cities")
    name = models.CharField(max_length=200, db_index=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)   # high precision
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    population = models.BigIntegerField(default=0)

    class Meta:
        unique_together = ("name", "country", "region")  # prevent duplicate city names in same region
        indexes = [
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return f"{self.name}, {self.country.iso2}"


class PostalCode(models.Model):
    """Postal/ZIP code system — may or may not be tied to a specific city."""
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="postal_codes")
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True, related_name="postal_codes")
    code = models.CharField(max_length=20, db_index=True)

    class Meta:
        unique_together = ("country", "code")  # avoids duplicates per country
        indexes = [
            models.Index(fields=["code"]),
        ]

    def __str__(self):
        return f"{self.code} - {self.country.iso2}" + (f" ({self.city.name})" if self.city else "")

class DHLAvailableCountry(models.Model):
    """Countries where DHL shipping is supported."""
    country = models.OneToOneField(Country, on_delete=models.CASCADE, related_name="dhl_info")
    enabled = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)  # optional: DHL-specific notes

    class Meta:
        verbose_name_plural = "DHL Available Countries"

    def __str__(self):
        return f"DHL: {self.country.name} ({'Enabled' if self.enabled else 'Disabled'})"
