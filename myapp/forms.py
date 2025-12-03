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
    TrademarkFiling,
    TrademarkFilingCompliance,
    TrademarkFilingInstant,
    CompanyAddressChange,
    MOAAlteration,
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
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )

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
            'lead_source',
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
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )

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
            'lead_source',
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
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )

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
            'lead_source',
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
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )

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
            'lead_source',
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
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )

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
            'lead_source',
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
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )

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
            'lead_source',
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
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )

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
            'lead_source',
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
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )

    organisation_type = forms.ChoiceField(
        choices=MSMEUdyamRegistration.ORGANISATION_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = MSMEUdyamRegistration
        fields = [
            'lead_source',
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
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )

    entity_type = forms.ChoiceField(
        choices=CompanyLLPRegistration.ENTITY_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = CompanyLLPRegistration
        fields = [
            'lead_source',
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
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )

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
            'lead_source',
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
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )

    standard = forms.ChoiceField(
        choices=ISOCertification.STANDARD_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = ISOCertification
        fields = [
            'lead_source',
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


class TrademarkFilingForm(forms.ModelForm):
    """Form for Trademark Filing intake."""
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )

    applicant_type = forms.ChoiceField(
        choices=TrademarkFiling.APPLICANT_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = TrademarkFiling
        fields = [
            'lead_source',
            'brand_logo',
            'applicant_type',
            'classes',
            'first_use_date',
        ]
        widgets = {
            'brand_logo': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe or attach logo'}),
            'classes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 35, 42'}),
            'first_use_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class TrademarkFilingComplianceForm(forms.ModelForm):
    """Form for Trademark Filing + Compliance intake."""
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )

    watch_scope = forms.ChoiceField(
        choices=TrademarkFilingCompliance.WATCH_SCOPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )

    class Meta:
        model = TrademarkFilingCompliance
        fields = [
            'lead_source',
            'existing_tm_numbers',
            'portfolio_size',
            'watch_scope',
            'renewal_month',
        ]
        widgets = {
            'existing_tm_numbers': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'If any'}),
            'portfolio_size': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Portfolio size'}),
            'renewal_month': forms.TextInput(attrs={'class': 'form-control', 'type': 'month', 'placeholder': 'Select month'}),
        }


class TrademarkFilingInstantForm(forms.ModelForm):
    """Form for Trademark Filing (Instant Process) intake."""
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )

    filing_window = forms.ChoiceField(
        choices=TrademarkFilingInstant.FILING_WINDOW_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )

    class Meta:
        model = TrademarkFilingInstant
        fields = [
            'lead_source',
            'urgency_reason',
            'filing_window',
            'contact_mobile',
        ]
        widgets = {
            'urgency_reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Launch / diligence / other'}),
            'contact_mobile': forms.TextInput(attrs={'class': 'form-control', 'type': 'tel', 'placeholder': '+91XXXXXXXXXX'}),
        }


class CompanyAddressChangeForm(forms.ModelForm):
    """Form for Company Address Change intake."""
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )

    entity_type = forms.ChoiceField(
        choices=CompanyAddressChange.ENTITY_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    shift_type = forms.ChoiceField(
        choices=CompanyAddressChange.SHIFT_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = CompanyAddressChange
        fields = [
            'lead_source',
            'entity_type',
            'shift_type',
            'effective_date',
            'new_address',
        ]
        widgets = {
            'effective_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'new_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Complete address'}),
        }


class MOAAlterationForm(forms.ModelForm):
    """Form for MOA Alteration intake."""
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )

    alteration_type = forms.ChoiceField(
        choices=MOAAlteration.ALTERATION_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = MOAAlteration
        fields = [
            'lead_source',
            'alteration_type',
            'proposed_object_name',
            'effective_date',
        ]
        widgets = {
            'proposed_object_name': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Draft text / options'}),
            'effective_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class ProfessionalTaxRegistrationForm(forms.ModelForm):
    """Form for Professional Tax Registration intake."""
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )

    business_type = forms.ChoiceField(
        choices=ProfessionalTaxRegistration.BUSINESS_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = ProfessionalTaxRegistration
        fields = [
            'lead_source',
            'business_name',
            'business_type',
            'pan_number',
            'gst_number',
            'business_address',
            'bank_account_details',
            'number_of_employees',
            'business_start_date',
            'monthly_salary_details',
        ]
        widgets = {
            'business_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Business name'}),
            'pan_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ABCDE1234F', 'maxlength': 10}),
            'gst_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'GSTIN'}),
            'business_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Complete business address'}),
            'bank_account_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Bank account details'}),
            'number_of_employees': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Number of employees'}),
            'business_start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'monthly_salary_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Monthly salary details'}),
        }


class IECRegistrationForm(forms.ModelForm):
    """Form for IEC Registration intake."""
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )

    business_type = forms.ChoiceField(
        choices=IECRegistration.BUSINESS_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = IECRegistration
        fields = [
            'lead_source',
            'firm_name',
            'pan_number',
            'business_type',
            'incorporation_date',
            'bank_account_details',
            'directors_partners_details',
            'branch_offices',
        ]
        widgets = {
            'firm_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Firm/Company name'}),
            'pan_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ABCDE1234F', 'maxlength': 10}),
            'incorporation_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'bank_account_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Bank account details'}),
            'directors_partners_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Directors/Partners details'}),
            'branch_offices': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Branch offices details'}),
        }


class ICEGateRegistrationForm(forms.ModelForm):
    """Form for ICE Gate Registration intake."""
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )

    user_role = forms.ChoiceField(
        choices=ICEGateRegistration.USER_ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = ICEGateRegistration
        fields = [
            'lead_source',
            'company_name',
            'pan_number',
            'iec_number',
            'user_role',
            'authorized_person_name',
            'authorized_person_details',
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company name'}),
            'pan_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ABCDE1234F', 'maxlength': 10}),
            'iec_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'IEC number'}),
            'authorized_person_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Authorized person name'}),
            'authorized_person_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Authorized person details'}),
        }


class TradeLicenseRegistrationForm(forms.ModelForm):
    """Form for Trade License Registration intake."""
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )

    business_type = forms.ChoiceField(
        choices=TradeLicenseRegistration.BUSINESS_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = TradeLicenseRegistration
        fields = [
            'lead_source',
            'business_name',
            'business_type',
            'business_address',
            'pan_number',
            'gst_number',
            'number_of_employees',
            'business_start_date',
            'municipal_area',
            'required_permissions',
        ]
        widgets = {
            'business_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Business name'}),
            'business_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Complete business address'}),
            'pan_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ABCDE1234F', 'maxlength': 10}),
            'gst_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'GSTIN'}),
            'number_of_employees': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Number of employees'}),
            'business_start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'municipal_area': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Municipal area'}),
            'required_permissions': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Required permissions'}),
        }


class DSCRegistrationForm(forms.ModelForm):
    """Form for DSC Registration intake."""
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )

    dsc_type = forms.ChoiceField(
        choices=DSCRegistration.DSC_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    organisation_type = forms.ChoiceField(
        choices=DSCRegistration.ORGANISATION_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )

    class Meta:
        model = DSCRegistration
        fields = [
            'lead_source',
            'pan_number',
            'aadhaar_number',
            'organisation_name',
            'organisation_type',
            'organisation_address',
            'dsc_type',
        ]
        widgets = {
            'pan_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ABCDE1234F', 'maxlength': 10}),
            'aadhaar_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Aadhaar number', 'maxlength': 12}),
            'organisation_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Organisation name'}),
            'organisation_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Organisation address'}),
        }


class CompanyNameChangeForm(forms.ModelForm):
    """Form for Company Name Change intake."""
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )

    class Meta:
        model = CompanyNameChange
        fields = [
            'lead_source',
            'current_company_name',
            'cin_number',
            'proposed_new_name',
            'reason_for_change',
            'board_meeting_date',
            'registered_office_address',
            'directors_details',
            'shareholders_details',
        ]
        widgets = {
            'current_company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Current company name'}),
            'cin_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CIN number'}),
            'proposed_new_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Proposed new name'}),
            'reason_for_change': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Reason for name change'}),
            'board_meeting_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'registered_office_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Registered office address'}),
            'directors_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Directors details'}),
            'shareholders_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Shareholders details'}),
        }


class DirectorChangeForm(forms.ModelForm):
    """Form for Director Change intake."""
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )

    change_type = forms.ChoiceField(
        choices=DirectorChange.CHANGE_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = DirectorChange
        fields = [
            'lead_source',
            'company_name',
            'cin_number',
            'change_type',
            'new_director_name',
            'new_director_din',
            'new_director_pan',
            'new_director_aadhaar',
            'new_director_address',
            'new_director_email',
            'new_director_mobile',
            'appointment_date',
            'existing_directors_details',
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company name'}),
            'cin_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CIN number'}),
            'new_director_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'New director name'}),
            'new_director_din': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'DIN'}),
            'new_director_pan': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'PAN', 'maxlength': 10}),
            'new_director_aadhaar': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Aadhaar', 'maxlength': 12}),
            'new_director_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'New director address'}),
            'new_director_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'new_director_mobile': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mobile number'}),
            'appointment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'existing_directors_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Existing directors details'}),
        }


class CompanyClosureForm(forms.ModelForm):
    """Form for Company Closure intake."""
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )

    closure_type = forms.ChoiceField(
        choices=CompanyClosure.CLOSURE_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = CompanyClosure
        fields = [
            'lead_source',
            'company_name',
            'cin_number',
            'closure_type',
            'reason_for_closure',
            'registered_office_address',
            'directors_details',
            'shareholders_details',
            'liabilities_details',
            'assets_details',
            'board_meeting_date',
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company name'}),
            'cin_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CIN number'}),
            'reason_for_closure': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Reason for closure'}),
            'registered_office_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Registered office address'}),
            'directors_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Directors details'}),
            'shareholders_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Shareholders details'}),
            'liabilities_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Liabilities details'}),
            'assets_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Assets details'}),
            'board_meeting_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class RCMCRegistrationForm(forms.ModelForm):
    """Form for RCMC Registration intake."""
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )

    class Meta:
        model = RCMCRegistration
        fields = [
            'lead_source',
            'firm_name',
            'iec_number',
            'pan_number',
            'registered_office_address',
            'export_products_details',
            'export_performance_details',
            'related_export_council_name',
        ]
        widgets = {
            'firm_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Firm/Company name'}),
            'iec_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'IEC number'}),
            'pan_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ABCDE1234F', 'maxlength': 10}),
            'registered_office_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Registered office address'}),
            'export_products_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Export products details'}),
            'export_performance_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Export performance details'}),
            'related_export_council_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Related export council name'}),
        }


class ShopEstablishmentRegistrationForm(forms.ModelForm):
    """Form for Shop Establishment Registration intake."""
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )

    state = forms.ChoiceField(
        choices=ShopEstablishmentRegistration.STATE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    business_type = forms.ChoiceField(
        choices=ShopEstablishmentRegistration.BUSINESS_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = ShopEstablishmentRegistration
        fields = [
            'lead_source',
            'shop_establishment_name',
            'state',
            'business_type',
            'business_address',
            'pan_number',
            'gst_number',
            'number_of_employees',
            'business_start_date',
            'working_hours',
            'weekly_holiday',
            'municipal_area',
        ]
        widgets = {
            'shop_establishment_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Shop/Establishment name'}),
            'business_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Complete business address'}),
            'pan_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ABCDE1234F', 'maxlength': 10}),
            'gst_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'GSTIN'}),
            'number_of_employees': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Number of employees'}),
            'business_start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'working_hours': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 9 AM - 6 PM'}),
            'weekly_holiday': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Sunday'}),
            'municipal_area': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Municipal area'}),
        }


class DINApplicationForm(forms.ModelForm):
    """Form for DIN Application intake."""
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )
    
    class Meta:
        model = DINApplication
        fields = [
            'lead_source',
            'applicant_name',
            'father_name',
            'date_of_birth',
            'address',
            'pan_number',
            'aadhaar_number',
            'email',
            'phone',
            'whatsapp',
        ]
        widgets = {
            'applicant_name': forms.TextInput(attrs={'class': 'form-control'}),
            'father_name': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'pan_number': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '10'}),
            'aadhaar_number': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '12'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'whatsapp': forms.TextInput(attrs={'class': 'form-control'}),
        }


class GSTRegistrationForm(forms.ModelForm):
    """Form for GST Registration intake."""
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )
    
    business_type = forms.ChoiceField(
        choices=GSTRegistration.BUSINESS_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    
    class Meta:
        model = GSTRegistration
        fields = [
            'lead_source',
            'legal_entity_name',
            'trade_name',
            'business_type',
            'pan_number',
            'aadhaar_number',
            'principal_place_address',
            'additional_places',
            'bank_account_number',
            'bank_ifsc',
            'bank_name',
            'authorized_signatory_name',
            'authorized_signatory_designation',
            'nature_of_business',
            'email',
            'phone',
        ]
        widgets = {
            'legal_entity_name': forms.TextInput(attrs={'class': 'form-control'}),
            'trade_name': forms.TextInput(attrs={'class': 'form-control'}),
            'pan_number': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '10'}),
            'aadhaar_number': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '12'}),
            'principal_place_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'additional_places': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'bank_account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_ifsc': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '11'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'authorized_signatory_name': forms.TextInput(attrs={'class': 'form-control'}),
            'authorized_signatory_designation': forms.TextInput(attrs={'class': 'form-control'}),
            'nature_of_business': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }


class GSTFilingForm(forms.ModelForm):
    """Form for GST Filing intake."""
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )
    
    return_type = forms.ChoiceField(
        choices=GSTFiling.RETURN_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    
    class Meta:
        model = GSTFiling
        fields = [
            'lead_source',
            'gstin_number',
            'return_type',
            'return_period',
            'total_sales',
            'total_purchases',
            'output_tax',
            'input_tax_credit',
            'net_tax_payable',
            'payment_details',
            'filing_date',
        ]
        widgets = {
            'gstin_number': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '15'}),
            'return_period': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 04-2024'}),
            'total_sales': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'total_purchases': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'output_tax': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'input_tax_credit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'net_tax_payable': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'filing_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class CompanyComplianceROCLLPForm(forms.ModelForm):
    """Form for Company Compliance (ROC) LLP intake."""
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )
    
    filing_type = forms.ChoiceField(
        choices=CompanyComplianceROCLLP.FILING_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    
    class Meta:
        model = CompanyComplianceROCLLP
        fields = [
            'lead_source',
            'company_name',
            'registration_number',
            'filing_type',
            'financial_year',
            'due_date',
            'filing_date',
            'notes',
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'registration_number': forms.TextInput(attrs={'class': 'form-control'}),
            'financial_year': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 2023-24'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'filing_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class AuthorizedPaidupCapitalIncreaseForm(forms.ModelForm):
    """Form for Authorized & Paid-up Capital Increase intake."""
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )
    
    class Meta:
        model = AuthorizedPaidupCapitalIncrease
        fields = [
            'lead_source',
            'company_name',
            'cin_number',
            'current_authorized_capital',
            'new_authorized_capital',
            'current_paidup_capital',
            'new_paidup_capital',
            'reason_for_increase',
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'cin_number': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '21'}),
            'current_authorized_capital': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'new_authorized_capital': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'current_paidup_capital': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'new_paidup_capital': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'reason_for_increase': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class DINKYCForm(forms.ModelForm):
    """Form for DIN KYC intake."""
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )
    
    class Meta:
        model = DINKYC
        fields = [
            'lead_source',
            'din_number',
            'director_name',
            'pan_number',
            'aadhaar_number',
            'email',
            'phone',
            'address',
        ]
        widgets = {
            'din_number': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '8'}),
            'director_name': forms.TextInput(attrs={'class': 'form-control'}),
            'pan_number': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '10'}),
            'aadhaar_number': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '12'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class NGODarpanForm(forms.ModelForm):
    """Form for NGO Darpan Registration intake."""
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )
    
    class Meta:
        model = NGODarpan
        fields = [
            'lead_source',
            'organization_name',
            'registration_number',
            'registration_type',
            'registration_date',
            'address',
            'contact_person',
            'email',
            'phone',
            'objectives',
        ]
        widgets = {
            'organization_name': forms.TextInput(attrs={'class': 'form-control'}),
            'registration_number': forms.TextInput(attrs={'class': 'form-control'}),
            'registration_type': forms.TextInput(attrs={'class': 'form-control'}),
            'registration_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'objectives': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ITRFilingForm(forms.ModelForm):
    """Form for ITR Filing intake."""
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )
    
    itr_type = forms.ChoiceField(
        choices=ITRFiling.ITR_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    
    class Meta:
        model = ITRFiling
        fields = [
            'lead_source',
            'pan_number',
            'assessment_year',
            'itr_type',
            'total_income',
            'total_deductions',
            'taxable_income',
            'tax_amount',
            'advance_tax_paid',
            'tds_amount',
            'refund_or_balance_tax',
            'filing_date',
        ]
        widgets = {
            'pan_number': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '10'}),
            'assessment_year': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 2024-25'}),
            'total_income': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'total_deductions': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'taxable_income': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tax_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'advance_tax_paid': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tds_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'refund_or_balance_tax': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'filing_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class INC20ABusinessCommencementForm(forms.ModelForm):
    """Form for INC-20A (Business Commencement) intake."""
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )
    
    class Meta:
        model = INC20ABusinessCommencement
        fields = [
            'lead_source',
            'company_name',
            'cin_number',
            'incorporation_date',
            'commencement_date',
            'business_activity',
            'registered_office_address',
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'cin_number': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '21'}),
            'incorporation_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'commencement_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'business_activity': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'registered_office_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class GEMRegistrationForm(forms.ModelForm):
    """Form for GEM Registration intake."""
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )
    
    class Meta:
        model = GEMRegistration
        fields = [
            'lead_source',
            'business_name',
            'business_type',
            'pan_number',
            'gstin_number',
            'address',
            'contact_person',
            'email',
            'phone',
            'products_services',
            'bank_account_number',
            'bank_ifsc',
        ]
        widgets = {
            'business_name': forms.TextInput(attrs={'class': 'form-control'}),
            'business_type': forms.TextInput(attrs={'class': 'form-control'}),
            'pan_number': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '10'}),
            'gstin_number': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '15'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'products_services': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'bank_account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_ifsc': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '11'}),
        }


class StartupIndiaSeedFundingForm(forms.ModelForm):
    """Form for Start-up INDIA – SEED FUNDING intake."""
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )
    
    class Meta:
        model = StartupIndiaSeedFunding
        fields = [
            'lead_source',
            'startup_name',
            'cin_number',
            'startup_india_registration_number',
            'funding_amount_requested',
            'business_description',
            'innovation_usp',
            'market_potential',
            'founder_details',
            'contact_email',
            'contact_phone',
        ]
        widgets = {
            'startup_name': forms.TextInput(attrs={'class': 'form-control'}),
            'cin_number': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '21'}),
            'startup_india_registration_number': forms.TextInput(attrs={'class': 'form-control'}),
            'funding_amount_requested': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'business_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'innovation_usp': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'market_potential': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'founder_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
        }


class CSR1NGOForm(forms.ModelForm):
    """Form for CSR-1 (NGO) intake."""
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )
    
    class Meta:
        model = CSR1NGO
        fields = [
            'lead_source',
            'ngo_name',
            'registration_number',
            'registration_type',
            'address',
            'contact_person',
            'email',
            'phone',
            'objectives',
            'csr_activities',
        ]
        widgets = {
            'ngo_name': forms.TextInput(attrs={'class': 'form-control'}),
            'registration_number': forms.TextInput(attrs={'class': 'form-control'}),
            'registration_type': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'objectives': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'csr_activities': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class Registration12A80GForm(forms.ModelForm):
    """Form for 12A & 80G Registration intake."""
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )
    
    class Meta:
        model = Registration12A80G
        fields = [
            'lead_source',
            'organization_name',
            'registration_number',
            'registration_type',
            'address',
            'contact_person',
            'email',
            'phone',
            'objectives',
            'registration_12a_required',
            'registration_80g_required',
        ]
        widgets = {
            'organization_name': forms.TextInput(attrs={'class': 'form-control'}),
            'registration_number': forms.TextInput(attrs={'class': 'form-control'}),
            'registration_type': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'objectives': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'registration_12a_required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'registration_80g_required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class PartnershipRegistrationForm(forms.ModelForm):
    """Form for Partnership Registration intake."""
    
    lead_source = forms.CharField(
        initial='website',
        widget=forms.HiddenInput(),
        required=False
    )
    
    class Meta:
        model = PartnershipRegistration
        fields = [
            'lead_source',
            'firm_name',
            'principal_place_of_business',
            'business_activity',
            'partner_details',
            'capital_contribution',
            'profit_sharing_ratio',
            'contact_email',
            'contact_phone',
        ]
        widgets = {
            'firm_name': forms.TextInput(attrs={'class': 'form-control'}),
            'principal_place_of_business': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'business_activity': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'partner_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'capital_contribution': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'profit_sharing_ratio': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 50:50 or 60:40'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
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
