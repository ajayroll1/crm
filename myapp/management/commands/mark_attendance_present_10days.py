"""
Management command to mark last 10 days attendance as Present
with check-in time between 9:50 AM to 10:00 AM
and check-out time at 7:00 PM or later
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, datetime, time
import random
from myapp.models import Attendance, Employee


class Command(BaseCommand):
    help = 'Mark last 10 days attendance as Present with flexible check-in/check-out times'

    def handle(self, *args, **options):
        self.stdout.write('Starting to mark attendance as Present...')
        
        # Get all employees
        employees = Employee.objects.all()
        total_employees = employees.count()
        
        if total_employees == 0:
            self.stdout.write(self.style.WARNING('No employees found in the database.'))
            return
        
        self.stdout.write(f'Found {total_employees} employees')
        
        # Calculate dates - last 10 days excluding Sundays
        today = timezone.now().date()
        dates_to_update = []
        current_date = today - timedelta(days=1)  # Start from yesterday
        
        # Go back and collect 10 working days (excluding Sundays)
        while len(dates_to_update) < 10:
            # Check if it's not Sunday (weekday() returns 0 for Monday, 6 for Sunday)
            if current_date.weekday() != 6:  # 6 is Sunday
                dates_to_update.append(current_date)
            current_date -= timedelta(days=1)
        
        # Sort dates in ascending order (oldest first)
        dates_to_update.sort()
        
        self.stdout.write(f'Updating attendance for {len(dates_to_update)} days:')
        for date in dates_to_update:
            self.stdout.write(f'  - {date.strftime("%Y-%m-%d (%A)")}')
        
        total_updated = 0
        total_created = 0
        
        for employee in employees:
            employee_name = employee.get_full_name()
            
            for date in dates_to_update:
                # Get or create attendance record
                attendance, created = Attendance.objects.get_or_create(
                    employee=employee,
                    date=date,
                    defaults={
                        'employee_name': employee_name,
                    }
                )
                
                # Generate random check-in time between 9:50 AM to 10:00 AM
                # Random minutes between 50 to 60 (9:50 to 10:00)
                check_in_minute = random.randint(50, 60)
                if check_in_minute == 60:
                    check_in_hour = 10
                    check_in_minute = 0
                else:
                    check_in_hour = 9
                
                check_in_time_obj = time(check_in_hour, check_in_minute, 0)
                check_in_datetime = timezone.make_aware(
                    datetime.combine(date, check_in_time_obj)
                )
                
                # Generate random check-out time at 7:00 PM or later
                # Random hours between 7 PM to 8 PM (19:00 to 20:00)
                check_out_hour = random.randint(19, 20)
                check_out_minute = random.randint(0, 59)
                check_out_time_obj = time(check_out_hour, check_out_minute, 0)
                check_out_datetime = timezone.make_aware(
                    datetime.combine(date, check_out_time_obj)
                )
                
                # Update attendance record
                attendance.check_in_time = check_in_datetime
                attendance.check_out_time = check_out_datetime
                attendance.employee_name = employee_name
                attendance.save()
                
                if created:
                    total_created += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Created & Marked Present: {employee_name} - {date.strftime("%Y-%m-%d")} '
                            f'(Check-in: {check_in_time_obj.strftime("%H:%M")}, '
                            f'Check-out: {check_out_time_obj.strftime("%H:%M")})'
                        )
                    )
                else:
                    total_updated += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f'Updated & Marked Present: {employee_name} - {date.strftime("%Y-%m-%d")} '
                            f'(Check-in: {check_in_time_obj.strftime("%H:%M")}, '
                            f'Check-out: {check_out_time_obj.strftime("%H:%M")})'
                        )
                    )
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Attendance marking completed!'))
        self.stdout.write(f'Total employees processed: {total_employees}')
        self.stdout.write(f'Total days per employee: {len(dates_to_update)}')
        self.stdout.write(self.style.SUCCESS(f'Records created: {total_created}'))
        self.stdout.write(self.style.WARNING(f'Records updated: {total_updated}'))
        self.stdout.write('')
        self.stdout.write('Check-in times: 9:50 AM to 10:00 AM')
        self.stdout.write('Check-out times: 7:00 PM or later')

