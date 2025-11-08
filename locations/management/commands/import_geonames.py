# locations/management/commands/import_geonames.py
import os
import zipfile
import requests
from io import TextIOWrapper
from django.core.management.base import BaseCommand
from django.conf import settings
from locations.models import Country, Region, City, PostalCode
from django.db import transaction

GEONAMES_BASE = "https://download.geonames.org/export/dump"

class Command(BaseCommand):
    help = "Import GeoNames (countries and cities). Use --countries=US,NG and --min-pop=5000 to limit."

    def add_arguments(self, parser):
        parser.add_argument("--countries", type=str, help="Comma-separated ISO country codes (e.g. US,NG).")
        parser.add_argument("--min-pop", type=int, default=5000, help="Minimum city population to import (0 = all).")
        parser.add_argument("--limit", type=int, default=0, help="Stop after N cities (for testing).")

    def handle(self, *args, **options):
        countries_arg = options.get("countries")
        min_pop = options.get("min_pop") or 0
        limit = options.get("limit") or 0

        countries = None
        if countries_arg:
            countries = [c.strip().upper() for c in countries_arg.split(",")]
            self.stdout.write(f"Filtering countries: {countries}")

        # 1) Import country list
        ci_url = GEONAMES_BASE + "/countryInfo.txt"
        r = requests.get(ci_url, timeout=30)
        for line in r.text.splitlines():
            if line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 5:
                continue
            code = parts[0]
            name = parts[4]
            if countries and code not in countries:
                continue
            Country.objects.update_or_create(code=code, defaults={"name": name})

        # 2) Download allCountries.zip
        zip_url = GEONAMES_BASE + "/allCountries.zip"
        local_zip = os.path.join(settings.BASE_DIR, "allCountries.zip")

        if not os.path.exists(local_zip):
            self.stdout.write("Downloading GeoNames allCountries.zip (may be large)...")
            r = requests.get(zip_url, stream=True, timeout=60)
            with open(local_zip, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024*1024):
                    if chunk:
                        f.write(chunk)

        # 3) Extract & import cities
        self.stdout.write("Extracting and importing cities (streaming)...")
        created = 0
        with zipfile.ZipFile(local_zip) as zf:
            with zf.open("allCountries.txt") as fh:
                reader = TextIOWrapper(fh, encoding="utf-8")
                batch = []
                for i, line in enumerate(reader):
                    parts = line.strip().split("\t")
                    if len(parts) < 15:
                        continue
                    name = parts[1]
                    country_code = parts[8]
                    admin1 = parts[10]
                    try:
                        population = int(parts[14])
                    except:
                        population = 0

                    if countries and country_code not in countries:
                        continue
                    if population < min_pop:
                        continue

                    try:
                        country = Country.objects.get(code=country_code)
                    except Country.DoesNotExist:
                        continue

                    region, _ = Region.objects.get_or_create(country=country, code=admin1, defaults={"name": admin1 or ""})
                    batch.append(City(country=country, region=region, name=name,
                                      population=population,
                                      latitude=float(parts[4]) if parts[4] else None,
                                      longitude=float(parts[5]) if parts[5] else None))

                    if len(batch) >= 1000:
                        City.objects.bulk_create(batch, ignore_conflicts=True)
                        created += len(batch)
                        batch = []
                        self.stdout.write(f"Imported {created} cities so far...")
                        if limit and created >= limit:
                            break

                if batch:
                    City.objects.bulk_create(batch, ignore_conflicts=True)
                    created += len(batch)

        self.stdout.write(self.style.SUCCESS(f"Import completed: {created} cities"))
