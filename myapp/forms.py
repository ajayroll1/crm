from django import forms
from django.core.exceptions import ValidationError
from .models import (
    Lead,
    ROCComplianceRecord,
    GSTFilingRecord,
    ITRFilingRecord,
    BookkeepingChecklistRecord,
    TDSComplianceRecord,
    StartupIndiaRegistration,
    FSSAILicense,
    MSMEUdyamRegistration,
    CompanyLLPRegistration,
    FirePollutionLicense,
    ISOCertification,
)

class LeadForm(forms.ModelForm):
    """
    Lead form with custom validation
    यह form lead data को validate करता है और save करता है
    """
    
    created_by = forms.CharField(label="Created By", required=False, widget=forms.TextInput(attrs={
        'class': 'form-control', 'readonly': 'readonly', 'style': 'background:#eee;'
    }))

    class Meta:
        model = Lead
        fields = [
            'name', 'email', 'phone', 'company', 'source', 'priority', 
            'owner', 'use_case', 'next_action', 'due_date', 'due_time',
            'website', 'industry', 'city', 'country', 'budget', 
            'timeline', 'tags', 'notes', 'created_by'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Full name',
                'required': True
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'name@example.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. +91 98765 43210'
            }),
            'company': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Company name'
            }),
            'source': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'priority': forms.Select(attrs={
                'class': 'form-select'
            }),
            'owner': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Assigned to',
                'required': True
            }),
            'use_case': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'What do they need?',
                'required': True
            }),
            'next_action': forms.Select(attrs={
                'class': 'form-select'
            }),
            'due_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'due_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://...'
            }),
            'industry': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. BFSI, Retail'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'budget': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 1–2 Lakh'
            }),
            'timeline': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 2 months'
            }),
            'tags': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Comma separated e.g. BFSI, Enterprise'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add required field indicators
        self.fields['name'].label = 'Name *'
        self.fields['source'].label = 'Source *'
        self.fields['owner'].label = 'Owner (assignee) *'
        self.fields['use_case'].label = 'Use-case (1–2 lines) *'
        
        # Set default values
        self.fields['priority'].initial = 'Med'
        self.fields['next_action'].initial = 'None'
    
    def clean(self):
        """
        Custom validation for the form
        यहाँ हम custom validation करते हैं
        """
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        phone = cleaned_data.get('phone')
        
        # Either email or phone must be provided
        if not email and not phone:
            raise ValidationError('Either Email or Phone is required.')
        
        # Email validation
        if email:
            if not email.strip():
                raise ValidationError('Email cannot be empty.')
        
        # Phone validation
        if phone:
            if not phone.strip():
                raise ValidationError('Phone cannot be empty.')
            # Check phone format
            import re
            phone_pattern = r'^[0-9+\-()\s]{7,20}$'
            if not re.match(phone_pattern, phone.strip()):
                raise ValidationError('Enter a valid phone number.')
        
        return cleaned_data
    
    def clean_email(self):
        """Email specific validation"""
        email = self.cleaned_data.get('email')
        if email:
            email = email.strip()
            if not email:
                return None
        return email
    
    def clean_phone(self):
        """Phone specific validation"""
        phone = self.cleaned_data.get('phone')
        if phone:
            phone = phone.strip()
            if not phone:
                return None
        return phone


class ROCComplianceForm(forms.ModelForm):
    """Form for ROC compliance intake."""

    compliance_period = forms.ChoiceField(
        choices=[
            ('Form AOC-4', 'Form AOC-4'),
            ('Form MGT-7', 'Form MGT-7'),
            ('Form ADT-1', 'Form ADT-1'),
            ('Form DIR-3 KYC', 'Form DIR-3 KYC'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    digital_signature = forms.ChoiceField(
        choices=[
            ('Director DSC (Class 3)', 'Director DSC (Class 3)'),
            ('Practicing CA DSC', 'Practicing CA DSC'),
            ('Company Secretary DSC', 'Company Secretary DSC'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = ROCComplianceRecord
        fields = [
            'company_name',
            'cin_llpin',
            'financial_year',
            'agm_date',
            'compliance_period',
            'digital_signature',
            'pending_queries',
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter registered company name'}),
            'cin_llpin': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'LXXXX00XXYYYYYYYY'}),
            'financial_year': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '2024-2025'}),
            'agm_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'pending_queries': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Mention board approval status, audit observations...'}),
        }


class GSTFilingForm(forms.ModelForm):
    """Form for GST return builder."""

    RETURN_CHOICES = [
        ('GSTR-1', 'GSTR-1'),
        ('GSTR-3B', 'GSTR-3B'),
        ('GSTR-9', 'GSTR-9'),
        ('GSTR-9C', 'GSTR-9C'),
    ]

    FILING_SCHEME_CHOICES = [
        ('Regular', 'Regular'),
        ('QRMP (Quarterly)', 'QRMP (Quarterly)'),
        ('Composition', 'Composition'),
    ]

    return_type = forms.ChoiceField(
        choices=RETURN_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    filing_scheme = forms.ChoiceField(
        choices=FILING_SCHEME_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = GSTFilingRecord
        fields = [
            'gstin',
            'return_period',
            'return_type',
            'filing_scheme',
            'tax_payable',
            'input_credit_utilized',
            'internal_remarks',
        ]
        widgets = {
            'gstin': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '27ABCDE1234F1Z5'}),
            'return_period': forms.DateInput(attrs={'class': 'form-control', 'type': 'month'}),
            'tax_payable': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
            'input_credit_utilized': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
            'internal_remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Record reconciliation notes, differences between GSTR-2B and purchase register...'}),
        }


class ITRFilingForm(forms.ModelForm):
    """Form for ITR intake."""

    assessment_year = forms.ChoiceField(
        choices=[
            ('2025-26', '2025-26'),
            ('2024-25', '2024-25'),
            ('2023-24', '2023-24'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    return_form = forms.ChoiceField(
        choices=[
            ('ITR-1', 'ITR-1'),
            ('ITR-2', 'ITR-2'),
            ('ITR-3', 'ITR-3'),
            ('ITR-4', 'ITR-4'),
            ('ITR-6', 'ITR-6'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    client_category = forms.ChoiceField(
        choices=[
            ('Individual', 'Individual'),
            ('HUF', 'HUF'),
            ('Firm / LLP', 'Firm / LLP'),
            ('Company', 'Company'),
            ('Trust', 'Trust'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    books_of_account = forms.ChoiceField(
        choices=[
            ('Maintained', 'Maintained'),
            ('Not Maintained', 'Not Maintained'),
            ('Presumptive Scheme', 'Presumptive Scheme'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = ITRFilingRecord
        fields = [
            'taxpayer_name',
            'pan',
            'assessment_year',
            'return_form',
            'client_category',
            'books_of_account',
            'computation_notes',
        ]
        widgets = {
            'taxpayer_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Name as per PAN'}),
            'pan': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ABCDE1234F', 'maxlength': 10}),
            'computation_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Record adjustments, disallowances, carry forward losses, MAT/AMT calculation...'}),
        }


class BookkeepingChecklistForm(forms.ModelForm):
    """Form for daily bookkeeping checklist."""

    cash_book_updated = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )
    bank_entries_reconciled = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )
    inventory_updated = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )

    class Meta:
        model = BookkeepingChecklistRecord
        fields = [
            'closing_date',
            'prepared_by',
            'cash_book_updated',
            'bank_entries_reconciled',
            'inventory_updated',
            'outstanding_notes',
        ]
        widgets = {
            'closing_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'prepared_by': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Team member name'}),
            'outstanding_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Mention pending vendor bills, client approvals, missing vouchers...'}),
        }


class TDSComplianceForm(forms.ModelForm):
    """Form for TDS payment & return tracker."""

    section = forms.ChoiceField(
        choices=[
            ('192 - Salary', '192 - Salary'),
            ('194C - Contractors', '194C - Contractors'),
            ('194J - Professional Fees', '194J - Professional Fees'),
            ('194I - Rent', '194I - Rent'),
            ('195 - Non-resident Payments', '195 - Non-resident Payments'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = TDSComplianceRecord
        fields = [
            'deductor_tan',
            'section',
            'deduction_month',
            'total_payment_amount',
            'tds_deducted',
            'challan_number',
            'challan_date',
        ]
        widgets = {
            'deductor_tan': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ABCD12345E'}),
            'deduction_month': forms.DateInput(attrs={'class': 'form-control', 'type': 'month'}),
            'total_payment_amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
            'tds_deducted': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
            'challan_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 20242560012345'}),
            'challan_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class StartupIndiaRegistrationForm(forms.ModelForm):
    """Form for Start-up India Registration intake."""

    entity_type = forms.ChoiceField(
        choices=StartupIndiaRegistration.ENTITY_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    industry_sector = forms.ChoiceField(
        choices=StartupIndiaRegistration.INDUSTRY_SECTOR_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = StartupIndiaRegistration
        fields = [
            'legal_entity_name',
            'incorporation_date',
            'entity_type',
            'industry_sector',
            'authorised_contact',
            'email',
            'innovation_usp',
        ]
        widgets = {
            'legal_entity_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'As per COI'}),
            'incorporation_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'authorised_contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Founder / Director'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@company.com'}),
            'innovation_usp': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Summarise solution & uniqueness'}),
        }


class FSSAILicenseForm(forms.ModelForm):
    """Form for FSSAI Food Licensing intake."""

    licence_type = forms.ChoiceField(
        choices=FSSAILicense.LICENCE_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    business_nature = forms.ChoiceField(
        choices=FSSAILicense.BUSINESS_NATURE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    licence_tenure = forms.ChoiceField(
        choices=FSSAILicense.LICENCE_TENURE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = FSSAILicense
        fields = [
            'business_brand_name',
            'licence_type',
            'business_nature',
            'premises_address',
            'employees',
            'licence_tenure',
        ]
        widgets = {
            'business_brand_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Legal / Brand name'}),
            'premises_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Full address with PIN'}),
            'employees': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Food handlers count'}),
        }


class MSMEUdyamRegistrationForm(forms.ModelForm):
    """Form for MSME / Udyam Registration intake."""

    organisation_type = forms.ChoiceField(
        choices=MSMEUdyamRegistration.ORGANISATION_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = MSMEUdyamRegistration
        fields = [
            'entity_name',
            'organisation_type',
            'plant_machinery_investment',
            'annual_turnover',
            'principal_activity',
        ]
        widgets = {
            'entity_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'As per PAN'}),
            'plant_machinery_investment': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 2500000'}),
            'annual_turnover': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 5000000'}),
            'principal_activity': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Goods/services description'}),
        }


class CompanyLLPRegistrationForm(forms.ModelForm):
    """Form for Company / LLP Registration intake."""

    entity_type = forms.ChoiceField(
        choices=CompanyLLPRegistration.ENTITY_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = CompanyLLPRegistration
        fields = [
            'entity_type',
            'directors_partners',
            'proposed_names',
            'authorised_capital',
            'registered_office',
        ]
        widgets = {
            'directors_partners': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'placeholder': 'e.g. 2'}),
            'proposed_names': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'List three options'}),
            'authorised_capital': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 100000'}),
            'registered_office': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Address with PIN'}),
        }


class FirePollutionLicenseForm(forms.ModelForm):
    """Form for Fire & Pollution Licence intake."""

    establishment_type = forms.ChoiceField(
        choices=FirePollutionLicense.ESTABLISHMENT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    pollution_category = forms.ChoiceField(
        choices=FirePollutionLicense.POLLUTION_CATEGORY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = FirePollutionLicense
        fields = [
            'establishment_type',
            'built_up_area',
            'pollution_category',
            'safety_installations',
        ]
        widgets = {
            'built_up_area': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 12000'}),
            'safety_installations': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Hydrants, sprinklers, ETP, etc.'}),
        }


class ISOCertificationForm(forms.ModelForm):
    """Form for ISO Certification intake."""

    standard = forms.ChoiceField(
        choices=ISOCertification.STANDARD_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = ISOCertification
        fields = [
            'standard',
            'locations',
            'employee_strength',
            'existing_certifications',
        ]
        widgets = {
            'locations': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'No. of sites'}),
            'employee_strength': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Employee count'}),
            'existing_certifications': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'If any'}),
        }


class LeadFilterForm(forms.Form):
    """
    Form for filtering leads
    यह form leads को filter करने के लिए है
    """
    
    FILTER_TYPE_CHOICES = [
        ('date', 'Date'),
        ('month', 'Month'),
        ('year', 'Year'),
        ('between', 'Between'),
    ]
    
    filter_type = forms.ChoiceField(
        choices=FILTER_TYPE_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='date'
    )
    
    single_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    month = forms.CharField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'month'
        })
    )
    
    year = forms.IntegerField(
        required=False,
        min_value=2000,
        max_value=2100,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. 2025'
        })
    )
    
    from_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    to_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    def clean(self):
        """Validate filter form"""
        cleaned_data = super().clean()
        filter_type = cleaned_data.get('filter_type')
        
        if filter_type == 'date' and not cleaned_data.get('single_date'):
            raise ValidationError('Please select a date.')
        
        if filter_type == 'month' and not cleaned_data.get('month'):
            raise ValidationError('Please select a month.')
        
        if filter_type == 'year' and not cleaned_data.get('year'):
            raise ValidationError('Please enter a year.')
        
        if filter_type == 'between':
            from_date = cleaned_data.get('from_date')
            to_date = cleaned_data.get('to_date')
            if not from_date or not to_date:
                raise ValidationError('Please select both from and to dates.')
            if from_date > to_date:
                raise ValidationError('From date cannot be after to date.')
        
        return cleaned_data
