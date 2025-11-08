import os
import csv
from django.core.management.base import BaseCommand
from django.conf import settings
from locations.models import Country, Region, City
from django.db import transaction

class Command(BaseCommand):
    help = "Import cities from SimpleMaps world-cities CSV into City table (with Region support)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--min-pop", type=int, default=10000,
            help="Minimum population to import a city (default 10000). Use 0 to import all."
        )
        parser.add_argument(
            "--limit", type=int, default=0,
            help="Limit number of cities imported (0 = no limit)."
        )

    def handle(self, *args, **options):
        min_pop = options["min_pop"]
        limit = options["limit"]

        csv_path = os.path.join(settings.BASE_DIR, "locations", "data", "worldcities.csv")
        if not os.path.exists(csv_path):
            self.stderr.write(self.style.ERROR(f"CSV file not found: {csv_path}"))
            return

        count = 0
        batch = []
        batch_size = 1000
        region_cache = {}  # cache: {(country_id, region_name): Region}

        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    pop = int(row.get("population") or 0)
                except ValueError:
                    pop = 0

                if pop < min_pop:
                    continue

                iso2 = row.get("iso2", "").strip()
                if not iso2:
                    continue

                try:
                    country = Country.objects.get(iso2__iexact=iso2)
                except Country.DoesNotExist:
                    continue  # skip if country missing

                name = row.get("city").strip()
                admin = row.get("admin_name", "").strip()
                lat = row.get("lat")
                lng = row.get("lng")

                # ✅ handle Region (admin_name)
                region = None
                if admin:
                    key = (country.id, admin.lower())
                    if key in region_cache:
                        region = region_cache[key]
                    else:
                        region, _ = Region.objects.get_or_create(
                            country=country,
                            name=admin
                        )
                        region_cache[key] = region

                city = City(
                    name=name,
                    country=country,
                    region=region,
                    latitude=float(lat) if lat else None,
                    longitude=float(lng) if lng else None,
                    population=pop
                )
                batch.append(city)

                if len(batch) >= batch_size:
                    City.objects.bulk_create(batch, ignore_conflicts=True)
                    count += len(batch)
                    batch = []
                    self.stdout.write(f"Imported {count} cities so far...")
                    if limit and count >= limit:
                        break

                if limit and count >= limit:
                    break

            # final batch
            if batch and (not limit or count < limit):
                City.objects.bulk_create(batch, ignore_conflicts=True)
                count += len(batch)

        self.stdout.write(self.style.SUCCESS(f"✅ Finished importing cities. Total: {count}"))
