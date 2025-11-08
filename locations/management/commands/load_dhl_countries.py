import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from locations.models import Country, DHLAvailableCountry

class Command(BaseCommand):
    help = "Fetch DHL supported countries via DHL API and update DHLAvailableCountry table"

    def handle(self, *args, **options):
        url = settings.DHL_API_URL
        headers = {
            "DHL-API-Key": settings.DHL_API_KEY,
            # Sometimes they also require Basic Auth (depends on API)
        }

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to fetch DHL countries: {e}"))
            return

        count = 0
        for item in data.get("countries", []):
            iso2 = item.get("countryCode")
            if not iso2:
                continue

            try:
                country = Country.objects.get(iso2__iexact=iso2)
            except Country.DoesNotExist:
                self.stderr.write(self.style.WARNING(f"Skipping unknown country: {iso2}"))
                continue

            DHLAvailableCountry.objects.update_or_create(
                country=country,
                defaults={"enabled": True}
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f"✅ Synced DHL countries: {count}"))
