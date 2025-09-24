from django.core.management.base import BaseCommand, CommandError
from apps.users.models import PositionStaff, BranchStaff
import csv


class Command(BaseCommand):
    help = "Import positions from CSV file."

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Path to CSV file')
        parser.add_argument('--delimiter', type=str, default=',', help='CSV delimiter (default ,)')

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        delimiter = options['delimiter']

        created = 0
        updated = 0

        try:
            with open(csv_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile, delimiter=delimiter)

                # Required fields
                required = ['name_uz']
                for field in required:
                    if field not in reader.fieldnames:
                        raise CommandError(f"Missing required column: {field}")

                for row in reader:
                    name_uz = row.get('name_uz')
                    name_uz_cyrl = row.get('name_uz_cyrl', '')
                    name_ru = row.get('name_ru', '')
                    branch_name_uz = row.get('branch_name_uz')

                    if not name_uz:
                        self.stdout.write(self.style.WARNING(f"Skip row with missing name_uz: {row}"))
                        continue

                    # Find branch if specified
                    branch = None
                    if branch_name_uz:
                        branch = BranchStaff.objects.filter(name_uz=branch_name_uz).first()
                        if not branch:
                            self.stdout.write(self.style.WARNING(f"Branch not found: {branch_name_uz}"))
                    work_domain = row.get('work_domain')
                    position, is_created = PositionStaff.objects.get_or_create(
                        name_uz=name_uz,
                        defaults={
                            'name_uz_cyrl': name_uz_cyrl,
                            'name_ru': name_ru,
                            'branch': branch,
                            'work_domain': work_domain
                        }
                    )

                    if is_created:
                        created += 1
                        self.stdout.write(self.style.SUCCESS(f"Created position: {position.name_uz}"))
                    else:
                        # Update existing position
                        position.name_uz_cyrl = name_uz_cyrl
                        position.name_ru = name_ru
                        position.branch = branch
                        position.save()
                        updated += 1
                        self.stdout.write(self.style.SUCCESS(f"Updated position: {position.name_uz}"))

        except FileNotFoundError:
            raise CommandError(f"CSV file not found: {csv_path}")
        except Exception as e:
            raise CommandError(f"Error processing CSV: {str(e)}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Import completed. Created: {created}, Updated: {updated}"
            )
        )
