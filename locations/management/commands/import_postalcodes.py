# locations/management/commands/import_postalcodes.py
import os
import zipfile
import requests
from io import TextIOWrapper
from django.core.management.base import BaseCommand
from django.conf import settings
from locations.models import Country, City, PostalCode

GEONAMES_POSTAL_BASE = "https://download.geonames.org/export/zip"

class Command(BaseCommand):
    help = "Import GeoNames postal codes for specified countries: --countries=US,NG"

    def add_arguments(self, parser):
        parser.add_argument("--countries", type=str, help="Comma-separated ISO country codes (e.g. US,NG).")

    def handle(self, *args, **options):
        countries_arg = options.get("countries")
        if not countries_arg:
            self.stdout.write(self.style.ERROR("Please pass --countries=US,NG"))
            return
        countries = [c.strip().upper() for c in countries_arg.split(",")]

        for cc in countries:
            zip_url = f"{GEONAMES_POSTAL_BASE}/{cc}.zip"
            local_zip = os.path.join(settings.BASE_DIR, f"{cc}.zip")
            self.stdout.write(f"Downloading postal codes for {cc}...")
            r = requests.get(zip_url, stream=True, timeout=30)
            if r.status_code != 200:
                self.stdout.write(self.style.WARNING(f"No postal file for {cc} (status {r.status_code})"))
                continue
            with open(local_zip, "wb") as f:
                for chunk in r.iter_content(1024*1024):
                    if chunk:
                        f.write(chunk)
            with zipfile.ZipFile(local_zip) as zf:
                # postal file is like US.txt
                filename = f"{cc}.txt"
                if filename not in zf.namelist():
                    # sometimes files have different naming; search first entry
                    filename = zf.namelist()[0]
                with zf.open(filename) as fh:
                    reader = TextIOWrapper(fh, encoding="utf-8")
                    created = 0
                    for line in reader:
                        parts = line.strip().split("\t")
                        if len(parts) < 3:
                            continue
                        # format: country_code, postal_code, place_name, admin_name1, admin_code1, admin_name2, admin_code2, lat, lon
                        country_code = parts[0]
                        postal = parts[1]
                        place_name = parts[2]

                        try:
                            country = Country.objects.get(code=country_code)
                        except Country.DoesNotExist:
                            continue

                        # match by place_name (exact)
                        city = City.objects.filter(country=country, name__iexact=place_name).first()
                        PostalCode.objects.update_or_create(country=country, code=postal, defaults={"city": city})
                        created += 1
                    self.stdout.write(self.style.SUCCESS(f"Imported {created} postal codes for {cc}"))
