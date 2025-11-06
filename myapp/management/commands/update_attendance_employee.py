"""
Management command to update existing attendance records with employee foreign key
"""
from django.core.management.base import BaseCommand
from myapp.models import Attendance, Employee


class Command(BaseCommand):
    help = 'Update existing attendance records to link them with employee foreign key'

    def handle(self, *args, **options):
        self.stdout.write('Starting to update attendance records...')
        
        # Get all attendance records without employee foreign key
        attendance_records = Attendance.objects.filter(employee__isnull=True)
        total_records = attendance_records.count()
        
        self.stdout.write(f'Found {total_records} attendance records without employee foreign key')
        
        updated_count = 0
        not_found_count = 0
        
        for attendance in attendance_records:
            # Try to find employee by matching employee_name
            employee_name = attendance.employee_name.strip()
            
            if not employee_name:
                self.stdout.write(self.style.WARNING(f'Attendance ID {attendance.id} has no employee_name'))
                not_found_count += 1
                continue
            
            # Split name into first and last name
            name_parts = employee_name.split(' ', 1)
            first_name = name_parts[0] if name_parts else ''
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            
            employee = None
            
            # Try to find by first_name and last_name
            if first_name and last_name:
                employee = Employee.objects.filter(
                    first_name__iexact=first_name,
                    last_name__iexact=last_name
                ).first()
            
            # If not found, try by full name match
            if not employee:
                # Try exact match with get_full_name()
                employees = Employee.objects.all()
                for emp in employees:
                    if emp.get_full_name().strip().lower() == employee_name.lower():
                        employee = emp
                        break
            
            # If still not found, try partial match
            if not employee:
                employees = Employee.objects.filter(
                    first_name__icontains=first_name
                )
                for emp in employees:
                    if emp.get_full_name().strip().lower() == employee_name.lower():
                        employee = emp
                        break
            
            if employee:
                attendance.employee = employee
                attendance.save()
                updated_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Updated attendance ID {attendance.id} ({attendance.employee_name}) -> Employee ID {employee.id} ({employee.get_full_name()})'
                    )
                )
            else:
                not_found_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'Could not find employee for attendance ID {attendance.id} with name: {employee_name}'
                    )
                )
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Update completed!'))
        self.stdout.write(f'Total records: {total_records}')
        self.stdout.write(self.style.SUCCESS(f'Updated: {updated_count}'))
        self.stdout.write(self.style.WARNING(f'Not found: {not_found_count}'))

