from django.contrib import admin
from .models import (
    Lead,
    LeaveRequest,
    Document,
    Quote,
    ClientOnboarding,
    ROCComplianceRecord,
    GSTFilingRecord,
    ITRFilingRecord,
    BookkeepingChecklistRecord,
    TDSComplianceRecord,
)

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


@admin.register(ROCComplianceRecord)
class ROCComplianceRecordAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'financial_year', 'agm_date', 'compliance_period', 'user', 'created_at')
    list_filter = ('compliance_period', 'digital_signature', 'financial_year', 'created_at')
    search_fields = ('company_name', 'cin_llpin')
    date_hierarchy = 'created_at'


@admin.register(GSTFilingRecord)
class GSTFilingRecordAdmin(admin.ModelAdmin):
    list_display = ('gstin', 'return_type', 'return_period', 'filing_scheme', 'user', 'created_at')
    list_filter = ('return_type', 'filing_scheme', 'created_at')
    search_fields = ('gstin',)
    date_hierarchy = 'created_at'


@admin.register(ITRFilingRecord)
class ITRFilingRecordAdmin(admin.ModelAdmin):
    list_display = ('taxpayer_name', 'pan', 'assessment_year', 'return_form', 'client_category', 'user', 'created_at')
    list_filter = ('assessment_year', 'return_form', 'client_category', 'created_at')
    search_fields = ('taxpayer_name', 'pan')
    date_hierarchy = 'created_at'


@admin.register(BookkeepingChecklistRecord)
class BookkeepingChecklistRecordAdmin(admin.ModelAdmin):
    list_display = ('prepared_by', 'closing_date', 'cash_book_updated', 'bank_entries_reconciled', 'inventory_updated', 'user', 'created_at')
    list_filter = ('cash_book_updated', 'bank_entries_reconciled', 'inventory_updated', 'closing_date', 'created_at')
    search_fields = ('prepared_by',)
    date_hierarchy = 'created_at'


@admin.register(TDSComplianceRecord)
class TDSComplianceRecordAdmin(admin.ModelAdmin):
    list_display = ('deductor_tan', 'section', 'deduction_month', 'tds_deducted', 'user', 'created_at')
    list_filter = ('section', 'deduction_month', 'created_at')
    search_fields = ('deductor_tan', 'challan_number')
    date_hierarchy = 'created_at'
