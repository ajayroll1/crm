"""
Management command to export all employees' email, password, and phone from database
"""
import csv
from django.core.management.base import BaseCommand
from myapp.models import Employee


class Command(BaseCommand):
    help = 'Export all employees email, password, and phone number to console or CSV file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv',
            type=str,
            help='Export to CSV file (provide filename, e.g., employees.csv)',
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['table', 'list', 'csv'],
            default='table',
            help='Output format: table (default), list, or csv',
        )

    def handle(self, *args, **options):
        # Get all employees
        employees = Employee.objects.all().order_by('email')
        total_count = employees.count()
        
        if total_count == 0:
            self.stdout.write(self.style.WARNING('No employees found in the database.'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'\nFound {total_count} employees in the database.\n'))
        
        # If CSV file is specified
        if options['csv']:
            filename = options['csv']
            self.export_to_csv(employees, filename)
            self.stdout.write(self.style.SUCCESS(f'\nData exported to {filename}'))
            return
        
        # Console output based on format
        if options['format'] == 'csv':
            self.print_csv_format(employees)
        elif options['format'] == 'list':
            self.print_list_format(employees)
        else:  # table format
            self.print_table_format(employees)
    
    def export_to_csv(self, employees, filename):
        """Export data to CSV file"""
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['ID', 'Name', 'Email', 'Phone', 'Password (Hashed)', 'Password Set', 'Status', 'Role']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for emp in employees:
                password_set = 'Yes' if (emp.password and emp.password.strip()) else 'No'
                writer.writerow({
                    'ID': emp.id,
                    'Name': emp.get_full_name(),
                    'Email': emp.email or '',
                    'Phone': emp.phone or '',
                    'Password (Hashed)': emp.password or '',
                    'Password Set': password_set,
                    'Status': emp.status or '',
                    'Role': emp.role or '',
                })
    
    def print_csv_format(self, employees):
        """Print in CSV format to console"""
        # Print header
        print('ID,Name,Email,Phone,Password (Hashed),Password Set,Status,Role')
        
        for emp in employees:
            password_set = 'Yes' if (emp.password and emp.password.strip()) else 'No'
            name = emp.get_full_name().replace(',', ' ')
            email = (emp.email or '').replace(',', ' ')
            phone = (emp.phone or '').replace(',', ' ')
            password = (emp.password or '').replace(',', ' ')
            print(f'{emp.id},{name},{email},{phone},{password},{password_set},{emp.status or ""},{emp.role or ""}')
    
    def print_list_format(self, employees):
        """Print in list format"""
        for idx, emp in enumerate(employees, 1):
            password_set = 'Yes' if (emp.password and emp.password.strip()) else 'No'
            self.stdout.write(f'\n{idx}. {emp.get_full_name()} (ID: {emp.id})')
            self.stdout.write(f'   Email: {emp.email or "N/A"}')
            self.stdout.write(f'   Phone: {emp.phone or "N/A"}')
            self.stdout.write(f'   Password Set: {password_set}')
            if emp.password:
                self.stdout.write(f'   Password (Hashed): {emp.password}')
            self.stdout.write(f'   Status: {emp.status or "N/A"}')
            self.stdout.write(f'   Role: {emp.role or "N/A"}')
    
    def print_table_format(self, employees):
        """Print in table format"""
        # Calculate column widths
        max_id_len = max(len(str(emp.id)) for emp in employees) if employees else 2
        max_name_len = max(len(emp.get_full_name()) for emp in employees) if employees else 4
        max_email_len = max(len(emp.email or '') for emp in employees) if employees else 5
        max_phone_len = max(len(emp.phone or '') for emp in employees) if employees else 5
        max_password_len = 20  # Limit password display
        
        # Ensure minimum widths
        max_id_len = max(max_id_len, 2)
        max_name_len = max(max_name_len, 4, 20)
        max_email_len = max(max_email_len, 5, 30)
        max_phone_len = max(max_phone_len, 5, 15)
        
        # Print header
        header = (
            f"{'ID':<{max_id_len}} | "
            f"{'Name':<{max_name_len}} | "
            f"{'Email':<{max_email_len}} | "
            f"{'Phone':<{max_phone_len}} | "
            f"{'Password Set':<12} | "
            f"{'Status':<10} | "
            f"{'Role':<10}"
        )
        self.stdout.write(header)
        self.stdout.write('-' * len(header))
        
        # Print data
        for emp in employees:
            password_set = 'Yes' if (emp.password and emp.password.strip()) else 'No'
            password_display = (emp.password[:max_password_len] + '...') if emp.password and len(emp.password) > max_password_len else (emp.password or 'N/A')
            
            row = (
                f"{str(emp.id):<{max_id_len}} | "
                f"{emp.get_full_name():<{max_name_len}} | "
                f"{(emp.email or 'N/A'):<{max_email_len}} | "
                f"{(emp.phone or 'N/A'):<{max_phone_len}} | "
                f"{password_set:<12} | "
                f"{(emp.status or 'N/A'):<10} | "
                f"{(emp.role or 'N/A'):<10}"
            )
            self.stdout.write(row)
            
            # Print password hash on next line if set
            if emp.password:
                password_row = (
                    f"{'':<{max_id_len}} | "
                    f"{'Password:':<{max_name_len}} | "
                    f"{password_display:<{max_email_len}} | "
                    f"{'':<{max_phone_len}} | "
                    f"{'':<12} | "
                    f"{'':<10} | "
                    f"{'':<10}"
                )
                self.stdout.write(self.style.WARNING(password_row))
        
        self.stdout.write('')

