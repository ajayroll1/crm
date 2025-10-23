from django import forms
from django.core.exceptions import ValidationError
from .models import Lead

class LeadForm(forms.ModelForm):
    """
    Lead form with custom validation
    यह form lead data को validate करता है और save करता है
    """
    
    class Meta:
        model = Lead
        fields = [
            'name', 'email', 'phone', 'company', 'source', 'priority', 
            'owner', 'use_case', 'next_action', 'due_date', 'due_time',
            'website', 'industry', 'city', 'country', 'budget', 
            'timeline', 'tags', 'notes'
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
