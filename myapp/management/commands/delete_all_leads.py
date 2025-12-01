"""
Management command to delete all leads from the database
"""
from django.core.management.base import BaseCommand
from myapp.models import Lead


class Command(BaseCommand):
    help = 'Delete all leads from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force deletion without confirmation',
        )

    def handle(self, *args, **options):
        # Get count of all leads
        total_leads = Lead.objects.count()
        
        if total_leads == 0:
            self.stdout.write(self.style.WARNING('No leads found in the database.'))
            return
        
        self.stdout.write(f'Found {total_leads} leads in the database.')
        
        # Ask for confirmation unless --force flag is used
        if not options['force']:
            confirm = input(f'Are you sure you want to delete all {total_leads} leads? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.WARNING('Deletion cancelled.'))
                return
        
        # Delete all leads
        deleted_count = Lead.objects.all().delete()[0]
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Successfully deleted {deleted_count} leads from the database.'))

