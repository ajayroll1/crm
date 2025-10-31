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
