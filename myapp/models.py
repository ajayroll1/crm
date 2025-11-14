from django.db import models
from django.core.validators import EmailValidator, RegexValidator
from django.utils import timezone
from django.conf import settings

# Create your models here.

class Lead(models.Model):
  
    # Priority choices
    PRIORITY_CHOICES = [
        ('Low', 'Low'),
        ('Med', 'Medium'),
        ('High', 'High'),
    ]
    
    # Source choices
    SOURCE_CHOICES = [
        ('Website', 'Website'),
        ('Referral', 'Referral'),
        ('Cold Call', 'Cold Call'),
        ('Social', 'Social Media'),
        ('Event', 'Event'),
        ('Other', 'Other'),
    ]
    
    # Next action choices
    NEXT_ACTION_CHOICES = [
        ('Call', 'Call'),
        ('Email', 'Email'),
        ('Demo', 'Demo'),
        ('Meeting', 'Meeting'),
        ('None', 'None'),
    ]
    
    # Basic Information (Required fields)
    name = models.CharField(max_length=100, verbose_name="Full Name")
    email = models.EmailField(blank=True, null=True, validators=[EmailValidator()])
    phone = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        validators=[RegexValidator(
            regex=r'^[0-9+\-()\s]{7,20}$',
            message='Enter a valid phone number'
        )]
    )
    company = models.CharField(max_length=100, blank=True, null=True)
    
    # Lead Management
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES, verbose_name="Lead Source")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='Med')
    owner = models.CharField(max_length=100, verbose_name="Assigned Owner")
    use_case = models.TextField(verbose_name="Use Case", help_text="What do they need?")
    
    # Next Actions
    next_action = models.CharField(
        max_length=20, 
        choices=NEXT_ACTION_CHOICES, 
        blank=True, 
        null=True,
        default='None'
    )
    due_date = models.DateField(blank=True, null=True)
    due_time = models.TimeField(blank=True, null=True)
    
    # Optional Information
    website = models.URLField(blank=True, null=True)
    industry = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=50, blank=True, null=True)
    country = models.CharField(max_length=50, blank=True, null=True)
    budget = models.CharField(max_length=100, blank=True, null=True)
    timeline = models.CharField(max_length=100, blank=True, null=True, verbose_name="Decision Timeline")
    tags = models.CharField(max_length=200, blank=True, null=True, help_text="Comma separated tags")
    notes = models.TextField(blank=True, null=True)
    
    # System fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Lead"
        verbose_name_plural = "Leads"
    
    def __str__(self):
        return f"{self.name} - {self.company or 'No Company'}"
    
    def get_full_due_datetime(self):
        """Get combined due date and time"""
        if self.due_date and self.due_time:
            return timezone.datetime.combine(self.due_date, self.due_time)
        return None
    
    def get_priority_badge_class(self):
        """Get Bootstrap badge class for priority"""
        priority_classes = {
            'High': 'bg-danger',
            'Med': 'bg-warning text-dark',
            'Low': 'bg-success'
        }
        return priority_classes.get(self.priority, 'bg-secondary')
    
    def clean(self):
        """Custom validation"""
        from django.core.exceptions import ValidationError
        
        # Either email or phone must be provided
        if not self.email and not self.phone:
            raise ValidationError('Either email or phone number is required.')
        
        # Validate email format if provided
        if self.email:
            EmailValidator()(self.email)
        
        # Validate phone format if provided
        if self.phone:
            phone_validator = RegexValidator(
                regex=r'^[0-9+\-()\s]{7,20}$',
                message='Enter a valid phone number'
            )
            phone_validator(self.phone)
    
    def save(self, *args, **kwargs):
        """Override save to run clean validation"""
        self.clean()
        super().save(*args, **kwargs)


class LeaveRequest(models.Model):
    """Stores employee leave requests."""
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Cancelled', 'Cancelled'),
    ]

    # Link to auth user when available
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leave_requests'
    )
    applicant_name = models.CharField(max_length=150, blank=True, null=True)

    leave_type = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField()
    days = models.PositiveIntegerField()
    reason = models.TextField()
    contact = models.CharField(max_length=100, blank=True, null=True)
    handover = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')

    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-applied_at']

    def __str__(self):
        return f"{self.applicant_name or self.user or 'Anonymous'} - {self.leave_type} ({self.start_date} to {self.end_date})"


def document_upload_path(instance, filename):
    from datetime import datetime
    now = datetime.now()
    return f"uploads/documents/{now.year}/{now.month:02d}/{filename}"


class Document(models.Model):
    """Employee uploaded documents"""
    PRIVACY_CHOICES = [
        ('private', 'Private'),
        ('team', 'Team Access'),
        ('public', 'Public'),
    ]

    CATEGORY_CHOICES = [
        ('personal', 'Personal'),
        ('work', 'Work Related'),
        ('contracts', 'Contracts'),
        ('certificates', 'Certificates'),
        ('other', 'Other'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')
    file = models.FileField(upload_to=document_upload_path)
    original_name = models.CharField(max_length=255)
    size_bytes = models.BigIntegerField(default=0)
    mime_type = models.CharField(max_length=100, blank=True, null=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='personal')
    privacy = models.CharField(max_length=20, choices=PRIVACY_CHOICES, default='private')
    description = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.original_name


class Quote(models.Model):
    """Quotation/Quote management"""
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Sent', 'Sent'),
        ('Accepted', 'Accepted'),
        ('Declined', 'Declined'),
    ]
    
    CURRENCY_CHOICES = [
        ('INR', 'INR (₹)'),
        ('USD', 'USD ($)'),
        ('EUR', 'EUR (€)'),
    ]
    
    # Client Information
    client_name = models.CharField(max_length=200, verbose_name="Client Name")
    company = models.CharField(max_length=200, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    
    # Quote Details
    quote_number = models.CharField(max_length=50, unique=True, verbose_name="Quote #")
    owner = models.CharField(max_length=100, verbose_name="Owner/Assignee")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Draft')
    currency = models.CharField(max_length=10, choices=CURRENCY_CHOICES, default='INR')
    valid_until = models.DateField(verbose_name="Valid Until")
    
    # Financial
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # Additional Information
    notes = models.TextField(blank=True, null=True, verbose_name="Notes for client")
    terms = models.TextField(blank=True, null=True, verbose_name="Terms & Conditions")
    project_pdf = models.FileField(upload_to='quotes/pdfs/', blank=True, null=True, verbose_name="Project Details PDF")
    
    # Line Items (stored as JSON)
    items = models.JSONField(default=list, blank=True, help_text="List of quote items")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Quote"
        verbose_name_plural = "Quotes"
    
    def __str__(self):
        return f"{self.quote_number} - {self.client_name}"
    
    def get_status_badge_class(self):
        """Get Bootstrap badge class for status"""
        status_classes = {
            'Draft': 'bg-secondary',
            'Sent': 'bg-warning text-dark',
            'Accepted': 'bg-success',
            'Declined': 'bg-danger'
        }
        return status_classes.get(self.status, 'bg-secondary')


class ClientOnboarding(models.Model):
    """Client Onboarding management"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('pending', 'Pending'),
        ('on_hold', 'On Hold'),
        ('completed', 'Completed'),
    ]
    
    DURATION_UNIT_CHOICES = [
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
        ('years', 'Years'),
    ]
    
    # Client Information
    client_name = models.CharField(max_length=200, verbose_name="Client Name")
    company_name = models.CharField(max_length=200, blank=True, null=True)
    client_email = models.EmailField(blank=True, null=True)
    client_phone = models.CharField(max_length=20, blank=True, null=True)
    
    # Project Details
    project_name = models.CharField(max_length=300, verbose_name="Project Name")
    project_description = models.TextField(blank=True, null=True)
    project_duration = models.PositiveIntegerField(verbose_name="Duration")
    duration_unit = models.CharField(max_length=10, choices=DURATION_UNIT_CHOICES, default='months')
    project_cost = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Project Cost")
    
    # Assignment
    assigned_engineer = models.CharField(max_length=100, verbose_name="Assigned Engineer")
    start_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Client Onboarding"
        verbose_name_plural = "Client Onboardings"
    
    def __str__(self):
        return f"{self.client_name} - {self.project_name}"
    
    def get_duration_display_text(self):
        """Get formatted duration text"""
        return f"{self.project_duration} {self.duration_unit}"
    
    def get_status_badge_class(self):
        """Get Bootstrap badge class for status"""
        status_classes = {
            'active': 'bg-success',
            'pending': 'bg-warning text-dark',
            'on_hold': 'bg-secondary',
            'completed': 'bg-info'
        }
        return status_classes.get(self.status, 'bg-secondary')


class ROCComplianceRecord(models.Model):
    """Stores ROC compliance preparation details for accounts team."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='roc_compliance_records'
    )
    company_name = models.CharField(max_length=255)
    cin_llpin = models.CharField(max_length=25, verbose_name="CIN / LLPIN")
    financial_year = models.CharField(max_length=20)
    agm_date = models.DateField(null=True, blank=True)
    compliance_period = models.CharField(max_length=100)
    digital_signature = models.CharField(max_length=100)
    pending_queries = models.TextField(blank=True, null=True)
    documents = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "ROC Compliance Record"
        verbose_name_plural = "ROC Compliance Records"

    def __str__(self):
        return f"{self.company_name} ({self.financial_year})"


class GSTFilingRecord(models.Model):
    """Stores GST return preparation details."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='gst_filing_records'
    )
    gstin = models.CharField(max_length=15, verbose_name="GSTIN")
    return_period = models.CharField(max_length=7, help_text="YYYY-MM format")
    return_type = models.CharField(max_length=20)
    filing_scheme = models.CharField(max_length=30)
    tax_payable = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    input_credit_utilized = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    internal_remarks = models.TextField(blank=True, null=True)
    data_files = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "GST Filing Record"
        verbose_name_plural = "GST Filing Records"

    def __str__(self):
        return f"{self.gstin} - {self.return_type} ({self.return_period})"


class ITRFilingRecord(models.Model):
    """Stores income tax return intake details."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='itr_filing_records'
    )
    taxpayer_name = models.CharField(max_length=255)
    pan = models.CharField(max_length=10)
    assessment_year = models.CharField(max_length=9)
    return_form = models.CharField(max_length=10)
    client_category = models.CharField(max_length=50)
    books_of_account = models.CharField(max_length=50)
    computation_notes = models.TextField(blank=True, null=True)
    documents = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "ITR Filing Record"
        verbose_name_plural = "ITR Filing Records"

    def __str__(self):
        return f"{self.taxpayer_name} - {self.assessment_year}"


class BookkeepingChecklistRecord(models.Model):
    """Stores daily accounts & bookkeeping checklist submissions."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bookkeeping_checklists'
    )
    closing_date = models.DateField(null=True, blank=True)
    prepared_by = models.CharField(max_length=255)
    cash_book_updated = models.BooleanField(default=False)
    bank_entries_reconciled = models.BooleanField(default=False)
    inventory_updated = models.BooleanField(default=False)
    outstanding_notes = models.TextField(blank=True, null=True)
    reconciliation_documents = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-closing_date', '-created_at']
        verbose_name = "Bookkeeping Checklist Record"
        verbose_name_plural = "Bookkeeping Checklist Records"

    def __str__(self):
        closing = self.closing_date.strftime('%Y-%m-%d') if self.closing_date else 'No Date'
        return f"{self.prepared_by} - {closing}"


class TDSComplianceRecord(models.Model):
    """Stores TDS payment and return tracker submissions."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tds_compliance_records'
    )
    deductor_tan = models.CharField(max_length=10, verbose_name="Deductor TAN")
    section = models.CharField(max_length=30)
    deduction_month = models.CharField(max_length=7, help_text="YYYY-MM format")
    total_payment_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tds_deducted = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    challan_number = models.CharField(max_length=25)
    challan_date = models.DateField(null=True, blank=True)
    proofs = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "TDS Compliance Record"
        verbose_name_plural = "TDS Compliance Records"

    def __str__(self):
        return f"{self.deductor_tan} - {self.section} ({self.deduction_month})"


class StartupIndiaRegistration(models.Model):
    """Stores Start-up India Registration submissions."""

    ENTITY_TYPE_CHOICES = [
        ('Pvt Ltd', 'Pvt Ltd'),
        ('LLP', 'LLP'),
        ('Partnership', 'Partnership'),
        ('OPC', 'OPC'),
        ('Section 8', 'Section 8'),
    ]

    INDUSTRY_SECTOR_CHOICES = [
        ('Tech', 'Tech'),
        ('Manufacturing', 'Manufacturing'),
        ('Fintech', 'Fintech'),
        ('Healthcare', 'Healthcare'),
        ('Other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('ready', 'Ready'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='startup_india_registrations'
    )
    legal_entity_name = models.CharField(max_length=255, verbose_name="Legal Entity Name")
    incorporation_date = models.DateField(verbose_name="Incorporation Date", null=True, blank=True)
    entity_type = models.CharField(max_length=50, choices=ENTITY_TYPE_CHOICES, verbose_name="Entity Type")
    industry_sector = models.CharField(max_length=50, choices=INDUSTRY_SECTOR_CHOICES, verbose_name="Industry Sector")
    authorised_contact = models.CharField(max_length=255, verbose_name="Authorised Contact", blank=True)
    email = models.EmailField(verbose_name="Email", blank=True)
    innovation_usp = models.TextField(verbose_name="Innovation / USP", blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    documents = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Start-up India Registration"
        verbose_name_plural = "Start-up India Registrations"

    def __str__(self):
        return f"{self.legal_entity_name} - {self.entity_type}"


class FSSAILicense(models.Model):
    """Stores FSSAI Food Licensing submissions."""

    LICENCE_TYPE_CHOICES = [
        ('Basic', 'Basic'),
        ('State', 'State'),
        ('Central', 'Central'),
        ('Import/Export', 'Import/Export'),
    ]

    BUSINESS_NATURE_CHOICES = [
        ('Manufacturing', 'Manufacturing'),
        ('Distributor', 'Distributor'),
        ('Storage', 'Storage'),
        ('Catering', 'Catering'),
    ]

    LICENCE_TENURE_CHOICES = [
        ('1 Year', '1 Year'),
        ('2 Years', '2 Years'),
        ('3 Years', '3 Years'),
        ('5 Years', '5 Years'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('ready', 'Ready'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fssai_licenses'
    )
    business_brand_name = models.CharField(max_length=255, verbose_name="Business / Brand Name")
    licence_type = models.CharField(max_length=50, choices=LICENCE_TYPE_CHOICES, verbose_name="Licence Type")
    business_nature = models.CharField(max_length=50, choices=BUSINESS_NATURE_CHOICES, verbose_name="Business Nature")
    premises_address = models.TextField(verbose_name="Premises Address", blank=True)
    employees = models.IntegerField(verbose_name="Employees", null=True, blank=True)
    licence_tenure = models.CharField(max_length=20, choices=LICENCE_TENURE_CHOICES, verbose_name="Licence Tenure")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    documents = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "FSSAI License"
        verbose_name_plural = "FSSAI Licenses"

    def __str__(self):
        return f"{self.business_brand_name} - {self.licence_type}"


class MSMEUdyamRegistration(models.Model):
    """Stores MSME / Udyam Registration submissions."""

    ORGANISATION_TYPE_CHOICES = [
        ('Proprietorship', 'Proprietorship'),
        ('Partnership', 'Partnership'),
        ('LLP', 'LLP'),
        ('Company', 'Company'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('ready', 'Ready'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='msme_registrations'
    )
    entity_name = models.CharField(max_length=255, verbose_name="Entity Name")
    organisation_type = models.CharField(
        max_length=50,
        choices=ORGANISATION_TYPE_CHOICES,
        verbose_name="Organisation Type"
    )
    plant_machinery_investment = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        verbose_name="Plant & Machinery Investment (₹)",
        default=0
    )
    annual_turnover = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        verbose_name="Annual Turnover (₹)",
        default=0
    )
    principal_activity = models.TextField(verbose_name="Principal Activity", blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "MSME / Udyam Registration"
        verbose_name_plural = "MSME / Udyam Registrations"

    def __str__(self):
        return f"{self.entity_name} - {self.organisation_type}"


class CompanyLLPRegistration(models.Model):
    """Stores Company / LLP Registration submissions."""

    ENTITY_TYPE_CHOICES = [
        ('Pvt Ltd', 'Pvt Ltd'),
        ('LLP', 'LLP'),
        ('OPC', 'OPC'),
        ('Section 8', 'Section 8'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('ready', 'Ready'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='company_llp_registrations'
    )
    entity_type = models.CharField(max_length=50, choices=ENTITY_TYPE_CHOICES, verbose_name="Entity Type")
    directors_partners = models.PositiveIntegerField(verbose_name="Directors / Partners", default=1)
    proposed_names = models.TextField(verbose_name="Proposed Names (3)")
    authorised_capital = models.DecimalField(max_digits=16, decimal_places=2, verbose_name="Authorised Capital (₹)", default=0)
    registered_office = models.TextField(verbose_name="Registered Office")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    documents = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Company / LLP Registration"
        verbose_name_plural = "Company / LLP Registrations"

    def __str__(self):
        return f"{self.get_entity_type_display()} - {self.proposed_names.splitlines()[0] if self.proposed_names else 'Proposal'}"


class FirePollutionLicense(models.Model):
    """Stores Fire & Pollution Licence submissions."""

    ESTABLISHMENT_CHOICES = [
        ('Manufacturing', 'Manufacturing'),
        ('Warehouse', 'Warehouse'),
        ('Restaurant', 'Restaurant'),
        ('Retail', 'Retail'),
        ('Office', 'Office'),
    ]

    POLLUTION_CATEGORY_CHOICES = [
        ('White', 'White'),
        ('Green', 'Green'),
        ('Orange', 'Orange'),
        ('Red', 'Red'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('ready', 'Ready'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fire_pollution_licenses'
    )
    establishment_type = models.CharField(max_length=50, choices=ESTABLISHMENT_CHOICES, verbose_name="Establishment Type")
    built_up_area = models.PositiveIntegerField(verbose_name="Built-up Area (sq.ft)")
    pollution_category = models.CharField(max_length=20, choices=POLLUTION_CATEGORY_CHOICES, verbose_name="Pollution Category")
    safety_installations = models.TextField(verbose_name="Safety Installations")
    documents = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Fire & Pollution License"
        verbose_name_plural = "Fire & Pollution Licenses"

    def __str__(self):
        return f"{self.establishment_type} - {self.pollution_category}"


class ISOCertification(models.Model):
    """Stores ISO Certification submissions."""

    STANDARD_CHOICES = [
        ('ISO 9001', 'ISO 9001'),
        ('ISO 14001', 'ISO 14001'),
        ('ISO 45001', 'ISO 45001'),
        ('ISO 27001', 'ISO 27001'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('ready', 'Ready'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='iso_certifications'
    )
    standard = models.CharField(max_length=50, choices=STANDARD_CHOICES, verbose_name="Standard")
    locations = models.PositiveIntegerField(verbose_name="Locations", help_text="No. of sites", default=1)
    employee_strength = models.PositiveIntegerField(verbose_name="Employee Strength", null=True, blank=True)
    existing_certifications = models.TextField(verbose_name="Existing Certifications", blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    documents = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "ISO Certification"
        verbose_name_plural = "ISO Certifications"

    def __str__(self):
        return f"{self.standard} - {self.locations} location(s)"


class Attendance(models.Model):
    """Employee attendance check in/out records"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='attendance_records',
        null=True,
        blank=True
    )
    employee = models.ForeignKey(
        'Employee',
        on_delete=models.CASCADE,
        related_name='attendance_records',
        null=True,
        blank=True,
        verbose_name="Employee"
    )
    employee_name = models.CharField(max_length=150)
    date = models.DateField()
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_in_photo = models.TextField(null=True, blank=True)  # Store as base64 or file path
    check_out_time = models.DateTimeField(null=True, blank=True)
    check_out_photo = models.TextField(null=True, blank=True)  # Store as base64 or file path
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', '-check_in_time']
        verbose_name = "Attendance"
        verbose_name_plural = "Attendances"
        unique_together = [['user', 'date'], ['employee', 'date']]  # One record per user/employee per day
    
    def __str__(self):
        return f"{self.employee_name} - {self.date}"
    
    def calculate_work_hours(self):
        """Calculate work hours, minutes, and seconds"""
        if not self.check_in_time or not self.check_out_time:
            return None
        
        delta = self.check_out_time - self.check_in_time
        total_seconds = int(delta.total_seconds())
        
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        return {
            'hours': hours,
            'minutes': minutes,
            'seconds': seconds,
            'total_seconds': total_seconds,
            'formatted': f"{hours}h {minutes}m {seconds}s"
        }

class Employee(models.Model):
    """Employee master data model"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('on_leave', 'On Leave'),
        ('terminated', 'Terminated'),
    ]
    
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]
    
    EMPLOYMENT_TYPE_CHOICES = [
        ('Full-time', 'Full-time'),
        ('Part-time', 'Part-time'),
        ('Contract', 'Contract'),
        ('Intern', 'Intern'),
    ]
    
    ROLE_CHOICES = [
        ('Employee', 'Employee'),
        ('Admin', 'Admin'),
    ]
    
    PAY_CYCLE_CHOICES = [
        ('Monthly', 'Monthly'),
        ('Bi-weekly', 'Bi-weekly'),
    ]
    
    # Personal Information
    first_name = models.CharField(max_length=100, verbose_name="First Name")
    last_name = models.CharField(max_length=100, verbose_name="Last Name")
    emp_code = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="Employee Code")
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)
    dob = models.DateField(blank=True, null=True, verbose_name="Date of Birth")
    email = models.EmailField(verbose_name="Email")
    phone = models.CharField(max_length=20, verbose_name="Phone")
    address_current = models.TextField(blank=True, null=True, verbose_name="Current Address")
    address_permanent = models.TextField(blank=True, null=True, verbose_name="Permanent Address")
    photo = models.ImageField(upload_to='uploads/employees/photos/', blank=True, null=True, verbose_name="Profile Photo")
    
    # Job Information
    designation = models.CharField(max_length=100, blank=True, null=True, verbose_name="Designation")
    department = models.CharField(max_length=100, blank=True, null=True, verbose_name="Department")
    manager = models.CharField(max_length=100, blank=True, null=True, verbose_name="Reporting Manager")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='Employee', blank=True, null=True, verbose_name="Role")
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE_CHOICES, blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    joining_date = models.DateField(blank=True, null=True)
    probation = models.IntegerField(blank=True, null=True, verbose_name="Probation (months)")
    
    # Payroll
    ctc = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, verbose_name="CTC (Annual)")
    basic = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    hra = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, verbose_name="HRA")
    allowances = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    deductions = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    variable = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, verbose_name="Variable/Bonus")
    pay_cycle = models.CharField(max_length=20, choices=PAY_CYCLE_CHOICES, blank=True, null=True)
    
    # Banking
    bank_name = models.CharField(max_length=200, blank=True, null=True)
    account_number = models.CharField(max_length=50, blank=True, null=True)
    ifsc = models.CharField(max_length=20, blank=True, null=True, verbose_name="IFSC")
    upi = models.CharField(max_length=100, blank=True, null=True, verbose_name="UPI ID")
    pan = models.CharField(max_length=20, blank=True, null=True, verbose_name="PAN")
    aadhaar = models.CharField(max_length=20, blank=True, null=True, verbose_name="Aadhaar")
    
    # Tax/IDs
    uan = models.CharField(max_length=50, blank=True, null=True, verbose_name="UAN (PF)")
    esic = models.CharField(max_length=50, blank=True, null=True, verbose_name="ESIC No")
    gst = models.CharField(max_length=50, blank=True, null=True, verbose_name="GST (if any)")
    
    # Emergency Contacts
    emg_name1 = models.CharField(max_length=100, blank=True, null=True, verbose_name="Primary Contact Name")
    emg_relation1 = models.CharField(max_length=50, blank=True, null=True, verbose_name="Primary Relation")
    emg_phone1 = models.CharField(max_length=20, blank=True, null=True, verbose_name="Primary Phone")
    emg_name2 = models.CharField(max_length=100, blank=True, null=True, verbose_name="Secondary Contact Name")
    emg_relation2 = models.CharField(max_length=50, blank=True, null=True, verbose_name="Secondary Relation")
    emg_phone2 = models.CharField(max_length=20, blank=True, null=True, verbose_name="Secondary Phone")
    
    # Assets
    asset_laptop = models.CharField(max_length=200, blank=True, null=True)
    asset_phone = models.CharField(max_length=200, blank=True, null=True)
    asset_other = models.CharField(max_length=200, blank=True, null=True)
    
    # Access
    work_email = models.EmailField(blank=True, null=True, verbose_name="Work Email")
    github = models.CharField(max_length=200, blank=True, null=True, verbose_name="Git/GitHub")
    pm_tool = models.CharField(max_length=200, blank=True, null=True, verbose_name="Jira/PM Tool")
    vpn = models.CharField(max_length=10, blank=True, null=True, verbose_name="VPN Access")
    access_level = models.CharField(max_length=20, blank=True, null=True, verbose_name="Access Level")
    
    # Notes
    notes = models.TextField(blank=True, null=True)
    
    # Documents
    doc_aadhaar = models.FileField(upload_to='uploads/employees/documents/', blank=True, null=True, verbose_name="Aadhaar Card")
    doc_pan = models.FileField(upload_to='uploads/employees/documents/', blank=True, null=True, verbose_name="PAN Card")
    doc_bank = models.FileField(upload_to='uploads/employees/documents/', blank=True, null=True, verbose_name="Bank Passbook/Cancelled Cheque")
    doc_experience = models.FileField(upload_to='uploads/employees/documents/', blank=True, null=True, verbose_name="Experience Letter(s)")
    doc_education = models.FileField(upload_to='uploads/employees/documents/', blank=True, null=True, verbose_name="Education Certificates")
    doc_prev_offer_relieve = models.FileField(upload_to='uploads/employees/documents/', blank=True, null=True, verbose_name="Previous Company Offer/Relieving Letter")
    doc_current_offer = models.FileField(upload_to='uploads/employees/documents/', blank=True, null=True, verbose_name="Current Company Offer/Appointment Letter")
    doc_salary_slips = models.FileField(upload_to='uploads/employees/documents/', blank=True, null=True, verbose_name="Latest Month Salary Slips")
    
    # Leave Balances
    annual_leave = models.IntegerField(default=20, verbose_name="Annual Leave Days")
    sick_leave = models.IntegerField(default=12, verbose_name="Sick Leave Days")
    personal_leave = models.IntegerField(default=5, verbose_name="Personal Leave Days")
    maternity_leave = models.IntegerField(default=90, verbose_name="Maternity Leave Days")
    paternity_leave = models.IntegerField(default=15, verbose_name="Paternity Leave Days")
    emergency_leave = models.IntegerField(default=3, verbose_name="Emergency Leave Days")
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Employee"
        verbose_name_plural = "Employees"
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.emp_code or 'No Code'}"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    def get_initials(self):
        """Get initials for avatar"""
        first = self.first_name[0].upper() if self.first_name else ''
        last = self.last_name[0].upper() if self.last_name else ''
        return (first + last)[:2]
    
    def get_net_salary(self):
        """Calculate net salary (Basic + HRA + Allowances + Variable - Deductions)"""
        from decimal import Decimal
        basic = self.basic or Decimal('0')
        hra = self.hra or Decimal('0')
        allowances = self.allowances or Decimal('0')
        variable = self.variable or Decimal('0')
        deductions = self.deductions or Decimal('0')
        return basic + hra + allowances + variable - deductions


class EmployeeMessage(models.Model):
    """Employee messaging system - messages between employees and admin"""
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages',
        null=True,
        blank=True,
        verbose_name="Sender User"
    )
    receiver_id = models.CharField(max_length=100, verbose_name="Receiver ID")  # Can be employee ID or admin_{user_id}
    receiver_name = models.CharField(max_length=200, verbose_name="Receiver Name")
    
    # Sender information (logged in user details)
    sender_name = models.CharField(max_length=200, verbose_name="Sender Name")
    sender_designation = models.CharField(max_length=100, blank=True, null=True, verbose_name="Sender Designation")
    sender_department = models.CharField(max_length=100, blank=True, null=True, verbose_name="Sender Department")
    
    # Message content
    message = models.TextField(verbose_name="Message", blank=True, null=True)
    
    # Attachments
    image = models.ImageField(upload_to='messages/images/%Y/%m/%d/', blank=True, null=True, verbose_name="Image")
    attachment = models.FileField(upload_to='messages/attachments/%Y/%m/%d/', blank=True, null=True, verbose_name="Attachment")
    attachment_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Attachment Name")
    
    # Status
    is_read = models.BooleanField(default=False, verbose_name="Is Read")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Employee Message"
        verbose_name_plural = "Employee Messages"
    
    def __str__(self):
        return f"{self.sender_name} -> {self.receiver_name}: {self.message[:50]}"
    
    def get_receiver_type(self):
        """Check if receiver is admin or employee"""
        if self.receiver_id.startswith('admin_'):
            return 'admin'
        return 'employee'


class PaymentTransaction(models.Model):
    """Payment transaction records for employee payments"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('bank_transfer', 'Bank Transfer'),
        ('upi', 'UPI'),
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
        ('other', 'Other'),
    ]
    
    # Employee Information
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='payment_transactions',
        verbose_name="Employee"
    )
    employee_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Employee Name Snapshot"
    )
    employee_department = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Department Snapshot"
    )
    
    # Payment Details
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Payment Amount")
    basic = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, verbose_name="Basic Salary")
    hra = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, verbose_name="HRA")
    allowances = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, verbose_name="Allowances")
    deductions = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, verbose_name="Deductions")
    variable = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, verbose_name="Variable/Bonus")
    ctc = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, verbose_name="CTC")
    
    # Payment Information
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='bank_transfer', verbose_name="Payment Method")
    transaction_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="Transaction ID")
    reference_number = models.CharField(max_length=100, blank=True, null=True, verbose_name="Reference Number")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed', verbose_name="Status")
    
    # Payment Period
    payment_month = models.IntegerField(verbose_name="Payment Month (1-12)")
    payment_year = models.IntegerField(verbose_name="Payment Year")
    payment_date = models.DateField(verbose_name="Payment Date")
    
    # Notes
    notes = models.TextField(blank=True, null=True, verbose_name="Notes")
    
    # Processed by
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_payments',
        verbose_name="Processed By"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-payment_date', '-created_at']
        verbose_name = "Payment Transaction"
        verbose_name_plural = "Payment Transactions"
        indexes = [
            models.Index(fields=['employee', '-payment_date']),
            models.Index(fields=['payment_year', 'payment_month']),
        ]
    
    def __str__(self):
        return f"{self.get_employee_name()} - ₹{self.amount} - {self.payment_date}"
    
    def get_month_name(self):
        """Get month name from month number"""
        from datetime import datetime
        try:
            return datetime(2000, self.payment_month, 1).strftime('%B')
        except:
            return f"Month {self.payment_month}"
    
    def get_payment_period(self):
        """Get formatted payment period"""
        return f"{self.get_month_name()} {self.payment_year}"

    def get_employee_name(self):
        """Snapshot-friendly accessor for employee name"""
        if self.employee_name:
            return self.employee_name
        if self.employee_id:
            try:
                return self.employee.get_full_name()
            except Employee.DoesNotExist:
                return ""
        return ""

    def get_employee_department(self):
        """Snapshot-friendly accessor for employee department"""
        if self.employee_department:
            return self.employee_department
        if self.employee_id:
            try:
                return self.employee.department or ""
            except Employee.DoesNotExist:
                return ""
        return ""