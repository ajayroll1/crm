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
    address = models.TextField(blank=True, null=True, verbose_name="Address")
    
    # Lead Management
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES, verbose_name="Lead Source")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='Med')
    owner = models.CharField(max_length=100, verbose_name="Assigned Owner")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_leads',
        verbose_name="Assigned To Employee"
    )
    imported_by = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='imported_leads',
        verbose_name="Imported By"
    )
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
    amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, verbose_name="Amount")
    timeline = models.CharField(max_length=100, blank=True, null=True, verbose_name="Decision Timeline")
    tags = models.CharField(max_length=200, blank=True, null=True, help_text="Comma separated tags")
    notes = models.TextField(blank=True, null=True)
    
    # Status field for lead conversion tracking
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Contacted', 'Contacted'),
        ('Qualified', 'Qualified'),
        ('Proposal', 'Proposal'),
        ('Negotiation', 'Negotiation'),
        ('Won', 'Won'),
        ('Lost', 'Lost'),
    ]
    conversion_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending', blank=True, null=True, verbose_name="Status")
    
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
    
    @property
    def conversion_badge(self):
        """Get Bootstrap badge class for conversion status"""
        status_classes = {
            'Pending': 'bg-secondary',
            'Contacted': 'bg-info',
            'Qualified': 'bg-primary',
            'Proposal': 'bg-warning text-dark',
            'Negotiation': 'bg-warning text-dark',
            'Won': 'bg-success',
            'Lost': 'bg-danger',
        }
        return status_classes.get(self.conversion_status or 'Pending', 'bg-secondary')
    
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


class Invoice(models.Model):
    """Invoice management"""
    STATUS_CHOICES = [
        ('Paid', 'Paid'),
        ('Unpaid', 'Unpaid'),
        ('Partial', 'Partial'),
        ('Cancelled', 'Cancelled'),
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
    
    # Invoice Details
    invoice_number = models.CharField(max_length=50, unique=True, verbose_name="Invoice #")
    invoice_date = models.DateField(verbose_name="Invoice Date")
    owner = models.CharField(max_length=100, verbose_name="Owner/Assignee")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Unpaid')
    currency = models.CharField(max_length=10, choices=CURRENCY_CHOICES, default='INR')
    
    # Financial
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    gst_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="GST Percentage (%)")
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="GST Amount")
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    amount_received = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Amount Received")
    payment_history = models.JSONField(default=list, blank=True, help_text="List of partial payments with amount and date")
    
    # Additional Information
    notes = models.TextField(blank=True, null=True, verbose_name="Notes")
    terms = models.TextField(blank=True, null=True, verbose_name="Terms & Conditions")
    
    # Line Items (stored as JSON)
    items = models.JSONField(default=list, blank=True, help_text="List of invoice items")
    
    # Selected Bank Accounts (stored as JSON array of bank account IDs)
    selected_bank_accounts = models.JSONField(default=list, blank=True, help_text="List of selected bank account IDs to display on invoice")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'myapp_invoice'
        ordering = ['-invoice_date', '-created_at']
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"
    
    def __str__(self):
        return f"{self.invoice_number} - {self.client_name}"
    
    def get_status_badge_class(self):
        """Get Bootstrap badge class for status"""
        status_classes = {
            'Paid': 'bg-success',
            'Unpaid': 'bg-danger',
            'Partial': 'bg-warning text-dark',
            'Cancelled': 'bg-secondary'
        }
        return status_classes.get(self.status, 'bg-secondary')
    
    def get_pending_balance(self):
        """Calculate pending balance (Total - Amount Received)"""
        pending = float(self.total) - float(self.amount_received)
        return max(0, pending)
    
    def calculate_status(self):
        """Calculate status based on pending balance"""
        if self.status == 'Cancelled':
            return 'Cancelled'
        
        pending = self.get_pending_balance()
        if pending <= 0:
            return 'Paid'
        elif self.amount_received > 0:
            return 'Partial'
        else:
            return 'Unpaid'
    
    def save(self, *args, **kwargs):
        """Auto-update status based on pending balance before saving"""
        # Only auto-update if status is not Cancelled
        if self.status != 'Cancelled':
            calculated_status = self.calculate_status()
            if self.status != calculated_status:
                self.status = calculated_status
        super().save(*args, **kwargs)


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

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('submitted', 'Submitted'),
        ('complete', 'Complete'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='roc_compliance_records'
    )
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_roc_records',
        verbose_name="Assigned To"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Status")
    # Applicant/User Information
    applicant_name = models.CharField(max_length=255, verbose_name="Applicant Name", blank=True, null=True)
    applicant_phone = models.CharField(max_length=20, verbose_name="Phone Number", blank=True, null=True)
    applicant_whatsapp = models.CharField(max_length=20, verbose_name="WhatsApp Number", blank=True, null=True)
    applicant_email = models.EmailField(verbose_name="Email", blank=True, null=True)
    applicant_address = models.TextField(verbose_name="Address", blank=True, null=True)
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

    def get_status_badge_class(self):
        """Return Bootstrap badge class for display"""
        status_classes = {
            'pending': 'bg-warning text-dark',
            'accepted': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'complete': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary')


class GSTFilingRecord(models.Model):
    """Stores GST return preparation details."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('submitted', 'Submitted'),
        ('complete', 'Complete'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='gst_filing_records'
    )
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_gst_records',
        verbose_name="Assigned To"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Status")
    # Applicant/User Information
    applicant_name = models.CharField(max_length=255, verbose_name="Applicant Name", blank=True, null=True)
    applicant_phone = models.CharField(max_length=20, verbose_name="Phone Number", blank=True, null=True)
    applicant_whatsapp = models.CharField(max_length=20, verbose_name="WhatsApp Number", blank=True, null=True)
    applicant_email = models.EmailField(verbose_name="Email", blank=True, null=True)
    applicant_address = models.TextField(verbose_name="Address", blank=True, null=True)
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

    def get_status_badge_class(self):
        """Return Bootstrap badge class for display"""
        status_classes = {
            'pending': 'bg-warning text-dark',
            'accepted': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'complete': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary')


class ITRFilingRecord(models.Model):
    """Stores income tax return intake details."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('submitted', 'Submitted'),
        ('complete', 'Complete'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='itr_filing_records'
    )
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_itr_records',
        verbose_name="Assigned To"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Status")
    # Applicant/User Information
    applicant_name = models.CharField(max_length=255, verbose_name="Applicant Name", blank=True, null=True)
    applicant_phone = models.CharField(max_length=20, verbose_name="Phone Number", blank=True, null=True)
    applicant_whatsapp = models.CharField(max_length=20, verbose_name="WhatsApp Number", blank=True, null=True)
    applicant_email = models.EmailField(verbose_name="Email", blank=True, null=True)
    applicant_address = models.TextField(verbose_name="Address", blank=True, null=True)
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

    def get_status_badge_class(self):
        """Return Bootstrap badge class for display"""
        status_classes = {
            'pending': 'bg-warning text-dark',
            'accepted': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'complete': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary')


class BookkeepingChecklistRecord(models.Model):
    """Stores daily accounts & bookkeeping checklist submissions."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('submitted', 'Submitted'),
        ('complete', 'Complete'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bookkeeping_checklists'
    )
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_bookkeeping_records',
        verbose_name="Assigned To"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Status")
    # Applicant/User Information
    applicant_name = models.CharField(max_length=255, verbose_name="Applicant Name", blank=True, null=True)
    applicant_phone = models.CharField(max_length=20, verbose_name="Phone Number", blank=True, null=True)
    applicant_whatsapp = models.CharField(max_length=20, verbose_name="WhatsApp Number", blank=True, null=True)
    applicant_email = models.EmailField(verbose_name="Email", blank=True, null=True)
    applicant_address = models.TextField(verbose_name="Address", blank=True, null=True)
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

    def get_status_badge_class(self):
        """Return Bootstrap badge class for display"""
        status_classes = {
            'pending': 'bg-warning text-dark',
            'accepted': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'complete': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary')


class TDSComplianceRecord(models.Model):
    """Stores TDS payment and return tracker submissions."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('submitted', 'Submitted'),
        ('complete', 'Complete'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tds_compliance_records'
    )
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tds_records',
        verbose_name="Assigned To"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Status")
    # Applicant/User Information
    applicant_name = models.CharField(max_length=255, verbose_name="Applicant Name", blank=True, null=True)
    applicant_phone = models.CharField(max_length=20, verbose_name="Phone Number", blank=True, null=True)
    applicant_whatsapp = models.CharField(max_length=20, verbose_name="WhatsApp Number", blank=True, null=True)
    applicant_email = models.EmailField(verbose_name="Email", blank=True, null=True)
    applicant_address = models.TextField(verbose_name="Address", blank=True, null=True)
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

    def get_status_badge_class(self):
        """Return Bootstrap badge class for display"""
        status_classes = {
            'pending': 'bg-warning text-dark',
            'accepted': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'complete': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary')


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
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_startup_records',
        verbose_name="Assigned To"
    )
    # Applicant/User Information
    applicant_name = models.CharField(max_length=255, verbose_name="Applicant Name", blank=True, null=True)
    applicant_phone = models.CharField(max_length=20, verbose_name="Phone Number", blank=True, null=True)
    applicant_whatsapp = models.CharField(max_length=20, verbose_name="WhatsApp Number", blank=True, null=True)
    applicant_email = models.EmailField(verbose_name="Email", blank=True, null=True)
    applicant_address = models.TextField(verbose_name="Address", blank=True, null=True)
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

    def get_status_badge_class(self):
        status_classes = {
            'draft': 'bg-secondary text-dark',
            'pending': 'bg-warning text-dark',
            'ready': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'approved': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary text-dark')


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
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_fssai_records',
        verbose_name="Assigned To"
    )
    # Applicant/User Information
    applicant_name = models.CharField(max_length=255, verbose_name="Applicant Name", blank=True, null=True)
    applicant_phone = models.CharField(max_length=20, verbose_name="Phone Number", blank=True, null=True)
    applicant_whatsapp = models.CharField(max_length=20, verbose_name="WhatsApp Number", blank=True, null=True)
    applicant_email = models.EmailField(verbose_name="Email", blank=True, null=True)
    applicant_address = models.TextField(verbose_name="Address", blank=True, null=True)
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

    def get_status_badge_class(self):
        status_classes = {
            'draft': 'bg-secondary text-dark',
            'pending': 'bg-warning text-dark',
            'ready': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'approved': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary text-dark')


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
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_msme_records',
        verbose_name="Assigned To"
    )
    # Applicant/User Information
    applicant_name = models.CharField(max_length=255, verbose_name="Applicant Name", blank=True, null=True)
    applicant_phone = models.CharField(max_length=20, verbose_name="Phone Number", blank=True, null=True)
    applicant_whatsapp = models.CharField(max_length=20, verbose_name="WhatsApp Number", blank=True, null=True)
    applicant_email = models.EmailField(verbose_name="Email", blank=True, null=True)
    applicant_address = models.TextField(verbose_name="Address", blank=True, null=True)
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

    def get_status_badge_class(self):
        status_classes = {
            'draft': 'bg-secondary text-dark',
            'pending': 'bg-warning text-dark',
            'ready': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'approved': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary text-dark')


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
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_company_llp_records',
        verbose_name="Assigned To"
    )
    # Applicant/User Information
    applicant_name = models.CharField(max_length=255, verbose_name="Applicant Name", blank=True, null=True)
    applicant_phone = models.CharField(max_length=20, verbose_name="Phone Number", blank=True, null=True)
    applicant_whatsapp = models.CharField(max_length=20, verbose_name="WhatsApp Number", blank=True, null=True)
    applicant_email = models.EmailField(verbose_name="Email", blank=True, null=True)
    applicant_address = models.TextField(verbose_name="Address", blank=True, null=True)
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

    def get_status_badge_class(self):
        status_classes = {
            'draft': 'bg-secondary text-dark',
            'pending': 'bg-warning text-dark',
            'ready': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'approved': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary text-dark')


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
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_fire_pollution_records',
        verbose_name="Assigned To"
    )
    # Applicant/User Information
    applicant_name = models.CharField(max_length=255, verbose_name="Applicant Name", blank=True, null=True)
    applicant_phone = models.CharField(max_length=20, verbose_name="Phone Number", blank=True, null=True)
    applicant_whatsapp = models.CharField(max_length=20, verbose_name="WhatsApp Number", blank=True, null=True)
    applicant_email = models.EmailField(verbose_name="Email", blank=True, null=True)
    applicant_address = models.TextField(verbose_name="Address", blank=True, null=True)
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

    def get_status_badge_class(self):
        status_classes = {
            'draft': 'bg-secondary text-dark',
            'pending': 'bg-warning text-dark',
            'ready': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'approved': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary text-dark')


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
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_iso_records',
        verbose_name="Assigned To"
    )
    # Applicant/User Information
    applicant_name = models.CharField(max_length=255, verbose_name="Applicant Name", blank=True, null=True)
    applicant_phone = models.CharField(max_length=20, verbose_name="Phone Number", blank=True, null=True)
    applicant_whatsapp = models.CharField(max_length=20, verbose_name="WhatsApp Number", blank=True, null=True)
    applicant_email = models.EmailField(verbose_name="Email", blank=True, null=True)
    applicant_address = models.TextField(verbose_name="Address", blank=True, null=True)
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

    def get_status_badge_class(self):
        status_classes = {
            'draft': 'bg-secondary text-dark',
            'pending': 'bg-warning text-dark',
            'ready': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'approved': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary text-dark')


class TrademarkFiling(models.Model):
    """Stores Trademark Filing submissions."""

    APPLICANT_TYPE_CHOICES = [
        ('Individual', 'Individual'),
        ('Firm', 'Firm'),
        ('Company/LLP', 'Company/LLP'),
        ('Trust/Society', 'Trust/Society'),
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
        related_name='trademark_filings'
    )
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_trademark_records',
        verbose_name="Assigned To"
    )
    # Applicant/User Information
    applicant_name = models.CharField(max_length=255, verbose_name="Applicant Name", blank=True, null=True)
    applicant_phone = models.CharField(max_length=20, verbose_name="Phone Number", blank=True, null=True)
    applicant_whatsapp = models.CharField(max_length=20, verbose_name="WhatsApp Number", blank=True, null=True)
    applicant_email = models.EmailField(verbose_name="Email", blank=True, null=True)
    applicant_address = models.TextField(verbose_name="Address", blank=True, null=True)
    brand_logo = models.TextField(verbose_name="Brand / Logo", help_text="Describe or attach logo")
    applicant_type = models.CharField(max_length=50, choices=APPLICANT_TYPE_CHOICES, verbose_name="Applicant Type")
    classes = models.CharField(max_length=200, verbose_name="Classes", help_text="e.g. 35, 42")
    first_use_date = models.DateField(verbose_name="First Use Date", null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    documents = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Trademark Filing"
        verbose_name_plural = "Trademark Filings"

    def __str__(self):
        return f"{self.brand_logo[:50]}... - {self.applicant_type}"

    def get_status_badge_class(self):
        status_classes = {
            'draft': 'bg-secondary text-dark',
            'pending': 'bg-warning text-dark',
            'ready': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'approved': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary text-dark')


class TrademarkFilingCompliance(models.Model):
    """Stores Trademark Filing + Compliance submissions."""

    WATCH_SCOPE_CHOICES = [
        ('Identical', 'Identical'),
        ('Similar', 'Similar'),
        ('Domains/Handles', 'Domains/Handles'),
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
        related_name='trademark_filing_compliances'
    )
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_trademark_compliance_records',
        verbose_name="Assigned To"
    )
    # Applicant/User Information
    applicant_name = models.CharField(max_length=255, verbose_name="Applicant Name", blank=True, null=True)
    applicant_phone = models.CharField(max_length=20, verbose_name="Phone Number", blank=True, null=True)
    applicant_whatsapp = models.CharField(max_length=20, verbose_name="WhatsApp Number", blank=True, null=True)
    applicant_email = models.EmailField(verbose_name="Email", blank=True, null=True)
    applicant_address = models.TextField(verbose_name="Address", blank=True, null=True)
    existing_tm_numbers = models.TextField(verbose_name="Existing TM Numbers", blank=True, help_text="If any")
    portfolio_size = models.PositiveIntegerField(verbose_name="Portfolio Size", null=True, blank=True)
    watch_scope = models.CharField(max_length=50, choices=WATCH_SCOPE_CHOICES, verbose_name="Watch Scope", blank=True)
    renewal_month = models.CharField(max_length=50, verbose_name="Renewal Month", blank=True, help_text="e.g. January, February")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    documents = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Trademark Filing + Compliance"
        verbose_name_plural = "Trademark Filing + Compliances"

    def __str__(self):
        return f"TM Compliance - Portfolio: {self.portfolio_size or 'N/A'}"

    def get_status_badge_class(self):
        status_classes = {
            'draft': 'bg-secondary text-dark',
            'pending': 'bg-warning text-dark',
            'ready': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'approved': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary text-dark')


class TrademarkFilingInstant(models.Model):
    """Stores Trademark Filing (Instant Process) submissions."""

    FILING_WINDOW_CHOICES = [
        ('Before 1 PM', 'Before 1 PM'),
        ('Before 6 PM', 'Before 6 PM'),
        ('Weekend', 'Weekend'),
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
        related_name='trademark_filing_instants'
    )
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_trademark_instant_records',
        verbose_name="Assigned To"
    )
    # Applicant/User Information
    applicant_name = models.CharField(max_length=255, verbose_name="Applicant Name", blank=True, null=True)
    applicant_phone = models.CharField(max_length=20, verbose_name="Phone Number", blank=True, null=True)
    applicant_whatsapp = models.CharField(max_length=20, verbose_name="WhatsApp Number", blank=True, null=True)
    applicant_email = models.EmailField(verbose_name="Email", blank=True, null=True)
    applicant_address = models.TextField(verbose_name="Address", blank=True, null=True)
    urgency_reason = models.TextField(verbose_name="Urgency Reason", help_text="Launch / diligence / other")
    filing_window = models.CharField(max_length=50, choices=FILING_WINDOW_CHOICES, verbose_name="Filing Window", blank=True)
    contact_mobile = models.CharField(max_length=20, verbose_name="Contact Mobile", blank=True, help_text="+91XXXXXXXXXX")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    documents = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Trademark Filing (Instant Process)"
        verbose_name_plural = "Trademark Filing (Instant Process)"

    def __str__(self):
        return f"Instant TM - {self.filing_window or 'N/A'} - {self.urgency_reason[:30]}..."

    def get_status_badge_class(self):
        status_classes = {
            'draft': 'bg-secondary text-dark',
            'pending': 'bg-warning text-dark',
            'ready': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'approved': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary text-dark')


class CompanyAddressChange(models.Model):
    """Stores Company Address Change submissions."""

    ENTITY_TYPE_CHOICES = [
        ('Company', 'Company'),
        ('LLP', 'LLP'),
    ]

    SHIFT_TYPE_CHOICES = [
        ('Within city', 'Within city'),
        ('Within ROC', 'Within ROC'),
        ('Inter-ROC / State', 'Inter-ROC / State'),
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
        related_name='company_address_changes'
    )
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_address_change_records',
        verbose_name="Assigned To"
    )
    # Applicant/User Information
    applicant_name = models.CharField(max_length=255, verbose_name="Applicant Name", blank=True, null=True)
    applicant_phone = models.CharField(max_length=20, verbose_name="Phone Number", blank=True, null=True)
    applicant_whatsapp = models.CharField(max_length=20, verbose_name="WhatsApp Number", blank=True, null=True)
    applicant_email = models.EmailField(verbose_name="Email", blank=True, null=True)
    applicant_address = models.TextField(verbose_name="Address", blank=True, null=True)
    entity_type = models.CharField(max_length=50, choices=ENTITY_TYPE_CHOICES, verbose_name="Entity Type")
    shift_type = models.CharField(max_length=50, choices=SHIFT_TYPE_CHOICES, verbose_name="Type of Shift")
    effective_date = models.DateField(verbose_name="Effective Date", null=True, blank=True)
    new_address = models.TextField(verbose_name="New Address", help_text="Complete address")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    documents = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Company Address Change"
        verbose_name_plural = "Company Address Changes"

    def __str__(self):
        return f"{self.entity_type} - {self.shift_type} - {self.new_address[:30]}..."

    def get_status_badge_class(self):
        status_classes = {
            'draft': 'bg-secondary text-dark',
            'pending': 'bg-warning text-dark',
            'ready': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'approved': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary text-dark')


class MOAAlteration(models.Model):
    """Stores MOA Alteration submissions."""

    ALTERATION_TYPE_CHOICES = [
        ('Object change', 'Object change'),
        ('Name change', 'Name change'),
        ('Authorised capital', 'Authorised capital'),
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
        related_name='moa_alterations'
    )
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_moa_alteration_records',
        verbose_name="Assigned To"
    )
    # Applicant/User Information
    applicant_name = models.CharField(max_length=255, verbose_name="Applicant Name", blank=True, null=True)
    applicant_phone = models.CharField(max_length=20, verbose_name="Phone Number", blank=True, null=True)
    applicant_whatsapp = models.CharField(max_length=20, verbose_name="WhatsApp Number", blank=True, null=True)
    applicant_email = models.EmailField(verbose_name="Email", blank=True, null=True)
    applicant_address = models.TextField(verbose_name="Address", blank=True, null=True)
    alteration_type = models.CharField(max_length=50, choices=ALTERATION_TYPE_CHOICES, verbose_name="Alteration Type")
    proposed_object_name = models.TextField(verbose_name="Proposed Object/Name", help_text="Draft text / options")
    effective_date = models.DateField(verbose_name="Effective Date", null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    documents = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "MOA Alteration"
        verbose_name_plural = "MOA Alterations"

    def __str__(self):
        return f"{self.alteration_type} - {self.proposed_object_name[:30]}..."

    def get_status_badge_class(self):
        status_classes = {
            'draft': 'bg-secondary text-dark',
            'pending': 'bg-warning text-dark',
            'ready': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'approved': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary text-dark')


class ProfessionalTaxRegistration(models.Model):
    """Stores Professional Tax Registration submissions."""

    BUSINESS_TYPE_CHOICES = [
        ('Proprietorship', 'Proprietorship'),
        ('Partnership', 'Partnership'),
        ('Company', 'Company'),
        ('LLP', 'LLP'),
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
        related_name='professional_tax_registrations'
    )
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_professional_tax_records',
        verbose_name="Assigned To"
    )
    # Applicant/User Information
    applicant_name = models.CharField(max_length=255, verbose_name="Applicant Name", blank=True, null=True)
    applicant_phone = models.CharField(max_length=20, verbose_name="Phone Number", blank=True, null=True)
    applicant_whatsapp = models.CharField(max_length=20, verbose_name="WhatsApp Number", blank=True, null=True)
    applicant_email = models.EmailField(verbose_name="Email", blank=True, null=True)
    applicant_address = models.TextField(verbose_name="Address", blank=True, null=True)
    business_name = models.CharField(max_length=255, verbose_name="Business Name")
    business_type = models.CharField(max_length=50, choices=BUSINESS_TYPE_CHOICES, verbose_name="Business Type")
    pan_number = models.CharField(max_length=10, verbose_name="PAN Number", blank=True)
    gst_number = models.CharField(max_length=15, verbose_name="GST Number", blank=True)
    business_address = models.TextField(verbose_name="Business Address")
    bank_account_details = models.TextField(verbose_name="Bank Account Details", blank=True)
    number_of_employees = models.PositiveIntegerField(verbose_name="Number of Employees", null=True, blank=True)
    business_start_date = models.DateField(verbose_name="Business Start Date", null=True, blank=True)
    monthly_salary_details = models.TextField(verbose_name="Monthly Salary Details", blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    documents = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Professional Tax Registration"
        verbose_name_plural = "Professional Tax Registrations"

    def __str__(self):
        return f"{self.business_name} - {self.business_type}"

    def get_status_badge_class(self):
        status_classes = {
            'draft': 'bg-secondary text-dark',
            'pending': 'bg-warning text-dark',
            'ready': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'approved': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary text-dark')


class IECRegistration(models.Model):
    """Stores IEC (Import Export Code) Registration submissions."""

    BUSINESS_TYPE_CHOICES = [
        ('Proprietorship', 'Proprietorship'),
        ('Partnership', 'Partnership'),
        ('Company', 'Company'),
        ('LLP', 'LLP'),
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
        related_name='iec_registrations'
    )
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_iec_records',
        verbose_name="Assigned To"
    )
    # Applicant/User Information
    applicant_name = models.CharField(max_length=255, verbose_name="Applicant Name", blank=True, null=True)
    applicant_phone = models.CharField(max_length=20, verbose_name="Phone Number", blank=True, null=True)
    applicant_whatsapp = models.CharField(max_length=20, verbose_name="WhatsApp Number", blank=True, null=True)
    applicant_email = models.EmailField(verbose_name="Email", blank=True, null=True)
    applicant_address = models.TextField(verbose_name="Address", blank=True, null=True)
    firm_name = models.CharField(max_length=255, verbose_name="Firm/Company Name")
    pan_number = models.CharField(max_length=10, verbose_name="PAN Number")
    business_type = models.CharField(max_length=50, choices=BUSINESS_TYPE_CHOICES, verbose_name="Business Type")
    incorporation_date = models.DateField(verbose_name="Incorporation/Establishment Date", null=True, blank=True)
    bank_account_details = models.TextField(verbose_name="Bank Account Details", blank=True)
    directors_partners_details = models.TextField(verbose_name="Directors/Partners Details", blank=True)
    branch_offices = models.TextField(verbose_name="Branch Offices Details", blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    documents = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "IEC Registration"
        verbose_name_plural = "IEC Registrations"

    def __str__(self):
        return f"{self.firm_name} - {self.pan_number}"

    def get_status_badge_class(self):
        status_classes = {
            'draft': 'bg-secondary text-dark',
            'pending': 'bg-warning text-dark',
            'ready': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'approved': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary text-dark')


class ICEGateRegistration(models.Model):
    """Stores ICE Gate Registration submissions."""

    USER_ROLE_CHOICES = [
        ('Shipping Agent', 'Shipping Agent'),
        ('Custom Broker', 'Custom Broker'),
        ('Importer/Exporter', 'Importer/Exporter'),
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
        related_name='icegate_registrations'
    )
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_icegate_records',
        verbose_name="Assigned To"
    )
    # Applicant/User Information
    applicant_name = models.CharField(max_length=255, verbose_name="Applicant Name", blank=True, null=True)
    applicant_phone = models.CharField(max_length=20, verbose_name="Phone Number", blank=True, null=True)
    applicant_whatsapp = models.CharField(max_length=20, verbose_name="WhatsApp Number", blank=True, null=True)
    applicant_email = models.EmailField(verbose_name="Email", blank=True, null=True)
    applicant_address = models.TextField(verbose_name="Address", blank=True, null=True)
    company_name = models.CharField(max_length=255, verbose_name="Company Name")
    pan_number = models.CharField(max_length=10, verbose_name="PAN Number")
    iec_number = models.CharField(max_length=10, verbose_name="IEC Number", blank=True)
    user_role = models.CharField(max_length=50, choices=USER_ROLE_CHOICES, verbose_name="User Role")
    authorized_person_name = models.CharField(max_length=255, verbose_name="Authorized Person Name", blank=True)
    authorized_person_details = models.TextField(verbose_name="Authorized Person Details", blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    documents = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "ICE Gate Registration"
        verbose_name_plural = "ICE Gate Registrations"

    def __str__(self):
        return f"{self.company_name} - {self.user_role}"

    def get_status_badge_class(self):
        status_classes = {
            'draft': 'bg-secondary text-dark',
            'pending': 'bg-warning text-dark',
            'ready': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'approved': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary text-dark')


class TradeLicenseRegistration(models.Model):
    """Stores Trade License Registration submissions."""

    BUSINESS_TYPE_CHOICES = [
        ('Proprietorship', 'Proprietorship'),
        ('Partnership', 'Partnership'),
        ('Company', 'Company'),
        ('LLP', 'LLP'),
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
        related_name='trade_license_registrations'
    )
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_trade_license_records',
        verbose_name="Assigned To"
    )
    # Applicant/User Information
    applicant_name = models.CharField(max_length=255, verbose_name="Applicant Name", blank=True, null=True)
    applicant_phone = models.CharField(max_length=20, verbose_name="Phone Number", blank=True, null=True)
    applicant_whatsapp = models.CharField(max_length=20, verbose_name="WhatsApp Number", blank=True, null=True)
    applicant_email = models.EmailField(verbose_name="Email", blank=True, null=True)
    applicant_address = models.TextField(verbose_name="Address", blank=True, null=True)
    business_name = models.CharField(max_length=255, verbose_name="Business Name")
    business_type = models.CharField(max_length=50, choices=BUSINESS_TYPE_CHOICES, verbose_name="Business Type")
    business_address = models.TextField(verbose_name="Business Address")
    pan_number = models.CharField(max_length=10, verbose_name="PAN Number", blank=True)
    gst_number = models.CharField(max_length=15, verbose_name="GST Number", blank=True)
    number_of_employees = models.PositiveIntegerField(verbose_name="Number of Employees", null=True, blank=True)
    business_start_date = models.DateField(verbose_name="Business Start Date", null=True, blank=True)
    municipal_area = models.CharField(max_length=255, verbose_name="Municipal Area", blank=True)
    required_permissions = models.TextField(verbose_name="Required Permissions", blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    documents = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Trade License Registration"
        verbose_name_plural = "Trade License Registrations"

    def __str__(self):
        return f"{self.business_name} - {self.business_type}"

    def get_status_badge_class(self):
        status_classes = {
            'draft': 'bg-secondary text-dark',
            'pending': 'bg-warning text-dark',
            'ready': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'approved': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary text-dark')


class DSCRegistration(models.Model):
    """Stores DSC (Digital Signature Certificate) Registration submissions."""

    DSC_TYPE_CHOICES = [
        ('Class 2', 'Class 2'),
        ('Class 3', 'Class 3'),
    ]

    ORGANISATION_TYPE_CHOICES = [
        ('Individual', 'Individual'),
        ('Private Limited', 'Private Limited'),
        ('Public Limited', 'Public Limited'),
        ('LLP', 'LLP'),
        ('Partnership', 'Partnership'),
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
        related_name='dsc_registrations'
    )
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_dsc_records',
        verbose_name="Assigned To"
    )
    # Applicant/User Information
    applicant_name = models.CharField(max_length=255, verbose_name="Applicant Name", blank=True, null=True)
    applicant_phone = models.CharField(max_length=20, verbose_name="Phone Number", blank=True, null=True)
    applicant_whatsapp = models.CharField(max_length=20, verbose_name="WhatsApp Number", blank=True, null=True)
    applicant_email = models.EmailField(verbose_name="Email", blank=True, null=True)
    applicant_address = models.TextField(verbose_name="Address", blank=True, null=True)
    pan_number = models.CharField(max_length=10, verbose_name="PAN Number")
    aadhaar_number = models.CharField(max_length=12, verbose_name="Aadhaar Number", blank=True)
    organisation_name = models.CharField(max_length=255, verbose_name="Organisation Name", blank=True)
    organisation_type = models.CharField(max_length=50, choices=ORGANISATION_TYPE_CHOICES, verbose_name="Organisation Type", blank=True)
    organisation_address = models.TextField(verbose_name="Organisation Address", blank=True)
    dsc_type = models.CharField(max_length=20, choices=DSC_TYPE_CHOICES, verbose_name="DSC Type")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    documents = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "DSC Registration"
        verbose_name_plural = "DSC Registrations"

    def __str__(self):
        return f"{self.applicant_name or 'N/A'} - {self.dsc_type}"

    def get_status_badge_class(self):
        status_classes = {
            'draft': 'bg-secondary text-dark',
            'pending': 'bg-warning text-dark',
            'ready': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'approved': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary text-dark')


class CompanyNameChange(models.Model):
    """Stores Company Name Change submissions."""

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
        related_name='company_name_changes'
    )
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_company_name_change_records',
        verbose_name="Assigned To"
    )
    # Applicant/User Information
    applicant_name = models.CharField(max_length=255, verbose_name="Applicant Name", blank=True, null=True)
    applicant_phone = models.CharField(max_length=20, verbose_name="Phone Number", blank=True, null=True)
    applicant_whatsapp = models.CharField(max_length=20, verbose_name="WhatsApp Number", blank=True, null=True)
    applicant_email = models.EmailField(verbose_name="Email", blank=True, null=True)
    applicant_address = models.TextField(verbose_name="Address", blank=True, null=True)
    current_company_name = models.CharField(max_length=255, verbose_name="Current Company Name")
    cin_number = models.CharField(max_length=25, verbose_name="CIN Number")
    proposed_new_name = models.CharField(max_length=255, verbose_name="Proposed New Name")
    reason_for_change = models.TextField(verbose_name="Reason for Name Change", blank=True)
    board_meeting_date = models.DateField(verbose_name="Board Meeting Date", null=True, blank=True)
    registered_office_address = models.TextField(verbose_name="Registered Office Address", blank=True)
    directors_details = models.TextField(verbose_name="Directors Details", blank=True)
    shareholders_details = models.TextField(verbose_name="Shareholders Details", blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    documents = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Company Name Change"
        verbose_name_plural = "Company Name Changes"

    def __str__(self):
        return f"{self.current_company_name} -> {self.proposed_new_name}"

    def get_status_badge_class(self):
        status_classes = {
            'draft': 'bg-secondary text-dark',
            'pending': 'bg-warning text-dark',
            'ready': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'approved': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary text-dark')


class DirectorChange(models.Model):
    """Stores Director Change submissions."""

    CHANGE_TYPE_CHOICES = [
        ('Appointment', 'Appointment'),
        ('Resignation', 'Resignation'),
        ('Removal', 'Removal'),
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
        related_name='director_changes'
    )
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_director_change_records',
        verbose_name="Assigned To"
    )
    # Applicant/User Information
    applicant_name = models.CharField(max_length=255, verbose_name="Applicant Name", blank=True, null=True)
    applicant_phone = models.CharField(max_length=20, verbose_name="Phone Number", blank=True, null=True)
    applicant_whatsapp = models.CharField(max_length=20, verbose_name="WhatsApp Number", blank=True, null=True)
    applicant_email = models.EmailField(verbose_name="Email", blank=True, null=True)
    applicant_address = models.TextField(verbose_name="Address", blank=True, null=True)
    company_name = models.CharField(max_length=255, verbose_name="Company Name")
    cin_number = models.CharField(max_length=25, verbose_name="CIN Number")
    change_type = models.CharField(max_length=50, choices=CHANGE_TYPE_CHOICES, verbose_name="Change Type")
    new_director_name = models.CharField(max_length=255, verbose_name="New Director Name", blank=True)
    new_director_din = models.CharField(max_length=10, verbose_name="New Director DIN", blank=True)
    new_director_pan = models.CharField(max_length=10, verbose_name="New Director PAN", blank=True)
    new_director_aadhaar = models.CharField(max_length=12, verbose_name="New Director Aadhaar", blank=True)
    new_director_address = models.TextField(verbose_name="New Director Address", blank=True)
    new_director_email = models.EmailField(verbose_name="New Director Email", blank=True)
    new_director_mobile = models.CharField(max_length=20, verbose_name="New Director Mobile", blank=True)
    appointment_date = models.DateField(verbose_name="Appointment Date", null=True, blank=True)
    existing_directors_details = models.TextField(verbose_name="Existing Directors Details", blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    documents = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Director Change"
        verbose_name_plural = "Director Changes"

    def __str__(self):
        return f"{self.company_name} - {self.change_type}"

    def get_status_badge_class(self):
        status_classes = {
            'draft': 'bg-secondary text-dark',
            'pending': 'bg-warning text-dark',
            'ready': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'approved': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary text-dark')


class CompanyClosure(models.Model):
    """Stores Company Closure submissions."""

    CLOSURE_TYPE_CHOICES = [
        ('Voluntary Winding Up', 'Voluntary Winding Up'),
        ('Compulsory Winding Up', 'Compulsory Winding Up'),
        ('Strike Off', 'Strike Off'),
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
        related_name='company_closures'
    )
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_company_closure_records',
        verbose_name="Assigned To"
    )
    # Applicant/User Information
    applicant_name = models.CharField(max_length=255, verbose_name="Applicant Name", blank=True, null=True)
    applicant_phone = models.CharField(max_length=20, verbose_name="Phone Number", blank=True, null=True)
    applicant_whatsapp = models.CharField(max_length=20, verbose_name="WhatsApp Number", blank=True, null=True)
    applicant_email = models.EmailField(verbose_name="Email", blank=True, null=True)
    applicant_address = models.TextField(verbose_name="Address", blank=True, null=True)
    company_name = models.CharField(max_length=255, verbose_name="Company Name")
    cin_number = models.CharField(max_length=25, verbose_name="CIN Number")
    closure_type = models.CharField(max_length=50, choices=CLOSURE_TYPE_CHOICES, verbose_name="Closure Type")
    reason_for_closure = models.TextField(verbose_name="Reason for Closure", blank=True)
    registered_office_address = models.TextField(verbose_name="Registered Office Address", blank=True)
    directors_details = models.TextField(verbose_name="Directors Details", blank=True)
    shareholders_details = models.TextField(verbose_name="Shareholders Details", blank=True)
    liabilities_details = models.TextField(verbose_name="Liabilities Details", blank=True)
    assets_details = models.TextField(verbose_name="Assets Details", blank=True)
    board_meeting_date = models.DateField(verbose_name="Board Meeting Date", null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    documents = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Company Closure"
        verbose_name_plural = "Company Closures"

    def __str__(self):
        return f"{self.company_name} - {self.closure_type}"

    def get_status_badge_class(self):
        status_classes = {
            'draft': 'bg-secondary text-dark',
            'pending': 'bg-warning text-dark',
            'ready': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'approved': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary text-dark')


class RCMCRegistration(models.Model):
    """Stores RCMC (Registration Cum Membership Certificate) submissions."""

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
        related_name='rcmc_registrations'
    )
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_rcmc_records',
        verbose_name="Assigned To"
    )
    # Applicant/User Information
    applicant_name = models.CharField(max_length=255, verbose_name="Applicant Name", blank=True, null=True)
    applicant_phone = models.CharField(max_length=20, verbose_name="Phone Number", blank=True, null=True)
    applicant_whatsapp = models.CharField(max_length=20, verbose_name="WhatsApp Number", blank=True, null=True)
    applicant_email = models.EmailField(verbose_name="Email", blank=True, null=True)
    applicant_address = models.TextField(verbose_name="Address", blank=True, null=True)
    firm_name = models.CharField(max_length=255, verbose_name="Firm/Company Name")
    iec_number = models.CharField(max_length=10, verbose_name="IEC Number")
    pan_number = models.CharField(max_length=10, verbose_name="PAN Number")
    registered_office_address = models.TextField(verbose_name="Registered Office Address")
    export_products_details = models.TextField(verbose_name="Export Products Details", blank=True)
    export_performance_details = models.TextField(verbose_name="Export Performance Details", blank=True)
    related_export_council_name = models.CharField(max_length=255, verbose_name="Related Export Council Name", blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    documents = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "RCMC Registration"
        verbose_name_plural = "RCMC Registrations"

    def __str__(self):
        return f"{self.firm_name} - {self.iec_number}"

    def get_status_badge_class(self):
        status_classes = {
            'draft': 'bg-secondary text-dark',
            'pending': 'bg-warning text-dark',
            'ready': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'approved': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary text-dark')


class ShopEstablishmentRegistration(models.Model):
    """Stores Shop Establishment Registration submissions (Jharkhand & West Bengal)."""

    STATE_CHOICES = [
        ('Jharkhand', 'Jharkhand'),
        ('West Bengal', 'West Bengal'),
    ]

    BUSINESS_TYPE_CHOICES = [
        ('Proprietorship', 'Proprietorship'),
        ('Partnership', 'Partnership'),
        ('Company', 'Company'),
        ('LLP', 'LLP'),
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
        related_name='shop_establishment_registrations'
    )
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_shop_establishment_records',
        verbose_name="Assigned To"
    )
    # Applicant/User Information
    applicant_name = models.CharField(max_length=255, verbose_name="Applicant Name", blank=True, null=True)
    applicant_phone = models.CharField(max_length=20, verbose_name="Phone Number", blank=True, null=True)
    applicant_whatsapp = models.CharField(max_length=20, verbose_name="WhatsApp Number", blank=True, null=True)
    applicant_email = models.EmailField(verbose_name="Email", blank=True, null=True)
    applicant_address = models.TextField(verbose_name="Address", blank=True, null=True)
    shop_establishment_name = models.CharField(max_length=255, verbose_name="Shop/Establishment Name")
    state = models.CharField(max_length=50, choices=STATE_CHOICES, verbose_name="State")
    business_type = models.CharField(max_length=50, choices=BUSINESS_TYPE_CHOICES, verbose_name="Business Type")
    business_address = models.TextField(verbose_name="Business Address")
    pan_number = models.CharField(max_length=10, verbose_name="PAN Number", blank=True)
    gst_number = models.CharField(max_length=15, verbose_name="GST Number", blank=True)
    number_of_employees = models.PositiveIntegerField(verbose_name="Number of Employees", null=True, blank=True)
    business_start_date = models.DateField(verbose_name="Business Start Date", null=True, blank=True)
    working_hours = models.CharField(max_length=100, verbose_name="Working Hours", blank=True)
    weekly_holiday = models.CharField(max_length=50, verbose_name="Weekly Holiday", blank=True)
    municipal_area = models.CharField(max_length=255, verbose_name="Municipal Area", blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    documents = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Shop Establishment Registration"
        verbose_name_plural = "Shop Establishment Registrations"

    def __str__(self):
        return f"{self.shop_establishment_name} - {self.state}"

    def get_status_badge_class(self):
        status_classes = {
            'draft': 'bg-secondary text-dark',
            'pending': 'bg-warning text-dark',
            'ready': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'approved': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary text-dark')


class DINApplication(models.Model):
    """Stores DIN (Director Identification Number) Application submissions."""
    
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
        related_name='din_applications'
    )
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_din_records',
        verbose_name="Assigned To"
    )
    applicant_name = models.CharField(max_length=255, verbose_name="Applicant Full Name")
    father_name = models.CharField(max_length=255, verbose_name="Father's Name", blank=True, null=True)
    date_of_birth = models.DateField(verbose_name="Date of Birth", null=True, blank=True)
    address = models.TextField(verbose_name="Address", blank=True, null=True)
    pan_number = models.CharField(max_length=10, verbose_name="PAN Number", blank=True, null=True)
    aadhaar_number = models.CharField(max_length=12, verbose_name="Aadhaar Number", blank=True, null=True)
    email = models.EmailField(verbose_name="Email", blank=True, null=True)
    phone = models.CharField(max_length=20, verbose_name="Phone Number", blank=True, null=True)
    whatsapp = models.CharField(max_length=20, verbose_name="WhatsApp Number", blank=True, null=True)
    photograph = models.FileField(upload_to='din/photos/', blank=True, null=True, verbose_name="Photograph")
    signature = models.FileField(upload_to='din/signatures/', blank=True, null=True, verbose_name="Signature")
    identity_proof = models.FileField(upload_to='din/identity/', blank=True, null=True, verbose_name="Identity Proof")
    address_proof = models.FileField(upload_to='din/address/', blank=True, null=True, verbose_name="Address Proof")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    documents = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "DIN Application"
        verbose_name_plural = "DIN Applications"
    
    def __str__(self):
        return f"{self.applicant_name} - DIN Application"
    
    def get_status_badge_class(self):
        status_classes = {
            'draft': 'bg-secondary text-dark',
            'pending': 'bg-warning text-dark',
            'ready': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'approved': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary text-dark')


class GSTRegistration(models.Model):
    """Stores GST Registration submissions."""
    
    BUSINESS_TYPE_CHOICES = [
        ('Proprietorship', 'Proprietorship'),
        ('Partnership', 'Partnership'),
        ('Private Limited', 'Private Limited'),
        ('Public Limited', 'Public Limited'),
        ('LLP', 'LLP'),
        ('HUF', 'HUF'),
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
        related_name='gst_registrations'
    )
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_gst_reg_records',
        verbose_name="Assigned To"
    )
    legal_entity_name = models.CharField(max_length=255, verbose_name="Legal Entity Name")
    trade_name = models.CharField(max_length=255, verbose_name="Trade Name", blank=True, null=True)
    business_type = models.CharField(max_length=50, choices=BUSINESS_TYPE_CHOICES, verbose_name="Business Type")
    pan_number = models.CharField(max_length=10, verbose_name="PAN Number")
    aadhaar_number = models.CharField(max_length=12, verbose_name="Aadhaar Number", blank=True, null=True)
    principal_place_address = models.TextField(verbose_name="Principal Place of Business Address")
    additional_places = models.TextField(verbose_name="Additional Business Places", blank=True, null=True)
    bank_account_number = models.CharField(max_length=50, verbose_name="Bank Account Number", blank=True, null=True)
    bank_ifsc = models.CharField(max_length=11, verbose_name="Bank IFSC Code", blank=True, null=True)
    bank_name = models.CharField(max_length=255, verbose_name="Bank Name", blank=True, null=True)
    authorized_signatory_name = models.CharField(max_length=255, verbose_name="Authorized Signatory Name", blank=True, null=True)
    authorized_signatory_designation = models.CharField(max_length=100, verbose_name="Designation", blank=True, null=True)
    nature_of_business = models.TextField(verbose_name="Nature of Business (Goods/Services)", blank=True, null=True)
    email = models.EmailField(verbose_name="Email", blank=True, null=True)
    phone = models.CharField(max_length=20, verbose_name="Phone Number", blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    documents = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "GST Registration"
        verbose_name_plural = "GST Registrations"
    
    def __str__(self):
        return f"{self.legal_entity_name} - GST Registration"
    
    def get_status_badge_class(self):
        status_classes = {
            'draft': 'bg-secondary text-dark',
            'pending': 'bg-warning text-dark',
            'ready': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'approved': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary text-dark')


class GSTFiling(models.Model):
    """Stores GST Filing submissions."""
    
    RETURN_TYPE_CHOICES = [
        ('GSTR-1', 'GSTR-1 (Outward Supplies)'),
        ('GSTR-3B', 'GSTR-3B (Monthly Return)'),
        ('GSTR-9', 'GSTR-9 (Annual Return)'),
        ('GSTR-9C', 'GSTR-9C (Reconciliation Statement)'),
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
        related_name='gst_filings'
    )
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_gst_filing_records',
        verbose_name="Assigned To"
    )
    gstin_number = models.CharField(max_length=15, verbose_name="GSTIN Number")
    return_type = models.CharField(max_length=50, choices=RETURN_TYPE_CHOICES, verbose_name="Return Type")
    return_period = models.CharField(max_length=20, verbose_name="Return Period (e.g., 04-2024)", blank=True, null=True)
    total_sales = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Total Sales", null=True, blank=True)
    total_purchases = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Total Purchases", null=True, blank=True)
    output_tax = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Output Tax", null=True, blank=True)
    input_tax_credit = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Input Tax Credit", null=True, blank=True)
    net_tax_payable = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Net Tax Payable", null=True, blank=True)
    payment_details = models.TextField(verbose_name="Payment Details", blank=True, null=True)
    filing_date = models.DateField(verbose_name="Filing Date", null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    documents = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "GST Filing"
        verbose_name_plural = "GST Filings"
    
    def __str__(self):
        return f"{self.gstin_number} - {self.return_type}"
    
    def get_status_badge_class(self):
        status_classes = {
            'draft': 'bg-secondary text-dark',
            'pending': 'bg-warning text-dark',
            'ready': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'approved': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary text-dark')


class CompanyComplianceROCLLP(models.Model):
    """Stores Company Compliance (ROC) LLP submissions."""
    
    FILING_TYPE_CHOICES = [
        ('Annual Return', 'Annual Return'),
        ('Financial Statement', 'Financial Statement'),
        ('Form 11', 'Form 11 (Annual Return)'),
        ('Form 8', 'Form 8 (Statement of Account & Solvency)'),
        ('Form 3', 'Form 3 (Change in Partners)'),
        ('Form 4', 'Form 4 (Change in Partners Details)'),
        ('Form 5', 'Form 5 (Notice of Change of Name)'),
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
        related_name='roc_llp_compliances'
    )
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_roc_llp_records',
        verbose_name="Assigned To"
    )
    company_name = models.CharField(max_length=255, verbose_name="Company/LLP Name")
    registration_number = models.CharField(max_length=50, verbose_name="CIN/LLPIN Number", blank=True, null=True)
    filing_type = models.CharField(max_length=100, choices=FILING_TYPE_CHOICES, verbose_name="Filing Type")
    financial_year = models.CharField(max_length=20, verbose_name="Financial Year", blank=True, null=True)
    due_date = models.DateField(verbose_name="Due Date", null=True, blank=True)
    filing_date = models.DateField(verbose_name="Filing Date", null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    documents = models.JSONField(default=list, blank=True)
    notes = models.TextField(verbose_name="Notes", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Company Compliance (ROC) LLP"
        verbose_name_plural = "Company Compliance (ROC) LLP"
    
    def __str__(self):
        return f"{self.company_name} - {self.filing_type}"
    
    def get_status_badge_class(self):
        status_classes = {
            'draft': 'bg-secondary text-dark',
            'pending': 'bg-warning text-dark',
            'ready': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'approved': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary text-dark')


class AuthorizedPaidupCapitalIncrease(models.Model):
    """Stores Authorized Capital & Paid-up Capital Increase submissions."""
    
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
        related_name='capital_increases'
    )
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_capital_increase_records',
        verbose_name="Assigned To"
    )
    company_name = models.CharField(max_length=255, verbose_name="Company Name")
    cin_number = models.CharField(max_length=21, verbose_name="CIN Number", blank=True, null=True)
    current_authorized_capital = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Current Authorized Capital", null=True, blank=True)
    new_authorized_capital = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="New Authorized Capital", null=True, blank=True)
    current_paidup_capital = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Current Paid-up Capital", null=True, blank=True)
    new_paidup_capital = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="New Paid-up Capital", null=True, blank=True)
    reason_for_increase = models.TextField(verbose_name="Reason for Increase", blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    documents = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Authorized & Paid-up Capital Increase"
        verbose_name_plural = "Authorized & Paid-up Capital Increases"
    
    def __str__(self):
        return f"{self.company_name} - Capital Increase"
    
    def get_status_badge_class(self):
        status_classes = {
            'draft': 'bg-secondary text-dark',
            'pending': 'bg-warning text-dark',
            'ready': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'approved': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary text-dark')


class DINKYC(models.Model):
    """Stores DIN KYC submissions."""
    
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
        related_name='din_kyc_submissions'
    )
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_din_kyc_records',
        verbose_name="Assigned To"
    )
    din_number = models.CharField(max_length=8, verbose_name="DIN Number")
    director_name = models.CharField(max_length=255, verbose_name="Director Name")
    pan_number = models.CharField(max_length=10, verbose_name="PAN Number", blank=True, null=True)
    aadhaar_number = models.CharField(max_length=12, verbose_name="Aadhaar Number", blank=True, null=True)
    email = models.EmailField(verbose_name="Email", blank=True, null=True)
    phone = models.CharField(max_length=20, verbose_name="Phone Number", blank=True, null=True)
    address = models.TextField(verbose_name="Current Address", blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    documents = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "DIN KYC"
        verbose_name_plural = "DIN KYC"
    
    def __str__(self):
        return f"{self.director_name} - DIN: {self.din_number}"
    
    def get_status_badge_class(self):
        status_classes = {
            'draft': 'bg-secondary text-dark',
            'pending': 'bg-warning text-dark',
            'ready': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'approved': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary text-dark')


class NGODarpan(models.Model):
    """Stores NGO Darpan Registration submissions."""
    
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
        related_name='ngo_darpan_registrations'
    )
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_ngo_darpan_records',
        verbose_name="Assigned To"
    )
    organization_name = models.CharField(max_length=255, verbose_name="Organization Name")
    registration_number = models.CharField(max_length=50, verbose_name="Registration Number", blank=True, null=True)
    registration_type = models.CharField(max_length=100, verbose_name="Registration Type (Trust/Society/Section 8)", blank=True, null=True)
    registration_date = models.DateField(verbose_name="Registration Date", null=True, blank=True)
    address = models.TextField(verbose_name="Registered Address", blank=True, null=True)
    contact_person = models.CharField(max_length=255, verbose_name="Contact Person", blank=True, null=True)
    email = models.EmailField(verbose_name="Email", blank=True, null=True)
    phone = models.CharField(max_length=20, verbose_name="Phone Number", blank=True, null=True)
    objectives = models.TextField(verbose_name="Objectives of Organization", blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    documents = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "NGO Darpan Registration"
        verbose_name_plural = "NGO Darpan Registrations"
    
    def __str__(self):
        return f"{self.organization_name} - NGO Darpan"
    
    def get_status_badge_class(self):
        status_classes = {
            'draft': 'bg-secondary text-dark',
            'pending': 'bg-warning text-dark',
            'ready': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'approved': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary text-dark')


class ITRFiling(models.Model):
    """Stores ITR Filing submissions."""
    
    ITR_TYPE_CHOICES = [
        ('ITR-1', 'ITR-1 (Sahaj)'),
        ('ITR-2', 'ITR-2 (For Individuals)'),
        ('ITR-3', 'ITR-3 (For Business/Profession)'),
        ('ITR-4', 'ITR-4 (Sugam)'),
        ('ITR-5', 'ITR-5 (For Firms/LLPs)'),
        ('ITR-6', 'ITR-6 (For Companies)'),
        ('ITR-7', 'ITR-7 (For Trusts)'),
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
        related_name='itr_filings'
    )
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_itr_filing_records',
        verbose_name="Assigned To"
    )
    pan_number = models.CharField(max_length=10, verbose_name="PAN Number")
    assessment_year = models.CharField(max_length=10, verbose_name="Assessment Year (e.g., 2024-25)", blank=True, null=True)
    itr_type = models.CharField(max_length=20, choices=ITR_TYPE_CHOICES, verbose_name="ITR Type")
    total_income = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Total Income", null=True, blank=True)
    total_deductions = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Total Deductions", null=True, blank=True)
    taxable_income = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Taxable Income", null=True, blank=True)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Tax Amount", null=True, blank=True)
    advance_tax_paid = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Advance Tax Paid", null=True, blank=True)
    tds_amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="TDS Amount", null=True, blank=True)
    refund_or_balance_tax = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Refund/Balance Tax", null=True, blank=True)
    filing_date = models.DateField(verbose_name="Filing Date", null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    documents = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "ITR Filing"
        verbose_name_plural = "ITR Filings"
    
    def __str__(self):
        return f"{self.pan_number} - {self.assessment_year}"
    
    def get_status_badge_class(self):
        status_classes = {
            'draft': 'bg-secondary text-dark',
            'pending': 'bg-warning text-dark',
            'ready': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'approved': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary text-dark')


class INC20ABusinessCommencement(models.Model):
    """Stores INC-20A (Business Commencement) submissions."""
    
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
        related_name='inc20a_submissions'
    )
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_inc20a_records',
        verbose_name="Assigned To"
    )
    company_name = models.CharField(max_length=255, verbose_name="Company Name")
    cin_number = models.CharField(max_length=21, verbose_name="CIN Number", blank=True, null=True)
    incorporation_date = models.DateField(verbose_name="Date of Incorporation", null=True, blank=True)
    commencement_date = models.DateField(verbose_name="Date of Commencement of Business", null=True, blank=True)
    business_activity = models.TextField(verbose_name="Business Activity Description", blank=True, null=True)
    registered_office_address = models.TextField(verbose_name="Registered Office Address", blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    documents = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "INC-20A (Business Commencement)"
        verbose_name_plural = "INC-20A (Business Commencement)"
    
    def __str__(self):
        return f"{self.company_name} - INC-20A"
    
    def get_status_badge_class(self):
        status_classes = {
            'draft': 'bg-secondary text-dark',
            'pending': 'bg-warning text-dark',
            'ready': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'approved': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary text-dark')


class GEMRegistration(models.Model):
    """Stores GEM (Government e-Marketplace) Registration submissions."""
    
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
        related_name='gem_registrations'
    )
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_gem_records',
        verbose_name="Assigned To"
    )
    business_name = models.CharField(max_length=255, verbose_name="Business Name")
    business_type = models.CharField(max_length=100, verbose_name="Business Type (Proprietorship/Partnership/Company)", blank=True, null=True)
    pan_number = models.CharField(max_length=10, verbose_name="PAN Number", blank=True, null=True)
    gstin_number = models.CharField(max_length=15, verbose_name="GSTIN Number", blank=True, null=True)
    address = models.TextField(verbose_name="Business Address", blank=True, null=True)
    contact_person = models.CharField(max_length=255, verbose_name="Contact Person", blank=True, null=True)
    email = models.EmailField(verbose_name="Email", blank=True, null=True)
    phone = models.CharField(max_length=20, verbose_name="Phone Number", blank=True, null=True)
    products_services = models.TextField(verbose_name="Products/Services to be Listed", blank=True, null=True)
    bank_account_number = models.CharField(max_length=50, verbose_name="Bank Account Number", blank=True, null=True)
    bank_ifsc = models.CharField(max_length=11, verbose_name="Bank IFSC Code", blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    documents = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "GEM Registration"
        verbose_name_plural = "GEM Registrations"
    
    def __str__(self):
        return f"{self.business_name} - GEM Registration"
    
    def get_status_badge_class(self):
        status_classes = {
            'draft': 'bg-secondary text-dark',
            'pending': 'bg-warning text-dark',
            'ready': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'approved': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary text-dark')


class StartupIndiaSeedFunding(models.Model):
    """Stores Start-up INDIA – SEED FUNDING submissions."""
    
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
        related_name='startup_seed_funding_submissions'
    )
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_seed_funding_records',
        verbose_name="Assigned To"
    )
    startup_name = models.CharField(max_length=255, verbose_name="Startup Name")
    cin_number = models.CharField(max_length=21, verbose_name="CIN Number", blank=True, null=True)
    startup_india_registration_number = models.CharField(max_length=50, verbose_name="Startup India Registration Number", blank=True, null=True)
    funding_amount_requested = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Funding Amount Requested", null=True, blank=True)
    business_description = models.TextField(verbose_name="Business Description", blank=True, null=True)
    innovation_usp = models.TextField(verbose_name="Innovation/USP", blank=True, null=True)
    market_potential = models.TextField(verbose_name="Market Potential", blank=True, null=True)
    founder_details = models.TextField(verbose_name="Founder Details", blank=True, null=True)
    contact_email = models.EmailField(verbose_name="Contact Email", blank=True, null=True)
    contact_phone = models.CharField(max_length=20, verbose_name="Contact Phone", blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    documents = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Start-up INDIA – SEED FUNDING"
        verbose_name_plural = "Start-up INDIA – SEED FUNDING"
    
    def __str__(self):
        return f"{self.startup_name} - Seed Funding"
    
    def get_status_badge_class(self):
        status_classes = {
            'draft': 'bg-secondary text-dark',
            'pending': 'bg-warning text-dark',
            'ready': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'approved': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary text-dark')


class CSR1NGO(models.Model):
    """Stores CSR-1 (NGO) submissions."""
    
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
        related_name='csr1_ngo_submissions'
    )
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_csr1_records',
        verbose_name="Assigned To"
    )
    ngo_name = models.CharField(max_length=255, verbose_name="NGO Name")
    registration_number = models.CharField(max_length=50, verbose_name="Registration Number", blank=True, null=True)
    registration_type = models.CharField(max_length=100, verbose_name="Registration Type (Trust/Society/Section 8)", blank=True, null=True)
    address = models.TextField(verbose_name="Registered Address", blank=True, null=True)
    contact_person = models.CharField(max_length=255, verbose_name="Contact Person", blank=True, null=True)
    email = models.EmailField(verbose_name="Email", blank=True, null=True)
    phone = models.CharField(max_length=20, verbose_name="Phone Number", blank=True, null=True)
    objectives = models.TextField(verbose_name="Objectives", blank=True, null=True)
    csr_activities = models.TextField(verbose_name="CSR Activities", blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    documents = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "CSR-1 (NGO)"
        verbose_name_plural = "CSR-1 (NGO)"
    
    def __str__(self):
        return f"{self.ngo_name} - CSR-1"
    
    def get_status_badge_class(self):
        status_classes = {
            'draft': 'bg-secondary text-dark',
            'pending': 'bg-warning text-dark',
            'ready': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'approved': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary text-dark')


class Registration12A80G(models.Model):
    """Stores 12A & 80G Registration submissions."""
    
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
        related_name='registration_12a_80g'
    )
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_12a_80g_records',
        verbose_name="Assigned To"
    )
    organization_name = models.CharField(max_length=255, verbose_name="Organization Name")
    registration_number = models.CharField(max_length=50, verbose_name="Registration Number", blank=True, null=True)
    registration_type = models.CharField(max_length=100, verbose_name="Registration Type (Trust/Society/Section 8)", blank=True, null=True)
    address = models.TextField(verbose_name="Registered Address", blank=True, null=True)
    contact_person = models.CharField(max_length=255, verbose_name="Contact Person", blank=True, null=True)
    email = models.EmailField(verbose_name="Email", blank=True, null=True)
    phone = models.CharField(max_length=20, verbose_name="Phone Number", blank=True, null=True)
    objectives = models.TextField(verbose_name="Objectives", blank=True, null=True)
    registration_12a_required = models.BooleanField(default=True, verbose_name="12A Registration Required")
    registration_80g_required = models.BooleanField(default=True, verbose_name="80G Registration Required")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    documents = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "12A & 80G Registration"
        verbose_name_plural = "12A & 80G Registrations"
    
    def __str__(self):
        return f"{self.organization_name} - 12A & 80G"
    
    def get_status_badge_class(self):
        status_classes = {
            'draft': 'bg-secondary text-dark',
            'pending': 'bg-warning text-dark',
            'ready': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'approved': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary text-dark')


class PartnershipRegistration(models.Model):
    """Stores Partnership Registration submissions."""
    
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
        related_name='partnership_registrations'
    )
    lead_source = models.CharField(max_length=100, default='website', verbose_name="Lead Source")
    assigned_to = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_partnership_records',
        verbose_name="Assigned To"
    )
    firm_name = models.CharField(max_length=255, verbose_name="Partnership Firm Name")
    principal_place_of_business = models.TextField(verbose_name="Principal Place of Business", blank=True, null=True)
    business_activity = models.TextField(verbose_name="Business Activity", blank=True, null=True)
    partner_details = models.TextField(verbose_name="Partner Details (Name, Address, Share)", blank=True, null=True)
    capital_contribution = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Total Capital Contribution", null=True, blank=True)
    profit_sharing_ratio = models.CharField(max_length=100, verbose_name="Profit Sharing Ratio", blank=True, null=True)
    contact_email = models.EmailField(verbose_name="Contact Email", blank=True, null=True)
    contact_phone = models.CharField(max_length=20, verbose_name="Contact Phone", blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    documents = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Partnership Registration"
        verbose_name_plural = "Partnership Registrations"
    
    def __str__(self):
        return f"{self.firm_name} - Partnership"
    
    def get_status_badge_class(self):
        status_classes = {
            'draft': 'bg-secondary text-dark',
            'pending': 'bg-warning text-dark',
            'ready': 'bg-info text-dark',
            'submitted': 'bg-primary text-dark',
            'approved': 'bg-success text-dark',
        }
        return status_classes.get(self.status, 'bg-secondary text-dark')


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
    
    # Authentication
    password = models.CharField(max_length=128, blank=True, null=True, verbose_name="Password", help_text="Hashed password. If set, user must login with password instead of phone.")
    
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


class CompanyBankAccount(models.Model):
    """Company bank account details for invoices"""
    account_name = models.CharField(max_length=255, verbose_name="Account Name")
    bank_name = models.CharField(max_length=255, verbose_name="Bank Name")
    account_number = models.CharField(max_length=50, verbose_name="Account Number")
    ifsc = models.CharField(max_length=20, verbose_name="IFSC Code")
    branch = models.CharField(max_length=255, blank=True, null=True, verbose_name="Branch")
    is_active = models.BooleanField(default=True, verbose_name="Active")
    is_default = models.BooleanField(default=False, verbose_name="Default Account")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Company Bank Account"
        verbose_name_plural = "Company Bank Accounts"
        ordering = ['-is_default', '-created_at']
    
    def __str__(self):
        return f"{self.bank_name} - {self.account_number}"