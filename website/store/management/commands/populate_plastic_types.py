from django.core.management.base import BaseCommand
from store.models import PlasticType


class Command(BaseCommand):
    help = 'Populate initial plastic types (PLA and PETG)'

    def handle(self, *args, **options):
        plastic_types_data = [
            {
                'name': 'PLA',
                'description': 'Polylactic Acid - biodegradable thermoplastic',
                'points_per_kg_basic': 100,
                'points_per_kg_premium': 120
            },
            {
                'name': 'PETG',
                'description': 'Polyethylene Terephthalate Glycol - durable and recyclable',
                'points_per_kg_basic': 100,
                'points_per_kg_premium': 120
            },
        ]

        for data in plastic_types_data:
            plastic_type, created = PlasticType.objects.get_or_create(
                name=data['name'],
                defaults={
                    'description': data['description'],
                    'points_per_kg_basic': data['points_per_kg_basic'],
                    'points_per_kg_premium': data['points_per_kg_premium']
                }
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created plastic type: {plastic_type.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'→ Plastic type already exists: {plastic_type.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'\nTotal plastic types in database: {PlasticType.objects.count()}')
        )
