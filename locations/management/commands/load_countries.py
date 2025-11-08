import csv
import os
from django.core.management.base import BaseCommand
from locations.models import Country

# 🚚 DHL supported countries (ISO2 codes)
DHL_COUNTRIES = [
    "US", "GB", "DE", "FR", "NG", "ZA", "IN", "CN", "JP", "BR", "CA", "AU"
]

class Command(BaseCommand):
    help = "Load DHL supported countries from worldcities.csv"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default="locations/data/worldcities.csv",  # ✅ your file path
            help="Path to worldcities.csv",
        )

    def handle(self, *args, **options):
        file_path = options["file"]
        if not os.path.exists(file_path):
            self.stderr.write(self.style.ERROR(f"File not found: {file_path}"))
            return

        with open(file_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            seen = set()
            for row in reader:
                iso2 = row.get("iso2", "").strip()
                if not iso2 or iso2 not in DHL_COUNTRIES:
                    continue

                if iso2 in seen:
                    continue  # avoid duplicates
                seen.add(iso2)

                Country.objects.get_or_create(
                    iso2=iso2,
                    defaults={
                        "name": row.get("country", "").strip(),
                        "iso3": row.get("iso3", "").strip(),
                    },
                )
                self.stdout.write(self.style.SUCCESS(f"Added {iso2}"))

        self.stdout.write(self.style.SUCCESS("✅ Countries loaded successfully!"))
