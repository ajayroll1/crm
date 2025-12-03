"""
Management command to add test data for all 14 new services
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
from myapp.models import (
    DINApplication,
    GSTRegistration,
    GSTFiling,
    CompanyComplianceROCLLP,
    AuthorizedPaidupCapitalIncrease,
    DINKYC,
    NGODarpan,
    ITRFiling,
    INC20ABusinessCommencement,
    GEMRegistration,
    StartupIndiaSeedFunding,
    CSR1NGO,
    Registration12A80G,
    PartnershipRegistration,
)


class Command(BaseCommand):
    help = 'Add test data for all 14 new services'

    def handle(self, *args, **options):
        self.stdout.write('Adding test data for all 14 new services...')
        self.stdout.write('')
        
        # 1. DIN Application
        try:
            din_app = DINApplication.objects.create(
                applicant_name='Rajesh Kumar',
                father_name='Suresh Kumar',
                date_of_birth=date(1985, 5, 15),
                address='123, MG Road, Bangalore, Karnataka - 560001',
                pan_number='ABCDE1234F',
                aadhaar_number='123456789012',
                email='rajesh.kumar@example.com',
                phone='9876543210',
                whatsapp='9876543210',
                status='pending',
            )
            self.stdout.write(self.style.SUCCESS('✓ DIN Application test data added'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ DIN Application: {str(e)}'))
        
        # 2. GST Registration
        try:
            gst_reg = GSTRegistration.objects.create(
                legal_entity_name='Tech Solutions Pvt Ltd',
                trade_name='TechSol',
                business_type='Private Limited',
                pan_number='TECHS1234P',
                aadhaar_number='987654321098',
                principal_place_address='456, IT Park, Hyderabad, Telangana - 500081',
                additional_places='Branch Office: 789, Commercial Street, Mumbai',
                bank_account_number='1234567890123456',
                bank_ifsc='HDFC0001234',
                bank_name='HDFC Bank',
                authorized_signatory_name='Priya Sharma',
                authorized_signatory_designation='Director',
                nature_of_business='Software Development and IT Services',
                email='info@techsolutions.com',
                phone='9123456789',
                status='pending',
            )
            self.stdout.write(self.style.SUCCESS('✓ GST Registration test data added'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ GST Registration: {str(e)}'))
        
        # 3. GST Filing
        try:
            gst_filing = GSTFiling.objects.create(
                gstin_number='27TECHS1234P1Z5',
                return_type='GSTR-3B',
                return_period='04-2024',
                total_sales=Decimal('500000.00'),
                total_purchases=Decimal('300000.00'),
                output_tax=Decimal('90000.00'),
                input_tax_credit=Decimal('54000.00'),
                net_tax_payable=Decimal('36000.00'),
                payment_details='Paid via NEFT - Transaction ID: NEFT123456789',
                filing_date=date(2024, 5, 20),
                status='submitted',
            )
            self.stdout.write(self.style.SUCCESS('✓ GST Filing test data added'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ GST Filing: {str(e)}'))
        
        # 4. Company Compliance (ROC) LLP
        try:
            roc_llp = CompanyComplianceROCLLP.objects.create(
                company_name='Innovate LLP',
                registration_number='AAB-1234',
                filing_type='Annual Return',
                financial_year='2023-24',
                due_date=date(2024, 10, 30),
                filing_date=date(2024, 9, 15),
                notes='Annual return filed with all required documents',
                status='submitted',
            )
            self.stdout.write(self.style.SUCCESS('✓ Company Compliance (ROC) LLP test data added'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Company Compliance (ROC) LLP: {str(e)}'))
        
        # 5. Authorized Capital & Paid-up Capital Increase
        try:
            capital_increase = AuthorizedPaidupCapitalIncrease.objects.create(
                company_name='Growth Enterprises Pvt Ltd',
                cin_number='U74999MH2020PTC345678',
                current_authorized_capital=Decimal('1000000.00'),
                new_authorized_capital=Decimal('5000000.00'),
                current_paidup_capital=Decimal('500000.00'),
                new_paidup_capital=Decimal('2000000.00'),
                reason_for_increase='Business expansion and working capital requirements',
                status='pending',
            )
            self.stdout.write(self.style.SUCCESS('✓ Authorized & Paid-up Capital Increase test data added'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Authorized & Paid-up Capital Increase: {str(e)}'))
        
        # 6. DIN KYC
        try:
            din_kyc = DINKYC.objects.create(
                din_number='01234567',
                director_name='Amit Patel',
                pan_number='AMITP5678Q',
                aadhaar_number='112233445566',
                email='amit.patel@example.com',
                phone='9988776655',
                address='789, Business Tower, Ahmedabad, Gujarat - 380001',
                status='pending',
            )
            self.stdout.write(self.style.SUCCESS('✓ DIN KYC test data added'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ DIN KYC: {str(e)}'))
        
        # 7. NGO Darpan
        try:
            ngo_darpan = NGODarpan.objects.create(
                organization_name='Education for All Foundation',
                registration_number='TR/2020/123456',
                registration_type='Trust',
                registration_date=date(2020, 3, 15),
                address='321, Social Welfare Complex, Delhi - 110001',
                contact_person='Dr. Meera Singh',
                email='info@educationforall.org',
                phone='9876543211',
                objectives='To provide quality education to underprivileged children and promote literacy',
                status='pending',
            )
            self.stdout.write(self.style.SUCCESS('✓ NGO Darpan test data added'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ NGO Darpan: {str(e)}'))
        
        # 8. ITR Filing
        try:
            itr_filing = ITRFiling.objects.create(
                pan_number='ITRFL1234R',
                assessment_year='2024-25',
                itr_type='ITR-3',
                total_income=Decimal('1500000.00'),
                total_deductions=Decimal('200000.00'),
                taxable_income=Decimal('1300000.00'),
                tax_amount=Decimal('234000.00'),
                advance_tax_paid=Decimal('200000.00'),
                tds_amount=Decimal('30000.00'),
                refund_or_balance_tax=Decimal('4000.00'),
                filing_date=date(2024, 7, 31),
                status='submitted',
            )
            self.stdout.write(self.style.SUCCESS('✓ ITR Filing test data added'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ ITR Filing: {str(e)}'))
        
        # 9. INC-20A (Business Commencement)
        try:
            inc20a = INC20ABusinessCommencement.objects.create(
                company_name='New Ventures Pvt Ltd',
                cin_number='U72900KA2024PTC123456',
                incorporation_date=date(2024, 1, 15),
                commencement_date=date(2024, 3, 1),
                business_activity='Manufacturing and trading of electronic goods',
                registered_office_address='555, Industrial Area, Bangalore, Karnataka - 560058',
                status='submitted',
            )
            self.stdout.write(self.style.SUCCESS('✓ INC-20A (Business Commencement) test data added'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ INC-20A: {str(e)}'))
        
        # 10. GEM Registration
        try:
            gem_reg = GEMRegistration.objects.create(
                business_name='Government Supplies Co',
                business_type='Private Limited',
                pan_number='GEMRG5678T',
                gstin_number='29GEMRG5678T1Z2',
                address='888, Government Complex, New Delhi - 110001',
                contact_person='Vikram Mehta',
                email='contact@govsupplies.com',
                phone='9123456780',
                products_services='Office supplies, stationery, furniture, and IT equipment',
                bank_account_number='9876543210987654',
                bank_ifsc='SBIN0001234',
                status='pending',
            )
            self.stdout.write(self.style.SUCCESS('✓ GEM Registration test data added'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ GEM Registration: {str(e)}'))
        
        # 11. Start-up INDIA – SEED FUNDING
        try:
            seed_funding = StartupIndiaSeedFunding.objects.create(
                startup_name='InnovateTech Solutions',
                cin_number='U72900MH2023PTC456789',
                startup_india_registration_number='DIPP123456',
                funding_amount_requested=Decimal('5000000.00'),
                business_description='AI-powered healthcare solutions for rural India',
                innovation_usp='Mobile-based telemedicine platform with AI diagnostics',
                market_potential='Targeting 500 million rural population with limited healthcare access',
                founder_details='Founder: Dr. Anjali Verma, Co-founder: Rahul Kapoor',
                contact_email='contact@innovatetech.in',
                contact_phone='9876543212',
                status='pending',
            )
            self.stdout.write(self.style.SUCCESS('✓ Start-up INDIA – SEED FUNDING test data added'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Start-up INDIA – SEED FUNDING: {str(e)}'))
        
        # 12. CSR-1 (NGO)
        try:
            csr1_ngo = CSR1NGO.objects.create(
                ngo_name='Green Earth Foundation',
                registration_number='S/2021/789012',
                registration_type='Society',
                address='654, Environmental Park, Pune, Maharashtra - 411001',
                contact_person='Arjun Desai',
                email='info@greenearth.org',
                phone='9123456781',
                objectives='Environmental conservation, tree plantation, and sustainable development',
                csr_activities='Tree plantation drives, waste management programs, environmental awareness campaigns',
                status='pending',
            )
            self.stdout.write(self.style.SUCCESS('✓ CSR-1 (NGO) test data added'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ CSR-1 (NGO): {str(e)}'))
        
        # 13. 12A & 80G Registration
        try:
            reg_12a_80g = Registration12A80G.objects.create(
                organization_name='Helping Hands Trust',
                registration_number='TR/2019/345678',
                registration_type='Trust',
                address='987, Charity Lane, Chennai, Tamil Nadu - 600001',
                contact_person='Lakshmi Iyer',
                email='info@helpinghands.org',
                phone='9123456782',
                objectives='Providing healthcare, education, and livelihood support to marginalized communities',
                registration_12a_required=True,
                registration_80g_required=True,
                status='pending',
            )
            self.stdout.write(self.style.SUCCESS('✓ 12A & 80G Registration test data added'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ 12A & 80G Registration: {str(e)}'))
        
        # 14. Partnership Registration
        try:
            partnership = PartnershipRegistration.objects.create(
                firm_name='Sharma & Associates',
                principal_place_of_business='234, Partnership Plaza, Jaipur, Rajasthan - 302001',
                business_activity='Legal consultancy and advisory services',
                partner_details='Partner 1: Ramesh Sharma (50% share), Partner 2: Suresh Gupta (50% share)',
                capital_contribution=Decimal('1000000.00'),
                profit_sharing_ratio='50:50',
                contact_email='info@sharmaassociates.com',
                contact_phone='9123456783',
                status='pending',
            )
            self.stdout.write(self.style.SUCCESS('✓ Partnership Registration test data added'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Partnership Registration: {str(e)}'))
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✓ Test data addition completed for all 14 new services!'))

