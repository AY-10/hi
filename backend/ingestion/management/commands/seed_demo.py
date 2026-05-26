from django.core.management.base import BaseCommand

from ingestion.services import seed_demo_data


class Command(BaseCommand):
    help = 'Seed the demo organization and review dataset.'

    def handle(self, *args, **options):
        organization = seed_demo_data()
        self.stdout.write(self.style.SUCCESS(
            f'Seeded demo data for {organization.name}'))
