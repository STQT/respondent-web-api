import random
from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _
from apps.users.models import BranchStaff, PositionStaff, GTFStaff


class Command(BaseCommand):
    help = 'Create test staff data (branches, positions, GTF)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=5,
            help='Number of GTF entries to create (default: 5)'
        )

    def handle(self, *args, **options):
        count = options['count']
        
        # Create test branches
        branches_data = [
            {'name_uz': 'Главный офис', 'name_uz_cyrl': 'Главный офис', 'name_ru': 'Главный офис'},
            {'name_uz': 'Ташкентский филиал', 'name_uz_cyrl': 'Ташкентский филиал', 'name_ru': 'Ташкентский филиал'},
            {'name_uz': 'Самаркандский филиал', 'name_uz_cyrl': 'Самаркандский филиал', 'name_ru': 'Самаркандский филиал'},
            {'name_uz': 'Бухарский филиал', 'name_uz_cyrl': 'Бухарский филиал', 'name_ru': 'Бухарский филиал'},
            {'name_uz': 'Андижанский филиал', 'name_uz_cyrl': 'Андижанский филиал', 'name_ru': 'Андижанский филиал'},
        ]
        
        branches = []
        for branch_data in branches_data:
            branch, created = BranchStaff.objects.get_or_create(
                name_uz=branch_data['name_uz'],
                defaults=branch_data
            )
            branches.append(branch)
            if created:
                self.stdout.write(f'Created branch: {branch.name_uz}')
        
        # Create test GTF
        gtf_data = [
            {'name_uz': 'ГТФ-1', 'name_uz_cyrl': 'ГТФ-1', 'name_ru': 'ГТФ-1'},
            {'name_uz': 'ГТФ-2', 'name_uz_cyrl': 'ГТФ-2', 'name_ru': 'ГТФ-2'},
            {'name_uz': 'ГТФ-3', 'name_uz_cyrl': 'ГТФ-3', 'name_ru': 'ГТФ-3'},
            {'name_uz': 'ГТФ-4', 'name_uz_cyrl': 'ГТФ-4', 'name_ru': 'ГТФ-4'},
            {'name_uz': 'ГТФ-5', 'name_uz_cyrl': 'ГТФ-5', 'name_ru': 'ГТФ-5'},
        ]
        
        gtf_list = []
        for gtf_item in gtf_data:
            gtf, created = GTFStaff.objects.get_or_create(
                name_uz=gtf_item['name_uz'],
                defaults=gtf_item
            )
            gtf_list.append(gtf)
            if created:
                self.stdout.write(f'Created GTF: {gtf.name_uz}')
        
        # Create test positions
        positions_data = [
            {'name_uz': 'Инженер', 'name_uz_cyrl': 'Инженер', 'name_ru': 'Инженер', 'work_domain': 'natural_gas'},
            {'name_uz': 'Старший инженер', 'name_uz_cyrl': 'Старший инженер', 'name_ru': 'Старший инженер', 'work_domain': 'natural_gas'},
            {'name_uz': 'Техник', 'name_uz_cyrl': 'Техник', 'name_ru': 'Техник', 'work_domain': 'lpg_gas'},
            {'name_uz': 'Оператор', 'name_uz_cyrl': 'Оператор', 'name_ru': 'Оператор', 'work_domain': 'both'},
            {'name_uz': 'Менеджер', 'name_uz_cyrl': 'Менеджер', 'name_ru': 'Менеджер', 'work_domain': 'natural_gas'},
            {'name_uz': 'Специалист по безопасности', 'name_uz_cyrl': 'Специалист по безопасности', 'name_ru': 'Специалист по безопасности', 'work_domain': 'both'},
        ]
        
        positions = []
        for pos_data in positions_data:
            position, created = PositionStaff.objects.get_or_create(
                name_uz=pos_data['name_uz'],
                defaults={
                    **pos_data,
                    'branch': random.choice(branches)
                }
            )
            positions.append(position)
            if created:
                self.stdout.write(f'Created position: {position.name_uz} (Branch: {position.branch.name_uz})')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Test staff data created successfully!\n'
                f'Branches: {len(branches)}\n'
                f'GTF: {len(gtf_list)}\n'
                f'Positions: {len(positions)}'
            )
        )
        
        # Show available IDs for testing
        self.stdout.write('\n=== Available IDs for testing ===')
        self.stdout.write('GTF IDs:')
        for gtf in gtf_list:
            self.stdout.write(f'  ID {gtf.id}: {gtf.name_uz}')
        
        self.stdout.write('\nPosition IDs:')
        for pos in positions:
            self.stdout.write(f'  ID {pos.id}: {pos.name_uz} (Branch: {pos.branch.name_uz})')
        
        self.stdout.write('\nBranch IDs:')
        for branch in branches:
            self.stdout.write(f'  ID {branch.id}: {branch.name_uz}')
