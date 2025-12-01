"""
Management command to add test data for all new services
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from myapp.models import (
    ProfessionalTaxRegistration,
    IECRegistration,
    ICEGateRegistration,
    TradeLicenseRegistration,
    DSCRegistration,
    CompanyNameChange,
    DirectorChange,
    CompanyClosure,
    RCMCRegistration,
    ShopEstablishmentRegistration,
)


class Command(BaseCommand):
    help = 'Add test data for all new services (Professional Tax, IEC, ICE Gate, Trade License, DSC, Company Name Change, Director Change, Company Closure, RCMC, Shop Establishment)'

    def handle(self, *args, **options):
        self.stdout.write('Adding test data for all new services...')
        self.stdout.write('')
        
        # 1. Professional Tax Registration
        try:
            professional_tax = ProfessionalTaxRegistration.objects.create(
                applicant_name='Rajesh Kumar',
                applicant_phone='9876543210',
                applicant_whatsapp='9876543210',
                applicant_email='rajesh.kumar@example.com',
                applicant_address='123, MG Road, Bangalore, Karnataka - 560001',
                business_name='Rajesh Enterprises',
                business_type='Proprietorship',
                pan_number='ABCDE1234F',
                gst_number='29ABCDE1234F1Z5',
                business_address='123, MG Road, Bangalore, Karnataka - 560001',
                bank_account_details='HDFC Bank, Account: 1234567890, IFSC: HDFC0001234',
                number_of_employees=15,
                business_start_date=date(2020, 1, 15),
                monthly_salary_details='Total monthly salary: ₹2,50,000',
                status='pending',
            )
            self.stdout.write(self.style.SUCCESS('✓ Professional Tax Registration test data added'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Professional Tax Registration: {str(e)}'))
        
        # 2. IEC Registration
        try:
            iec = IECRegistration.objects.create(
                applicant_name='Priya Sharma',
                applicant_phone='9876543211',
                applicant_whatsapp='9876543211',
                applicant_email='priya.sharma@example.com',
                applicant_address='456, Commercial Street, Mumbai, Maharashtra - 400001',
                firm_name='Sharma Exports Pvt Ltd',
                pan_number='BCDEF2345G',
                business_type='Company',
                incorporation_date=date(2019, 5, 20),
                bank_account_details='ICICI Bank, Account: 2345678901, IFSC: ICIC0002345',
                directors_partners_details='Priya Sharma - Director, Ramesh Sharma - Director',
                branch_offices='Mumbai (Head Office), Delhi (Branch)',
                status='pending',
            )
            self.stdout.write(self.style.SUCCESS('✓ IEC Registration test data added'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ IEC Registration: {str(e)}'))
        
        # 3. ICE Gate Registration
        try:
            icegate = ICEGateRegistration.objects.create(
                applicant_name='Amit Patel',
                applicant_phone='9876543212',
                applicant_whatsapp='9876543212',
                applicant_email='amit.patel@example.com',
                applicant_address='789, Industrial Area, Surat, Gujarat - 395001',
                company_name='Patel Shipping Services',
                pan_number='CDEFG3456H',
                iec_number='1234567890',
                user_role='Shipping Agent',
                authorized_person_name='Amit Patel',
                authorized_person_details='Director and Authorized Signatory',
                status='pending',
            )
            self.stdout.write(self.style.SUCCESS('✓ ICE Gate Registration test data added'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ ICE Gate Registration: {str(e)}'))
        
        # 4. Trade License Registration
        try:
            trade_license = TradeLicenseRegistration.objects.create(
                applicant_name='Sunita Devi',
                applicant_phone='9876543213',
                applicant_whatsapp='9876543213',
                applicant_email='sunita.devi@example.com',
                applicant_address='321, Market Street, Kolkata, West Bengal - 700001',
                business_name='Sunita General Store',
                business_type='Proprietorship',
                business_address='321, Market Street, Kolkata, West Bengal - 700001',
                pan_number='DEFGH4567I',
                gst_number='19DEFGH4567I2Z6',
                number_of_employees=5,
                business_start_date=date(2021, 3, 10),
                municipal_area='Kolkata Municipal Corporation',
                required_permissions='Food License, Fire Safety Certificate',
                status='pending',
            )
            self.stdout.write(self.style.SUCCESS('✓ Trade License Registration test data added'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Trade License Registration: {str(e)}'))
        
        # 5. DSC Registration
        try:
            dsc = DSCRegistration.objects.create(
                applicant_name='Vikram Singh',
                applicant_phone='9876543214',
                applicant_whatsapp='9876543214',
                applicant_email='vikram.singh@example.com',
                applicant_address='654, Business Park, Noida, Uttar Pradesh - 201301',
                pan_number='EFGHI5678J',
                aadhaar_number='123456789012',
                organisation_name='Singh Technologies Pvt Ltd',
                organisation_type='Private Limited',
                organisation_address='654, Business Park, Noida, Uttar Pradesh - 201301',
                dsc_type='Class 3',
                status='pending',
            )
            self.stdout.write(self.style.SUCCESS('✓ DSC Registration test data added'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ DSC Registration: {str(e)}'))
        
        # 6. Company Name Change
        try:
            company_name_change = CompanyNameChange.objects.create(
                applicant_name='Anjali Mehta',
                applicant_phone='9876543215',
                applicant_whatsapp='9876543215',
                applicant_email='anjali.mehta@example.com',
                applicant_address='987, Corporate Tower, Pune, Maharashtra - 411001',
                current_company_name='Mehta Trading Company Pvt Ltd',
                cin_number='U12345MH2018PTC123456',
                proposed_new_name='Mehta Global Trading Pvt Ltd',
                reason_for_change='Rebranding and expansion to international markets',
                board_meeting_date=date(2024, 12, 15),
                registered_office_address='987, Corporate Tower, Pune, Maharashtra - 411001',
                directors_details='Anjali Mehta - Managing Director, Ravi Mehta - Director',
                shareholders_details='Anjali Mehta - 60%, Ravi Mehta - 40%',
                status='pending',
            )
            self.stdout.write(self.style.SUCCESS('✓ Company Name Change test data added'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Company Name Change: {str(e)}'))
        
        # 7. Director Change
        try:
            director_change = DirectorChange.objects.create(
                applicant_name='Kiran Reddy',
                applicant_phone='9876543216',
                applicant_whatsapp='9876543216',
                applicant_email='kiran.reddy@example.com',
                applicant_address='147, Tech Park, Hyderabad, Telangana - 500001',
                company_name='Reddy Software Solutions Pvt Ltd',
                cin_number='U67890TS2020PTC234567',
                change_type='Appointment',
                new_director_name='Suresh Reddy',
                new_director_din='01234567',
                new_director_pan='FGHIJ6789K',
                new_director_aadhaar='234567890123',
                new_director_address='258, IT Hub, Hyderabad, Telangana - 500002',
                new_director_email='suresh.reddy@example.com',
                new_director_mobile='9876543217',
                appointment_date=date(2024, 11, 1),
                existing_directors_details='Kiran Reddy - Managing Director, Priya Reddy - Director',
                status='pending',
            )
            self.stdout.write(self.style.SUCCESS('✓ Director Change test data added'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Director Change: {str(e)}'))
        
        # 8. Company Closure
        try:
            company_closure = CompanyClosure.objects.create(
                applicant_name='Rohit Verma',
                applicant_phone='9876543218',
                applicant_whatsapp='9876543218',
                applicant_email='rohit.verma@example.com',
                applicant_address='369, Business Center, Delhi - 110001',
                company_name='Verma Manufacturing Pvt Ltd',
                cin_number='U11111DL2015PTC345678',
                closure_type='Voluntary Winding Up',
                reason_for_closure='Business no longer viable, all operations ceased',
                registered_office_address='369, Business Center, Delhi - 110001',
                directors_details='Rohit Verma - Managing Director',
                shareholders_details='Rohit Verma - 100%',
                liabilities_details='Bank loan: ₹5,00,000, Creditors: ₹2,00,000',
                assets_details='Plant & Machinery: ₹10,00,000, Inventory: ₹3,00,000',
                board_meeting_date=date(2024, 10, 20),
                status='pending',
            )
            self.stdout.write(self.style.SUCCESS('✓ Company Closure test data added'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Company Closure: {str(e)}'))
        
        # 9. RCMC Registration
        try:
            rcmc = RCMCRegistration.objects.create(
                applicant_name='Neha Agarwal',
                applicant_phone='9876543219',
                applicant_whatsapp='9876543219',
                applicant_email='neha.agarwal@example.com',
                applicant_address='741, Export Zone, Chennai, Tamil Nadu - 600001',
                firm_name='Agarwal Exports International',
                iec_number='2345678901',
                pan_number='GHIJK7890L',
                registered_office_address='741, Export Zone, Chennai, Tamil Nadu - 600001',
                export_products_details='Textiles, Garments, Handicrafts',
                export_performance_details='FY 2023-24: ₹50,00,000, FY 2022-23: ₹35,00,000',
                related_export_council_name='Export Promotion Council for Handicrafts',
                status='pending',
            )
            self.stdout.write(self.style.SUCCESS('✓ RCMC Registration test data added'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ RCMC Registration: {str(e)}'))
        
        # 10. Shop Establishment Registration
        try:
            shop_establishment = ShopEstablishmentRegistration.objects.create(
                applicant_name='Manoj Kumar',
                applicant_phone='9876543220',
                applicant_whatsapp='9876543220',
                applicant_email='manoj.kumar@example.com',
                applicant_address='852, Main Road, Ranchi, Jharkhand - 834001',
                shop_establishment_name='Manoj Electronics & Appliances',
                state='Jharkhand',
                business_type='Proprietorship',
                business_address='852, Main Road, Ranchi, Jharkhand - 834001',
                pan_number='HIJKL8901M',
                gst_number='20HIJKL8901M3Z7',
                number_of_employees=8,
                business_start_date=date(2022, 6, 1),
                working_hours='9:00 AM - 8:00 PM',
                weekly_holiday='Sunday',
                municipal_area='Ranchi Municipal Corporation',
                status='pending',
            )
            self.stdout.write(self.style.SUCCESS('✓ Shop Establishment Registration test data added'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Shop Establishment Registration: {str(e)}'))
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Test data addition completed!'))

