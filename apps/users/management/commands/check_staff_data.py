from django.core.management.base import BaseCommand
from apps.users.models import BranchStaff, PositionStaff, GTFStaff


class Command(BaseCommand):
    help = 'Check existing staff data'

    def handle(self, *args, **options):
        self.stdout.write('=== Checking Staff Data ===\n')
        
        # Check GTFStaff
        gtf_count = GTFStaff.objects.count()
        self.stdout.write(f'GTFStaff: {gtf_count} entries')
        if gtf_count > 0:
            for gtf in GTFStaff.objects.all()[:10]:  # Show first 10
                self.stdout.write(f'  ID {gtf.id}: {gtf.name_uz}')
            if gtf_count > 10:
                self.stdout.write(f'  ... and {gtf_count - 10} more')
        else:
            self.stdout.write('  No GTFStaff entries found!')
        
        # Check BranchStaff
        branch_count = BranchStaff.objects.count()
        self.stdout.write(f'\nBranchStaff: {branch_count} entries')
        if branch_count > 0:
            for branch in BranchStaff.objects.all()[:10]:  # Show first 10
                self.stdout.write(f'  ID {branch.id}: {branch.name_uz}')
            if branch_count > 10:
                self.stdout.write(f'  ... and {branch_count - 10} more')
        else:
            self.stdout.write('  No BranchStaff entries found!')
        
        # Check PositionStaff
        position_count = PositionStaff.objects.count()
        self.stdout.write(f'\nPositionStaff: {position_count} entries')
        if position_count > 0:
            for pos in PositionStaff.objects.all()[:10]:  # Show first 10
                branch_name = pos.branch.name_uz if pos.branch else 'No branch'
                self.stdout.write(f'  ID {pos.id}: {pos.name_uz} (Branch: {branch_name}, Work Domain: {pos.work_domain})')
            if position_count > 10:
                self.stdout.write(f'  ... and {position_count - 10} more')
        else:
            self.stdout.write('  No PositionStaff entries found!')
        
        # Summary
        self.stdout.write(f'\n=== Summary ===')
        self.stdout.write(f'Total GTFStaff: {gtf_count}')
        self.stdout.write(f'Total BranchStaff: {branch_count}')
        self.stdout.write(f'Total PositionStaff: {position_count}')
        
        if gtf_count == 0:
            self.stdout.write(
                self.style.WARNING('\n⚠️  No GTFStaff entries found! Run: python manage.py create_test_staff')
            )
        
        if branch_count == 0:
            self.stdout.write(
                self.style.WARNING('\n⚠️  No BranchStaff entries found! Run: python manage.py create_test_staff')
            )
        
        if position_count == 0:
            self.stdout.write(
                self.style.WARNING('\n⚠️  No PositionStaff entries found! Run: python manage.py create_test_staff')
            )
