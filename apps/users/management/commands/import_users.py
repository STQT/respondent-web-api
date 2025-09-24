from django.core.management.base import BaseCommand, CommandError
from apps.users.models import User, BranchStaff, PositionStaff, GTFStaff
import csv


class Command(BaseCommand):
    help = "Import users from CSV file."

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

                # Required minimal fields
                required = ['phone_number', 'password', 'branch_name_uz', 'position_name_uz', 'gtf_name_uz']
                for field in required:
                    if field not in reader.fieldnames:
                        raise CommandError(f"Missing required column: {field}")

                for row in reader:
                    phone_number = row.get('phone_number')
                    password = row.get('password')
                    # name is optional now
                    name = row.get('name', '')
                    work_domain = row.get('work_domain')

                    # Branch multilingual
                    branch_name_uz = row.get('branch_name_uz')
                    branch_name_uz_cyrl = row.get('branch_name_uz_cyrl')
                    branch_name_ru = row.get('branch_name_ru')

                    # Position multilingual
                    position_name_uz = row.get('position_name_uz')
                    position_name_uz_cyrl = row.get('position_name_uz_cyrl')
                    position_name_ru = row.get('position_name_ru')

                    # GTF multilingual
                    gtf_name_uz = row.get('gtf_name_uz')
                    gtf_name_uz_cyrl = row.get('gtf_name_uz_cyrl')
                    gtf_name_ru = row.get('gtf_name_ru')

                    if not phone_number or not password:
                        self.stdout.write(self.style.WARNING(f"Skip row with missing phone/password: {row}"))
                        continue

                    user, is_created = User.objects.get_or_create(
                        phone_number=phone_number,
                        defaults={'name': name}
                    )

                    # Resolve BranchStaff by any of names or create if multilingual provided
                    if branch_name_uz or branch_name_uz_cyrl or branch_name_ru:
                        branch = None
                        if not branch and branch_name_uz:
                            branch = BranchStaff.objects.filter(name_uz=branch_name_uz).first()
                        if not branch and branch_name_ru:
                            branch = BranchStaff.objects.filter(name_ru=branch_name_ru).first()
                        # Create new branch when multilingual provided
                        if not branch and (branch_name_uz or branch_name_uz_cyrl or branch_name_ru):
                            branch = BranchStaff.objects.create(
                                name_uz=branch_name_uz or '',
                                name_uz_cyrl=branch_name_uz_cyrl or '',
                                name_ru=branch_name_ru or ''
                            )
                        # Branch is now linked to position, not directly to user

                    # Resolve PositionStaff similarly
                    if position_name_uz or position_name_uz_cyrl or position_name_ru:
                        position = None
                        if not position and position_name_uz:
                            position = PositionStaff.objects.filter(name_uz=position_name_uz).first()
                        if not position and position_name_ru:
                            position = PositionStaff.objects.filter(name_ru=position_name_ru).first()
                        if not position and (position_name_uz or position_name_uz_cyrl or position_name_ru):
                            # Create position with branch reference
                            position = PositionStaff.objects.create(
                                name_uz=position_name_uz or '',
                                name_uz_cyrl=position_name_uz_cyrl or '',
                                name_ru=position_name_ru or '',
                                branch=branch  # Link to the branch we found/created above
                            )
                        if position:
                            user.position = position

                    # Resolve GTFStaff similarly
                    if gtf_name_uz or gtf_name_uz_cyrl or gtf_name_ru:
                        gtf = None
                        if not gtf and gtf_name_uz:
                            gtf = GTFStaff.objects.filter(name_uz=gtf_name_uz).first()
                        if not gtf and gtf_name_ru:
                            gtf = GTFStaff.objects.filter(name_ru=gtf_name_ru).first()
                        if not gtf and (gtf_name_uz or gtf_name_uz_cyrl or gtf_name_ru):
                            gtf = GTFStaff.objects.create(
                                name_uz=gtf_name_uz or '',
                                name_uz_cyrl=gtf_name_uz_cyrl or '',
                                name_ru=gtf_name_ru or ''
                            )
                        if gtf:
                            user.gtf = gtf

                    if work_domain:
                        user.work_domain = work_domain

                    if is_created:
                        user.set_password(password)
                        created += 1
                    else:
                        if password:
                            user.set_password(password)
                        user.name = name or user.name
                        updated += 1

                    user.save()

        except FileNotFoundError:
            raise CommandError(f"File not found: {csv_path}")

        self.stdout.write(self.style.SUCCESS(f"Import completed. Created: {created}, Updated: {updated}"))


