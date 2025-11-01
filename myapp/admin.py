from django.contrib import admin
from .models import Lead, LeaveRequest, Document, Quote, ClientOnboarding

# Register your models here.

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'company', 'source', 'priority', 'owner', 'created_at')
    list_filter = ('priority', 'source', 'created_at')
    search_fields = ('name', 'email', 'company', 'phone')
    date_hierarchy = 'created_at'

@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ('applicant_name', 'leave_type', 'start_date', 'end_date', 'days', 'status')
    list_filter = ('status', 'leave_type', 'start_date')
    search_fields = ('applicant_name', 'reason')

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('original_name', 'category', 'privacy', 'size_bytes', 'uploaded_at')
    list_filter = ('category', 'privacy', 'uploaded_at')
    search_fields = ('original_name', 'description')

@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ('quote_number', 'client_name', 'company', 'status', 'total', 'valid_until', 'created_at')
    list_filter = ('status', 'currency', 'created_at', 'valid_until')
    search_fields = ('quote_number', 'client_name', 'company', 'email')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at')

@admin.register(ClientOnboarding)
class ClientOnboardingAdmin(admin.ModelAdmin):
    list_display = ('client_name', 'project_name', 'project_cost', 'assigned_engineer', 'status', 'created_at')
    list_filter = ('status', 'duration_unit', 'created_at')
    search_fields = ('client_name', 'company_name', 'project_name', 'assigned_engineer')
    date_hierarchy = 'created_at'
