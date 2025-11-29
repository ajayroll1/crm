from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, Http404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth import logout as auth_logout, login as auth_login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.files.storage import default_storage
from django.contrib.staticfiles import finders
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.urls import reverse
from datetime import datetime, date
from collections import defaultdict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json
import os
import uuid
import calendar
import re
from io import BytesIO
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

def _store_uploaded_files(files, subdir):
    """
    Save uploaded files under media/accounts/<subdir>/YYYY/MM/DD/ and return stored paths list.
    """
    saved_paths = []
    if not files:
        return saved_paths

    date_path = timezone.now().strftime('%Y/%m/%d')
    for uploaded_file in files:
        if not uploaded_file:
            continue
        filename = f"{uuid.uuid4().hex}_{uploaded_file.name}"
        storage_path = os.path.join('accounts', subdir, date_path, filename)
        saved_path = default_storage.save(storage_path, uploaded_file)
        saved_paths.append(saved_path)
    return saved_paths


def generate_invoice_number_for_date(invoice_date):
    """
    Generate invoice number: SA + DD + WEEKDAY(3) + YYYY + counter(2 digits)
    Counter increments per prefix to keep numbers unique.
    """
    if not invoice_date:
        invoice_date = timezone.localdate()
    day_str = f"{invoice_date.day:02d}"
    weekday_str = invoice_date.strftime('%a').upper()
    year_str = str(invoice_date.year)
    prefix = f"SA{day_str}{weekday_str}{year_str}"

    existing_numbers = Invoice.objects.filter(
        invoice_number__startswith=prefix
    ).values_list('invoice_number', flat=True)

    counter = 1
    pattern = re.compile(rf'^{re.escape(prefix)}(\d+)$')
    for number in existing_numbers:
        match = pattern.match(number)
        if match:
            suffix_val = int(match.group(1))
            if suffix_val >= counter:
                counter = suffix_val + 1

    return f"{prefix}{counter:02d}"
from .models import (
    Lead,
    LeaveRequest,
    Document,
    Attendance,
    Quote,
    Invoice,
    ClientOnboarding,
    Employee,
    EmployeeMessage,
    PaymentTransaction,
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
)
from .forms import (
    LeadForm,
    LeadFilterForm,
    ROCComplianceForm,
    GSTFilingForm,
    ITRFilingForm,
    BookkeepingChecklistForm,
    TDSComplianceForm,
    StartupIndiaRegistrationForm,
    FSSAILicenseForm,
    MSMEUdyamRegistrationForm,
    CompanyLLPRegistrationForm,
    FirePollutionLicenseForm,
    ISOCertificationForm,
    TrademarkFilingForm,
    TrademarkFilingComplianceForm,
    TrademarkFilingInstantForm,
    CompanyAddressChangeForm,
    MOAAlterationForm,
)
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie

SECTION_CONFIG = {
    'roc': {
        'model': ROCComplianceRecord,
        'form': ROCComplianceForm,
        'title': 'ROC Compliance',
        'success_message': 'ROC compliance record updated successfully.',
    },
    'gst': {
        'model': GSTFilingRecord,
        'form': GSTFilingForm,
        'title': 'GST Filing',
        'success_message': 'GST filing record updated successfully.',
    },
    'itr': {
        'model': ITRFilingRecord,
        'form': ITRFilingForm,
        'title': 'ITR Filing',
        'success_message': 'ITR filing record updated successfully.',
    },
    'bookkeeping': {
        'model': BookkeepingChecklistRecord,
        'form': BookkeepingChecklistForm,
        'title': 'Bookkeeping Checklist',
        'success_message': 'Bookkeeping checklist updated successfully.',
    },
    'tds': {
        'model': TDSComplianceRecord,
        'form': TDSComplianceForm,
        'title': 'TDS Compliance',
        'success_message': 'TDS compliance record updated successfully.',
    },
}

def get_company_logo_path():
    """
    Locate the company logo within static files so reportlab can embed it.
    """
    logo_relative = COMPANY_PROFILE.get('logo_path')
    if not logo_relative:
        return None
    static_path = finders.find(logo_relative)
    if static_path and os.path.exists(static_path):
        return static_path
    fallback = os.path.join(settings.BASE_DIR, 'static', logo_relative)
    return fallback if os.path.exists(fallback) else None


INDIAN_UNITS = [
    (10000000, 'Crore'),
    (100000, 'Lakh'),
    (1000, 'Thousand'),
    (100, 'Hundred'),
]

ONES = [
    '', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven',
    'Eight', 'Nine', 'Ten', 'Eleven', 'Twelve', 'Thirteen',
    'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen'
]

TENS = [
    '', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty',
    'Seventy', 'Eighty', 'Ninety'
]


def _two_digit_words(number):
    if number < 20:
        return ONES[number]
    tens, ones = divmod(number, 10)
    return TENS[tens] + (f' {ONES[ones]}' if ones else '')


def _three_digit_words(number):
    hundred, remainder = divmod(number, 100)
    words = ''
    if hundred:
        words += f"{ONES[hundred]} Hundred"
        if remainder:
            words += ' and '
    if remainder:
        words += _two_digit_words(remainder)
    return words.strip()


def amount_to_words(amount):
    """
    Convert Decimal amount into words following Indian numbering system.
    """
    if amount is None:
        return ''
    decimal_value = Decimal(amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    rupees = int(decimal_value)
    paise = int((decimal_value - rupees) * 100)

    if rupees == 0:
        rupee_words = 'Zero'
    else:
        remaining = rupees
        parts = []
        for value, label in INDIAN_UNITS:
            count, remaining = divmod(remaining, value)
            if count:
                parts.append(f"{_three_digit_words(count)} {label}")
        if remaining:
            parts.append(_three_digit_words(remaining))
        rupee_words = ' '.join(filter(None, parts))

    rupee_phrase = f"{rupee_words.strip()} Rupees"
    if paise:
        paise_words = _two_digit_words(paise) or 'Zero'
        rupee_phrase += f" and {paise_words} Paise"

    return f"{rupee_phrase} Only"

COMPANY_PROFILE = {
    'name': 'Sujata Associates Consultancy Pvt Ltd',
    'tagline': 'Business Consulting & Compliance Partner',
    'gstin': '19AAZCS9337C1ZM',
    'pan': 'AAZCS9337C',
    'address_lines': [
        '4, Fairlie Place, HMP House, 5th Floor, Kolkata 700 001 (W.B.)',
        'Email: info@sujataassociates.com    Ph: 90380013',
        'State Name: West Bengal, State Code: 19'
    ],
    'logo_path': 'images/Logo-new-final.png',
    'bank_details': {
        'account_name': 'Sujata Associates Consultancy Pvt Ltd',
        'bank_name': 'Bank of Maharashtra',
        'account_number': '60476131014',
        'ifsc': 'MAHB0001272',
        'branch': 'Bidhan Nagar, Kolkata'
    }
}


def _get_section_config(section):
    config = SECTION_CONFIG.get(section)
    if not config:
        raise Http404("Invalid section")
    return config

def home(request):
  """Home page - show login form if not authenticated, else redirect to dashboard"""
  if request.user.is_authenticated:
    # Check user role and redirect accordingly
    try:
      employee = Employee.objects.get(email=request.user.email)
      if employee.role == 'Admin':
        return redirect('dashboard')
      else:
        return redirect('employee_dashboard')
    except Employee.DoesNotExist:
      # If no employee record, check if user is staff/admin
      if request.user.is_staff:
        return redirect('dashboard')
      else:
        return redirect('employee_dashboard')
  return render(request,'pages/homepage.html')

def login_view(request):
  """Login view - authenticate user with email and password/phone based on whether password is set"""
  if request.method == 'POST':
    email = request.POST.get('email', '').strip().lower()  # Convert to lowercase for case-insensitive matching
    password_input = request.POST.get('password', '').strip()  # Can be password or phone number
    
    # Validate input
    if not email:
      messages.error(request, 'Please enter your email address.')
      return redirect('home')
    
    if not password_input:
      messages.error(request, 'Please enter your password or phone number.')
      return redirect('home')
    
    # Basic email format validation
    if '@' not in email or '.' not in email:
      messages.error(request, 'Please enter a valid email address.')
      return redirect('home')
    
    # Find Employee by email (case-insensitive)
    try:
      employee = Employee.objects.get(email__iexact=email)
    except Employee.DoesNotExist:
      messages.error(request, 'Invalid email address. Please check your email and try again.')
      return redirect('home')
    except Employee.MultipleObjectsReturned:
      # If multiple employees found (shouldn't happen), get the first one
      employee = Employee.objects.filter(email__iexact=email).first()
    
    # Check if employee is active
    if employee.status != 'active':
      messages.error(request, 'Your account has been deactivated. Please contact administrator.')
      return redirect('home')
    
    # Check if password is set in Employee model
    if employee.password and employee.password.strip():
      # Password is set - authenticate using password
      from django.contrib.auth.hashers import check_password
      if not check_password(password_input, employee.password):
        messages.error(request, 'Invalid password. Please check your password and try again.')
        return redirect('home')
      # Password is correct, proceed with login
      login_password = password_input
    else:
      # Password is not set - use phone number authentication (old method)
      if not employee.phone:
        messages.error(request, 'Your account does not have a phone number registered. Please contact administrator.')
        return redirect('home')
      
      # Verify phone number matches
      # Normalize phone numbers for comparison (remove spaces, dashes, etc.)
      employee_phone = ''.join(filter(str.isdigit, employee.phone or ''))
      input_phone = ''.join(filter(str.isdigit, password_input))
      
      if not input_phone:
        messages.error(request, 'Please enter a valid phone number.')
        return redirect('home')
      
      if employee_phone != input_phone:
        messages.error(request, 'Invalid phone number. Please check your phone number and try again.')
        return redirect('home')
      
      # Phone matches, use phone as login password
      login_password = password_input
    
    # Check if employee is active
    if employee.status != 'active':
      messages.error(request, 'Your account has been deactivated. Please contact administrator.')
      return redirect('home')
    
    # Get or create User account for this employee
    user = None
    try:
      # Try to find existing user by email (case-insensitive)
      user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
      # Create User account for Employee if it doesn't exist
      username = email.split('@')[0]  # Use email prefix as username
      # Ensure username is unique
      base_username = username
      counter = 1
      while User.objects.filter(username=username).exists():
        username = f"{base_username}{counter}"
        counter += 1
      
      try:
        # Create user with login_password (can be phone or password)
        user = User.objects.create_user(
          username=username,
          email=employee.email,  # Use employee's email from database (original case)
          password=login_password,  # Use login_password (phone or password)
          first_name=employee.first_name,
          last_name=employee.last_name,
          is_staff=(employee.role == 'Admin')
        )
      except Exception as e:
        messages.error(request, f'Error creating user account: {str(e)}. Please contact administrator.')
        return redirect('home')
    except User.MultipleObjectsReturned:
      # If multiple users found (shouldn't happen), get the first one
      user = User.objects.filter(email__iexact=email).first()
    except Exception as e:
      messages.error(request, 'An error occurred during login. Please try again or contact administrator.')
      return redirect('home')
    
    # Authenticate user
    authenticated_user = authenticate(request, username=user.username, password=login_password)
    
    if authenticated_user is not None:
      if authenticated_user.is_active:
        # Login the user
        auth_login(request, authenticated_user)
        
        # Check today's attendance status
        today = timezone.now().date()
        today_attendance = None
        
        # Try to get today's attendance record
        try:
          if employee:
            today_attendance = Attendance.objects.filter(
              employee=employee,
              date=today
            ).first()
          if not today_attendance and authenticated_user:
            today_attendance = Attendance.objects.filter(
              user=authenticated_user,
              date=today
            ).first()
        except:
          pass
        
        # Check attendance status and show message
        if today_attendance:
          if today_attendance.check_in_time and today_attendance.check_out_time:
            messages.info(request, f'Welcome back! You have already completed check-in and check-out today.')
          elif today_attendance.check_in_time:
            check_in_time = today_attendance.check_in_time.strftime('%I:%M %p')
            messages.info(request, f'Welcome back! You checked in at {check_in_time}. Don\'t forget to check out!')
          else:
            messages.info(request, f'Welcome back! Please complete your check-in.')
        else:
          messages.info(request, f'Welcome back! Please complete your check-in for today.')
        
        # Get role from Employee model
        role = employee.role or 'Employee'
        
        # Redirect based on role
        if role == 'Admin':
          messages.success(request, f'Welcome back, {employee.get_full_name()}!')
          return redirect('dashboard')
        else:
          messages.success(request, f'Welcome back, {employee.get_full_name()}!')
          return redirect('employee_dashboard')
      else:
        messages.error(request, 'Your account has been disabled.')
        return redirect('home')
    else:
      # Authentication failed - update user password (phone/password might have changed)
      if user is not None:
        user.set_password(login_password)
        user.save()
        authenticated_user = authenticate(request, username=user.username, password=login_password)
        if authenticated_user:
          auth_login(request, authenticated_user)
          
          # Check today's attendance status
          today = timezone.now().date()
          today_attendance = None
          
          # Try to get today's attendance record
          try:
            if employee:
              today_attendance = Attendance.objects.filter(
                employee=employee,
                date=today
              ).first()
            if not today_attendance and authenticated_user:
              today_attendance = Attendance.objects.filter(
                user=authenticated_user,
                date=today
              ).first()
          except:
            pass
          
          # Check attendance status and show message
          if today_attendance:
            if today_attendance.check_in_time and today_attendance.check_out_time:
              messages.info(request, f'Welcome back! You have already completed check-in and check-out today.')
            elif today_attendance.check_in_time:
              check_in_time = today_attendance.check_in_time.strftime('%I:%M %p')
              messages.info(request, f'Welcome back! You checked in at {check_in_time}. Don\'t forget to check out!')
            else:
              messages.info(request, f'Welcome back! Please complete your check-in.')
          else:
            messages.info(request, f'Welcome back! Please complete your check-in for today.')
          
          role = employee.role or 'Employee'
          if role == 'Admin':
            messages.success(request, f'Welcome back, {employee.get_full_name()}!')
            return redirect('dashboard')
          else:
            messages.success(request, f'Welcome back, {employee.get_full_name()}!')
            return redirect('employee_dashboard')
        else:
          messages.error(request, 'Authentication failed. Please try again.')
          return redirect('home')
      else:
        messages.error(request, 'User account not found. Please contact administrator.')
        return redirect('home')
  
  # If GET request, redirect to home
  return redirect('home')

def logout_view(request):
  """Logout view - logs out user and redirects to home"""
  auth_logout(request)
  messages.success(request, 'You have been logged out successfully.')
  return redirect('home')

def about(request):
  return HttpResponse('About page ')


def services(request):
  return  HttpResponse('Service page ')


def projects(request):
  return HttpResponse('Projects page')


def careers(request):
  return HttpResponse('carrers page')


def contact(request):
  return HttpResponse('Contact page ')



def quote(request):
  return HttpResponse('Get a Quote Page ')


@login_required
def dashboard(request):
  """Admin dashboard - requires login and Admin role"""
  # Check if user has Admin role
  try:
    employee = Employee.objects.get(email=request.user.email)
    if employee.role != 'Admin':
      messages.warning(request, 'You do not have permission to access this page.')
      return redirect('employee_dashboard')
  except Employee.DoesNotExist:
    # If no employee record, check if user is staff
    if not request.user.is_staff:
      messages.warning(request, 'You do not have permission to access this page.')
      return redirect('employee_dashboard')
  
  # Get current date and timezone
  now = timezone.now()
  current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
  current_date = now.date()
  
  # Calculate metrics
  # Total Leads
  total_leads = Lead.objects.filter(is_active=True).count()
  leads_this_month = Lead.objects.filter(is_active=True, created_at__gte=current_month_start).count()
  
  # Quotes/Deals
  total_quotes = Quote.objects.count()
  quotes_in_progress = Quote.objects.filter(status__in=['Draft', 'Sent']).count()
  quotes_closing_soon = Quote.objects.filter(status='Sent', valid_until__gte=current_date, valid_until__lte=current_date + timezone.timedelta(days=7)).count()
  
  # Projects
  total_projects = ClientOnboarding.objects.count()
  projects_in_progress = ClientOnboarding.objects.filter(status='active').count()
  projects_overdue = ClientOnboarding.objects.filter(
    status='active',
    start_date__isnull=False
  ).filter(
    start_date__lt=current_date - timezone.timedelta(days=30)
  ).count()
  
  # Leave Requests (as tickets)
  pending_leaves = LeaveRequest.objects.filter(status='Pending').count()
  overdue_leaves = LeaveRequest.objects.filter(
    status='Pending',
    start_date__lt=current_date
  ).count()
  
  # Lead Source Distribution
  lead_sources = Lead.objects.filter(is_active=True).values('source').annotate(count=Count('id'))
  lead_source_data = {}
  total_source_leads = 0
  for source in lead_sources:
    lead_source_data[source['source']] = source['count']
    total_source_leads += source['count']
  
  # Sales Funnel Data
  prospect_count = Lead.objects.filter(is_active=True).count()
  proposal_sent = Quote.objects.filter(status='Sent').count()
  negotiation_count = Quote.objects.filter(status='Sent', valid_until__gte=current_date).count()
  
  # Employee Distribution by Department
  employee_departments = Employee.objects.filter(status='active').values('department').annotate(count=Count('id'))
  dept_data = {}
  for dept in employee_departments:
    dept_name = dept['department'] or 'Unassigned'
    dept_data[dept_name] = dept['count']
  
  # Today's Attendance
  today_attendance = Attendance.objects.filter(date=current_date).select_related('user')
  present_employees = []
  for att in today_attendance:
    if att.check_in_time:
      employee_name = att.employee_name
      check_in = att.check_in_time
      present_employees.append({
        'name': employee_name,
        'check_in': check_in.strftime('%I:%M %p') if check_in else 'N/A',
        'status': 'Present'
      })
  
  # Recent Activity (last 5 attendance records)
  recent_activity = Attendance.objects.filter(check_in_time__isnull=False).order_by('-check_in_time')[:5]
  activity_list = []
  for att in recent_activity:
    activity_list.append({
      'employee': att.employee_name,
      'time': att.check_in_time.strftime('%I:%M %p') if att.check_in_time else 'N/A',
      'date': att.date.strftime('%b %d, %Y')
    })
  
  # Upcoming Contract Renewals (Quotes valid_until)
  upcoming_renewals = Quote.objects.filter(
    valid_until__gte=current_date
  ).order_by('valid_until')[:5]
  
  renewals_list = []
  for quote in upcoming_renewals:
    renewals_list.append({
      'client': quote.client_name,
      'renewal_date': quote.valid_until.strftime('%b %d, %Y')
    })
  
  # Pending Tasks (Leads with due dates)
  pending_tasks = Lead.objects.filter(
    due_date__isnull=False,
    due_date__gte=current_date
  ).order_by('due_date')[:5]
  
  tasks_list = []
  for lead in pending_tasks:
    tasks_list.append({
      'task': f"{lead.next_action} - {lead.name}",
      'due_date': lead.due_date.strftime('%b %d, %Y') if lead.due_date else 'N/A'
    })
  
  # Prepare context with JSON serialized data for charts
  context = {
    'total_leads': total_leads,
    'leads_this_month': leads_this_month,
    'total_quotes': total_quotes,
    'quotes_in_progress': quotes_in_progress,
    'quotes_closing_soon': quotes_closing_soon,
    'total_projects': total_projects,
    'projects_in_progress': projects_in_progress,
    'projects_overdue': projects_overdue,
    'pending_leaves': pending_leaves,
    'overdue_leaves': overdue_leaves,
    'lead_source_data': json.dumps(lead_source_data),
    'total_source_leads': total_source_leads,
    'prospect_count': prospect_count,
    'proposal_sent': proposal_sent,
    'negotiation_count': negotiation_count,
    'dept_data': json.dumps(dept_data),
    'present_employees': present_employees,
    'activity_list': activity_list,
    'renewals_list': renewals_list,
    'tasks_list': tasks_list,
    'user_name': request.user.get_full_name() or request.user.username or 'Admin',
  }
  
  return render(request, 'dashboard/dashboard.html', context)


@login_required
def accounts_department(request):
  """
  Accounts Department summary dashboard with compliance tabs.
  Reuses the same 5 category tabs as the employee Accounts workspace,
  and shows recent records in a responsive table from the selected category.
  """
  # Restrict to admin/staff similar to main dashboard
  try:
    employee = Employee.objects.get(email=request.user.email)
    if employee.role != 'Admin':
      messages.warning(request, 'You do not have permission to access this page.')
      return redirect('employee_dashboard')
  except Employee.DoesNotExist:
    if not request.user.is_staff:
      messages.warning(request, 'You do not have permission to access this page.')
      return redirect('employee_dashboard')

  # Determine active tab and search query from URL
  valid_tabs = ['roc', 'gst', 'itr', 'accounts', 'tds']
  active_tab = request.GET.get('tab', 'roc')
  if active_tab not in valid_tabs:
    active_tab = 'roc'

  search_query = request.GET.get('q', '').strip()
  page_number = request.GET.get('page')
  per_page = 15

  roc_page = gst_page = itr_page = bookkeeping_page = tds_page = None

  if active_tab == 'roc':
    qs = ROCComplianceRecord.objects.all()
    if search_query:
      qs = qs.filter(
        Q(company_name__icontains=search_query) |
        Q(cin_llpin__icontains=search_query) |
        Q(financial_year__icontains=search_query) |
        Q(compliance_period__icontains=search_query)
      )
    roc_page = Paginator(qs, per_page).get_page(page_number)

  elif active_tab == 'gst':
    qs = GSTFilingRecord.objects.all()
    if search_query:
      qs = qs.filter(
        Q(gstin__icontains=search_query) |
        Q(return_period__icontains=search_query) |
        Q(return_type__icontains=search_query) |
        Q(filing_scheme__icontains=search_query)
      )
    gst_page = Paginator(qs, per_page).get_page(page_number)

  elif active_tab == 'itr':
    qs = ITRFilingRecord.objects.all()
    if search_query:
      qs = qs.filter(
        Q(taxpayer_name__icontains=search_query) |
        Q(pan__icontains=search_query) |
        Q(assessment_year__icontains=search_query) |
        Q(return_form__icontains=search_query)
      )
    itr_page = Paginator(qs, per_page).get_page(page_number)

  elif active_tab == 'accounts':
    qs = BookkeepingChecklistRecord.objects.all()
    if search_query:
      qs = qs.filter(
        Q(prepared_by__icontains=search_query) |
        Q(outstanding_notes__icontains=search_query)
      )
    bookkeeping_page = Paginator(qs, per_page).get_page(page_number)

  elif active_tab == 'tds':
    qs = TDSComplianceRecord.objects.all()
    if search_query:
      qs = qs.filter(
        Q(deductor_tan__icontains=search_query) |
        Q(section__icontains=search_query) |
        Q(deduction_month__icontains=search_query) |
        Q(challan_number__icontains=search_query)
      )
    tds_page = Paginator(qs, per_page).get_page(page_number)

  context = {
    'active_tab': active_tab,
    'search_query': search_query,
    'roc_page': roc_page,
    'gst_page': gst_page,
    'itr_page': itr_page,
    'bookkeeping_page': bookkeeping_page,
    'tds_page': tds_page,
  }

  return render(request, 'dashboard/accounts_department.html', context)


@login_required
def backoffice_department(request):
  """
  Back office oversight view for admins.
  Shows tabbed datasets for every registration/licensing workflow with search & pagination.
  """
  try:
    employee = Employee.objects.get(email=request.user.email)
    if employee.role != 'Admin':
      messages.warning(request, 'You do not have permission to access this page.')
      return redirect('employee_dashboard')
  except Employee.DoesNotExist:
    if not request.user.is_staff:
      messages.warning(request, 'You do not have permission to access this page.')
      return redirect('employee_dashboard')

  service_definitions = [
    {
      'id': 'startup',
      'title': 'Start-up India Registration',
      'icon': 'bi-rocket-takeoff',
      'model': StartupIndiaRegistration,
      'search_fields': [
        'legal_entity_name__icontains',
        'entity_type__icontains',
        'industry_sector__icontains',
        'email__icontains',
      ],
    },
    {
      'id': 'fssai',
      'title': 'Food Licensing (FSSAI)',
      'icon': 'bi-egg-fried',
      'model': FSSAILicense,
      'search_fields': [
        'business_brand_name__icontains',
        'licence_type__icontains',
        'business_nature__icontains',
        'premises_address__icontains',
      ],
    },
    {
      'id': 'msme',
      'title': 'MSME / Udyam Registration',
      'icon': 'bi-building-gear',
      'model': MSMEUdyamRegistration,
      'search_fields': [
        'entity_name__icontains',
        'organisation_type__icontains',
        'principal_activity__icontains',
      ],
    },
    {
      'id': 'company-reg',
      'title': 'Company / LLP Registration',
      'icon': 'bi-diagram-3',
      'model': CompanyLLPRegistration,
      'search_fields': [
        'entity_type__icontains',
        'proposed_names__icontains',
        'registered_office__icontains',
      ],
    },
    {
      'id': 'fire-pollution',
      'title': 'Fire & Pollution Licences',
      'icon': 'bi-shield-check',
      'model': FirePollutionLicense,
      'search_fields': [
        'establishment_type__icontains',
        'pollution_category__icontains',
        'safety_installations__icontains',
      ],
    },
    {
      'id': 'iso',
      'title': 'ISO Certification (9001/14001/27001)',
      'icon': 'bi-award',
      'model': ISOCertification,
      'search_fields': [
        'standard__icontains',
        'existing_certifications__icontains',
      ],
    },
    {
      'id': 'tm-file',
      'title': 'Trademark Filing',
      'icon': 'bi-badge-tm',
      'model': TrademarkFiling,
      'search_fields': [
        'brand_logo__icontains',
        'applicant_type__icontains',
        'classes__icontains',
      ],
    },
    {
      'id': 'tm-compliance',
      'title': 'Trademark Filing + Compliance',
      'icon': 'bi-bag-check',
      'model': TrademarkFilingCompliance,
      'search_fields': [
        'existing_tm_numbers__icontains',
        'watch_scope__icontains',
      ],
    },
    {
      'id': 'tm-instant',
      'title': 'Trademark Filing (Instant Process)',
      'icon': 'bi-lightning-charge',
      'model': TrademarkFilingInstant,
      'search_fields': [
        'urgency_reason__icontains',
        'filing_window__icontains',
        'contact_mobile__icontains',
      ],
    },
    {
      'id': 'address-change',
      'title': 'Company Address Change',
      'icon': 'bi-geo-alt',
      'model': CompanyAddressChange,
      'search_fields': [
        'entity_type__icontains',
        'shift_type__icontains',
        'new_address__icontains',
      ],
    },
    {
      'id': 'moa-alter',
      'title': 'MOA Alteration',
      'icon': 'bi-file-earmark-text',
      'model': MOAAlteration,
      'search_fields': [
        'alteration_type__icontains',
        'proposed_object_name__icontains',
      ],
    },
  ]

  service_map = {service['id']: service for service in service_definitions}
  tab_counts = {}
  services = []
  for svc in service_definitions:
    count = svc['model'].objects.count()
    tab_counts[svc['id']] = count
    services.append({
      'id': svc['id'],
      'title': svc['title'],
      'icon': svc['icon'],
      'count': count,
    })

  active_tab = request.GET.get('tab', 'startup')
  if active_tab not in service_map:
    active_tab = 'startup'

  search_query = request.GET.get('q', '').strip()
  page_number = request.GET.get('page')
  per_page = 15

  active_service = service_map[active_tab]
  queryset = active_service['model'].objects.all().order_by('-created_at')

  if search_query:
    search_filter = Q()
    for lookup in active_service['search_fields']:
      search_filter |= Q(**{lookup: search_query})
    queryset = queryset.filter(search_filter)

  page_obj = Paginator(queryset, per_page).get_page(page_number)

  context = {
    'services': services,
    'active_tab': active_tab,
    'active_service': active_service,
    'search_query': search_query,
    'page_obj': page_obj,
    'tab_counts': tab_counts,
  }

  return render(request, 'dashboard/backoffice_department.html', context)

def service_forms(request):
  """
  Service Forms page - User selects a service and then sees the form.
  Shows all services from Accounts Department and Back Office Department.
  Accessible to all users (no login required).
  """

  # Get selected service from query parameter
  selected_service = request.GET.get('service', '')
  
  # Define all services from Accounts Department
  accounts_services = [
    {
      'id': 'roc',
      'title': 'ROC Compliance',
      'icon': 'bi-file-earmark-check',
      'department': 'Accounts',
      'form_class': ROCComplianceForm,
      'form_name': 'roc',
      'model': ROCComplianceRecord,
    },
    {
      'id': 'gst',
      'title': 'GST Filing',
      'icon': 'bi-receipt',
      'department': 'Accounts',
      'form_class': GSTFilingForm,
      'form_name': 'gst',
      'model': GSTFilingRecord,
    },
    {
      'id': 'itr',
      'title': 'ITR Filing',
      'icon': 'bi-file-earmark-text',
      'department': 'Accounts',
      'form_class': ITRFilingForm,
      'form_name': 'itr',
      'model': ITRFilingRecord,
    },
    {
      'id': 'bookkeeping',
      'title': 'Bookkeeping Checklist',
      'icon': 'bi-clipboard-check',
      'department': 'Accounts',
      'form_class': BookkeepingChecklistForm,
      'form_name': 'bookkeeping',
      'model': BookkeepingChecklistRecord,
    },
    {
      'id': 'tds',
      'title': 'TDS Compliance',
      'icon': 'bi-cash-stack',
      'department': 'Accounts',
      'form_class': TDSComplianceForm,
      'form_name': 'tds',
      'model': TDSComplianceRecord,
    },
  ]
  
  # Define all services from Back Office Department
  backoffice_services = [
    {
      'id': 'startup',
      'title': 'Start-up India Registration',
      'icon': 'bi-rocket-takeoff',
      'department': 'Back Office',
      'form_class': StartupIndiaRegistrationForm,
      'form_name': 'startup_india',
      'model': StartupIndiaRegistration,
    },
    {
      'id': 'fssai',
      'title': 'Food Licensing (FSSAI)',
      'icon': 'bi-egg-fried',
      'department': 'Back Office',
      'form_class': FSSAILicenseForm,
      'form_name': 'fssai',
      'model': FSSAILicense,
    },
    {
      'id': 'msme',
      'title': 'MSME / Udyam Registration',
      'icon': 'bi-building-gear',
      'department': 'Back Office',
      'form_class': MSMEUdyamRegistrationForm,
      'form_name': 'msme',
      'model': MSMEUdyamRegistration,
    },
    {
      'id': 'company-llp',
      'title': 'Company / LLP Registration',
      'icon': 'bi-diagram-3',
      'department': 'Back Office',
      'form_class': CompanyLLPRegistrationForm,
      'form_name': 'company_llp',
      'model': CompanyLLPRegistration,
    },
    {
      'id': 'fire-pollution',
      'title': 'Fire & Pollution Licences',
      'icon': 'bi-shield-check',
      'department': 'Back Office',
      'form_class': FirePollutionLicenseForm,
      'form_name': 'fire_pollution',
      'model': FirePollutionLicense,
    },
    {
      'id': 'iso',
      'title': 'ISO Certification',
      'icon': 'bi-award',
      'department': 'Back Office',
      'form_class': ISOCertificationForm,
      'form_name': 'iso',
      'model': ISOCertification,
    },
    {
      'id': 'trademark',
      'title': 'Trademark Filing',
      'icon': 'bi-trademark',
      'department': 'Back Office',
      'form_class': TrademarkFilingForm,
      'form_name': 'trademark',
      'model': TrademarkFiling,
    },
    {
      'id': 'trademark-compliance',
      'title': 'Trademark Filing + Compliance',
      'icon': 'bi-shield-check',
      'department': 'Back Office',
      'form_class': TrademarkFilingComplianceForm,
      'form_name': 'trademark_compliance',
      'model': TrademarkFilingCompliance,
    },
    {
      'id': 'trademark-instant',
      'title': 'Trademark Filing (Instant)',
      'icon': 'bi-lightning',
      'department': 'Back Office',
      'form_class': TrademarkFilingInstantForm,
      'form_name': 'trademark_instant',
      'model': TrademarkFilingInstant,
    },
    {
      'id': 'address-change',
      'title': 'Company Address Change',
      'icon': 'bi-geo-alt',
      'department': 'Back Office',
      'form_class': CompanyAddressChangeForm,
      'form_name': 'address_change',
      'model': CompanyAddressChange,
    },
    {
      'id': 'moa-alteration',
      'title': 'MOA Alteration',
      'icon': 'bi-pencil-square',
      'department': 'Back Office',
      'form_class': MOAAlterationForm,
      'form_name': 'moa_alteration',
      'model': MOAAlteration,
    },
  ]
  
  # Combine all services
  all_services = accounts_services + backoffice_services
  
  # Find selected service
  selected_service_obj = None
  form_instance = None
  
  if selected_service:
    for service in all_services:
      if service['id'] == selected_service:
        selected_service_obj = service
        form_instance = service['form_class']()
        break
  
  # Handle form submission
  if request.method == 'POST':
    form_name = request.POST.get('form_name')
    
    # Find the service by form_name
    for service in all_services:
      if service['form_name'] == form_name:
        selected_service_obj = service
        form_instance = service['form_class'](request.POST, request.FILES)
        
        if form_instance.is_valid():
          record = form_instance.save(commit=False)
          # Only set user if authenticated, otherwise leave as None
          if request.user.is_authenticated:
            record.user = request.user
          else:
            record.user = None
          
          # Set lead_source to 'website' if not provided
          if not record.lead_source:
            record.lead_source = 'website'
          
          # Handle file uploads based on service type
          if form_name == 'roc':
            # Save applicant information for ROC Compliance
            applicant_name = request.POST.get('applicant_name', '').strip()
            applicant_phone = request.POST.get('applicant_phone', '').strip()
            applicant_whatsapp = request.POST.get('applicant_whatsapp', '').strip()
            applicant_email = request.POST.get('applicant_email', '').strip()
            applicant_address = request.POST.get('applicant_address', '').strip()
            
            if hasattr(record, 'applicant_name'):
              record.applicant_name = applicant_name if applicant_name else None
            if hasattr(record, 'applicant_phone'):
              record.applicant_phone = applicant_phone if applicant_phone else None
            if hasattr(record, 'applicant_whatsapp'):
              record.applicant_whatsapp = applicant_whatsapp if applicant_whatsapp else None
            if hasattr(record, 'applicant_email'):
              record.applicant_email = applicant_email if applicant_email else None
            if hasattr(record, 'applicant_address'):
              record.applicant_address = applicant_address if applicant_address else None
            
            uploaded_files = request.FILES.getlist('roc_documents')
            if uploaded_files:
              record.documents = _store_uploaded_files(uploaded_files, 'roc')
          
          elif form_name == 'gst':
            # Save applicant information for GST Filing
            applicant_name = request.POST.get('applicant_name', '').strip()
            applicant_phone = request.POST.get('applicant_phone', '').strip()
            applicant_whatsapp = request.POST.get('applicant_whatsapp', '').strip()
            applicant_email = request.POST.get('applicant_email', '').strip()
            applicant_address = request.POST.get('applicant_address', '').strip()
            
            if hasattr(record, 'applicant_name'):
              record.applicant_name = applicant_name if applicant_name else None
            if hasattr(record, 'applicant_phone'):
              record.applicant_phone = applicant_phone if applicant_phone else None
            if hasattr(record, 'applicant_whatsapp'):
              record.applicant_whatsapp = applicant_whatsapp if applicant_whatsapp else None
            if hasattr(record, 'applicant_email'):
              record.applicant_email = applicant_email if applicant_email else None
            if hasattr(record, 'applicant_address'):
              record.applicant_address = applicant_address if applicant_address else None
            
            files_map = {
              'outward_supplies': _store_uploaded_files(request.FILES.getlist('gst_outward_supplies'), 'gst/outward'),
              'input_tax_credit': _store_uploaded_files(request.FILES.getlist('gst_input_tax_credit'), 'gst/input-credit'),
              'reverse_charge': _store_uploaded_files(request.FILES.getlist('gst_reverse_charge'), 'gst/reverse-charge'),
              'eway_bill_summary': _store_uploaded_files(request.FILES.getlist('gst_eway_bill'), 'gst/eway-bill'),
            }
            record.data_files = {key: paths for key, paths in files_map.items() if paths}
          
          elif form_name == 'itr':
            # Save applicant information for ITR Filing
            applicant_name = request.POST.get('applicant_name', '').strip()
            applicant_phone = request.POST.get('applicant_phone', '').strip()
            applicant_whatsapp = request.POST.get('applicant_whatsapp', '').strip()
            applicant_email = request.POST.get('applicant_email', '').strip()
            applicant_address = request.POST.get('applicant_address', '').strip()
            
            if hasattr(record, 'applicant_name'):
              record.applicant_name = applicant_name if applicant_name else None
            if hasattr(record, 'applicant_phone'):
              record.applicant_phone = applicant_phone if applicant_phone else None
            if hasattr(record, 'applicant_whatsapp'):
              record.applicant_whatsapp = applicant_whatsapp if applicant_whatsapp else None
            if hasattr(record, 'applicant_email'):
              record.applicant_email = applicant_email if applicant_email else None
            if hasattr(record, 'applicant_address'):
              record.applicant_address = applicant_address if applicant_address else None
            
            uploaded_files = request.FILES.getlist('itr_documents')
            if uploaded_files:
              record.documents = _store_uploaded_files(uploaded_files, 'itr')
          
          elif form_name == 'bookkeeping':
            # Save applicant information for Bookkeeping Checklist
            applicant_name = request.POST.get('applicant_name', '').strip()
            applicant_phone = request.POST.get('applicant_phone', '').strip()
            applicant_whatsapp = request.POST.get('applicant_whatsapp', '').strip()
            applicant_email = request.POST.get('applicant_email', '').strip()
            applicant_address = request.POST.get('applicant_address', '').strip()
            
            if hasattr(record, 'applicant_name'):
              record.applicant_name = applicant_name if applicant_name else None
            if hasattr(record, 'applicant_phone'):
              record.applicant_phone = applicant_phone if applicant_phone else None
            if hasattr(record, 'applicant_whatsapp'):
              record.applicant_whatsapp = applicant_whatsapp if applicant_whatsapp else None
            if hasattr(record, 'applicant_email'):
              record.applicant_email = applicant_email if applicant_email else None
            if hasattr(record, 'applicant_address'):
              record.applicant_address = applicant_address if applicant_address else None
            
            uploaded_files = request.FILES.getlist('bookkeeping_documents')
            if uploaded_files:
              record.reconciliation_documents = _store_uploaded_files(uploaded_files, 'bookkeeping')
          
          elif form_name == 'tds':
            # Save applicant information for TDS Compliance
            applicant_name = request.POST.get('applicant_name', '').strip()
            applicant_phone = request.POST.get('applicant_phone', '').strip()
            applicant_whatsapp = request.POST.get('applicant_whatsapp', '').strip()
            applicant_email = request.POST.get('applicant_email', '').strip()
            applicant_address = request.POST.get('applicant_address', '').strip()
            
            if hasattr(record, 'applicant_name'):
              record.applicant_name = applicant_name if applicant_name else None
            if hasattr(record, 'applicant_phone'):
              record.applicant_phone = applicant_phone if applicant_phone else None
            if hasattr(record, 'applicant_whatsapp'):
              record.applicant_whatsapp = applicant_whatsapp if applicant_whatsapp else None
            if hasattr(record, 'applicant_email'):
              record.applicant_email = applicant_email if applicant_email else None
            if hasattr(record, 'applicant_address'):
              record.applicant_address = applicant_address if applicant_address else None
            
            uploaded_files = request.FILES.getlist('tds_proofs')
            if uploaded_files:
              record.proofs = _store_uploaded_files(uploaded_files, 'tds')
          
          elif form_name == 'startup_india':
            # Save applicant information for Start-up India Registration
            applicant_name = request.POST.get('applicant_name', '').strip()
            applicant_phone = request.POST.get('applicant_phone', '').strip()
            applicant_whatsapp = request.POST.get('applicant_whatsapp', '').strip()
            applicant_email = request.POST.get('applicant_email', '').strip()
            applicant_address = request.POST.get('applicant_address', '').strip()
            
            if hasattr(record, 'applicant_name'):
              record.applicant_name = applicant_name if applicant_name else None
            if hasattr(record, 'applicant_phone'):
              record.applicant_phone = applicant_phone if applicant_phone else None
            if hasattr(record, 'applicant_whatsapp'):
              record.applicant_whatsapp = applicant_whatsapp if applicant_whatsapp else None
            if hasattr(record, 'applicant_email'):
              record.applicant_email = applicant_email if applicant_email else None
            if hasattr(record, 'applicant_address'):
              record.applicant_address = applicant_address if applicant_address else None
            
            uploaded_files = request.FILES.getlist('startup_documents')
            if uploaded_files:
              record.documents = _store_uploaded_files(uploaded_files, 'startup_india')
            record.status = 'pending'
          
          elif form_name == 'fssai':
            # Save applicant information for FSSAI License
            applicant_name = request.POST.get('applicant_name', '').strip()
            applicant_phone = request.POST.get('applicant_phone', '').strip()
            applicant_whatsapp = request.POST.get('applicant_whatsapp', '').strip()
            applicant_email = request.POST.get('applicant_email', '').strip()
            applicant_address = request.POST.get('applicant_address', '').strip()
            
            if hasattr(record, 'applicant_name'):
              record.applicant_name = applicant_name if applicant_name else None
            if hasattr(record, 'applicant_phone'):
              record.applicant_phone = applicant_phone if applicant_phone else None
            if hasattr(record, 'applicant_whatsapp'):
              record.applicant_whatsapp = applicant_whatsapp if applicant_whatsapp else None
            if hasattr(record, 'applicant_email'):
              record.applicant_email = applicant_email if applicant_email else None
            if hasattr(record, 'applicant_address'):
              record.applicant_address = applicant_address if applicant_address else None
            
            uploaded_files = request.FILES.getlist('fssai_documents')
            if uploaded_files:
              record.documents = _store_uploaded_files(uploaded_files, 'fssai')
            record.status = 'pending'
          
          elif form_name == 'msme':
            # Save applicant information for MSME Registration
            applicant_name = request.POST.get('applicant_name', '').strip()
            applicant_phone = request.POST.get('applicant_phone', '').strip()
            applicant_whatsapp = request.POST.get('applicant_whatsapp', '').strip()
            applicant_email = request.POST.get('applicant_email', '').strip()
            applicant_address = request.POST.get('applicant_address', '').strip()
            
            if hasattr(record, 'applicant_name'):
              record.applicant_name = applicant_name if applicant_name else None
            if hasattr(record, 'applicant_phone'):
              record.applicant_phone = applicant_phone if applicant_phone else None
            if hasattr(record, 'applicant_whatsapp'):
              record.applicant_whatsapp = applicant_whatsapp if applicant_whatsapp else None
            if hasattr(record, 'applicant_email'):
              record.applicant_email = applicant_email if applicant_email else None
            if hasattr(record, 'applicant_address'):
              record.applicant_address = applicant_address if applicant_address else None
            
            record.status = 'pending'
          
          elif form_name == 'company_llp':
            # Save applicant information for Company/LLP Registration
            applicant_name = request.POST.get('applicant_name', '').strip()
            applicant_phone = request.POST.get('applicant_phone', '').strip()
            applicant_whatsapp = request.POST.get('applicant_whatsapp', '').strip()
            applicant_email = request.POST.get('applicant_email', '').strip()
            applicant_address = request.POST.get('applicant_address', '').strip()
            
            if hasattr(record, 'applicant_name'):
              record.applicant_name = applicant_name if applicant_name else None
            if hasattr(record, 'applicant_phone'):
              record.applicant_phone = applicant_phone if applicant_phone else None
            if hasattr(record, 'applicant_whatsapp'):
              record.applicant_whatsapp = applicant_whatsapp if applicant_whatsapp else None
            if hasattr(record, 'applicant_email'):
              record.applicant_email = applicant_email if applicant_email else None
            if hasattr(record, 'applicant_address'):
              record.applicant_address = applicant_address if applicant_address else None
            
            uploaded_files = request.FILES.getlist('company_documents')
            if uploaded_files:
              record.documents = _store_uploaded_files(uploaded_files, 'company_llp')
            record.status = 'pending'
          
          elif form_name == 'fire_pollution':
            # Save applicant information for Fire & Pollution License
            applicant_name = request.POST.get('applicant_name', '').strip()
            applicant_phone = request.POST.get('applicant_phone', '').strip()
            applicant_whatsapp = request.POST.get('applicant_whatsapp', '').strip()
            applicant_email = request.POST.get('applicant_email', '').strip()
            applicant_address = request.POST.get('applicant_address', '').strip()
            
            if hasattr(record, 'applicant_name'):
              record.applicant_name = applicant_name if applicant_name else None
            if hasattr(record, 'applicant_phone'):
              record.applicant_phone = applicant_phone if applicant_phone else None
            if hasattr(record, 'applicant_whatsapp'):
              record.applicant_whatsapp = applicant_whatsapp if applicant_whatsapp else None
            if hasattr(record, 'applicant_email'):
              record.applicant_email = applicant_email if applicant_email else None
            if hasattr(record, 'applicant_address'):
              record.applicant_address = applicant_address if applicant_address else None
            
            uploaded_files = request.FILES.getlist('fire_documents')
            if uploaded_files:
              record.documents = _store_uploaded_files(uploaded_files, 'fire_pollution')
            record.status = 'pending'
          
          elif form_name == 'iso':
            # Save applicant information for ISO Certification
            applicant_name = request.POST.get('applicant_name', '').strip()
            applicant_phone = request.POST.get('applicant_phone', '').strip()
            applicant_whatsapp = request.POST.get('applicant_whatsapp', '').strip()
            applicant_email = request.POST.get('applicant_email', '').strip()
            applicant_address = request.POST.get('applicant_address', '').strip()
            
            if hasattr(record, 'applicant_name'):
              record.applicant_name = applicant_name if applicant_name else None
            if hasattr(record, 'applicant_phone'):
              record.applicant_phone = applicant_phone if applicant_phone else None
            if hasattr(record, 'applicant_whatsapp'):
              record.applicant_whatsapp = applicant_whatsapp if applicant_whatsapp else None
            if hasattr(record, 'applicant_email'):
              record.applicant_email = applicant_email if applicant_email else None
            if hasattr(record, 'applicant_address'):
              record.applicant_address = applicant_address if applicant_address else None
            
            uploaded_files = request.FILES.getlist('iso_documents')
            if uploaded_files:
              record.documents = _store_uploaded_files(uploaded_files, 'iso')
            record.status = 'pending'
          
          elif form_name == 'trademark':
            # Save applicant information for Trademark Filing
            applicant_name = request.POST.get('applicant_name', '').strip()
            applicant_phone = request.POST.get('applicant_phone', '').strip()
            applicant_whatsapp = request.POST.get('applicant_whatsapp', '').strip()
            applicant_email = request.POST.get('applicant_email', '').strip()
            applicant_address = request.POST.get('applicant_address', '').strip()
            
            if hasattr(record, 'applicant_name'):
              record.applicant_name = applicant_name if applicant_name else None
            if hasattr(record, 'applicant_phone'):
              record.applicant_phone = applicant_phone if applicant_phone else None
            if hasattr(record, 'applicant_whatsapp'):
              record.applicant_whatsapp = applicant_whatsapp if applicant_whatsapp else None
            if hasattr(record, 'applicant_email'):
              record.applicant_email = applicant_email if applicant_email else None
            if hasattr(record, 'applicant_address'):
              record.applicant_address = applicant_address if applicant_address else None
            
            uploaded_files = request.FILES.getlist('trademark_documents')
            if uploaded_files:
              record.documents = _store_uploaded_files(uploaded_files, 'trademark')
            record.status = 'pending'
          
          elif form_name == 'trademark_compliance':
            # Save applicant information for Trademark Filing + Compliance
            applicant_name = request.POST.get('applicant_name', '').strip()
            applicant_phone = request.POST.get('applicant_phone', '').strip()
            applicant_whatsapp = request.POST.get('applicant_whatsapp', '').strip()
            applicant_email = request.POST.get('applicant_email', '').strip()
            applicant_address = request.POST.get('applicant_address', '').strip()
            
            if hasattr(record, 'applicant_name'):
              record.applicant_name = applicant_name if applicant_name else None
            if hasattr(record, 'applicant_phone'):
              record.applicant_phone = applicant_phone if applicant_phone else None
            if hasattr(record, 'applicant_whatsapp'):
              record.applicant_whatsapp = applicant_whatsapp if applicant_whatsapp else None
            if hasattr(record, 'applicant_email'):
              record.applicant_email = applicant_email if applicant_email else None
            if hasattr(record, 'applicant_address'):
              record.applicant_address = applicant_address if applicant_address else None
            
            uploaded_files = request.FILES.getlist('trademark_compliance_documents')
            if uploaded_files:
              record.documents = _store_uploaded_files(uploaded_files, 'trademark_compliance')
            record.status = 'pending'
          
          elif form_name == 'trademark_instant':
            # Save applicant information for Trademark Filing (Instant)
            applicant_name = request.POST.get('applicant_name', '').strip()
            applicant_phone = request.POST.get('applicant_phone', '').strip()
            applicant_whatsapp = request.POST.get('applicant_whatsapp', '').strip()
            applicant_email = request.POST.get('applicant_email', '').strip()
            applicant_address = request.POST.get('applicant_address', '').strip()
            
            if hasattr(record, 'applicant_name'):
              record.applicant_name = applicant_name if applicant_name else None
            if hasattr(record, 'applicant_phone'):
              record.applicant_phone = applicant_phone if applicant_phone else None
            if hasattr(record, 'applicant_whatsapp'):
              record.applicant_whatsapp = applicant_whatsapp if applicant_whatsapp else None
            if hasattr(record, 'applicant_email'):
              record.applicant_email = applicant_email if applicant_email else None
            if hasattr(record, 'applicant_address'):
              record.applicant_address = applicant_address if applicant_address else None
            
            uploaded_files = request.FILES.getlist('trademark_instant_documents')
            if uploaded_files:
              record.documents = _store_uploaded_files(uploaded_files, 'trademark_instant')
            record.status = 'pending'
          
          elif form_name == 'address_change':
            # Save applicant information for Company Address Change
            applicant_name = request.POST.get('applicant_name', '').strip()
            applicant_phone = request.POST.get('applicant_phone', '').strip()
            applicant_whatsapp = request.POST.get('applicant_whatsapp', '').strip()
            applicant_email = request.POST.get('applicant_email', '').strip()
            applicant_address = request.POST.get('applicant_address', '').strip()
            
            if hasattr(record, 'applicant_name'):
              record.applicant_name = applicant_name if applicant_name else None
            if hasattr(record, 'applicant_phone'):
              record.applicant_phone = applicant_phone if applicant_phone else None
            if hasattr(record, 'applicant_whatsapp'):
              record.applicant_whatsapp = applicant_whatsapp if applicant_whatsapp else None
            if hasattr(record, 'applicant_email'):
              record.applicant_email = applicant_email if applicant_email else None
            if hasattr(record, 'applicant_address'):
              record.applicant_address = applicant_address if applicant_address else None
            
            uploaded_files = request.FILES.getlist('address_change_documents')
            if uploaded_files:
              record.documents = _store_uploaded_files(uploaded_files, 'address_change')
            record.status = 'pending'
          
          elif form_name == 'moa_alteration':
            # Save applicant information for MOA Alteration
            applicant_name = request.POST.get('applicant_name', '').strip()
            applicant_phone = request.POST.get('applicant_phone', '').strip()
            applicant_whatsapp = request.POST.get('applicant_whatsapp', '').strip()
            applicant_email = request.POST.get('applicant_email', '').strip()
            applicant_address = request.POST.get('applicant_address', '').strip()
            
            if hasattr(record, 'applicant_name'):
              record.applicant_name = applicant_name if applicant_name else None
            if hasattr(record, 'applicant_phone'):
              record.applicant_phone = applicant_phone if applicant_phone else None
            if hasattr(record, 'applicant_whatsapp'):
              record.applicant_whatsapp = applicant_whatsapp if applicant_whatsapp else None
            if hasattr(record, 'applicant_email'):
              record.applicant_email = applicant_email if applicant_email else None
            if hasattr(record, 'applicant_address'):
              record.applicant_address = applicant_address if applicant_address else None
            
            uploaded_files = request.FILES.getlist('moa_alteration_documents')
            if uploaded_files:
              record.documents = _store_uploaded_files(uploaded_files, 'moa_alteration')
            record.status = 'pending'
          
          record.save()
          messages.success(request, f'{selected_service_obj["title"]} form submitted successfully!')
          return redirect('service_forms')
        else:
          messages.error(request, 'Please correct the errors in the form.')
        break
  
  # Get all records for each service to display in tables
  service_records = {}
  for service in all_services:
    try:
      records = service['model'].objects.all().order_by('-created_at')[:50]  # Latest 50 records
      service_records[service['id']] = records
    except:
      service_records[service['id']] = []
  
  context = {
    'accounts_services': accounts_services,
    'backoffice_services': backoffice_services,
    'all_services': all_services,
    'selected_service': selected_service,
    'selected_service_obj': selected_service_obj,
    'form': form_instance,
    'service_records': service_records,
  }
  
  return render(request, 'dashboard/service_forms.html', context)

@login_required
def service_leads(request):
  """
  Service Leads page - Shows all leads from service forms.
  Organized by Accounts and Back Office departments.
  """
  # Check if user has Admin role
  try:
    employee = Employee.objects.get(email=request.user.email)
    if employee.role != 'Admin':
      messages.warning(request, 'You do not have permission to access this page.')
      return redirect('employee_dashboard')
  except Employee.DoesNotExist:
    if not request.user.is_staff:
      messages.warning(request, 'You do not have permission to access this page.')
      return redirect('employee_dashboard')
  
  # Define all services
  accounts_services = [
    {'id': 'roc', 'title': 'ROC Compliance', 'model': ROCComplianceRecord, 'icon': 'bi-file-earmark-check'},
    {'id': 'gst', 'title': 'GST Filing', 'model': GSTFilingRecord, 'icon': 'bi-receipt'},
    {'id': 'itr', 'title': 'ITR Filing', 'model': ITRFilingRecord, 'icon': 'bi-file-earmark-text'},
    {'id': 'bookkeeping', 'title': 'Bookkeeping Checklist', 'model': BookkeepingChecklistRecord, 'icon': 'bi-clipboard-check'},
    {'id': 'tds', 'title': 'TDS Compliance', 'model': TDSComplianceRecord, 'icon': 'bi-cash-stack'},
  ]
  
  backoffice_services = [
    {'id': 'startup', 'title': 'Start-up India Registration', 'model': StartupIndiaRegistration, 'icon': 'bi-rocket-takeoff'},
    {'id': 'fssai', 'title': 'Food Licensing (FSSAI)', 'model': FSSAILicense, 'icon': 'bi-egg-fried'},
    {'id': 'msme', 'title': 'MSME / Udyam Registration', 'model': MSMEUdyamRegistration, 'icon': 'bi-building-gear'},
    {'id': 'company-llp', 'title': 'Company / LLP Registration', 'model': CompanyLLPRegistration, 'icon': 'bi-diagram-3'},
    {'id': 'fire-pollution', 'title': 'Fire & Pollution Licences', 'model': FirePollutionLicense, 'icon': 'bi-shield-check'},
    {'id': 'iso', 'title': 'ISO Certification', 'model': ISOCertification, 'icon': 'bi-award'},
    {'id': 'trademark', 'title': 'Trademark Filing', 'model': TrademarkFiling, 'icon': 'bi-trademark'},
    {'id': 'trademark-compliance', 'title': 'Trademark Filing + Compliance', 'model': TrademarkFilingCompliance, 'icon': 'bi-shield-check'},
    {'id': 'trademark-instant', 'title': 'Trademark Filing (Instant)', 'model': TrademarkFilingInstant, 'icon': 'bi-lightning'},
    {'id': 'address-change', 'title': 'Company Address Change', 'model': CompanyAddressChange, 'icon': 'bi-geo-alt'},
    {'id': 'moa-alteration', 'title': 'MOA Alteration', 'model': MOAAlteration, 'icon': 'bi-pencil-square'},
  ]
  
  # Get all records for each service
  accounts_leads = {}
  for service in accounts_services:
    records = service['model'].objects.all().order_by('-created_at')
    accounts_leads[service['id']] = {
      'title': service['title'],
      'icon': service['icon'],
      'records': records,
      'count': records.count(),
    }
  
  backoffice_leads = {}
  for service in backoffice_services:
    records = service['model'].objects.all().order_by('-created_at')
    backoffice_leads[service['id']] = {
      'title': service['title'],
      'icon': service['icon'],
      'records': records,
      'count': records.count(),
    }
  
  # Get all employees for assign dropdown
  accounts_employees = Employee.objects.filter(department__iexact='accounts', status='active').order_by('first_name', 'last_name')
  backoffice_employees = Employee.objects.filter(department__iexact='backoffice', status='active').order_by('first_name', 'last_name')
  
  context = {
    'accounts_leads': accounts_leads,
    'backoffice_leads': backoffice_leads,
    'accounts_employees': accounts_employees,
    'backoffice_employees': backoffice_employees,
  }
  
  return render(request, 'dashboard/service_leads.html', context)

@login_required
def assign_service_lead(request):
  """Assign a service lead to an employee"""
  if request.method == 'POST':
    try:
      service_type = request.POST.get('service_type')
      record_id = request.POST.get('record_id')
      employee_id = request.POST.get('employee_id')
      
      # Map service types to models
      service_models = {
        'roc': ROCComplianceRecord,
        'gst': GSTFilingRecord,
        'itr': ITRFilingRecord,
        'bookkeeping': BookkeepingChecklistRecord,
        'tds': TDSComplianceRecord,
        'startup': StartupIndiaRegistration,
        'fssai': FSSAILicense,
        'msme': MSMEUdyamRegistration,
        'company-llp': CompanyLLPRegistration,
        'fire-pollution': FirePollutionLicense,
        'iso': ISOCertification,
        'trademark': TrademarkFiling,
        'trademark-compliance': TrademarkFilingCompliance,
        'trademark-instant': TrademarkFilingInstant,
        'address-change': CompanyAddressChange,
        'moa-alteration': MOAAlteration,
      }
      
      if service_type not in service_models:
        return JsonResponse({'success': False, 'error': 'Invalid service type'})
      
      model_class = service_models[service_type]
      record = model_class.objects.get(id=record_id)
      
      if employee_id:
        employee = Employee.objects.get(id=employee_id)
        record.assigned_to = employee
      else:
        record.assigned_to = None
      
      record.save()
      
      return JsonResponse({
        'success': True,
        'message': 'Lead assigned successfully',
        'assigned_to': record.assigned_to.get_full_name() if record.assigned_to else None
      })
    except Exception as e:
      return JsonResponse({'success': False, 'error': str(e)})
  
  return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
def delete_service_lead(request):
  """Delete a service lead record"""
  if request.method == 'POST':
    try:
      service_type = request.POST.get('service_type')
      record_id = request.POST.get('record_id')
      
      # Map service types to models
      service_models = {
        'roc': ROCComplianceRecord,
        'gst': GSTFilingRecord,
        'itr': ITRFilingRecord,
        'bookkeeping': BookkeepingChecklistRecord,
        'tds': TDSComplianceRecord,
        'startup': StartupIndiaRegistration,
        'startup_india': StartupIndiaRegistration,
        'fssai': FSSAILicense,
        'msme': MSMEUdyamRegistration,
        'company-llp': CompanyLLPRegistration,
        'company_llp': CompanyLLPRegistration,
        'fire-pollution': FirePollutionLicense,
        'fire_pollution': FirePollutionLicense,
        'iso': ISOCertification,
        'trademark': TrademarkFiling,
        'trademark-compliance': TrademarkFilingCompliance,
        'trademark_compliance': TrademarkFilingCompliance,
        'trademark-instant': TrademarkFilingInstant,
        'trademark_instant': TrademarkFilingInstant,
        'address-change': CompanyAddressChange,
        'address_change': CompanyAddressChange,
        'moa-alteration': MOAAlteration,
        'moa_alteration': MOAAlteration,
      }
      
      if service_type not in service_models:
        return JsonResponse({'success': False, 'error': 'Invalid service type'})
      
      model_class = service_models[service_type]
      record = model_class.objects.get(id=record_id)
      record.delete()
      
      return JsonResponse({
        'success': True,
        'message': 'Record deleted successfully'
      })
    except model_class.DoesNotExist:
      return JsonResponse({'success': False, 'error': 'Record not found'})
    except Exception as e:
      return JsonResponse({'success': False, 'error': str(e)})
  
  return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
def update_service_lead_status(request):
  """Update status of a service lead"""
  if request.method == 'POST':
    try:
      service_type = request.POST.get('service_type')
      record_id = request.POST.get('record_id')
      status = request.POST.get('status')
      
      # Map service types to models
      service_models = {
        'roc': ROCComplianceRecord,
        'gst': GSTFilingRecord,
        'itr': ITRFilingRecord,
        'bookkeeping': BookkeepingChecklistRecord,
        'tds': TDSComplianceRecord,
      }
      
      if service_type not in service_models:
        return JsonResponse({'success': False, 'error': 'Invalid service type'})
      
      # Validate status
      valid_statuses = ['pending', 'accepted', 'submitted', 'complete']
      if status not in valid_statuses:
        return JsonResponse({'success': False, 'error': 'Invalid status'})
      
      model_class = service_models[service_type]
      record = model_class.objects.get(id=record_id)
      
      # Check if user has permission (must be assigned to them or be admin)
      try:
        employee = Employee.objects.get(email=request.user.email)
        if employee.role != 'Admin' and record.assigned_to != employee:
          return JsonResponse({'success': False, 'error': 'You do not have permission to update this record'})
      except Employee.DoesNotExist:
        if not request.user.is_staff:
          return JsonResponse({'success': False, 'error': 'Permission denied'})
      
      record.status = status
      record.save()
      
      return JsonResponse({
        'success': True,
        'message': 'Status updated successfully',
        'status': status,
        'status_display': record.get_status_display()
      })
    except Exception as e:
      return JsonResponse({'success': False, 'error': str(e)})
  else:
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def dashboard_leaves(request):
    """Dashboard view to manage all leave requests - requires login and Admin role"""
    # Check if user has Admin role
    try:
      employee = Employee.objects.get(email=request.user.email)
      if employee.role != 'Admin':
        messages.warning(request, 'You do not have permission to access this page.')
        return redirect('employee_dashboard')
    except Employee.DoesNotExist:
      if not request.user.is_staff:
        messages.warning(request, 'You do not have permission to access this page.')
        return redirect('employee_dashboard')
    from django.core.paginator import Paginator
    
    # Get all leave requests from database
    leave_requests = LeaveRequest.objects.all().order_by('-applied_at')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        leave_requests = leave_requests.filter(
            Q(applicant_name__icontains=search_query) |
            Q(leave_type__icontains=search_query) |
            Q(reason__icontains=search_query) |
            Q(status__icontains=search_query)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        leave_requests = leave_requests.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(leave_requests, 10)  # 10 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Count by status
    status_counts = {
        'pending': LeaveRequest.objects.filter(status='Pending').count(),
        'approved': LeaveRequest.objects.filter(status='Approved').count(),
        'rejected': LeaveRequest.objects.filter(status='Rejected').count(),
        'cancelled': LeaveRequest.objects.filter(status='Cancelled').count(),
        'total': LeaveRequest.objects.count()
    }
    
    # Get total count for pagination display
    total_leave_requests = leave_requests.count()
    
    context = {
        'leave_requests': page_obj,
        'status_counts': status_counts,
        'search_query': search_query,
        'status_filter': status_filter,
        'total_leave_requests': total_leave_requests,
    }
    return render(request, 'dashboard/leaves.html', context)

@require_POST
@login_required
def leave_status_update(request, leave_id):
    """Update leave request status and update employee leave balance when approved"""
    try:
        leave = LeaveRequest.objects.get(id=leave_id)
        new_status = request.POST.get('status', '').strip()
        
        if new_status not in ['Pending', 'Approved', 'Rejected', 'Cancelled']:
            return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)
        
        old_status = leave.status
        leave.status = new_status
        leave.save()
        
        # If status changed to "Approved", subtract leave days from employee balance
        if new_status == 'Approved' and old_status != 'Approved':
            # Find employee by applicant_name
            if leave.applicant_name:
                name_parts = leave.applicant_name.strip().split(' ', 1)
                first_name = name_parts[0] if name_parts else ''
                last_name = name_parts[1] if len(name_parts) > 1 else ''
                
                employee_obj = None
                if first_name and last_name:
                    employee_obj = Employee.objects.filter(
                        first_name__iexact=first_name,
                        last_name__iexact=last_name
                    ).first()
                
                # If not found by name, try by user
                if not employee_obj and leave.user:
                    if leave.user.email:
                        employee_obj = Employee.objects.filter(email__iexact=leave.user.email).first()
                
                if employee_obj:
                    # Map leave_type to Employee model field
                    leave_type_mapping = {
                        'annual': 'annual_leave',
                        'sick': 'sick_leave',
                        'personal': 'personal_leave',
                        'maternity': 'maternity_leave',
                        'paternity': 'paternity_leave',
                        'emergency': 'emergency_leave',
                        # Also handle display names
                        'Annual Leave': 'annual_leave',
                        'Sick Leave': 'sick_leave',
                        'Personal Leave': 'personal_leave',
                        'Maternity': 'maternity_leave',
                        'Paternity': 'paternity_leave',
                        'Emergency': 'emergency_leave',
                    }
                    
                    employee_field = leave_type_mapping.get(leave.leave_type.lower() if leave.leave_type else '', None)
                    
                    if employee_field:
                        current_balance = getattr(employee_obj, employee_field, None) or 0
                        new_balance = max(0, current_balance - leave.days)  # Ensure non-negative
                        setattr(employee_obj, employee_field, new_balance)
                        employee_obj.save()
                        print(f"✅ Leave balance updated - {employee_field}: {current_balance} -> {new_balance} (subtracted {leave.days} days)")
        
        # If status changed from "Approved" to something else (Rejected/Cancelled), restore leave balance
        if old_status == 'Approved' and new_status in ['Rejected', 'Cancelled']:
            # Find employee
            if leave.applicant_name:
                name_parts = leave.applicant_name.strip().split(' ', 1)
                first_name = name_parts[0] if name_parts else ''
                last_name = name_parts[1] if len(name_parts) > 1 else ''
                
                employee_obj = None
                if first_name and last_name:
                    employee_obj = Employee.objects.filter(
                        first_name__iexact=first_name,
                        last_name__iexact=last_name
                    ).first()
                
                if not employee_obj and leave.user and leave.user.email:
                    employee_obj = Employee.objects.filter(email__iexact=leave.user.email).first()
                
                if employee_obj:
                    # Map leave_type to Employee model field
                    leave_type_mapping = {
                        'annual': 'annual_leave',
                        'sick': 'sick_leave',
                        'personal': 'personal_leave',
                        'maternity': 'maternity_leave',
                        'paternity': 'paternity_leave',
                        'emergency': 'emergency_leave',
                        'Annual Leave': 'annual_leave',
                        'Sick Leave': 'sick_leave',
                        'Personal Leave': 'personal_leave',
                        'Maternity': 'maternity_leave',
                        'Paternity': 'paternity_leave',
                        'Emergency': 'emergency_leave',
                    }
                    
                    employee_field = leave_type_mapping.get(leave.leave_type.lower() if leave.leave_type else '', None)
                    
                    if employee_field:
                        current_balance = getattr(employee_obj, employee_field, None) or 0
                        new_balance = current_balance + leave.days  # Restore the days
                        setattr(employee_obj, employee_field, new_balance)
                        employee_obj.save()
                        print(f"✅ Leave balance restored - {employee_field}: {current_balance} -> {new_balance} (restored {leave.days} days)")
        
        messages.success(request, f'Leave request #{leave_id} status updated from {old_status} to {new_status}')
        return JsonResponse({
            'success': True,
            'message': f'Status updated to {new_status}',
            'status': new_status
        })
    except LeaveRequest.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Leave request not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def leads(request):
    
    # Get all active leads
    leads_list = Lead.objects.filter(is_active=True).order_by('-created_at')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        leads_list = leads_list.filter(
            Q(name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(company__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(owner__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(leads_list, 10)  # Show 10 leads per page
    page_number = request.GET.get('page')
    leads = paginator.get_page(page_number)

    # Determine conversion status by cross-checking ClientOnboarding records
    def normalize_email(value):
        return value.strip().lower() if value else ''

    def normalize_phone(value):
        if not value:
            return ''
        return re.sub(r'\D+', '', value)

    client_contacts = list(ClientOnboarding.objects.all().values('client_email', 'client_phone', 'client_name'))
    client_emails = {normalize_email(item['client_email']) for item in client_contacts if item['client_email']}
    client_phones = {normalize_phone(item['client_phone']) for item in client_contacts if item['client_phone']}
    client_names = {normalize_email(item['client_name']) for item in client_contacts if item['client_name']}

    for lead in leads:
        email_key = normalize_email(lead.email)
        phone_key = normalize_phone(lead.phone)
        name_key = normalize_email(lead.name)

        converted = any([
            email_key and email_key in client_emails,
            phone_key and phone_key in client_phones,
            name_key and name_key in client_names
        ])

        lead.conversion_status = 'Converted' if converted else 'Pending'
        lead.conversion_badge = 'bg-success' if converted else 'bg-secondary'
    
    # Handle form submission
    if request.method == 'POST':
        form = LeadForm(request.POST)
        if form.is_valid():
            try:
                lead = form.save(commit=False)
                if request.user.is_authenticated:
                    lead.created_by = request.user
                lead.save()
                messages.success(request, f'Lead "{lead.name}" created successfully!')
                return redirect('leads')
            except Exception as e:
                messages.error(request, f'Error creating lead: {str(e)}')
        else:
            messages.error(request, 'Please fix the form errors below.')
    else:
        initial = {}
        if request.user.is_authenticated:
            initial['created_by'] = request.user.get_full_name() or request.user.username
        form = LeadForm(initial=initial)
    
    context = {
        'leads': leads,
        'form': form,
        'search_query': search_query,
        'total_leads': leads_list.count(),
    }
    
    return render(request, 'leads_section/leads.html', context)


@login_required
def lead_detail(request, lead_id):
    """
    View individual lead details
    यह individual lead की details show करता है
    """
    lead = get_object_or_404(Lead, id=lead_id, is_active=True)
    
    context = {
        'lead': lead,
    }
    
    return render(request, 'leads_section/lead_detail.html', context)


@login_required
def lead_edit(request, lead_id):
    """
    Edit existing lead
    यह existing lead को edit करने के लिए है
    """
    lead = get_object_or_404(Lead, id=lead_id, is_active=True)
    
    if request.method == 'POST':
        form = LeadForm(request.POST, instance=lead)
        if form.is_valid():
            try:
                updated_lead = form.save()
                messages.success(request, f'Lead "{updated_lead.name}" updated successfully!')
                return redirect('leads')
            except Exception as e:
                messages.error(request, f'Error updating lead: {str(e)}')
        else:
            messages.error(request, 'Please fix the form errors below.')
    else:
        form = LeadForm(instance=lead)
    
    context = {
        'form': form,
        'lead': lead,
        'is_edit': True,
    }
    
    return render(request, 'leads_section/lead_form.html', context)


@login_required
def lead_delete(request, lead_id):
    """
    Delete lead (soft delete)
    यह lead को delete करता है (soft delete)
    """
    lead = get_object_or_404(Lead, id=lead_id, is_active=True)
    
    if request.method == 'POST':
        lead.is_active = False
        lead.save()
        messages.success(request, f'Lead "{lead.name}" deleted successfully!')
        return redirect('leads')
    
    context = {
        'lead': lead,
    }
    
    return render(request, 'leads_section/lead_confirm_delete.html', context)


def lead_filter(request):
    """
    Filter leads by date criteria
    यह leads को date के basis पर filter करता है
    """
    if request.method == 'POST':
        form = LeadFilterForm(request.POST)
        if form.is_valid():
            filter_type = form.cleaned_data['filter_type']
            leads_list = Lead.objects.filter(is_active=True)
            
            if filter_type == 'date':
                single_date = form.cleaned_data['single_date']
                leads_list = leads_list.filter(due_date=single_date)
                
            elif filter_type == 'month':
                month = form.cleaned_data['month']
                year, month_num = month.split('-')
                leads_list = leads_list.filter(
                    due_date__year=year,
                    due_date__month=month_num
                )
                
            elif filter_type == 'year':
                year = form.cleaned_data['year']
                leads_list = leads_list.filter(due_date__year=year)
                
            elif filter_type == 'between':
                from_date = form.cleaned_data['from_date']
                to_date = form.cleaned_data['to_date']
                leads_list = leads_list.filter(
                    due_date__gte=from_date,
                    due_date__lte=to_date
                )
            
            # Return filtered results as JSON for AJAX
            filtered_leads = []
            for lead in leads_list:
                filtered_leads.append({
                    'id': lead.id,
                    'name': lead.name,
                    'email': lead.email or '-',
                    'phone': lead.phone or '-',
                    'company': lead.company or '-',
                    'owner': lead.owner,
                    'priority': lead.priority,
                    'next_action': lead.next_action or '-',
                    'due': lead.get_full_due_datetime().strftime('%d-%b-%Y %H:%M') if lead.get_full_due_datetime() else '-',
                    'priority_class': lead.get_priority_badge_class()
                })
            
            return JsonResponse({
                'success': True,
                'leads': filtered_leads,
                'count': len(filtered_leads)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid form data'})


def lead_export(request):
    """
    Export leads to CSV
    यह leads को CSV में export करता है
    """
    import csv
    from django.http import HttpResponse
    
    # Get all active leads
    leads = Lead.objects.filter(is_active=True).order_by('-created_at')
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="leads_export.csv"'
    
    writer = csv.writer(response)
    
    # Write headers
    writer.writerow([
        'Name', 'Email', 'Phone', 'Company', 'Source', 'Priority', 
        'Owner', 'Use Case', 'Next Action', 'Due Date', 'Due Time',
        'Website', 'Industry', 'City', 'Country', 'Budget', 
        'Timeline', 'Tags', 'Notes', 'Created At'
    ])
    
    # Write data
    for lead in leads:
        writer.writerow([
            lead.name,
            lead.email or '',
            lead.phone or '',
            lead.company or '',
            lead.source,
            lead.priority,
            lead.owner,
            lead.use_case,
            lead.next_action or '',
            lead.due_date or '',
            lead.due_time or '',
            lead.website or '',
            lead.industry or '',
            lead.city or '',
            lead.country or '',
            lead.budget or '',
            lead.timeline or '',
            lead.tags or '',
            lead.notes or '',
            lead.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    return response


def lead_import(request):
    """
    Import leads from CSV
    यह CSV से leads import करता है
    """
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        
        try:
            import csv
            import io
            
            # Read CSV file
            file_data = csv_file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(file_data))
            
            imported_count = 0
            error_count = 0
            
            for row in csv_reader:
                try:
                    # Create lead from CSV row
                    lead_data = {
                        'name': row.get('Name', ''),
                        'email': row.get('Email', '') or None,
                        'phone': row.get('Phone', '') or None,
                        'company': row.get('Company', '') or None,
                        'source': row.get('Source', 'Other'),
                        'priority': row.get('Priority', 'Med'),
                        'owner': row.get('Owner', ''),
                        'use_case': row.get('Use Case', ''),
                        'next_action': row.get('Next Action', 'None'),
                        'website': row.get('Website', '') or None,
                        'industry': row.get('Industry', '') or None,
                        'city': row.get('City', '') or None,
                        'country': row.get('Country', '') or None,
                        'budget': row.get('Budget', '') or None,
                        'timeline': row.get('Timeline', '') or None,
                        'tags': row.get('Tags', '') or None,
                        'notes': row.get('Notes', '') or None,
                    }
                    
                    # Parse dates if provided
                    if row.get('Due Date'):
                        try:
                            lead_data['due_date'] = datetime.strptime(row['Due Date'], '%Y-%m-%d').date()
                        except:
                            pass
                    
                    if row.get('Due Time'):
                        try:
                            lead_data['due_time'] = datetime.strptime(row['Due Time'], '%H:%M').time()
                        except:
                            pass
                    
                    # Create lead
                    Lead.objects.create(**lead_data)
                    imported_count += 1
                    
                except Exception as e:
                    error_count += 1
                    print(f"Error importing row: {e}")
                    continue
            
            messages.success(
                request, 
                f'Import completed! {imported_count} leads imported successfully. {error_count} errors occurred.'
            )
            
        except Exception as e:
            messages.error(request, f'Error importing file: {str(e)}')
    
    return redirect('leads')


def lead_get_data(request, lead_id):
    """
    Get lead data for edit modal
    यह edit modal के लिए lead data return करता है
    """
    try:
        lead = get_object_or_404(Lead, id=lead_id, is_active=True)
        
        data = {
            'id': lead.id,
            'name': lead.name,
            'email': lead.email or '',
            'phone': lead.phone or '',
            'company': lead.company or '',
            'owner': lead.owner,
            'source': lead.source,
            'priority': lead.priority,
            'use_case': lead.use_case,
            'next_action': lead.next_action or '',
            'due_date': lead.due_date.strftime('%Y-%m-%d') if lead.due_date else '',
            'due_time': lead.due_time.strftime('%H:%M') if lead.due_time else '',
            'website': lead.website or '',
            'industry': lead.industry or '',
            'city': lead.city or '',
            'country': lead.country or '',
            'budget': lead.budget or '',
            'timeline': lead.timeline or '',
            'tags': lead.tags or '',
            'notes': lead.notes or '',
            'created_at': lead.created_at.strftime('%d-%b-%Y %H:%M') if lead.created_at else '',
            'updated_at': lead.updated_at.strftime('%d-%b-%Y %H:%M') if lead.updated_at else '',
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_POST
def assign_engineer(request, lead_id):
    """
    Assign engineer to this lead (AJAX)
    POST expects: engineer (str)
    """
    try:
        lead = get_object_or_404(Lead, id=lead_id, is_active=True)
        engineer = request.POST.get('engineer', '').strip()
        if not engineer:
            return JsonResponse({'success': False, 'error': 'Engineer name is required.'}, status=400)
        lead.owner = engineer
        lead.save(update_fields=['owner'])
        return JsonResponse({'success': True, 'engineer': engineer})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)






@login_required
def accounts(request):
    """Accounts page - displays client receivables and employee account details with payroll"""
    from django.core.paginator import Paginator
    from django.db.models import Sum, Q
    from decimal import Decimal
    
    # Get all employees with their payroll information
    employees = Employee.objects.all().order_by('-created_at')
    
    # Pagination for employees
    employees_page_num = request.GET.get('emp_page', 1)
    employees_paginator = Paginator(employees, 10)  # Show 10 employees per page
    try:
        employees_page = employees_paginator.page(employees_page_num)
    except PageNotAnInteger:
        employees_page = employees_paginator.page(1)
    except EmptyPage:
        employees_page = employees_paginator.page(employees_paginator.num_pages)
    
    # Get all clients from ClientOnboarding
    clients_onboarding = ClientOnboarding.objects.all().order_by('-created_at')
    
    # Prepare client accounts data
    client_accounts = []
    for client in clients_onboarding:
        # Get all quotes for this client (match by client_name)
        client_quotes = Quote.objects.filter(client_name__iexact=client.client_name)
        
        # Calculate financial metrics
        total_quoted = client_quotes.aggregate(total=Sum('total'))['total'] or Decimal('0')
        
        # Amount invoiced = sum of accepted quotes
        amount_invoiced = client_quotes.filter(status='Accepted').aggregate(
            total=Sum('total')
        )['total'] or Decimal('0')
        
        # If no quotes, use project_cost from ClientOnboarding
        if total_quoted == 0 and client.project_cost:
            total_quoted = client.project_cost
            # If status is active or completed, consider it as invoiced
            if client.status in ['active', 'completed']:
                amount_invoiced = client.project_cost
        
        # Amount received - for now, use project_cost if status is completed
        # In a real system, this would come from a Payment model
        amount_received = Decimal('0')
        if client.status == 'completed':
            amount_received = amount_invoiced  # Assume full payment for completed projects
        
        # Outstanding = Invoiced - Received
        outstanding = amount_invoiced - amount_received
        
        # Get last payment date (for now, use updated_at if status is completed)
        last_payment = None
        if client.status == 'completed' and client.updated_at:
            last_payment = client.updated_at.date()
        
        # Get status for display
        if outstanding == 0 and amount_invoiced > 0:
            payment_status = 'Paid'
            status_badge = 'bg-success'
        elif amount_received > 0 and outstanding > 0:
            payment_status = 'Partially Paid'
            status_badge = 'bg-warning text-dark'
        elif amount_invoiced > 0:
            payment_status = 'Unpaid'
            status_badge = 'bg-danger'
        else:
            payment_status = 'Pending'
            status_badge = 'bg-secondary'
        
        client_accounts.append({
            'id': client.id,
            'client_name': client.client_name,
            'company_name': client.company_name,
            'email': client.client_email,
            'phone': client.client_phone,
            'total_quoted': total_quoted,
            'amount_invoiced': amount_invoiced,
            'amount_received': amount_received,
            'outstanding': outstanding,
            'last_payment': last_payment,
            'status': payment_status,
            'status_badge': status_badge,
            'project_name': client.project_name,
            'project_cost': client.project_cost,
            'quotes': client_quotes,
        })
    
    # Pagination for clients
    clients_page_num = request.GET.get('client_page', 1)
    clients_paginator = Paginator(client_accounts, 10)  # Show 10 clients per page
    try:
        clients_page = clients_paginator.page(clients_page_num)
    except PageNotAnInteger:
        clients_page = clients_paginator.page(1)
    except EmptyPage:
        clients_page = clients_paginator.page(clients_paginator.num_pages)
    
    # Get payment transactions for display
    payment_transactions = PaymentTransaction.objects.all().select_related('employee', 'processed_by').order_by('-payment_date', '-created_at')
    
    # Determine employees already paid for current month/year
    today = timezone.now().date()
    paid_this_month_ids = set(
        PaymentTransaction.objects.filter(
            payment_month=today.month,
            payment_year=today.year
        ).exclude(status__in=['failed', 'cancelled']).values_list('employee_id', flat=True)
    )
    
    # Pagination for payment transactions
    transactions_page_num = request.GET.get('trans_page', 1)
    transactions_paginator = Paginator(payment_transactions, 10)  # Show 10 transactions per page
    try:
        transactions_page = transactions_paginator.page(transactions_page_num)
    except PageNotAnInteger:
        transactions_page = transactions_paginator.page(1)
    except EmptyPage:
        transactions_page = transactions_paginator.page(transactions_paginator.num_pages)
    
    context = {
        'employees': employees_page,
        'clients': clients_page,
        'transactions': transactions_page,
        'paid_this_month_ids': paid_this_month_ids,
    }
    return render(request, 'accounnts/accounts.html', context)
## Kanban removed


@login_required
def clients(request):
    """Clients page - displays client accounts and onboarding information"""
    from django.core.paginator import Paginator
    from django.db.models import Sum, Q
    from decimal import Decimal
    
    # CLIENT ACCOUNTS SECTION
    # Search functionality for client accounts
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status_filter', '').strip()
    
    # Get all clients from ClientOnboarding
    clients_onboarding = ClientOnboarding.objects.all().order_by('-created_at')
    
    # Apply search filter for client accounts
    clients_for_accounts = clients_onboarding
    if search_query:
        clients_for_accounts = clients_onboarding.filter(
            Q(client_name__icontains=search_query) |
            Q(company_name__icontains=search_query) |
            Q(client_email__icontains=search_query) |
            Q(client_phone__icontains=search_query) |
            Q(project_name__icontains=search_query)
        )
    
    # Prepare client accounts data
    client_accounts = []
    for client in clients_for_accounts:
        # Get all quotes for this client (match by client_name)
        client_quotes = Quote.objects.filter(client_name__iexact=client.client_name)
        
        # Calculate financial metrics
        total_quoted = client_quotes.aggregate(total=Sum('total'))['total'] or Decimal('0')
        
        # Amount invoiced = sum of accepted quotes
        amount_invoiced = client_quotes.filter(status='Accepted').aggregate(
            total=Sum('total')
        )['total'] or Decimal('0')
        
        # If no quotes, use project_cost from ClientOnboarding
        if total_quoted == 0 and client.project_cost:
            total_quoted = client.project_cost
            # If status is active or completed, consider it as invoiced
            if client.status in ['active', 'completed']:
                amount_invoiced = client.project_cost
        
        # Amount received - check Invoice model
        amount_received = Decimal('0')
        invoices = Invoice.objects.filter(client_name__iexact=client.client_name)
        if invoices.exists():
            amount_received = invoices.aggregate(total=Sum('amount_received'))['total'] or Decimal('0')
        elif client.status == 'completed':
            amount_received = amount_invoiced  # Assume full payment for completed projects
        
        # Outstanding = Invoiced - Received
        outstanding = amount_invoiced - amount_received
        
        # Get last payment date
        last_payment = None
        if invoices.exists():
            last_invoice = invoices.order_by('-updated_at').first()
            if last_invoice and last_invoice.updated_at:
                last_payment = last_invoice.updated_at.date()
        elif client.status == 'completed' and client.updated_at:
            last_payment = client.updated_at.date()
        
        # Get status for display
        if outstanding == 0 and amount_invoiced > 0:
            payment_status = 'Paid'  # Paid
            status_badge = 'bg-success'
        elif amount_received > 0 and outstanding > 0:
            payment_status = 'Partially Paid'  # Partially Paid
            status_badge = 'bg-warning text-dark'
        elif amount_invoiced > 0:
            payment_status = 'Unpaid'  # Unpaid
            status_badge = 'bg-danger'
        else:
            payment_status = 'Pending'  # Pending
            status_badge = 'bg-secondary'
        
        client_accounts.append({
            'id': client.id,
            'client_name': client.client_name,
            'company_name': client.company_name,
            'email': client.client_email,
            'phone': client.client_phone,
            'total_quoted': total_quoted,
            'amount_invoiced': amount_invoiced,
            'amount_received': amount_received,
            'outstanding': outstanding,
            'last_payment': last_payment,
            'status': payment_status,
            'status_badge': status_badge,
            'project_name': client.project_name,
            'project_cost': client.project_cost,
            'project_status': client.status,
            'assigned_engineer': client.assigned_engineer,
            'start_date': client.start_date,
        })
    
    # Apply status filter
    if status_filter:
        client_accounts = [acc for acc in client_accounts if acc['status'] == status_filter]
    
    # Pagination for client accounts
    clients_page_num = request.GET.get('page', 1)
    clients_paginator = Paginator(client_accounts, 10)
    try:
        clients_page = clients_paginator.page(clients_page_num)
    except PageNotAnInteger:
        clients_page = clients_paginator.page(1)
    except EmptyPage:
        clients_page = clients_paginator.page(clients_paginator.num_pages)
    
    # ONBOARDING CLIENT SECTION - Handle POST for creating onboarding
    if request.method == 'POST' and 'onboard_submit' in request.POST:
        try:
            client_name = request.POST.get('client_name', '').strip()
            project_name = request.POST.get('project_name', '').strip()
            project_duration = request.POST.get('project_duration', '').strip()
            project_cost = request.POST.get('project_cost', '').strip()
            assigned_engineer = request.POST.get('assigned_engineer', '').strip()
            
            if not client_name or not project_name or not project_duration or not project_cost or not assigned_engineer:
                messages.error(request, 'Please fill in all required fields!')
                return redirect('clients')
            
            # Parse start_date if provided
            start_date = None
            start_date_str = request.POST.get('start_date', '').strip()
            if start_date_str:
                try:
                    from django.utils.dateparse import parse_date
                    start_date = parse_date(start_date_str)
                except (ValueError, TypeError):
                    start_date = None
            
            # Prepare optional fields
            company_name = request.POST.get('company_name', '').strip() or None
            client_email = request.POST.get('client_email', '').strip() or None
            client_phone = request.POST.get('client_phone', '').strip() or None
            project_description = request.POST.get('project_description', '').strip() or None
            
            # Create new onboarding
            ClientOnboarding.objects.create(
                client_name=client_name,
                company_name=company_name,
                client_email=client_email,
                client_phone=client_phone,
                project_name=project_name,
                project_description=project_description,
                project_duration=int(project_duration),
                duration_unit=request.POST.get('duration_unit', 'months'),
                project_cost=Decimal(str(project_cost)),
                assigned_engineer=assigned_engineer,
                start_date=start_date,
                status=request.POST.get('status', 'active')
            )
            
            messages.success(request, f'Client {client_name} onboarded successfully!')
            return redirect('clients')
        except Exception as e:
            messages.error(request, f'Error onboarding client: {str(e)}')
            return redirect('clients')
    
    # ONBOARDING CLIENT SECTION - Fetch Leads data
    onboard_search_query = request.GET.get('onboard_search', '').strip()
    source_filter = request.GET.get('source_filter', '').strip()
    owner_filter = request.GET.get('owner_filter', '').strip()
    
    leads_list = Lead.objects.filter(is_active=True).order_by('-created_at')
    
    if onboard_search_query:
        leads_list = leads_list.filter(
            Q(name__icontains=onboard_search_query) |
            Q(company__icontains=onboard_search_query) |
            Q(email__icontains=onboard_search_query) |
            Q(phone__icontains=onboard_search_query) |
            Q(owner__icontains=onboard_search_query)
        )
    
    # Apply filters
    if source_filter:
        leads_list = leads_list.filter(source=source_filter)
    
    if owner_filter:
        leads_list = leads_list.filter(owner__icontains=owner_filter)
    
    # Get available clients from Leads (excluding already onboarded ones)
    onboarded_client_names = set(ClientOnboarding.objects.values_list('client_name', flat=True).distinct())
    
    # Paginate leads (10 per page)
    leads_paginator = Paginator(leads_list, 10)
    leads_page_num = request.GET.get('leads_page', 1)
    try:
        leads_page = leads_paginator.page(leads_page_num)
    except PageNotAnInteger:
        leads_page = leads_paginator.page(1)
    except EmptyPage:
        leads_page = leads_paginator.page(leads_paginator.num_pages)
    
    # Add onboard status to each lead in the paginated page
    for lead in leads_page:
        lead.is_onboarded = lead.name in onboarded_client_names
    leads_for_onboarding = Lead.objects.filter(
        is_active=True
    ).exclude(name__in=onboarded_client_names).order_by('name')
    
    available_clients = []
    for lead in leads_for_onboarding:
        available_clients.append((
            lead.name,
            lead.company or '',
            lead.email or '',
            lead.phone or ''
        ))
    
    # Get all unique departments from Employee table
    from myapp.models import Employee
    departments = Employee.objects.filter(
        status='active',
        department__isnull=False
    ).exclude(department='').values_list('department', flat=True).distinct().order_by('department')
    
    context = {
        # Client Accounts
        'clients': clients_page,
        'search_query': search_query,
        # Onboarding Client (Leads)
        'leads': leads_page,
        'onboard_search_query': onboard_search_query,
        'available_clients': available_clients,
        'departments': departments,
    }
    return render(request, 'dashboard/clients.html', context)


@login_required
def get_employees_by_department(request):
    """Get employees by department via AJAX"""
    from django.http import JsonResponse
    
    department = request.GET.get('department', '').strip()
    
    if not department:
        return JsonResponse({'success': False, 'error': 'Department is required'})
    
    try:
        from myapp.models import Employee
        employees = Employee.objects.filter(
            department__iexact=department,
            status='active'
        ).order_by('first_name', 'last_name')
        
        employees_list = []
        for emp in employees:
            emp_name = emp.get_full_name()
            # Count assigned projects for this employee
            project_count = ClientOnboarding.objects.filter(assigned_engineer__iexact=emp_name).count()
            employees_list.append({
                'id': emp.id,
                'name': emp_name,
                'designation': emp.designation or '',
                'project_count': project_count
            })
        
        return JsonResponse({
            'success': True,
            'employees': employees_list
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def get_project_details(request, client_id):
    """Get project details for a client via AJAX"""
    from django.http import JsonResponse
    
    try:
        # Get ClientOnboarding record by client_id
        onboarding = ClientOnboarding.objects.get(id=client_id)
        
        # Get status badge class
        status_badge_classes = {
            'active': 'bg-success',
            'pending': 'bg-warning text-dark',
            'on_hold': 'bg-info',
            'completed': 'bg-secondary'
        }
        status_badge = status_badge_classes.get(onboarding.status, 'bg-secondary')
        
        # Get status display
        status_display = onboarding.get_status_display()
        
        # Get duration unit display
        duration_unit_map = {
            'days': 'Days',
            'weeks': 'Weeks',
            'months': 'Months',
            'years': 'Years'
        }
        duration_unit_display = duration_unit_map.get(onboarding.duration_unit, onboarding.duration_unit)
        
        # Format dates
        start_date = onboarding.start_date.strftime('%d %b %Y') if onboarding.start_date else None
        created_at = onboarding.created_at.strftime('%d %b %Y, %I:%M %p') if onboarding.created_at else None
        updated_at = onboarding.updated_at.strftime('%d %b %Y, %I:%M %p') if onboarding.updated_at else None
        
        project_data = {
            'client_name': onboarding.client_name,
            'company_name': onboarding.company_name,
            'client_email': onboarding.client_email,
            'client_phone': onboarding.client_phone,
            'project_name': onboarding.project_name,
            'project_description': onboarding.project_description,
            'project_cost': str(onboarding.project_cost),
            'project_duration': onboarding.project_duration,
            'duration_unit': duration_unit_display,
            'assigned_engineer': onboarding.assigned_engineer,
            'status': onboarding.status,
            'status_display': status_display,
            'status_badge': status_badge,
            'start_date': start_date,
            'created_at': created_at,
            'updated_at': updated_at,
        }
        
        return JsonResponse({
            'success': True,
            'project': project_data
        })
    except ClientOnboarding.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Project not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
def update_lead_onboard_status(request):
    """Update onboard status for a lead"""
    from django.http import JsonResponse
    
    try:
        lead_id = request.POST.get('lead_id')
        lead_name = request.POST.get('lead_name')
        status = request.POST.get('status')
        
        if not lead_id or not lead_name or not status:
            return JsonResponse({'success': False, 'error': 'Missing required parameters'})
        
        lead = Lead.objects.get(id=lead_id, name=lead_name)
        
        if status == 'yes':
            # Check if onboarding already exists
            existing_onboarding = ClientOnboarding.objects.filter(client_name__iexact=lead_name).first()
            if not existing_onboarding:
                # Create a basic onboarding record
                ClientOnboarding.objects.create(
                    client_name=lead.name,
                    company_name=lead.company,
                    client_email=lead.email,
                    client_phone=lead.phone,
                    project_name=f"Project for {lead.name}",
                    project_duration=1,
                    duration_unit='months',
                    project_cost=Decimal('0.00'),
                    assigned_engineer='',
                    status='pending'
                )
        else:
            # Delete onboarding if exists
            ClientOnboarding.objects.filter(client_name__iexact=lead_name).delete()
        
        return JsonResponse({'success': True, 'message': 'Onboard status updated successfully'})
        
    except Lead.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Lead not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def invoices(request):
    """Invoice page - displays invoices based on accepted quotes and client onboarding"""
    from django.core.paginator import Paginator
    from django.db.models import Sum, Q
    from decimal import Decimal
    from datetime import datetime, date
    import json
    
    # Handle POST request for creating new invoice or updating existing invoice
    if request.method == 'POST':
        try:
            # Check if this is an update request
            invoice_id = request.POST.get('invoice_id')
            is_update = invoice_id and invoice_id.strip()
            invoice = None
            
            if is_update:
                try:
                    invoice = Invoice.objects.get(id=int(invoice_id))
                except (Invoice.DoesNotExist, ValueError):
                    messages.error(request, 'Invoice not found for update.')
                    return redirect('invoices')
            
            # Get client information
            client_name = request.POST.get('client_name', '').strip()
            if not client_name:
                messages.error(request, 'Client name is required.')
                return redirect('invoices')
            
            company = request.POST.get('company', '').strip() or None
            email = request.POST.get('email', '').strip() or None
            phone = request.POST.get('phone', '').strip() or None
            
            # Get invoice details
            currency = request.POST.get('currency', 'INR')
            invoice_date_str = request.POST.get('invoice_date', '')
            owner = request.POST.get('owner', '').strip()
            if not owner:
                messages.error(request, 'Owner/Assignee is required.')
                return redirect('invoices')
            
            # Parse invoice date
            invoice_date = None
            if invoice_date_str:
                try:
                    invoice_date = datetime.strptime(invoice_date_str, '%Y-%m-%d').date()
                except ValueError:
                    invoice_date = date.today()
            else:
                invoice_date = date.today()
            
            invoice_number = request.POST.get('invoice_number', '').strip()
            if not invoice_number:
                invoice_number = generate_invoice_number_for_date(invoice_date)
            
            # Check if invoice number already exists (skip check if updating same invoice)
            existing_invoice = Invoice.objects.filter(invoice_number=invoice_number).first()
            if existing_invoice and (not is_update or existing_invoice.id != invoice.id):
                messages.error(request, f'Invoice number {invoice_number} already exists. Please use a different number.')
                return redirect('invoices')
            
            # Get payment status
            payment_status = request.POST.get('status', 'Unpaid')
            
            # Get items data (allow sparse indices when rows removed)
            items = []
            item_index_pattern = re.compile(r'^items\[(\d+)\]\[description\]$')
            item_indices = sorted(
                {int(match.group(1)) for key in request.POST.keys()
                 if (match := item_index_pattern.match(key))}
            )
            
            for item_index in item_indices:
                desc_key = f'items[{item_index}][description]'
                description = request.POST.get(desc_key, '').strip()
                if not description:
                    continue
                
                quantity_str = request.POST.get(f'items[{item_index}][quantity]', '1') or '1'
                price_str = request.POST.get(f'items[{item_index}][price]', '0') or '0'
                quantity = Decimal(quantity_str)
                price = Decimal(price_str)
                
                items.append({
                    'description': description,
                    'quantity': float(quantity),
                    'price': float(price),
                })
            
            if not items:
                messages.error(request, 'At least one item is required.')
                return redirect('invoices')
            
            # Calculate totals
            subtotal = Decimal(request.POST.get('subtotal', '0') or '0')
            discount = Decimal(request.POST.get('discount', '0') or '0')
            
            # Get GST information
            apply_gst = request.POST.get('apply_gst', 'no')
            gst_percent = Decimal('0')
            gst_amount = Decimal('0')
            if apply_gst == 'yes':
                gst_percent = Decimal(request.POST.get('gst_percent', '0') or '0')
                gst_amount = (subtotal * gst_percent) / 100
            
            total = Decimal(request.POST.get('total', '0') or '0')
            amount_received = Decimal(request.POST.get('amount_received', '0') or '0')
            
            # Get additional information
            notes = request.POST.get('notes', '').strip() or None
            terms = request.POST.get('terms', '').strip() or None
            
            # Update existing invoice or create new one
            if is_update and invoice:
                # Update existing invoice
                invoice.client_name = client_name
                invoice.company = company
                invoice.email = email
                invoice.phone = phone
                invoice.invoice_number = invoice_number
                invoice.invoice_date = invoice_date
                invoice.owner = owner
                invoice.status = payment_status
                invoice.currency = currency
                invoice.subtotal = subtotal
                invoice.discount = discount
                invoice.gst_percent = gst_percent
                invoice.gst_amount = gst_amount
                invoice.total = total
                invoice.amount_received = amount_received
                invoice.notes = notes
                invoice.terms = terms
                invoice.items = items
                invoice.save()
                messages.success(request, f'Invoice {invoice_number} updated successfully!')
            else:
                # Create new Invoice object
                invoice = Invoice.objects.create(
                    client_name=client_name,
                    company=company,
                    email=email,
                    phone=phone,
                    invoice_number=invoice_number,
                    invoice_date=invoice_date,
                    owner=owner,
                    status=payment_status,
                    currency=currency,
                    subtotal=subtotal,
                    discount=discount,
                    gst_percent=gst_percent,
                    gst_amount=gst_amount,
                    total=total,
                    amount_received=amount_received,
                    notes=notes,
                    terms=terms,
                    items=items,
                )
                messages.success(request, f'Invoice {invoice_number} created successfully!')
            
            # If payment status is Paid, try to create/update ClientOnboarding record
            if payment_status == 'Paid':
                client_onboard = ClientOnboarding.objects.filter(
                    client_name__iexact=client_name
                ).first()
                
                if not client_onboard:
                    # Create a basic client onboarding record with completed status
                    # Required fields: project_name, project_duration, project_cost, assigned_engineer
                    ClientOnboarding.objects.create(
                        client_name=client_name,
                        company_name=company or '',
                        client_email=email or '',
                        client_phone=phone or '',
                        project_name=f'Invoice {invoice_number}',
                        project_description=f'Invoice created for {invoice_number}',
                        project_duration=1,  # Default duration
                        duration_unit='months',  # Default unit
                        project_cost=total,
                        status='completed',
                        assigned_engineer=owner,
                        start_date=invoice_date,
                    )
                elif client_onboard.status != 'completed':
                    client_onboard.status = 'completed'
                    client_onboard.save()
            
            return redirect('invoices')
            
        except Exception as e:
            messages.error(request, f'Error creating invoice: {str(e)}')
            return redirect('invoices')
    
    # GET request handling
    # Search functionality
    search_query = request.GET.get('search', '').strip()
    
    # Get all invoices from Invoice model
    invoices_list = Invoice.objects.all().order_by('-invoice_date', '-created_at')
    
    # Apply search filter to invoices
    if search_query:
        invoices_list = invoices_list.filter(
            Q(invoice_number__icontains=search_query) |
            Q(client_name__icontains=search_query) |
            Q(company__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(owner__icontains=search_query)
        )
    
    # Prepare invoice data from Invoice model
    invoice_data = []
    for invoice in invoices_list:
        pending_balance = invoice.total - invoice.amount_received
        if pending_balance < Decimal('0.00'):
            pending_balance = Decimal('0.00')
        
        # Auto-update status if it doesn't match the calculated status
        calculated_status = invoice.calculate_status()
        if invoice.status != calculated_status and invoice.status != 'Cancelled':
            invoice.status = calculated_status
            invoice.save(update_fields=['status', 'updated_at'])
        
        invoice_data.append({
            'id': invoice.id,
            'invoice_number': invoice.invoice_number,
            'type': 'invoice',
            'client_name': invoice.client_name,
            'company': invoice.company,
            'email': invoice.email,
            'phone': invoice.phone,
            'amount': invoice.total,
            'currency': invoice.currency,
            'status': invoice.status,
            'status_badge': invoice.get_status_badge_class(),
            'date': invoice.invoice_date,
            'owner': invoice.owner,
            'pending_balance': pending_balance,
        })
    
    # Sort by date (newest first)
    invoice_data.sort(key=lambda x: x['date'], reverse=True)
    
    # Pagination
    paginator = Paginator(invoice_data, 10)  # Show 10 invoices per page
    page_num = request.GET.get('page', 1)
    try:
        invoices_page = paginator.page(page_num)
    except PageNotAnInteger:
        invoices_page = paginator.page(1)
    except EmptyPage:
        invoices_page = paginator.page(paginator.num_pages)
    
    # Calculate statistics
    total_invoices = len(invoice_data)
    total_amount = sum(Decimal(str(inv['amount'])) for inv in invoice_data)
    paid_count = sum(1 for inv in invoice_data if inv['status'] == 'Paid')
    unpaid_count = sum(1 for inv in invoice_data if inv['status'] == 'Unpaid')
    
    # Prepare selected invoice details if requested
    open_invoice_id = request.GET.get('open_invoice')
    selected_invoice = None
    if open_invoice_id:
        try:
            selected_obj = Invoice.objects.get(id=int(open_invoice_id))
            history_entries = selected_obj.payment_history if isinstance(selected_obj.payment_history, list) else []
            formatted_history = []
            for entry in history_entries:
                amount_val = Decimal(str(entry.get('amount', 0)))
                entry_date = entry.get('date')
                entry_created = entry.get('created_at')
                display_date = ''
                if entry_date:
                    try:
                        display_date = datetime.strptime(entry_date, '%Y-%m-%d').strftime('%b %d, %Y')
                    except ValueError:
                        display_date = entry_date
                elif entry_created:
                    try:
                        display_date = datetime.fromisoformat(entry_created).strftime('%b %d, %Y')
                    except ValueError:
                        display_date = entry_created
                formatted_history.append({
                    'amount': float(amount_val),
                    'amount_display': f"{amount_val:,.2f}",
                    'date': entry_date or '',
                    'date_display': display_date or ''
                })
            selected_invoice = {
                'id': selected_obj.id,
                'invoice_number': selected_obj.invoice_number,
                'client_name': selected_obj.client_name,
                'company': selected_obj.company or '',
                'email': selected_obj.email or '',
                'phone': selected_obj.phone or '',
                'currency': selected_obj.currency,
                'total': float(selected_obj.total),
                'amount_received': float(selected_obj.amount_received),
                'pending_balance': float(selected_obj.get_pending_balance()),
                'payment_history': formatted_history,
                'invoice_date': selected_obj.invoice_date.strftime('%b %d, %Y') if selected_obj.invoice_date else '',
            }
        except (Invoice.DoesNotExist, ValueError, TypeError):
            selected_invoice = None

    # Get existing clients for the dropdown
    existing_clients = []
    
    # Get unique clients from Invoice model
    invoice_clients = Invoice.objects.values('client_name', 'company', 'email', 'phone').distinct()
    for invoice_client in invoice_clients:
        if invoice_client['client_name']:
            existing_clients.append({
                'name': invoice_client['client_name'],
                'company': invoice_client.get('company') or '',
                'email': invoice_client.get('email') or '',
                'phone': invoice_client.get('phone') or '',
            })
    
    # Get unique clients from Quote model
    quote_clients = Quote.objects.values('client_name', 'company', 'email', 'phone').distinct()
    for quote_client in quote_clients:
        if quote_client['client_name']:
            # Check if client already exists
            if not any(client['name'].lower() == quote_client['client_name'].lower() for client in existing_clients):
                existing_clients.append({
                    'name': quote_client['client_name'],
                    'company': quote_client.get('company') or '',
                    'email': quote_client.get('email') or '',
                    'phone': quote_client.get('phone') or '',
                })
    
    # Get unique clients from ClientOnboarding model
    onboarding_clients = ClientOnboarding.objects.values('client_name', 'company_name', 'client_email', 'client_phone').distinct()
    for onboard_client in onboarding_clients:
        if onboard_client['client_name']:
            # Check if client already exists
            if not any(client['name'].lower() == onboard_client['client_name'].lower() for client in existing_clients):
                existing_clients.append({
                    'name': onboard_client['client_name'],
                    'company': onboard_client.get('company_name') or '',
                    'email': onboard_client.get('client_email') or '',
                    'phone': onboard_client.get('client_phone') or '',
                })
    
    # Sort clients by name
    existing_clients.sort(key=lambda x: x['name'].lower())
    
    today = timezone.localdate()
    suggested_invoice_number = generate_invoice_number_for_date(today)
    
    # Handle edit invoice
    edit_invoice_id = request.GET.get('edit_invoice')
    edit_invoice = None
    if edit_invoice_id:
        try:
            edit_invoice_obj = Invoice.objects.get(id=int(edit_invoice_id))
            edit_invoice = {
                'id': edit_invoice_obj.id,
                'client_name': edit_invoice_obj.client_name,
                'company': edit_invoice_obj.company or '',
                'email': edit_invoice_obj.email or '',
                'phone': edit_invoice_obj.phone or '',
                'invoice_number': edit_invoice_obj.invoice_number,
                'invoice_date': edit_invoice_obj.invoice_date.isoformat() if edit_invoice_obj.invoice_date else today.isoformat(),
                'owner': edit_invoice_obj.owner or '',
                'currency': edit_invoice_obj.currency,
                'subtotal': float(edit_invoice_obj.subtotal),
                'discount': float(edit_invoice_obj.discount),
                'apply_gst': 'yes' if edit_invoice_obj.gst_percent > 0 else 'no',
                'gst_percent': float(edit_invoice_obj.gst_percent),
                'gst_amount': float(edit_invoice_obj.gst_amount),
                'total': float(edit_invoice_obj.total),
                'amount_received': float(edit_invoice_obj.amount_received),
                'status': edit_invoice_obj.status,
                'notes': edit_invoice_obj.notes or '',
                'terms': edit_invoice_obj.terms or '',
                'items': edit_invoice_obj.items if isinstance(edit_invoice_obj.items, list) else [],
            }
        except (Invoice.DoesNotExist, ValueError, TypeError):
            edit_invoice = None
    
    context = {
        'invoices': invoices_page,
        'search_query': search_query,
        'total_invoices': total_invoices,
        'total_amount': total_amount,
        'paid_count': paid_count,
        'unpaid_count': unpaid_count,
        'existing_clients': existing_clients,
        'suggested_invoice_number': suggested_invoice_number,
        'company_profile': COMPANY_PROFILE,
        'selected_invoice': selected_invoice,
        'today_iso': today.isoformat(),
        'edit_invoice': edit_invoice,
    }
    return render(request, 'dashboard/invoices.html', context)


@login_required
def invoice_edit(request, invoice_type, invoice_id):
    """Edit invoice - redirects to appropriate edit page based on invoice type"""
    if invoice_type == 'invoice':
        # For Invoice model, redirect to invoices page with edit capability
        try:
            invoice = Invoice.objects.get(id=invoice_id)
            # Redirect to invoices page with edit_invoice parameter to open edit form
            return redirect(f"{reverse('invoices')}?edit_invoice={invoice_id}#create-invoice")
        except Invoice.DoesNotExist:
            messages.error(request, 'Invoice not found.')
            return redirect('invoices')
    elif invoice_type == 'quote':
        # Redirect to quotes page or create a quote edit modal/page
        # For now, redirect to quotes page with a message
        try:
            quote = Quote.objects.get(id=invoice_id)
            messages.info(request, f'To edit quote {quote.quote_number}, please use the Quotes page.')
            return redirect('quotes')
        except Quote.DoesNotExist:
            messages.error(request, 'Quote not found.')
            return redirect('invoices')
    elif invoice_type == 'onboarding':
        # Redirect to project management page where onboarding can be edited
        try:
            onboard = ClientOnboarding.objects.get(id=invoice_id)
            messages.info(request, f'To edit invoice for {onboard.client_name}, please use the Project Management page.')
            return redirect('project_management')
        except ClientOnboarding.DoesNotExist:
            messages.error(request, 'Client onboarding record not found.')
            return redirect('invoices')
    else:
        messages.error(request, 'Invalid invoice type.')
        return redirect('invoices')


@login_required
@require_POST
def invoice_delete(request, invoice_type, invoice_id):
    """Delete invoice - deletes the invoice, quote, or client onboarding record"""
    try:
        if invoice_type == 'invoice':
            invoice = get_object_or_404(Invoice, id=invoice_id)
            invoice_number = invoice.invoice_number
            client_name = invoice.client_name
            invoice.delete()
            messages.success(request, f'Invoice {invoice_number} for {client_name} deleted successfully!')
        elif invoice_type == 'quote':
            quote = get_object_or_404(Quote, id=invoice_id)
            quote_number = quote.quote_number
            client_name = quote.client_name
            quote.delete()
            messages.success(request, f'Invoice (Quote {quote_number}) for {client_name} deleted successfully!')
        elif invoice_type == 'onboarding':
            onboard = get_object_or_404(ClientOnboarding, id=invoice_id)
            client_name = onboard.client_name
            invoice_number = f'INV-{onboard.id:05d}'
            onboard.delete()
            messages.success(request, f'Invoice ({invoice_number}) for {client_name} deleted successfully!')
        else:
            messages.error(request, 'Invalid invoice type.')
            return redirect('invoices')
    except Exception as e:
        messages.error(request, f'Error deleting invoice: {str(e)}')
    
    return redirect('invoices')


@login_required
@require_POST
def invoice_pay_due(request, invoice_id):
    """Mark invoice as paid by clearing pending balance"""
    invoice = get_object_or_404(Invoice, id=invoice_id)
    try:
        pay_amount_str = request.POST.get('pay_amount', '').strip() or '0'
        pay_amount = Decimal(pay_amount_str)
    except (InvalidOperation, TypeError):
        pay_amount = Decimal('0')
    pay_date_str = request.POST.get('pay_date')
    pay_date = timezone.now().date()
    if pay_date_str:
        try:
            pay_date = datetime.strptime(pay_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    pending_before = Decimal(invoice.get_pending_balance())
    if pending_before <= 0:
        messages.info(request, f'Invoice {invoice.invoice_number} is already fully paid.')
        return redirect(f"{reverse('invoices')}?open_invoice={invoice.id}")
    
    if pay_amount <= 0 or pay_amount > pending_before:
        pay_amount = pending_before
    
    invoice.amount_received = Decimal(invoice.amount_received) + pay_amount
    history = list(invoice.payment_history or [])
    history.append({
        'amount': float(pay_amount),
        'date': pay_date.isoformat(),
        'created_at': timezone.now().isoformat()
    })
    invoice.payment_history = history
    if invoice.amount_received >= invoice.total:
        invoice.amount_received = invoice.total
        invoice.status = 'Paid'
    elif invoice.amount_received > 0:
        invoice.status = 'Partial'
    
    invoice.save(update_fields=['amount_received', 'status', 'updated_at', 'payment_history'])
    messages.success(request, f'INR {pay_amount:,.2f} applied to invoice {invoice.invoice_number}. Pending balance updated.')
    return redirect(f"{reverse('invoices')}?open_invoice={invoice.id}")


@login_required
@require_POST
def invoice_table_pdf_download(request):
    """Generate quick PDF using data provided from invoices table."""
    if not REPORTLAB_AVAILABLE:
        return JsonResponse({'error': 'PDF generation library (reportlab) is not installed.'}, status=400)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': 'Invalid request payload.'}, status=400)

    invoice_id = payload.get('invoice_id')
    invoice = None
    if invoice_id:
        try:
            invoice = Invoice.objects.get(id=int(invoice_id))
        except (Invoice.DoesNotExist, ValueError, TypeError):
            invoice = None

    # If we have a real invoice, prefer trusted DB values
    if invoice:
        invoice_number = invoice.invoice_number
        client_name = invoice.client_name
        company = invoice.company or ''
        email = invoice.email or ''
        phone = invoice.phone or ''
        amount_value = invoice.total or Decimal('0.00')
        amount_received_value = invoice.amount_received or Decimal('0.00')
        pending_balance_value = invoice.get_pending_balance()
        currency = invoice.currency or 'INR'
        status_text = invoice.status or 'Unpaid'
        invoice_date = invoice.invoice_date or date.today()
        owner = invoice.owner or ''
    else:
        # Fallback to table snapshot data
        invoice_number = (payload.get('invoice_number') or '').strip()
        client_name = (payload.get('client_name') or '').strip()
        company = (payload.get('company') or '').strip()
        email = (payload.get('email') or '').strip()
        phone = (payload.get('phone') or '').strip()
        amount_raw = payload.get('amount') or '0'
        currency = (payload.get('currency') or 'INR').strip()
        status_text = (payload.get('status') or 'Unpaid').strip()
        date_display = payload.get('date') or ''
        owner = (payload.get('owner') or '').strip()

        if not invoice_number or not client_name:
            return JsonResponse({'error': 'Invoice number and client name are required.'}, status=400)

        try:
            invoice_date = datetime.strptime(date_display, '%b %d, %Y').date()
        except (ValueError, TypeError):
            invoice_date = date.today()

        try:
            amount_value = Decimal(str(amount_raw))
        except (InvalidOperation, TypeError):
            amount_value = Decimal('0.00')
        
        # For snapshot data, set defaults
        amount_received_value = Decimal('0.00')
        pending_balance_value = amount_value

    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=36)
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'SnapshotTitle',
            parent=styles['Heading1'],
            fontSize=22,
            textColor=colors.HexColor('#2c3e50'),
            alignment=TA_CENTER,
            spaceAfter=20
        )

        normal_style = styles['Normal']
        normal_style.fontSize = 11

        elements = []
        elements.append(Paragraph("Invoice Snapshot", title_style))
        elements.append(Paragraph(f"Generated on {timezone.now().strftime('%d %b %Y, %I:%M %p')}", normal_style))
        elements.append(Spacer(1, 0.2 * inch))

        currency_symbol = {'USD': '$', 'EUR': '€'}.get(currency, '₹')
        
        due_display = f"{currency_symbol} {float(pending_balance_value):,.2f}" if pending_balance_value > 0 else f"{currency_symbol} {0:,.2f} (No Due)"
        summary_data = [
            ['Invoice #', invoice_number],
            ['Status', status_text],
            ['Owner/Assignee', owner or '-'],
            ['Date', invoice_date.strftime('%B %d, %Y')],
            ['Client Name', client_name],
            ['Company', company or '-'],
            ['Email', email or '-'],
            ['Phone', phone or '-'],
            ['Total Amount', f"{currency_symbol} {float(amount_value):,.2f}"],
            ['Previous Payment', f"{currency_symbol} {float(amount_received_value):,.2f}"],
            ['Due Payment', due_display],
        ]

        summary_table = Table(summary_data, colWidths=[2.2 * inch, 3.8 * inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#f5f5f5')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#d0d0d0')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#d0d0d0')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))

        elements.append(summary_table)
        elements.append(Spacer(1, 0.3 * inch))

        elements.append(Paragraph(
            "This PDF contains snapshot details captured directly from the invoices table. "
            "For a detailed invoice with line items and notes, please open the invoice record.",
            normal_style
        ))

        doc.build(elements)

        pdf = buffer.getvalue()
        buffer.close()

        response = HttpResponse(content_type='application/pdf')
        filename = f"Invoice_{invoice_number}_snapshot.pdf".replace(' ', '_')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = len(pdf)
        response.write(pdf)
        return response

    except Exception as exc:
        return JsonResponse({'error': f'Error generating PDF: {str(exc)}'}, status=500)


@login_required
def invoice_detail(request, invoice_id):
    """Return full invoice details as JSON (used for modal view)."""
    invoice = get_object_or_404(Invoice, id=invoice_id)
    raw_items = invoice.items if isinstance(invoice.items, list) else []
    items = []
    for item in raw_items:
        if isinstance(item, dict):
            items.append({
                'description': item.get('description') or item.get('name') or 'Item',
                'quantity': item.get('quantity', 1),
                'unit_price': item.get('unit_price', item.get('price', 0)),
                'total': item.get('total', item.get('amount', 0)),
            })
        else:
            items.append({
                'description': str(item),
                'quantity': 1,
                'unit_price': 0,
                'total': 0,
            })

    history_entries = []
    raw_history = invoice.payment_history if isinstance(invoice.payment_history, list) else []
    for entry in raw_history:
        amount_val = entry.get('amount', 0)
        try:
            amount_val = float(amount_val)
        except (TypeError, ValueError):
            amount_val = 0
        date_raw = entry.get('date')
        date_display = ''
        if date_raw:
            try:
                date_display = datetime.strptime(date_raw, '%Y-%m-%d').strftime('%b %d, %Y')
            except ValueError:
                date_display = date_raw
        elif entry.get('created_at'):
            try:
                date_display = datetime.fromisoformat(entry['created_at']).strftime('%b %d, %Y')
            except ValueError:
                date_display = entry['created_at']
        history_entries.append({
            'amount': amount_val,
            'date': date_raw or '',
            'date_display': date_display
        })

    data = {
        'id': invoice.id,
        'invoice_number': invoice.invoice_number,
        'status': invoice.status,
        'status_badge': invoice.get_status_badge_class(),
        'invoice_date': invoice.invoice_date.strftime('%b %d, %Y') if invoice.invoice_date else '',
        'invoice_date_iso': invoice.invoice_date.isoformat() if invoice.invoice_date else '',
        'owner': invoice.owner,
        'currency': invoice.currency,
        'created_at': invoice.created_at.strftime('%b %d, %Y %H:%M'),
        'client_name': invoice.client_name,
        'company': invoice.company or '',
        'email': invoice.email or '',
        'phone': invoice.phone or '',
        'subtotal': str(invoice.subtotal),
        'discount': str(invoice.discount),
        'gst_percent': str(invoice.gst_percent),
        'gst_amount': str(invoice.gst_amount),
        'total': str(invoice.total),
        'amount_received': str(invoice.amount_received),
        'pending_balance': str(invoice.get_pending_balance()),
        'notes': invoice.notes or '',
        'terms': invoice.terms or '',
        'items': items,
        'payment_history': history_entries,
    }
    return JsonResponse(data)


@login_required
def invoice_pdf_download(request, invoice_type, invoice_id):
    """Generate and download invoice as PDF"""
    if not REPORTLAB_AVAILABLE:
        messages.error(request, 'PDF generation library (reportlab) is not installed. Please install it to download invoices.')
        return redirect('invoices')
    
    try:
        # Get invoice data based on type
        if invoice_type == 'invoice':
            invoice = get_object_or_404(Invoice, id=invoice_id)
            invoice_data = {
                'invoice_number': invoice.invoice_number,
                'client_name': invoice.client_name,
                'company': invoice.company or '',
                'email': invoice.email or '',
                'phone': invoice.phone or '',
                'amount': invoice.total,
                'currency': invoice.currency,
                'date': invoice.invoice_date,
                'owner': invoice.owner,
                'items': invoice.items if invoice.items else [],
                'subtotal': invoice.subtotal,
                'discount': invoice.discount,
                'gst_percent': invoice.gst_percent,
                'gst_amount': invoice.gst_amount,
                'total': invoice.total,
                'amount_received': invoice.amount_received,
                'pending_balance': invoice.get_pending_balance(),
                'notes': invoice.notes or '',
                'terms': invoice.terms or '',
                'payment_history': invoice.payment_history if isinstance(invoice.payment_history, list) else [],
            }
        elif invoice_type == 'quote':
            quote = get_object_or_404(Quote, id=invoice_id)
            invoice_data = {
                'invoice_number': quote.quote_number,
                'client_name': quote.client_name,
                'company': quote.company or '',
                'email': quote.email or '',
                'phone': quote.phone or '',
                'amount': quote.total,
                'currency': quote.currency,
                'date': quote.created_at.date(),
                'owner': quote.owner,
                'items': quote.items if quote.items else [],
                'subtotal': quote.subtotal,
                'discount': quote.discount,
                'gst_percent': Decimal('0.00'),
                'gst_amount': Decimal('0.00'),
                'total': quote.total,
                'notes': quote.notes or '',
                'terms': quote.terms or '',
                'valid_until': quote.valid_until,
                'payment_history': [],
            }
        elif invoice_type == 'onboarding':
            onboard = get_object_or_404(ClientOnboarding, id=invoice_id)
            invoice_data = {
                'invoice_number': f'INV-{onboard.id:05d}',
                'client_name': onboard.client_name,
                'company': onboard.company_name or '',
                'email': onboard.client_email or '',
                'phone': onboard.client_phone or '',
                'amount': onboard.project_cost,
                'currency': 'INR',
                'date': onboard.created_at.date(),
                'owner': onboard.assigned_engineer or 'N/A',
                'items': [{
                    'description': onboard.project_name,
                    'quantity': 1,
                    'unit_price': float(onboard.project_cost),
                    'total': float(onboard.project_cost)
                }],
                'subtotal': onboard.project_cost,
                'discount': Decimal('0.00'),
                'gst_percent': Decimal('0.00'),
                'gst_amount': Decimal('0.00'),
                'total': onboard.project_cost,
                'notes': onboard.project_description or '',
                'terms': '',
                'valid_until': None,
                'payment_history': [],
            }
        else:
            messages.error(request, 'Invalid invoice type.')
            return redirect('invoices')
        
        def to_decimal(value, default=Decimal('0.00')):
            """Safely convert any numeric-like value to Decimal."""
            if value is None:
                return default
            if isinstance(value, Decimal):
                return value
            try:
                return Decimal(str(value))
            except (InvalidOperation, ValueError, TypeError):
                return default

        def normalize_quantity(value):
            qty = to_decimal(value, Decimal('1'))
            if qty == qty.to_integral():
                return str(int(qty))
            normalized = qty.normalize()
            # normalize() may produce scientific notation; format handles that.
            qty_str = format(normalized, 'f')
            return qty_str.rstrip('0').rstrip('.') if '.' in qty_str else qty_str

        # Create PDF buffer and styles
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )
        elements = []
        styles = getSampleStyleSheet()
        base_style = ParagraphStyle(
            'BaseStyle',
            parent=styles['Normal'],
            fontSize=10,
            leading=13,
            textColor=colors.HexColor('#2b2b2b')
        )
        bold_style = ParagraphStyle(
            'BoldStyle',
            parent=base_style,
            fontName='Helvetica-Bold'
        )
        brand_heading_style = ParagraphStyle(
            'BrandHeading',
            parent=bold_style,
            fontSize=20,
            alignment=TA_CENTER,
            textColor=accent_color,
            spaceAfter=6
        )
        brand_subheading_style = ParagraphStyle(
            'BrandSubHeading',
            parent=base_style,
            fontSize=10,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#4b4b4b'),
            leading=13
        )
        accent_color = colors.HexColor('#7B3F98')
        light_purple = colors.HexColor('#ede3f4')

        # Primary heading centered at top
        elements.append(Paragraph('SUJATA ASSOCIATES', brand_heading_style))
        elements.append(Paragraph('Sujata Associates Consultancy Pvt Ltd', brand_subheading_style))
        elements.append(Paragraph('4, Fairlie Place, HMP House, 5th Floor, Kolkata 700 001 (W.B.)', brand_subheading_style))
        elements.append(Paragraph('Email: info@sujataassociates.com | Ph: 90380013', brand_subheading_style))
        elements.append(Paragraph('GSTIN: 19AAZCS9337C1ZM | PAN: AAZCS9337C | State: West Bengal (Code 19)', brand_subheading_style))
        elements.append(Spacer(1, 0.05 * inch))

        # Header with logo and company info
        logo_path = get_company_logo_path()
        if logo_path:
            logo_img = Image(logo_path, width=110, height=55, hAlign='LEFT')
        else:
            logo_img = Paragraph(f"<b>{COMPANY_PROFILE['name']}</b>", bold_style)

        company_lines = [
            Paragraph(f"<b>{COMPANY_PROFILE['name'].upper()}</b>", bold_style),
            Paragraph(f"GST No.: {COMPANY_PROFILE['gstin']}    PAN No.: {COMPANY_PROFILE['pan']}", base_style)
        ]
        if COMPANY_PROFILE.get('tagline'):
            company_lines.append(Paragraph(COMPANY_PROFILE['tagline'], base_style))
        for line in COMPANY_PROFILE.get('address_lines', []):
            company_lines.append(Paragraph(line, base_style))

        proforma_box = Table(
            [[Paragraph('<b>Proforma Invoice</b>', ParagraphStyle('Proforma', parent=bold_style, alignment=TA_CENTER))]],
            colWidths=[1.5 * inch],
            rowHeights=[0.6 * inch]
        )
        proforma_box.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), accent_color),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 1, accent_color),
        ]))

        header_table = Table(
            [[logo_img, company_lines, proforma_box]],
            colWidths=[1.7 * inch, 3.8 * inch, 1.5 * inch]
        )
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 0.15 * inch))

        # Client and invoice meta information
        invoice_date = invoice_data.get('date')
        if not invoice_date:
            invoice_date = date.today()
        elif isinstance(invoice_date, datetime):
            invoice_date = invoice_date.date()

        client_details = [
            [Paragraph('<b>Client Name</b>', base_style), Paragraph(invoice_data.get('client_name', '-'), base_style)],
            [Paragraph('<b>Company</b>', base_style), Paragraph(invoice_data.get('company') or '-', base_style)],
            [Paragraph('<b>Email</b>', base_style), Paragraph(invoice_data.get('email') or '-', base_style)],
            [Paragraph('<b>Phone</b>', base_style), Paragraph(invoice_data.get('phone') or '-', base_style)],
        ]

        invoice_details = [
            [Paragraph('<b>Date</b>', base_style), Paragraph(invoice_date.strftime('%d.%m.%Y'), base_style)],
            [Paragraph('<b>Invoice #</b>', base_style), Paragraph(invoice_data['invoice_number'], base_style)],
            [Paragraph('<b>Status</b>', base_style), Paragraph(invoice.status if invoice_type == 'invoice' else 'Pending', base_style)],
        ]
        if invoice_data.get('valid_until'):
            invoice_details.append([
                Paragraph('<b>Valid Until</b>', base_style),
                Paragraph(invoice_data['valid_until'].strftime('%d.%m.%Y'), base_style)
            ])

        client_table = Table(
            [[client_details, invoice_details]],
            colWidths=[3.7 * inch, 3.0 * inch]
        )
        client_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), light_purple),
            ('BACKGROUND', (1, 0), (1, 0), light_purple),
            ('BOX', (0, 0), (-1, -1), 1, accent_color),
            ('INNERGRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#c0a5d4')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(client_table)
        elements.append(Spacer(1, 0.2 * inch))

        # Currency symbol helper
        currency_code = invoice_data.get('currency', 'INR')
        currency_symbol = {'USD': '$', 'EUR': '€'}.get(currency_code, '₹')

        def format_currency_value(value):
            amount = to_decimal(value)
            return f"{currency_symbol} {float(amount):,.2f}"

        def format_percent(value):
            try:
                dec_value = Decimal(value or 0)
            except (InvalidOperation, TypeError):
                dec_value = Decimal('0')
            if dec_value == 0:
                return '0'
            normalized = dec_value.normalize()
            percent_str = format(normalized, 'f')
            if '.' in percent_str:
                percent_str = percent_str.rstrip('0').rstrip('.')
            return percent_str

        def format_summary_amount(value):
            amount = to_decimal(value)
            if amount == 0:
                return '-'
            return format_currency_value(amount)

        # Items table replicating design
        raw_items = invoice_data.get('items') or []
        if isinstance(raw_items, str):
            try:
                raw_items = json.loads(raw_items)
            except (json.JSONDecodeError, ValueError, TypeError):
                raw_items = []

        items_data = [['S.No', 'Description', 'HSN Code', 'Qty', 'Rate', 'Amount']]
        if not raw_items:
            total_value = to_decimal(invoice_data.get('total', Decimal('0.00')))
            items_data.append(['01', 'Service/Product', '-', '1', format_currency_value(total_value), format_currency_value(total_value)])
        else:
            for idx, item in enumerate(raw_items, start=1):
                if isinstance(item, dict):
                    desc = item.get('description') or item.get('name') or 'Item'
                    hsn = item.get('hsn') or item.get('hsn_code') or '-'
                    qty_value = to_decimal(item.get('quantity', 1), Decimal('1'))
                    rate_value = to_decimal(item.get('unit_price', item.get('price', 0)), Decimal('0'))
                    total_value = item.get('total')
                    if total_value is None:
                        total_value = rate_value * qty_value
                    total_value = to_decimal(total_value, rate_value * qty_value)
                else:
                    desc = str(item)
                    hsn = '-'
                    qty_value = Decimal('1')
                    rate_value = Decimal('0')
                    total_value = Decimal('0')

                items_data.append([
                    f"{idx:02d}",
                    desc,
                    hsn,
                    normalize_quantity(qty_value),
                    format_currency_value(rate_value),
                    format_currency_value(total_value)
                ])

        items_table = Table(items_data, colWidths=[0.7 * inch, 2.8 * inch, 1.1 * inch, 0.8 * inch, 1.1 * inch, 1.1 * inch])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), accent_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#b18ccf')),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 0.15 * inch))

        # Summary totals with GST split similar to reference
        subtotal_value = to_decimal(invoice_data.get('subtotal', invoice_data.get('total', Decimal('0.00'))))
        discount_value = to_decimal(invoice_data.get('discount', Decimal('0.00')))
        gst_amount_value = to_decimal(invoice_data.get('gst_amount', Decimal('0.00')))
        gst_percent_value = to_decimal(invoice_data.get('gst_percent', Decimal('0.00')))
        total_value = to_decimal(invoice_data.get('total', Decimal('0.00')))

        cgst_percent = sgst_percent = Decimal('0.00')
        cgst_amount = sgst_amount = Decimal('0.00')
        igst_percent = Decimal('0.00')
        igst_amount = Decimal('0.00')
        if gst_percent_value > 0 and gst_amount_value > 0:
            cgst_percent = sgst_percent = (gst_percent_value / 2).quantize(Decimal('0.01'))
            cgst_amount = sgst_amount = (gst_amount_value / 2).quantize(Decimal('0.01'))
            igst_amount = gst_amount_value - (cgst_amount + sgst_amount)
            if igst_amount < 0:
                igst_amount = Decimal('0.00')
        else:
            igst_amount = gst_amount_value
            igst_percent = gst_percent_value

        # Get amount_received and pending_balance for invoice type
        amount_received_value = Decimal('0.00')
        pending_balance_value = total_value
        if invoice_type == 'invoice':
            amount_received_value = to_decimal(invoice_data.get('amount_received', Decimal('0.00')))
            pending_balance_value = to_decimal(invoice_data.get('pending_balance', total_value))
        
        due_summary_display = format_currency_value(pending_balance_value) if pending_balance_value > 0 else f"{format_currency_value(Decimal('0.00'))} (No Due)"
        summary_rows = [
            ['Total Value', format_currency_value(subtotal_value)],
            [f'Add : CGST {format_percent(cgst_percent)}%', format_summary_amount(cgst_amount)],
            [f'Add : SGST {format_percent(sgst_percent)}%', format_summary_amount(sgst_amount)],
            [f'Add : IGST {format_percent(igst_percent)}%', format_summary_amount(igst_amount)],
            ['Less : Discount (If Any)', format_summary_amount(discount_value)],
            ['', ''],
            ['Grand Total', format_currency_value(total_value)],
        ]
        
        # Add amount received and pending balance only for invoice type
        if invoice_type == 'invoice':
            summary_rows.append([Paragraph('<b>Previous Payment</b>', base_style), format_currency_value(amount_received_value)])
            summary_rows.append(['Due Payment', due_summary_display])
        else:
            summary_rows.append(['Amount Due', format_currency_value(total_value)])

        summary_table = Table(summary_rows, colWidths=[3.0 * inch, 1.8 * inch], hAlign='RIGHT')
        summary_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('TEXTCOLOR', (0, -2), (-1, -1), accent_color),
            ('FONTNAME', (0, -2), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('INNERGRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#b18ccf')),
            ('BOX', (0, 0), (-1, -1), 0.5, accent_color),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 0.15 * inch))

        # Payment history table for invoices
        if invoice_type == 'invoice':
            history_entries = invoice_data.get('payment_history') or []
            if isinstance(history_entries, str):
                try:
                    history_entries = json.loads(history_entries)
                except (json.JSONDecodeError, ValueError, TypeError):
                    history_entries = []
            payment_rows = [['#', 'Payment Date', 'Amount']]
            if history_entries:
                for idx, entry in enumerate(history_entries, start=1):
                    amount_val = to_decimal(entry.get('amount', Decimal('0.00')))
                    date_raw = entry.get('date') or entry.get('date_display') or entry.get('created_at')
                    date_display = '-'
                    if date_raw:
                        try:
                            date_display = datetime.strptime(date_raw[:10], '%Y-%m-%d').strftime('%d %b %Y')
                        except (ValueError, TypeError):
                            date_display = date_raw
                    payment_rows.append([
                        str(idx),
                        date_display,
                        format_currency_value(amount_val)
                    ])
            else:
                payment_rows.append(['-', 'No payments recorded', '-'])
            pending_display = format_currency_value(pending_balance_value) if pending_balance_value > 0 else f"{format_currency_value(Decimal('0.00'))} (No Due)"
            payment_rows.append(['', f'Pending Balance as of {date.today().strftime("%d %b %Y")}', pending_display])

            payment_table = Table(payment_rows, colWidths=[0.6 * inch, 3.2 * inch, 1.8 * inch])
            payment_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), light_purple),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
                ('BOX', (0, 0), (-1, -1), 0.4, accent_color),
                ('INNERGRID', (0, 0), (-1, -1), 0.2, colors.HexColor('#c0a5d4')),
            ]))
            elements.append(payment_table)
            elements.append(Spacer(1, 0.15 * inch))

        # Bank details table
        bank = COMPANY_PROFILE['bank_details']
        bank_rows = [
            ['Account Name', bank['account_name']],
            ['Bank Name', bank['bank_name']],
            ['Account No.', bank['account_number']],
            ['IFSC', bank['ifsc']],
            ['Branch', bank['branch']],
        ]
        bank_table = Table(bank_rows, colWidths=[1.6 * inch, 4.6 * inch])
        bank_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), light_purple),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOX', (0, 0), (-1, -1), 0.4, accent_color),
            ('INNERGRID', (0, 0), (-1, -1), 0.2, colors.HexColor('#c0a5d4')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ]))
        elements.append(bank_table)
        elements.append(Spacer(1, 0.1 * inch))

        # Amount in words and signature section
        amount_words_text = amount_to_words(total_value)
        elements.append(Paragraph(f"<b>Amount in Words:</b> {amount_words_text}", base_style))
        elements.append(Spacer(1, 0.2 * inch))

        signature_table = Table([
            [
                Paragraph('', base_style),
                Paragraph(f"For {COMPANY_PROFILE['name']}<br/><br/><br/>Authorised Signature", base_style)
            ]
        ], colWidths=[3.0 * inch, 3.0 * inch])
        signature_table.setStyle(TableStyle([
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ]))
        elements.append(signature_table)

        # Build PDF
        doc.build(elements)
        pdf = buffer.getvalue()
        buffer.close()

        response = HttpResponse(content_type='application/pdf')
        filename = f'Invoice_{invoice_data["invoice_number"]}.pdf'.replace(' ', '_').replace('/', '_')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = len(pdf)
        response.write(pdf)
        return response
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PDF Generation Error: {str(e)}")
        print(f"Traceback: {error_trace}")
        messages.error(request, f'Error generating PDF: {str(e)}')
        return redirect('invoices')


@login_required
@require_POST
@csrf_exempt
def pay_employee(request, employee_id):
    """Process payment for an employee"""
    try:
        employee = Employee.objects.get(id=employee_id)
        
        # Calculate net salary
        basic = employee.basic or Decimal('0')
        hra = employee.hra or Decimal('0')
        allowances = employee.allowances or Decimal('0')
        variable = employee.variable or Decimal('0')
        deductions = employee.deductions or Decimal('0')
        
        net_salary = basic + hra + allowances + variable - deductions
        
        # Get payment date from request or use today's date
        payment_date_str = request.POST.get('payment_date', '')
        if payment_date_str:
            try:
                payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d').date()
            except:
                payment_date = date.today()
        else:
            payment_date = date.today()
        
        # Get payment month and year
        payment_month = payment_date.month
        payment_year = payment_date.year
        
        # Prevent duplicate payment in the same month/year (except failed/cancelled)
        already_paid = PaymentTransaction.objects.filter(
            employee=employee,
            payment_month=payment_month,
            payment_year=payment_year
        ).exclude(status__in=['failed', 'cancelled']).exists()
        if already_paid:
            return JsonResponse({
                'success': False,
                'error': 'Payment already processed for this employee for this month.'
            }, status=400)
        
        # Get payment method from request
        payment_method = request.POST.get('payment_method', 'bank_transfer')
        
        # Get transaction ID and reference number if provided
        transaction_id = request.POST.get('transaction_id', '').strip() or None
        reference_number = request.POST.get('reference_number', '').strip() or None
        notes = request.POST.get('notes', '').strip() or None
        
        # Create payment transaction record
        payment_transaction = PaymentTransaction.objects.create(
            employee=employee,
            employee_name=employee.get_full_name(),
            employee_department=employee.department,
            amount=net_salary,
            basic=employee.basic,
            hra=employee.hra,
            allowances=employee.allowances,
            deductions=employee.deductions,
            variable=employee.variable,
            ctc=employee.ctc,
            payment_method=payment_method,
            transaction_id=transaction_id,
            reference_number=reference_number,
            payment_month=payment_month,
            payment_year=payment_year,
            payment_date=payment_date,
            notes=notes,
            processed_by=request.user,
            status='completed'
        )
        
        # Here you would typically:
        # 1. Generate a payslip
        # 2. Send payment to bank/UPI
        # 3. Send notification to employee
        
        return JsonResponse({
            'success': True,
            'message': f'Payment of ₹ {net_salary:,.2f} processed successfully for {employee.get_full_name()}',
            'net_salary': str(net_salary),
            'employee_name': employee.get_full_name(),
            'transaction_id': payment_transaction.id,
            'payment_date': payment_date.strftime('%d %B %Y')
        })
    except Employee.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Employee not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def leads_import_export(request):
  export_fields = ['name','email','phone','company','owner','source','priority','stage','use_case','next_action','due_date','due_time','city','country','industry','tags']
  return render(request, 'leads_section/leads_import_export.html', { 'export_fields': export_fields })


@login_required
def employees(request):
    """Employee management view - handles form submission and displays employee list"""
    from django.core.paginator import Paginator
    from decimal import Decimal, InvalidOperation
    
    # Handle form submission
    if request.method == 'POST':
        try:
            # Generate employee code if not provided
            emp_code = request.POST.get('emp_code', '').strip()
            if not emp_code:
                # Generate auto code
                last_emp = Employee.objects.order_by('-id').first()
                if last_emp and last_emp.emp_code:
                    try:
                        last_num = int(last_emp.emp_code.split('-')[-1])
                        emp_code = f"EMP-{last_num + 1:04d}"
                    except (ValueError, IndexError):
                        emp_code = f"EMP-{Employee.objects.count() + 1:04d}"
                else:
                    emp_code = f"EMP-{Employee.objects.count() + 1:04d}"
            
            # Check if employee ID is provided (for update)
            employee = None
            employee_id = request.POST.get('employee_id', '').strip()
            if employee_id:
                try:
                    employee = Employee.objects.get(id=int(employee_id))
                    # Use existing emp_code if not provided
                    if not emp_code and employee.emp_code:
                        emp_code = employee.emp_code
                except (Employee.DoesNotExist, ValueError):
                    employee_id = None
                    pass
            
            # If no employee ID, check by emp_code (for update)
            if not employee and emp_code:
                try:
                    employee = Employee.objects.get(emp_code=emp_code)
                except Employee.DoesNotExist:
                    pass
            
            # Create or update employee
            if employee:
                # Update existing
                employee.first_name = request.POST.get('first_name', '').strip() or employee.first_name
                employee.last_name = request.POST.get('last_name', '').strip() or employee.last_name
                employee.email = request.POST.get('email', '').strip() or employee.email
                employee.phone = request.POST.get('phone', '').strip() or employee.phone
            else:
                # Create new
                employee = Employee(
                    first_name=request.POST.get('first_name', '').strip(),
                    last_name=request.POST.get('last_name', '').strip(),
                    emp_code=emp_code,
                    email=request.POST.get('email', '').strip(),
                    phone=request.POST.get('phone', '').strip(),
                )
            
            # Personal Information
            employee.gender = request.POST.get('gender', '').strip() or None
            dob_str = request.POST.get('dob', '').strip()
            if dob_str:
                try:
                    from django.utils.dateparse import parse_date
                    employee.dob = parse_date(dob_str)
                except (ValueError, TypeError):
                    pass
            employee.address_current = request.POST.get('address_current', '').strip() or None
            employee.address_permanent = request.POST.get('address_permanent', '').strip() or None
            
            # Job Information
            employee.designation = request.POST.get('designation', '').strip() or None
            employee.department = request.POST.get('department', '').strip() or None
            employee.manager = request.POST.get('manager', '').strip() or None
            employee.role = request.POST.get('role', '').strip() or 'Employee'
            employee.employment_type = request.POST.get('employment_type', '').strip() or None
            employee.location = request.POST.get('location', '').strip() or None
            joining_date_str = request.POST.get('joining_date', '').strip()
            if joining_date_str:
                try:
                    from django.utils.dateparse import parse_date
                    employee.joining_date = parse_date(joining_date_str)
                except (ValueError, TypeError):
                    pass
            probation = request.POST.get('probation', '').strip()
            if probation and probation.isdigit():
                employee.probation = int(probation)
            
            # Payroll
            payroll_fields = ['ctc', 'basic', 'hra', 'allowances', 'deductions', 'variable']
            for field in payroll_fields:
                value = request.POST.get(field, '').strip()
                if value:
                    try:
                        # Remove currency symbols, commas, and spaces
                        cleaned_value = value.replace('₹', '').replace(',', '').replace(' ', '').replace('$', '').strip()
                        if cleaned_value:
                            # Convert to Decimal and validate range
                            # max_digits=12, decimal_places=2 means max value is 9999999999.99
                            decimal_value = Decimal(cleaned_value)
                            
                            # Check if value is within valid range
                            max_value = Decimal('9999999999.99')
                            min_value = Decimal('-9999999999.99')
                            
                            if decimal_value > max_value:
                                print(f"Warning: {field} value {decimal_value} exceeds max {max_value}, setting to None")
                                setattr(employee, field, None)
                            elif decimal_value < min_value:
                                print(f"Warning: {field} value {decimal_value} below min {min_value}, setting to None")
                                setattr(employee, field, None)
                            else:
                                # Ensure it has at most 2 decimal places
                                decimal_value = decimal_value.quantize(Decimal('0.01'))
                                setattr(employee, field, decimal_value)
                        else:
                            setattr(employee, field, None)
                    except (InvalidOperation, ValueError, TypeError) as e:
                        print(f"Error parsing {field}: {value}, Error: {str(e)}")
                        setattr(employee, field, None)
                else:
                    # If empty, set to None to clear the field
                    setattr(employee, field, None)
            
            pay_cycle = request.POST.get('pay_cycle', '').strip()
            employee.pay_cycle = pay_cycle if pay_cycle else None
            
            print(f"✅ Payroll data saved - CTC: {employee.ctc}, Basic: {employee.basic}, HRA: {employee.hra}, Allowances: {employee.allowances}, Deductions: {employee.deductions}, Variable: {employee.variable}, Pay Cycle: {employee.pay_cycle}")
            
            # Banking
            employee.bank_name = request.POST.get('bank_name', '').strip() or None
            employee.account_number = request.POST.get('account_number', '').strip() or None
            employee.ifsc = request.POST.get('ifsc', '').strip() or None
            employee.upi = request.POST.get('upi', '').strip() or None
            employee.pan = request.POST.get('pan', '').strip() or None
            employee.aadhaar = request.POST.get('aadhaar', '').strip() or None
            
            # Tax/IDs
            employee.uan = request.POST.get('uan', '').strip() or None
            employee.esic = request.POST.get('esic', '').strip() or None
            employee.gst = request.POST.get('gst', '').strip() or None
            
            # Emergency Contacts
            employee.emg_name1 = request.POST.get('emg_name1', '').strip() or None
            employee.emg_relation1 = request.POST.get('emg_relation1', '').strip() or None
            employee.emg_phone1 = request.POST.get('emg_phone1', '').strip() or None
            employee.emg_name2 = request.POST.get('emg_name2', '').strip() or None
            employee.emg_relation2 = request.POST.get('emg_relation2', '').strip() or None
            employee.emg_phone2 = request.POST.get('emg_phone2', '').strip() or None
            
            # Assets
            employee.asset_laptop = request.POST.get('asset_laptop', '').strip() or None
            employee.asset_phone = request.POST.get('asset_phone', '').strip() or None
            employee.asset_other = request.POST.get('asset_other', '').strip() or None
            
            # Access
            employee.work_email = request.POST.get('work_email', '').strip() or None
            employee.github = request.POST.get('github', '').strip() or None
            employee.pm_tool = request.POST.get('pm_tool', '').strip() or None
            employee.vpn = request.POST.get('vpn', '').strip() or None
            employee.access_level = request.POST.get('access_level', '').strip() or None
            
            # Notes
            employee.notes = request.POST.get('notes', '').strip() or None
            
            # Documents - Handle file uploads
            document_fields = [
                'doc_aadhaar', 'doc_pan', 'doc_bank', 'doc_experience',
                'doc_education', 'doc_prev_offer_relieve', 'doc_current_offer', 'doc_salary_slips'
            ]
            for field_name in document_fields:
                if field_name in request.FILES:
                    # Only update if a new file is uploaded
                    setattr(employee, field_name, request.FILES[field_name])
                    print(f"✅ Document saved - {field_name}: {request.FILES[field_name].name}")
                # If no new file is uploaded, keep existing file (don't overwrite with None)
            
            # Profile Photo
            if 'photo' in request.FILES:
                employee.photo = request.FILES['photo']
                print(f"✅ Profile photo saved - {request.FILES['photo'].name}")
            
            # Leave Balances
            for field in ['annual_leave', 'sick_leave', 'personal_leave', 'maternity_leave', 'paternity_leave', 'emergency_leave']:
                value = request.POST.get(field, '').strip()
                if value and value.isdigit():
                    setattr(employee, field, int(value))
            
            # Status
            employee.status = request.POST.get('status', 'active').strip() or 'active'
            
            employee.save()
            print(f"✅ Employee saved - ID: {employee.id}, Name: {employee.get_full_name()}, Code: {employee.emp_code}")
            
            # Check if request is AJAX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
                return JsonResponse({
                    'success': True,
                    'message': f'Employee "{employee.get_full_name()}" saved successfully!',
                    'employee_id': employee.id,
                    'emp_code': employee.emp_code
                })
            
            messages.success(request, f'Employee "{employee.get_full_name()}" saved successfully!')
            return redirect('employees')
        except Exception as e:
            error_msg = f'Error saving employee: {str(e)}'
            print(error_msg)
            
            # Check if request is AJAX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                }, status=400)
            
            messages.error(request, error_msg)
    
    # Get employee list for display
    employee_list = Employee.objects.all().order_by('-created_at')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        employee_list = employee_list.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(emp_code__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(designation__icontains=search_query) |
            Q(department__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(employee_list, 10)  # 10 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get employee for editing (if employee_id is provided in GET)
    edit_employee = None
    employee_id_edit = request.GET.get('edit', '').strip()
    if employee_id_edit:
        try:
            if employee_id_edit.isdigit():
                edit_employee = Employee.objects.get(id=int(employee_id_edit))
            else:
                edit_employee = Employee.objects.get(emp_code=employee_id_edit)
        except (Employee.DoesNotExist, ValueError):
            pass
    
    context = {
        'employees': page_obj,
        'search_query': search_query,
        'edit_employee': edit_employee,
    }
    return render(request, 'human_resource/employee.html', context)


@login_required
def employee_view(request, employee_id):
    """View employee details via AJAX"""
    try:
        employee = Employee.objects.get(id=employee_id)
        data = {
            'id': employee.id,
            'first_name': employee.first_name,
            'last_name': employee.last_name,
            'emp_code': employee.emp_code,
            'initials': employee.get_initials(),
            'photo_url': (employee.photo.url if getattr(employee, 'photo', None) else None),
            'email': employee.email,
            'phone': employee.phone,
            'designation': employee.designation,
            'department': employee.department,
            'role': employee.role,
            'status': employee.status,
            'gender': employee.gender,
            'dob': str(employee.dob) if employee.dob else None,
            'joining_date': str(employee.joining_date) if employee.joining_date else None,
            'address_current': employee.address_current,
            'address_permanent': employee.address_permanent,
            'manager': employee.manager,
            'employment_type': employee.employment_type,
            'location': employee.location,
            'work_email': employee.work_email,
            'annual_leave': employee.annual_leave,
            'sick_leave': employee.sick_leave,
            'personal_leave': employee.personal_leave,
            'maternity_leave': employee.maternity_leave,
            'paternity_leave': employee.paternity_leave,
            'emergency_leave': employee.emergency_leave,
            # Emergency contacts
            'emg_name1': employee.emg_name1,
            'emg_relation1': employee.emg_relation1,
            'emg_phone1': employee.emg_phone1,
            'emg_name2': employee.emg_name2,
            'emg_relation2': employee.emg_relation2,
            'emg_phone2': employee.emg_phone2,
            # Payroll
            'ctc': str(employee.ctc) if employee.ctc else None,
            'basic': str(employee.basic) if employee.basic else None,
            'hra': str(employee.hra) if employee.hra else None,
            'allowances': str(employee.allowances) if employee.allowances else None,
            'deductions': str(employee.deductions) if employee.deductions else None,
            'variable': str(employee.variable) if employee.variable else None,
            'pay_cycle': employee.pay_cycle,
            # Banking
            'bank_name': employee.bank_name,
            'account_number': employee.account_number,
            'ifsc': employee.ifsc,
            'upi': employee.upi,
            'pan': employee.pan,
            'aadhaar': employee.aadhaar,
            # Tax/IDs
            'uan': employee.uan,
            'esic': employee.esic,
            'gst': employee.gst,
            # Assets
            'asset_laptop': employee.asset_laptop,
            'asset_phone': employee.asset_phone,
            'asset_other': employee.asset_other,
            # Access
            'github': employee.github,
            'pm_tool': employee.pm_tool,
            'vpn': employee.vpn,
            'access_level': employee.access_level,
            # Notes
            'notes': employee.notes,
        }
        return JsonResponse({'success': True, 'employee': data})
    except Employee.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Employee not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def quotes(request):
    """
    Dashboard quotes view - displays quotes from database with tabs
    Separate tabs for Sent and Accepted quotes
    """
    from django.core.paginator import Paginator
    
    try:
        # Search functionality
        search_query = request.GET.get('search', '').strip()
        
        # Fetch Sent quotes
        sent_quotes_list = Quote.objects.filter(status='Sent').order_by('-created_at')
        
        # Fetch Accepted quotes (also check for Approved)
        accepted_quotes_list = Quote.objects.filter(
            Q(status='Accepted') | Q(status='Approved')
        ).order_by('-created_at')
        
        # Apply search filter to Sent quotes
        if search_query:
            sent_quotes_list = sent_quotes_list.filter(
                Q(quote_number__icontains=search_query) |
                Q(client_name__icontains=search_query) |
                Q(company__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(phone__icontains=search_query) |
                Q(owner__icontains=search_query)
            )
        
        # Apply search filter to Accepted quotes
        if search_query:
            accepted_quotes_list = accepted_quotes_list.filter(
                Q(quote_number__icontains=search_query) |
                Q(client_name__icontains=search_query) |
                Q(company__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(phone__icontains=search_query) |
                Q(owner__icontains=search_query)
            )
        
        # Paginate Sent quotes (10 per page)
        sent_paginator = Paginator(sent_quotes_list, 10)
        sent_page = request.GET.get('sent_page', 1)
        try:
            sent_quotes = sent_paginator.page(sent_page)
        except PageNotAnInteger:
            sent_quotes = sent_paginator.page(1)
        except EmptyPage:
            sent_quotes = sent_paginator.page(sent_paginator.num_pages)
        
        # Paginate Accepted quotes (10 per page)
        accepted_paginator = Paginator(accepted_quotes_list, 10)
        accepted_page = request.GET.get('accepted_page', 1)
        try:
            accepted_quotes = accepted_paginator.page(accepted_page)
        except PageNotAnInteger:
            accepted_quotes = accepted_paginator.page(1)
        except EmptyPage:
            accepted_quotes = accepted_paginator.page(accepted_paginator.num_pages)
        
        # Get status counts
        status_counts = {
            'draft': Quote.objects.filter(status='Draft').count(),
            'sent': Quote.objects.filter(status='Sent').count(),
            'accepted': Quote.objects.filter(Q(status='Accepted') | Q(status='Approved')).count(),
            'declined': Quote.objects.filter(status='Declined').count(),
            'total': Quote.objects.count()
        }
        
        context = {
            'sent_quotes': sent_quotes,
            'accepted_quotes': accepted_quotes,
            'search_query': search_query,
            'status_counts': status_counts,
            'total_sent_quotes': sent_quotes_list.count(),
            'total_accepted_quotes': accepted_quotes_list.count(),
        }
        
        return render(request, 'dashboard/quotes.html', context)
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Error in quotes view: {str(e)}', exc_info=True)
        
        messages.error(request, 'An error occurred while loading quotes. Please try again later.')
        
        context = {
            'sent_quotes': None,
            'accepted_quotes': None,
            'search_query': '',
            'status_counts': {'total': 0, 'sent': 0, 'accepted': 0},
            'total_sent_quotes': 0,
            'total_accepted_quotes': 0,
        }
        return render(request, 'dashboard/quotes.html', context)


@login_required
def contacts(request):
    """
    Contacts view - displays employee contact information
    
    Production-ready features:
    - Error handling
    - Input validation
    - Performance optimization
    - Security (XSS protection via Django templates)
    - Mobile responsive data structure
    
    This view demonstrates OOP concepts:
    - Class-based database queries (Employee.objects.all())
    - Method calls (get_full_name(), get_initials())
    - Data encapsulation (Employee model class)
    """
    try:
        from django.core.paginator import Paginator
        from django.utils.html import escape
        
        # Initialize variables
        search_query = ''
        department_filter = ''
        page_obj = None
        departments = []
        total_employees = 0
        
        # Fetch all active employees from database (optimized query)
        # Employee.objects.all() - This is using Django ORM (Object-Relational Mapping)
        # ORM is an OOP concept that maps database tables to Python classes
        employees = Employee.objects.filter(status='active').order_by('first_name', 'last_name')
        
        # Search functionality with input validation
        search_query = request.GET.get('search', '').strip()
        if search_query:
            # Limit search query length for security (prevent DoS)
            if len(search_query) > 200:
                search_query = search_query[:200]
                messages.warning(request, 'Search query was too long and has been truncated.')
            
            # Q objects allow complex database queries using OOP-style chaining
            # Only search if query is meaningful (at least 2 characters)
            if len(search_query) >= 2:
                employees = employees.filter(
                    Q(first_name__icontains=search_query) |
                    Q(last_name__icontains=search_query) |
                    Q(email__icontains=search_query) |
                    Q(phone__icontains=search_query) |
                    Q(designation__icontains=search_query) |
                    Q(department__icontains=search_query) |
                    Q(emg_phone1__icontains=search_query) |
                    Q(emg_phone2__icontains=search_query)
                )
            else:
                messages.info(request, 'Please enter at least 2 characters to search.')
        
        # Filter by department with input validation
        department_filter = request.GET.get('department', '').strip()
        if department_filter:
            # Validate department name length
            if len(department_filter) > 100:
                department_filter = department_filter[:100]
            
            employees = employees.filter(department__iexact=department_filter)
        
        # Get unique departments for filter dropdown (cached query)
        # This uses OOP method chaining: values_list() -> distinct()
        try:
            departments = list(Employee.objects.filter(
                status='active',
                department__isnull=False
            ).exclude(department='').values_list('department', flat=True).distinct())
            departments = [d for d in departments if d and d.strip()]  # Remove None/empty values
            departments.sort()
        except Exception as e:
            # Log error but don't break the page
            departments = []
        
        # Count total employees (optimized - only count if needed)
        total_employees = employees.count()
        
        # Pagination - 20 employees per page (mobile-friendly: 10 on small screens)
        items_per_page = 20
        paginator = Paginator(employees, items_per_page)
        page_number = request.GET.get('page', 1)
        
        try:
            page_number = int(page_number)
            if page_number < 1:
                page_number = 1
        except (ValueError, TypeError):
            page_number = 1
        
        try:
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
        
        # Prepare context with safe data
        context = {
            'employees': page_obj,  # Paginated employee list
            'departments': departments,  # List of departments for filter
            'search_query': escape(search_query),  # XSS protection
            'department_filter': escape(department_filter),  # XSS protection
            'total_employees': total_employees,
        }
        
        return render(request, 'dashboard/contacts.html', context)
        
    except Exception as e:
        # Production error handling - log error and show user-friendly message
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Error in contacts view: {str(e)}', exc_info=True)
        
        messages.error(request, 'An error occurred while loading contacts. Please try again later.')
        
        # Return empty context to prevent page crash
        context = {
            'employees': None,
            'departments': [],
            'search_query': '',
            'department_filter': '',
            'total_employees': 0,
        }
        return render(request, 'dashboard/contacts.html', context)


@require_POST
@login_required
def employee_delete(request, employee_id):
    """Delete employee"""
    try:
        employee = Employee.objects.get(id=employee_id)
        emp_name = employee.get_full_name()
        employee.delete()
        messages.success(request, f'Employee "{emp_name}" deleted successfully!')
        return JsonResponse({'success': True, 'message': f'Employee "{emp_name}" deleted successfully!'})
    except Employee.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Employee not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

def attendance(request):
  return render(request,'human_resource/attendance.html')

def attendance_data_api(request):
  """API endpoint to fetch attendance data for a given month"""
  from datetime import datetime, timedelta
  
  month_str = request.GET.get('month', '')
  if not month_str:
    return JsonResponse({'error': 'Month parameter required'}, status=400)
  
  try:
    year, month = map(int, month_str.split('-'))
  except:
    return JsonResponse({'error': 'Invalid month format. Use YYYY-MM'}, status=400)
  
  # Get start and end dates for the month
  start_date = date(year, month, 1)
  if month == 12:
    end_date = date(year + 1, 1, 1) - timedelta(days=1)
  else:
    end_date = date(year, month + 1, 1) - timedelta(days=1)
  
  # Get all active employees
  employees = Employee.objects.filter(status='active').order_by('first_name', 'last_name')
  
  # Get all attendance records for this month
  attendance_records = Attendance.objects.filter(
    date__gte=start_date,
    date__lte=end_date
  ).select_related('employee')
  
  # Create a map: (employee_id, date_str) -> attendance record
  attendance_map = {}
  for att in attendance_records:
    emp_id = att.employee.id if att.employee else None
    if emp_id:
      date_str = att.date.strftime('%Y-%m-%d')
      attendance_map[(emp_id, date_str)] = att
  
  # Prepare response data
  employees_data = []
  for emp in employees:
    emp_data = {
      'id': emp.id,
      'name': emp.get_full_name(),
      'department': emp.department or 'N/A'
    }
    employees_data.append(emp_data)
  
  # Prepare attendance data: key format: "empId_dateStr" -> status
  from django.utils import timezone
  today = timezone.now().date()
  
  attendance_data = {}
  for (emp_id, date_str), att in attendance_map.items():
    # Compare attendance date with today
    att_date = att.date
    is_today = att_date == today
    
    # For today's date: only return data if both check-in and check-out exist
    if is_today:
      if att.check_in_time and att.check_out_time:
        # Both check-in and check-out exist - calculate status
        delta = att.check_out_time - att.check_in_time
        total_seconds = int(delta.total_seconds())
        total_hours = total_seconds / 3600.0
        
        required_hours = 8.5
        half_day_hours = required_hours / 2.0
        
        if total_hours >= required_hours:
          status = 'P'  # Present
        elif total_hours >= half_day_hours:
          status = 'H'  # Half day
        else:
          status = 'A'  # Absent (less than half day)
        
        key = f"{emp_id}_{date_str}"
        attendance_data[key] = status
      # If only check-in exists (no check-out), don't add to attendance_data
      # This will keep today's date blank in the frontend
    else:
      # For past dates: calculate status normally
      status = 'A'  # Default to Absent
      
      if att.check_in_time and att.check_out_time:
        # Calculate work hours
        delta = att.check_out_time - att.check_in_time
        total_seconds = int(delta.total_seconds())
        total_hours = total_seconds / 3600.0
        
        required_hours = 8.5
        half_day_hours = required_hours / 2.0
        
        if total_hours >= required_hours:
          status = 'P'  # Present
        elif total_hours >= half_day_hours:
          status = 'H'  # Half day
        else:
          status = 'A'  # Absent (less than half day)
      elif att.check_in_time and not att.check_out_time:
        # Only check-in, no check-out - mark as Absent
        status = 'A'  # Absent (no check-out, cannot calculate hours)
      
      key = f"{emp_id}_{date_str}"
      attendance_data[key] = status
  
  return JsonResponse({
    'employees': employees_data,
    'attendance': attendance_data
  })

def leave(request):
    return render(request,'human_resource/leave.html')

@login_required
def reports(request):
    """
    Departmental report showing project & lead distribution per employee.
    Includes month and department filters plus responsive summary cards.
    """
    # Restrict to admin/staff similar to main dashboard
    try:
        employee = Employee.objects.get(email=request.user.email)
        if employee.role != 'Admin':
            messages.warning(request, 'You do not have permission to access this page.')
            return redirect('employee_dashboard')
    except Employee.DoesNotExist:
        if not request.user.is_staff:
            messages.warning(request, 'You do not have permission to access this page.')
            return redirect('employee_dashboard')

    tracked_departments = ['Sales', 'Engineering', 'Accounts', 'Back Office']
    department_alias_map = {
        'sales': 'Sales',
        'salesteam': 'Sales',
        'businessdevelopment': 'Sales',
        'engineering': 'Engineering',
        'engineer': 'Engineering',
        'tech': 'Engineering',
        'technology': 'Engineering',
        'development': 'Engineering',
        'accounts': 'Accounts',
        'account': 'Accounts',
        'accounting': 'Accounts',
        'finance': 'Accounts',
        'backoffice': 'Back Office',
        'backofficeteam': 'Back Office',
        'backofficeops': 'Back Office',
        'backofficeoperations': 'Back Office',
        'backoffice-support': 'Back Office'
    }

    def canonical_department(raw_value):
        if not raw_value:
            return None
        normalized = ''.join(raw_value.lower().split())
        for needle, label in department_alias_map.items():
            if needle in normalized:
                return label
        return None

    def normalize_key(value):
        return value.strip().lower() if value else ''

    def employee_keys(emp):
        keys = set()
        full_name = (emp.get_full_name() or '').strip()
        if full_name:
            keys.add(normalize_key(full_name))
        if emp.first_name:
            keys.add(normalize_key(emp.first_name))
        if emp.emp_code:
            keys.add(normalize_key(emp.emp_code))
        if emp.email:
            keys.add(normalize_key(emp.email))
        if emp.work_email:
            keys.add(normalize_key(emp.work_email))
        return {k for k in keys if k}

    def normalize_lead_status_key(value):
        if not value:
            return 'unspecified'
        lowered = value.strip().lower()
        if lowered in ('med', 'medium'):
            return 'medium'
        if lowered in ('high', 'low'):
            return lowered
        return lowered

    def lead_status_label(key):
        return {
            'high': 'High Priority',
            'medium': 'Medium Priority',
            'low': 'Low Priority',
            'unspecified': 'Unspecified'
        }.get(key, key.replace('_', ' ').title())

    def normalize_project_status_key(value):
        if not value:
            return 'unspecified'
        lowered = value.strip().lower()
        mapping = {
            'active': 'active',
            'in_progress': 'active',
            'inprogress': 'active',
            'pending': 'pending',
            'on_hold': 'on_hold',
            'onhold': 'on_hold',
            'completed': 'completed',
            'complete': 'completed',
        }
        return mapping.get(lowered, lowered)

    def project_status_label(key):
        return {
            'active': 'Active',
            'pending': 'Pending',
            'on_hold': 'On Hold',
            'completed': 'Completed',
            'unspecified': 'Unspecified'
        }.get(key, key.replace('_', ' ').title())

    # Filters
    department_param = request.GET.get('department', 'all').strip()
    selected_department = canonical_department(department_param) if department_param.lower() != 'all' else 'all'
    if not selected_department:
        selected_department = 'all'
    selected_department_label = selected_department if selected_department != 'all' else 'All Departments'

    month_param_raw = request.GET.get('month', '').strip()
    day_param_raw = request.GET.get('day', '').strip()
    month_input_value = ''
    day_input_value = ''
    showing_all_time = False
    now = timezone.now()

    # Check if day filter is provided
    if day_param_raw:
        try:
            selected_date = datetime.strptime(day_param_raw, '%Y-%m-%d').date()
            start_date = selected_date
            end_date = selected_date
            month_label = selected_date.strftime('%d %B %Y')
            month_input_value = selected_date.strftime('%Y-%m')
            day_input_value = day_param_raw
        except ValueError:
            day_param_raw = ''
            selected_date = None
    else:
        selected_date = None

    if not selected_date:
        if month_param_raw.lower() == 'all':
            start_date = None
            end_date = None
            month_label = 'All Time'
            showing_all_time = True
        else:
            if not month_param_raw:
                year = now.year
                month = now.month
            else:
                try:
                    year, month = map(int, month_param_raw.split('-'))
                except ValueError:
                    year = now.year
                    month = now.month
            start_date = date(year, month, 1)
            last_day = calendar.monthrange(year, month)[1]
            end_date = date(year, month, last_day)
            month_label = start_date.strftime('%B %Y')
            month_input_value = f"{year:04d}-{month:02d}"

    filters_active = bool(request.GET)

    # Aggregate leads and projects
    lead_filters = Q(is_active=True)
    if start_date and end_date:
        lead_filters &= Q(created_at__date__gte=start_date, created_at__date__lte=end_date)

    project_filters = Q()
    if start_date and end_date:
        project_filters &= Q(created_at__date__gte=start_date, created_at__date__lte=end_date)

    lead_status_counts = defaultdict(lambda: defaultdict(int))
    lead_total_counts = defaultdict(int)
    lead_status_display = {}
    priority_totals = defaultdict(int)

    # First, count all leads by priority for sales card (including those without owner)
    for row in Lead.objects.filter(lead_filters).values('priority').annotate(total=Count('id')):
        status_key = normalize_lead_status_key(row['priority'])
        priority_totals[status_key] += row['total']
        lead_status_display.setdefault(status_key, lead_status_label(status_key))

    # Then, count leads by owner for employee assignment breakdown
    for row in Lead.objects.filter(lead_filters).values('owner', 'priority').annotate(total=Count('id')):
        owner_key = normalize_key(row['owner'])
        if not owner_key:
            continue
        status_key = normalize_lead_status_key(row['priority'])
        lead_status_counts[owner_key][status_key] += row['total']
        lead_total_counts[owner_key] += row['total']
        lead_status_display.setdefault(status_key, lead_status_label(status_key))

    project_status_counts = defaultdict(lambda: defaultdict(int))
    project_total_counts = defaultdict(int)
    project_status_display = {}

    for row in ClientOnboarding.objects.filter(project_filters).values('assigned_engineer', 'status').annotate(total=Count('id')):
        engineer_key = normalize_key(row['assigned_engineer'])
        if not engineer_key:
            continue
        status_key = normalize_project_status_key(row['status'])
        project_status_counts[engineer_key][status_key] += row['total']
        project_total_counts[engineer_key] += row['total']
        project_status_display.setdefault(status_key, project_status_label(status_key))

    dept_summary = {
        dept: {
            'total_projects': 0,
            'completed_projects': 0,
            'pending_projects': 0,
            'total_leads': 0,
        } for dept in tracked_departments
    }

    employee_rows = []

    employees_qs = Employee.objects.all().order_by('first_name', 'last_name')

    for emp in employees_qs:
        dept_name = canonical_department(emp.department)
        if dept_name not in tracked_departments:
            continue

        keys = employee_keys(emp)
        project_by_status = defaultdict(int)
        project_total = 0
        for key in keys:
            for status_key, count in project_status_counts.get(key, {}).items():
                project_by_status[status_key] += count
                project_total += count

        lead_by_status = defaultdict(int)
        lead_total = 0
        for key in keys:
            for status_key, count in lead_status_counts.get(key, {}).items():
                lead_by_status[status_key] += count
                lead_total += count

        completed_count = project_by_status.get('completed', 0)
        pending_count = max(project_total - completed_count, 0)

        dept_summary[dept_name]['total_projects'] += project_total
        dept_summary[dept_name]['completed_projects'] += completed_count
        dept_summary[dept_name]['pending_projects'] += pending_count
        dept_summary[dept_name]['total_leads'] += lead_total
        if dept_name == 'Sales':
            dept_summary[dept_name]['leads_high'] = dept_summary[dept_name].get('leads_high', 0) + lead_by_status.get('high', 0)
            dept_summary[dept_name]['leads_medium'] = dept_summary[dept_name].get('leads_medium', 0) + lead_by_status.get('medium', 0)
            dept_summary[dept_name]['leads_low'] = dept_summary[dept_name].get('leads_low', 0) + lead_by_status.get('low', 0) + lead_by_status.get('unspecified', 0)

        employee_rows.append({
            'id': emp.id,
            'name': emp.get_full_name() or emp.first_name or 'Unnamed',
            'designation': emp.designation or '',
            'department': dept_name,
            'projects_total': project_total,
            'projects_completed': completed_count,
            'projects_pending': pending_count,
            'projects_by_status': dict(project_by_status),
            'leads_total': lead_total,
            'leads_by_status': dict(lead_by_status),
        })

    # Determine column orders
    project_status_base = ['active', 'pending', 'on_hold', 'completed']
    lead_status_base = ['high', 'medium', 'low']

    project_status_order = project_status_base[:]
    for counts in project_status_counts.values():
        for status_key in counts.keys():
            if status_key not in project_status_order:
                project_status_order.append(status_key)

    lead_status_order = lead_status_base[:]
    for counts in lead_status_counts.values():
        for status_key in counts.keys():
            if status_key not in lead_status_order:
                lead_status_order.append(status_key)

    for status in project_status_order:
        project_status_display.setdefault(status, project_status_label(status))
    for status in lead_status_order:
        lead_status_display.setdefault(status, lead_status_label(status))

    project_status_headers = [
        {'key': status, 'label': project_status_display[status]}
        for status in project_status_order
    ]
    lead_status_headers = [
        {'key': status, 'label': lead_status_display[status]}
        for status in lead_status_order
    ]

    # Add ordered counts for template consumption
    for row in employee_rows:
        row['project_status_counts'] = [
            {'key': header['key'], 'count': row['projects_by_status'].get(header['key'], 0)}
            for header in project_status_headers
        ]
        row['lead_status_counts'] = [
            {'key': header['key'], 'count': row['leads_by_status'].get(header['key'], 0)}
            for header in lead_status_headers
        ]

    if selected_department != 'all':
        filtered_rows = [row for row in employee_rows if row['department'] == selected_department]
    else:
        filtered_rows = employee_rows

    employee_reports = sorted(
        filtered_rows,
        key=lambda r: (-r['projects_total'], -r['leads_total'], r['name'].lower())
    )

    # Override Sales summary with overall lead totals - using same query as leads page
    # This ensures sales card shows exact same count as leads page (no date filter)
    sales_summary = dept_summary.get('Sales')
    if sales_summary is not None:
        # Use exact same query as leads page: Lead.objects.filter(is_active=True)
        # NO date filter - show all active leads like leads page does
        all_leads_queryset = Lead.objects.filter(is_active=True)
        sales_total_leads = all_leads_queryset.count()
        sales_summary['total_leads'] = sales_total_leads
        
        # Count by priority from the same queryset (using exact priority values from model)
        sales_summary['leads_high'] = all_leads_queryset.filter(priority='High').count()
        sales_summary['leads_medium'] = all_leads_queryset.filter(priority='Med').count()
        # Low and any other/unspecified priorities
        low_count = all_leads_queryset.filter(priority='Low').count()
        # Count any leads that don't have standard priority values
        other_count = all_leads_queryset.exclude(priority__in=['High', 'Med', 'Low']).count()
        sales_summary['leads_low'] = low_count + other_count

    modal_leads_queryset = Lead.objects.filter(is_active=True).order_by('-created_at')
    
    # Determine conversion status by cross-checking ClientOnboarding records
    def normalize_email(value):
        return value.strip().lower() if value else ''

    def normalize_phone(value):
        if not value:
            return ''
        return re.sub(r'\D+', '', value)

    client_contacts = list(ClientOnboarding.objects.all().values('client_email', 'client_phone', 'client_name'))
    client_emails = {normalize_email(item['client_email']) for item in client_contacts if item['client_email']}
    client_phones = {normalize_phone(item['client_phone']) for item in client_contacts if item['client_phone']}
    client_names = {normalize_email(item['client_name']) for item in client_contacts if item['client_name']}
    
    modal_leads = []
    for lead in modal_leads_queryset:
        email_key = normalize_email(lead.email)
        phone_key = normalize_phone(lead.phone)
        name_key = normalize_email(lead.name)

        converted = any([
            email_key and email_key in client_emails,
            phone_key and phone_key in client_phones,
            name_key and name_key in client_names
        ])

        conversion_status = 'Converted' if converted else 'Pending'
        conversion_badge = 'bg-success' if converted else 'bg-secondary'
        
        modal_leads.append({
            'id': lead.id,
            'name': lead.name,
            'email': lead.email or '-',
            'phone': lead.phone or '-',
            'company': lead.company or '-',
            'owner': lead.owner or '-',
            'priority': lead.priority,
            'source': lead.source,
            'status': conversion_status,
            'status_badge': conversion_badge,
            'next_action': lead.next_action or '-',
            'due_date': lead.due_date.strftime('%d-%b-%Y') if lead.due_date else '-',
            'created_at_display': lead.created_at.strftime('%d-%b-%Y %H:%M') if lead.created_at else '-',
            'created_month': lead.created_at.strftime('%Y-%m') if lead.created_at else '',
            'created_year': lead.created_at.strftime('%Y') if lead.created_at else '',
        })

    # Engineering department data for modal
    # Get all Engineering employees using the same logic as main reports
    engineering_employees_list = []
    for emp in employees_qs:
        dept_name = canonical_department(emp.department)
        if dept_name == 'Engineering':
            engineering_employees_list.append(emp)
    
    # Get all projects and match them to Engineering employees using same logic as main reports
    engineering_projects = []
    engineering_employee_keys = set()
    engineering_employee_name_map = {}  # Map normalized keys to actual employee names
    engineering_employee_project_map = {}  # Map employee to their projects
    
    for emp in engineering_employees_list:
        keys = employee_keys(emp)
        engineering_employee_keys.update(keys)
        emp_name = emp.get_full_name() or emp.first_name or 'Unknown'
        # Store mapping for display
        for key in keys:
            if key:
                engineering_employee_name_map[key] = emp_name
                engineering_employee_project_map[key] = {
                    'name': emp_name,
                    'designation': emp.designation or '',
                    'projects': []
                }
    
    # Get all projects (without date filter for modal)
    all_projects = ClientOnboarding.objects.all().order_by('-created_at')
    for project in all_projects:
        assigned_engineer_normalized = normalize_key(project.assigned_engineer)
        # Match using the same logic as main reports
        if assigned_engineer_normalized and assigned_engineer_normalized in engineering_employee_keys:
            project_data = {
                'id': project.id,
                'project_name': project.project_name,
                'client_name': project.client_name,
                'assigned_engineer': project.assigned_engineer,
                'status': project.status,
                'status_display': project.get_status_display(),
                'project_cost': project.project_cost,
                'start_date': project.start_date.strftime('%d-%b-%Y') if project.start_date else '-',
                'created_at_display': project.created_at.strftime('%d-%b-%Y %H:%M') if project.created_at else '-',
            }
            engineering_projects.append(project_data)
            # Add to employee's project list
            if assigned_engineer_normalized in engineering_employee_project_map:
                engineering_employee_project_map[assigned_engineer_normalized]['projects'].append(project_data)
    
    # Create list of engineering employees with their project status
    engineering_employees_with_projects = []
    for emp in engineering_employees_list:
        emp_name = emp.get_full_name() or emp.first_name or 'Unknown'
        keys = employee_keys(emp)
        has_projects = False
        unique_projects = set()  # Use set to avoid duplicate counting
        
        for key in keys:
            if key and key in engineering_employee_project_map:
                projects = engineering_employee_project_map[key]['projects']
                if projects:
                    has_projects = True
                    # Add project IDs to set to avoid duplicates
                    for proj in projects:
                        unique_projects.add(proj['id'])
        
        engineering_employees_with_projects.append({
            'name': emp_name,
            'designation': emp.designation or '',
            'has_projects': has_projects,
            'project_count': len(unique_projects),
            'status': 'Assigned' if has_projects else 'Not Assigned'
        })
    
    total_engineering_employees = len(engineering_employees_list)
    total_assigned_projects = len(engineering_projects)
    completed_projects_count = sum(1 for p in engineering_projects if p['status'] == 'completed')

    # Back Office department data for modal
    backoffice_employees = Employee.objects.filter(
        department__icontains='backoffice'
    ) | Employee.objects.filter(
        department__icontains='back office'
    ) | Employee.objects.filter(
        department__icontains='backofficeops'
    ) | Employee.objects.filter(
        department__icontains='backofficeoperations'
    ) | Employee.objects.filter(
        department__icontains='backoffice-support'
    )
    # Normalize department names
    backoffice_employees_list = []
    for emp in backoffice_employees:
        dept_name = canonical_department(emp.department)
        if dept_name == 'Back Office':
            backoffice_employees_list.append(emp)
    
    # Get all projects assigned to Back Office employees
    backoffice_projects = []
    backoffice_employee_names = {emp.get_full_name() or emp.first_name or '' for emp in backoffice_employees_list}
    backoffice_employee_names.update({emp.first_name or '' for emp in backoffice_employees_list if emp.first_name})
    backoffice_employee_names.update({emp.emp_code or '' for emp in backoffice_employees_list if emp.emp_code})
    backoffice_employee_names.update({emp.email or '' for emp in backoffice_employees_list if emp.email})
    backoffice_employee_names.update({emp.work_email or '' for emp in backoffice_employees_list if emp.work_email})
    backoffice_employee_names = {name.lower().strip() for name in backoffice_employee_names if name}
    
    all_projects_backoffice = ClientOnboarding.objects.all()
    for project in all_projects_backoffice:
        assigned_engineer_normalized = normalize_key(project.assigned_engineer)
        if assigned_engineer_normalized in backoffice_employee_names:
            backoffice_projects.append({
                'id': project.id,
                'project_name': project.project_name,
                'client_name': project.client_name,
                'assigned_engineer': project.assigned_engineer,
                'status': project.status,
                'status_display': project.get_status_display(),
                'project_cost': project.project_cost,
                'start_date': project.start_date.strftime('%d-%b-%Y') if project.start_date else '-',
                'created_at_display': project.created_at.strftime('%d-%b-%Y %H:%M') if project.created_at else '-',
            })
    
    # Prepare Back Office employees data with completed projects count
    backoffice_employees_data = []
    for emp in backoffice_employees_list:
        keys = employee_keys(emp)
        employee_projects_list = []
        completed_count = 0
        
        # Get projects for this employee
        for project in backoffice_projects:
            assigned_engineer_normalized = normalize_key(project['assigned_engineer'])
            # Check if assigned engineer matches any of the employee's keys
            if assigned_engineer_normalized in keys:
                employee_projects_list.append(project)
                if project['status'] == 'completed':
                    completed_count += 1
        
        backoffice_employees_data.append({
            'id': emp.id,
            'name': emp.get_full_name() or emp.first_name or 'Unnamed',
            'designation': emp.designation or '',
            'email': emp.email or '',
            'projects_total': len(employee_projects_list),
            'projects_completed': completed_count,
            'employee_projects': employee_projects_list,
            'employee_projects_json': json.dumps(employee_projects_list),
        })
    
    total_backoffice_employees = len(backoffice_employees_list)
    total_backoffice_projects = len(backoffice_projects)
    total_backoffice_completed = sum(1 for p in backoffice_projects if p['status'] == 'completed')

    department_cards = []
    for dept in tracked_departments:
        summary = dept_summary[dept]
        high_leads = summary.get('leads_high', 0)
        medium_leads = summary.get('leads_medium', 0)
        low_leads = summary.get('leads_low', 0)
        other_leads = summary['total_leads'] - high_leads - medium_leads - low_leads
        lead_breakdown = {
            'high': high_leads,
            'medium': medium_leads,
            'other': other_leads if other_leads > 0 else 0
        }
        department_cards.append({
            'name': dept,
            'total_projects': summary['total_projects'],
            'completed_projects': summary['completed_projects'],
            'pending_projects': summary['pending_projects'],
            'total_leads': summary['total_leads'],
            'lead_breakdown': lead_breakdown,
            'is_active': selected_department == dept,
        })

    # Prepare Accounts team employee data for modal
    accounts_employees_list = []
    accounts_employees_qs = Employee.objects.all()
    for emp in accounts_employees_qs:
        dept_name = canonical_department(emp.department)
        if dept_name == 'Accounts':
            accounts_employees_list.append(emp)
    
    # Get all projects assigned to Accounts employees
    accounts_projects = []
    accounts_employee_names = {emp.get_full_name() or emp.first_name or '' for emp in accounts_employees_list}
    accounts_employee_names.update({emp.first_name or '' for emp in accounts_employees_list if emp.first_name})
    accounts_employee_names.update({emp.emp_code or '' for emp in accounts_employees_list if emp.emp_code})
    accounts_employee_names.update({emp.email or '' for emp in accounts_employees_list if emp.email})
    accounts_employee_names.update({emp.work_email or '' for emp in accounts_employees_list if emp.work_email})
    accounts_employee_names = {name.lower().strip() for name in accounts_employee_names if name}
    
    all_projects_accounts = ClientOnboarding.objects.all()
    for project in all_projects_accounts:
        assigned_engineer_normalized = normalize_key(project.assigned_engineer)
        if assigned_engineer_normalized in accounts_employee_names:
            accounts_projects.append({
                'id': project.id,
                'project_name': project.project_name,
                'client_name': project.client_name,
                'assigned_engineer': project.assigned_engineer,
                'status': project.status,
                'status_display': project.get_status_display(),
                'project_cost': float(project.project_cost) if project.project_cost else 0,
                'start_date': project.start_date.strftime('%d-%b-%Y') if project.start_date else '-',
                'created_at': project.created_at.strftime('%d-%b-%Y') if project.created_at else '-',
                'created_at_display': project.created_at.strftime('%d-%b-%Y %H:%M') if project.created_at else '-',
            })
    
    accounts_employees_data = []
    for emp in accounts_employees_list:
        keys = employee_keys(emp)
        project_by_status = defaultdict(int)
        project_total = 0
        for key in keys:
            for status_key, count in project_status_counts.get(key, {}).items():
                project_by_status[status_key] += count
                project_total += count
        
        lead_by_status = defaultdict(int)
        lead_total = 0
        for key in keys:
            for status_key, count in lead_status_counts.get(key, {}).items():
                lead_by_status[status_key] += count
                lead_total += count
        
        # Get actual projects for this employee
        employee_projects_list = []
        for project in accounts_projects:
            assigned_engineer_normalized = normalize_key(project['assigned_engineer'])
            emp_name_normalized = normalize_key(emp.get_full_name() or emp.first_name or '')
            emp_first_name_normalized = normalize_key(emp.first_name or '')
            emp_code_normalized = normalize_key(emp.emp_code or '')
            emp_email_normalized = normalize_key(emp.email or '')
            
            if (assigned_engineer_normalized == emp_name_normalized or 
                assigned_engineer_normalized == emp_first_name_normalized or
                assigned_engineer_normalized == emp_code_normalized or
                assigned_engineer_normalized == emp_email_normalized):
                employee_projects_list.append({
                    'id': project['id'],
                    'project_name': project['project_name'],
                    'client_name': project['client_name'],
                    'status': project['status'],
                    'project_cost': project['project_cost'],
                    'created_at': project['created_at'],
                })
        
        accounts_employees_data.append({
            'id': emp.id,
            'name': emp.get_full_name() or emp.first_name or 'Unnamed',
            'designation': emp.designation or '',
            'email': emp.email or '',
            'projects_total': project_total,
            'projects_by_status': dict(project_by_status),
            'leads_total': lead_total,
            'leads_by_status': dict(lead_by_status),
            'employee_projects': employee_projects_list[:10],  # Limit to 10 projects
        })

    context = {
        'department_choices': [{'value': 'all', 'label': 'All Departments'}] + [
            {'value': dept, 'label': dept} for dept in tracked_departments
        ],
        'selected_department_value': selected_department,
        'selected_department_label': selected_department_label,
        'month_input_value': month_input_value,
        'day_input_value': day_input_value,
        'selected_month_label': month_label,
        'showing_all_time': showing_all_time,
        'filters_active': filters_active,
        'department_cards': department_cards,
        'employee_reports': employee_reports,
        'project_status_headers': project_status_headers,
        'lead_status_headers': lead_status_headers,
        'results_count': len(employee_reports),
        'modal_leads': modal_leads,
        'accounts_employees': accounts_employees_data,
        'engineering_employees_count': total_engineering_employees,
        'engineering_completed_projects': completed_projects_count,
        'engineering_total_projects': total_assigned_projects,
        'engineering_projects': engineering_projects,
        'engineering_employees_with_projects': engineering_employees_with_projects,
        'backoffice_employees_count': total_backoffice_employees,
        'backoffice_completed_projects': total_backoffice_completed,
        'backoffice_total_projects': total_backoffice_projects,
        'backoffice_employees': backoffice_employees_data,
        'backoffice_projects': backoffice_projects,
    }

    return render(request, 'dashboard/reports.html', context)


@login_required
def settings_view(request):
  """Settings view - fetches logged-in user's data"""
  # Handle POST request for saving profile
  if request.method == 'POST':
    try:
      user = request.user
      user_email = getattr(user, 'email', '')
      
      # Try to get employee
      employee = Employee.objects.filter(email__iexact=user_email).first()
      
      if not employee:
        # Try by name
        user_full_name = user.get_full_name() or user.username or ''
        if user_full_name:
          name_parts = user_full_name.strip().split(' ', 1)
          first_name = name_parts[0] if name_parts else ''
          last_name = name_parts[1] if len(name_parts) > 1 else ''
          
          if first_name and last_name:
            employee = Employee.objects.filter(
              first_name__iexact=first_name,
              last_name__iexact=last_name
            ).first()
      
      # Update employee data
      if employee:
        full_name = request.POST.get('full_name', '')
        if full_name:
          name_parts = full_name.strip().split(' ', 1)
          employee.first_name = name_parts[0] if name_parts else ''
          employee.last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        employee.phone = request.POST.get('phone', '') or employee.phone
        employee.designation = request.POST.get('designation', '') or employee.designation
        employee.save()
        
        messages.success(request, 'Profile updated successfully!')
      else:
        # Update User model if employee not found
        full_name = request.POST.get('full_name', '')
        if full_name:
          name_parts = full_name.strip().split(' ', 1)
          user.first_name = name_parts[0] if name_parts else ''
          user.last_name = name_parts[1] if len(name_parts) > 1 else ''
          user.save()
        
        messages.success(request, 'Profile updated successfully!')
        
    except Exception as e:
      messages.error(request, f'Error updating profile: {str(e)}')
  
  # Get logged-in user's information
  user = request.user
  employee = None
  user_full_name = 'Guest User'
  user_email = getattr(user, 'email', '')
  user_phone = ''
  user_designation = ''
  user_role = 'Employee'
  user_initials = 'GU'
  
  # Try to get employee data from Employee model
  if user.is_authenticated:
    try:
      # Try to get employee by email
      employee = Employee.objects.filter(email__iexact=user_email).first()
      
      # If not found by email, try by matching name
      if not employee:
        user_full_name = user.get_full_name() or user.username or ''
        if user_full_name:
          name_parts = user_full_name.strip().split(' ', 1)
          first_name = name_parts[0] if name_parts else ''
          last_name = name_parts[1] if len(name_parts) > 1 else ''
          
          if first_name and last_name:
            employee = Employee.objects.filter(
              first_name__iexact=first_name,
              last_name__iexact=last_name
            ).first()
      
      # If employee found, get data
      if employee:
        user_full_name = employee.get_full_name()
        user_email = employee.email or user_email
        user_phone = employee.phone or ''
        user_designation = employee.designation or ''
        user_role = employee.role or 'Employee'
        # Get initials for avatar
        user_initials = employee.get_initials() or (user_full_name[0:2].upper() if user_full_name else 'GU')
      else:
        # Use User model data
        user_full_name = user.get_full_name() or user.username or 'Guest User'
        user_email = getattr(user, 'email', '')
        user_initials = (user_full_name[0:2].upper() if user_full_name else 'GU')
        
    except Exception as e:
      print(f"Error fetching employee data: {str(e)}")
      # Fallback to User model data
      user_full_name = user.get_full_name() or user.username or 'Guest User'
      user_email = getattr(user, 'email', '')
      user_initials = (user_full_name[0:2].upper() if user_full_name else 'GU')
  
  # Prepare context
  context = {
    'user_full_name': user_full_name,
    'user_email': user_email,
    'user_phone': user_phone,
    'user_designation': user_designation,
    'user_role': user_role,
    'user_initials': user_initials,
  }
  
  return render(request, 'setting.html', context)

@login_required
def change_password_view(request):
  """Change password view - updates employee password"""
  if request.method == 'POST':
    try:
      user = request.user
      user_email = getattr(user, 'email', '')
      
      # Get employee
      employee = Employee.objects.filter(email__iexact=user_email).first()
      
      if not employee:
        # Try by name
        user_full_name = user.get_full_name() or user.username or ''
        if user_full_name:
          name_parts = user_full_name.strip().split(' ', 1)
          first_name = name_parts[0] if name_parts else ''
          last_name = name_parts[1] if len(name_parts) > 1 else ''
          
          if first_name and last_name:
            employee = Employee.objects.filter(
              first_name__iexact=first_name,
              last_name__iexact=last_name
            ).first()
      
      if not employee:
        return JsonResponse({'success': False, 'error': 'Employee record not found. Please contact administrator.'})
      
      # Get form data
      current_password = request.POST.get('current_password', '').strip()
      new_password = request.POST.get('new_password', '').strip()
      confirm_password = request.POST.get('confirm_password', '').strip()
      
      # Validation
      if not current_password or not new_password or not confirm_password:
        return JsonResponse({'success': False, 'error': 'All fields are required.'})
      
      if len(new_password) < 8:
        return JsonResponse({'success': False, 'error': 'New password must be at least 8 characters long.'})
      
      if new_password != confirm_password:
        return JsonResponse({'success': False, 'error': 'New password and confirm password do not match.'})
      
      # Check current password
      from django.contrib.auth.hashers import check_password, make_password
      
      # Verify current password based on whether password is set or not
      if employee.password and employee.password.strip():
        # Password is set - verify using password
        if not check_password(current_password, employee.password):
          return JsonResponse({'success': False, 'error': 'Current password is incorrect.'})
        
        # Check if new password is same as current password
        if check_password(new_password, employee.password):
          return JsonResponse({'success': False, 'error': 'New password must be different from current password.'})
      else:
        # Password is not set - verify using phone number
        if not employee.phone:
          return JsonResponse({'success': False, 'error': 'Phone number not found. Please contact administrator.'})
        
        employee_phone = ''.join(filter(str.isdigit, employee.phone or ''))
        input_phone = ''.join(filter(str.isdigit, current_password))
        
        if not input_phone:
          return JsonResponse({'success': False, 'error': 'Please enter a valid phone number.'})
        
        if employee_phone != input_phone:
          return JsonResponse({'success': False, 'error': 'Current phone number is incorrect.'})
        
        # Check if new password is same as phone (normalized)
        normalized_new_password = ''.join(filter(str.isdigit, new_password))
        if normalized_new_password == employee_phone:
          return JsonResponse({'success': False, 'error': 'New password cannot be the same as your phone number.'})
      
      # Hash and save new password
      employee.password = make_password(new_password)
      employee.save()
      
      # Also update User model password for consistency
      if user:
        user.set_password(new_password)
        user.save()
      
      return JsonResponse({'success': True, 'message': 'Password changed successfully!'}, status=200)
      
    except Exception as e:
      import traceback
      error_msg = str(e)
      print(f"Change password error: {error_msg}")
      print(traceback.format_exc())
      return JsonResponse({'success': False, 'error': f'Error changing password: {error_msg}'}, status=400)
  
  return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)

def in_out(request):
  return render(request, 'human_resource/in_out.html')


@login_required
def project_management(request):
  """Project management view - displays ClientOnboarding data"""
  from django.core.paginator import Paginator
  
  # Get all client onboarding records from database
  client_onboarding_list = ClientOnboarding.objects.all().order_by('-id')
  
  # Search functionality
  search_query = request.GET.get('search', '')
  if search_query:
    client_onboarding_list = client_onboarding_list.filter(
      Q(client_name__icontains=search_query) |
      Q(company_name__icontains=search_query) |
      Q(project_name__icontains=search_query) |
      Q(assigned_engineer__icontains=search_query)
    )
  
  # Filter by status
  status_filter = request.GET.get('status', '')
  if status_filter:
    client_onboarding_list = client_onboarding_list.filter(status=status_filter)
  
  # Pagination
  paginator = Paginator(client_onboarding_list, 10)  # 10 items per page
  page_number = request.GET.get('page')
  page_obj = paginator.get_page(page_number)
  
  # Count by status
  status_counts = {
    'total': ClientOnboarding.objects.count(),
    'active': ClientOnboarding.objects.filter(status='active').count(),
    'pending': ClientOnboarding.objects.filter(status='pending').count(),
    'on_hold': ClientOnboarding.objects.filter(status='on_hold').count(),
    'completed': ClientOnboarding.objects.filter(status='completed').count(),
  }
  
  # Get total count for pagination display
  total_projects = client_onboarding_list.count()
  
  context = {
    'client_onboarding_list': page_obj,
    'status_counts': status_counts,
    'search_query': search_query,
    'status_filter': status_filter,
    'total_projects': total_projects,
  }
  return render(request, "project_managemnet'/project.html", context)

@login_required
def project_onboard_view(request, onboard_id):
    """Get client onboarding details as JSON"""
    try:
        onboard = ClientOnboarding.objects.get(id=onboard_id)
        return JsonResponse({
            'id': onboard.id,
            'client_name': onboard.client_name or '',
            'company_name': onboard.company_name or '',
            'client_email': onboard.client_email or '',
            'client_phone': onboard.client_phone or '',
            'project_name': onboard.project_name or '',
            'project_description': onboard.project_description or '',
            'project_duration': onboard.project_duration,
            'duration_unit': onboard.duration_unit,
            'duration_display': f"{onboard.project_duration} {onboard.get_duration_unit_display()}",
            'project_cost': str(onboard.project_cost),
            'assigned_engineer': onboard.assigned_engineer or '',
            'start_date': onboard.start_date.strftime('%Y-%m-%d') if onboard.start_date else '',
            'start_date_display': onboard.start_date.strftime('%d %b %Y') if onboard.start_date else 'Not set',
            'status': onboard.status,
            'status_display': onboard.get_status_display(),
            'created_at': onboard.created_at.strftime('%d %b %Y %I:%M %p') if onboard.created_at else '',
            'updated_at': onboard.updated_at.strftime('%d %b %Y %I:%M %p') if onboard.updated_at else ''
        })
    except ClientOnboarding.DoesNotExist:
        return JsonResponse({'error': 'Project not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_POST
@login_required
def project_onboard_update(request, onboard_id):
    """Update client onboarding record"""
    try:
        onboard = ClientOnboarding.objects.get(id=onboard_id)
        
        # Update fields
        onboard.client_name = request.POST.get('client_name', '').strip() or onboard.client_name
        onboard.company_name = request.POST.get('company_name', '').strip() or None
        onboard.client_email = request.POST.get('client_email', '').strip() or None
        onboard.client_phone = request.POST.get('client_phone', '').strip() or None
        onboard.project_name = request.POST.get('project_name', '').strip() or onboard.project_name
        onboard.project_description = request.POST.get('project_description', '').strip() or None
        
        # Parse numeric fields
        if request.POST.get('project_duration'):
            onboard.project_duration = int(request.POST.get('project_duration'))
        if request.POST.get('project_cost'):
            onboard.project_cost = Decimal(request.POST.get('project_cost'))
        if request.POST.get('duration_unit'):
            onboard.duration_unit = request.POST.get('duration_unit')
        
        onboard.assigned_engineer = request.POST.get('assigned_engineer', '').strip() or onboard.assigned_engineer
        if request.POST.get('status'):
            onboard.status = request.POST.get('status')
        
        # Parse start_date
        start_date_str = request.POST.get('start_date', '').strip()
        if start_date_str:
            try:
                from django.utils.dateparse import parse_date
                onboard.start_date = parse_date(start_date_str)
            except (ValueError, TypeError):
                pass
        
        onboard.save()
        
        messages.success(request, f'Project updated successfully!')
        return JsonResponse({
            'success': True,
            'message': 'Project updated successfully!'
        })
    except ClientOnboarding.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Project not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

# Employee Portal Views
@login_required
def employee_dashboard(request):
    """Employee dashboard view - fetches data from employee tables"""
    from datetime import timedelta
    from django.db.models import Q, Sum
    from django.utils import timezone
    
    # Get logged-in user's information
    employee_obj = None
    employee_name = 'Guest User'
    employee_first_name = 'Guest'
    employee_initials = 'GU'
    employee_role = 'Employee'
    employee_designation = 'Employee'
    employee_id = 'N/A'
    employee_department = None
    
    if request.user.is_authenticated:
        # Get user's full name or username safely
        try:
            user_full_name = request.user.get_full_name() or request.user.username or ''
        except AttributeError:
            # Fallback if get_full_name doesn't exist
            user_full_name = getattr(request.user, 'first_name', '') + ' ' + getattr(request.user, 'last_name', '')
            user_full_name = user_full_name.strip() or request.user.username or ''
        
        # Try to match employee by name
        name_parts = user_full_name.strip().split(' ', 1)
        first_name = name_parts[0] if name_parts else ''
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        # Try to find employee by matching name
        if first_name and last_name:
            employee_obj = Employee.objects.filter(
                first_name__iexact=first_name,
                last_name__iexact=last_name
            ).first()
        
        # If not found by name, try by email
        if not employee_obj:
            user_email = getattr(request.user, 'email', None)
            if user_email:
                employee_obj = Employee.objects.filter(
                    email__iexact=user_email
                ).first()
        
        # If still not found, try by partial name match
        if not employee_obj and user_full_name:
            user_email = getattr(request.user, 'email', None)
            employees = Employee.objects.filter(
                Q(first_name__icontains=first_name) |
                Q(last_name__icontains=first_name) |
                Q(email__icontains=user_email if user_email else '')
            )
            employee_obj = employees.first()
        
        # Set employee info
        if employee_obj:
            employee_name = employee_obj.get_full_name()
            employee_first_name = employee_obj.first_name or ''
            employee_initials = employee_obj.get_initials() or 'GU'
            employee_role = employee_obj.designation or 'Employee'
            employee_designation = employee_obj.designation or 'Employee'
            employee_id = employee_obj.emp_code or 'N/A'
            employee_department = employee_obj.department or None
        else:
            employee_name = user_full_name
            employee_first_name = first_name or user_full_name.split()[0] if user_full_name else 'Guest'
            employee_initials = (employee_first_name[0] + (last_name[0] if last_name else employee_first_name[0])).upper() if employee_first_name else 'GU'
            employee_role = 'Employee'
            employee_designation = 'Employee'
    
    # Get current date and time
    now = timezone.now()
    current_date = now.strftime('%b %d, %Y')  # Format: "Dec 15, 2024"
    current_time = now.strftime('%I:%M %p')
    
    # Check today's attendance status
    today = now.date()
    today_attendance = None
    attendance_status = 'Absent'
    is_checked_in = False
    
    if request.user.is_authenticated:
        # Priority 1: If employee_obj exists, match by employee foreign key first
        if employee_obj:
            today_attendance = Attendance.objects.filter(
                employee=employee_obj,
                date=today
            ).first()
        
        # Priority 2: If not found by employee, try by employee_name
        if not today_attendance and employee_obj:
            today_attendance = Attendance.objects.filter(
                employee_name__iexact=employee_name,
                date=today
            ).first()
        
        # Priority 3: If not found, try by user
        if not today_attendance:
            today_attendance = Attendance.objects.filter(
                user=request.user,
                date=today
            ).first()
        
        if today_attendance:
            if today_attendance.check_in_time and not today_attendance.check_out_time:
                attendance_status = 'Present'
                is_checked_in = True
            elif today_attendance.check_in_time and today_attendance.check_out_time:
                attendance_status = 'Present'
    
    # Get projects from ClientOnboarding (similar to employee_projects)
    if request.user.is_authenticated:
        try:
            user_name = employee_name if employee_obj else (request.user.get_full_name() or request.user.username or '')
        except AttributeError:
            user_name = employee_name if employee_obj else request.user.username or ''
    else:
        user_name = employee_name
    client_onboardings = ClientOnboarding.objects.filter(
        assigned_engineer__iexact=user_name
    ).only(
        'id',
        'project_name',
        'project_description',
        'status',
        'start_date',
        'project_duration',
        'duration_unit',
        'assigned_engineer'
    ).order_by('-created_at')[:5]  # Get top 5 projects for dashboard
    
    # Convert to project data structure
    projects = []
    active_projects_count = 0
    tasks_completed_total = 0
    
    for onboarding in client_onboardings:
        # Calculate due date
        due_date = None
        if onboarding.start_date:
            duration_days = 0
            if onboarding.duration_unit == 'days':
                duration_days = onboarding.project_duration
            elif onboarding.duration_unit == 'weeks':
                duration_days = onboarding.project_duration * 7
            elif onboarding.duration_unit == 'months':
                duration_days = onboarding.project_duration * 30
            elif onboarding.duration_unit == 'years':
                duration_days = onboarding.project_duration * 365
            due_date = onboarding.start_date + timedelta(days=duration_days)
        
        # Map status
        status_map = {
            'active': 'In Progress',
            'pending': 'Pending',
            'on_hold': 'On Hold',
            'completed': 'Completed'
        }
        template_status = status_map.get(onboarding.status, 'Pending')
        
        # Count active projects
        if onboarding.status == 'active':
            active_projects_count += 1
        
        # Calculate progress
        progress_map = {
            'active': 50,
            'pending': 0,
            'on_hold': 30,
            'completed': 100
        }
        progress = progress_map.get(onboarding.status, 0)
        
        # Calculate tasks
        tasks_map = {
            'active': {'total': 10, 'completed': 5, 'pending': 5},
            'pending': {'total': 8, 'completed': 0, 'pending': 8},
            'on_hold': {'total': 12, 'completed': 4, 'pending': 8},
            'completed': {'total': 10, 'completed': 10, 'pending': 0}
        }
        tasks = tasks_map.get(onboarding.status, {'total': 8, 'completed': 0, 'pending': 8})
        tasks_completed_total += tasks['completed']
        
        # Derive project type
        project_type = 'Project'
        if onboarding.project_description:
            desc_lower = onboarding.project_description.lower()
            if 'web' in desc_lower or 'website' in desc_lower:
                project_type = 'Web Application'
            elif 'mobile' in desc_lower or 'app' in desc_lower:
                project_type = 'Mobile Application'
            elif 'database' in desc_lower or 'backend' in desc_lower:
                project_type = 'Backend Task'
            elif 'security' in desc_lower:
                project_type = 'Security Task'
            elif 'dashboard' in desc_lower or 'analytics' in desc_lower:
                project_type = 'Data Visualization'
            elif 'cloud' in desc_lower or 'infrastructure' in desc_lower:
                project_type = 'Infrastructure'
        
        # Format due date
        due_date_display = None
        if due_date:
            due_date_display = due_date.strftime('%b %d, %Y')
        
        project_data = {
            'id': onboarding.id,
            'name': onboarding.project_name,
            'type': project_type,
            'progress': progress,
            'due_date': due_date_display,
            'status': template_status,
            'description': onboarding.project_description or 'No description available.'
        }
        projects.append(project_data)
    
    # Calculate hours worked this week
    hours_worked = 0
    if request.user.is_authenticated:
        # Get start of week (Monday)
        today = now.date()
        start_of_week = today - timedelta(days=today.weekday())
        
        # Get all attendance records for this week
        # Priority 1: If employee_obj exists, match by employee foreign key first
        if employee_obj:
            week_attendance = Attendance.objects.filter(
                employee=employee_obj,
                date__gte=start_of_week,
                date__lte=today
            )
        else:
            week_attendance = Attendance.objects.none()
        
        # Priority 2: If no records found by employee, try by employee_name
        if not week_attendance.exists() and employee_obj:
            week_attendance = Attendance.objects.filter(
                employee_name__iexact=employee_name,
                date__gte=start_of_week,
                date__lte=today
            )
        
        # Priority 3: If no records found, try by user
        if not week_attendance.exists():
            week_attendance = Attendance.objects.filter(
                user=request.user,
                date__gte=start_of_week,
                date__lte=today
            )
        
        for att in week_attendance:
            work_hours = att.calculate_work_hours()
            if work_hours:
                hours_worked += work_hours['hours'] + (work_hours['minutes'] / 60)
    
    # Calculate attendance percentage for this month
    attendance_percentage = 0
    if request.user.is_authenticated:
        # Get start of month
        start_of_month = now.replace(day=1).date()
        
        # Get present days - Priority 1: If employee_obj exists, match by employee foreign key first
        if employee_obj:
            attendance_records = Attendance.objects.filter(
                employee=employee_obj,
                date__gte=start_of_month,
                date__lte=today,
                check_in_time__isnull=False
            ).order_by('date')
        else:
            attendance_records = Attendance.objects.none()
        
        # Priority 2: If no records found by employee, try by employee_name
        if not attendance_records.exists() and employee_obj:
            attendance_records = Attendance.objects.filter(
                employee_name__iexact=employee_name,
                date__gte=start_of_month,
                date__lte=today,
                check_in_time__isnull=False
            ).order_by('date')
        
        # Priority 3: If no records found, try by user
        if not attendance_records.exists():
            attendance_records = Attendance.objects.filter(
            user=request.user,
            date__gte=start_of_month,
            date__lte=today,
            check_in_time__isnull=False
            ).order_by('date')
        
        present_days = attendance_records.count()
        
        # Initialize working_days to avoid UnboundLocalError
        working_days = 0
        
        # If employee has attendance records, calculate from first attendance date
        if present_days > 0:
            # Get first attendance date
            first_attendance_date = attendance_records.first().date
            
            # Calculate working days from first attendance date to today
            total_days = (today - first_attendance_date).days + 1
            working_days = sum(1 for i in range(total_days) if (first_attendance_date + timedelta(days=i)).weekday() < 5)
        
        if working_days > 0:
            attendance_percentage = round((present_days / working_days) * 100, 1)
        else:
            # If no attendance records, use month start for calculation
            total_days = (today - start_of_month).days + 1
            working_days = sum(1 for i in range(total_days) if (start_of_month + timedelta(days=i)).weekday() < 5)
            
            if working_days > 0:
                attendance_percentage = 0
    
    # Get recent tasks from projects (derive from project status and tasks)
    recent_tasks = []
    for project in projects[:3]:  # Get top 3 projects for tasks
        if project['status'] != 'Completed':
            # Create sample tasks based on project
            task_status = 'In Progress' if project['status'] == 'In Progress' else 'Pending'
            recent_tasks.append({
                'title': f"Work on {project['name']}",
                'project': project['name'],
                'status': task_status,
                'completed': task_status == 'In Progress'
            })
    
    # Get today's schedule (attendance check-in/out, upcoming leaves)
    today_schedule = []
    if request.user.is_authenticated:
        # Add check-in time if exists
        if today_attendance and today_attendance.check_in_time:
            check_in_str = today_attendance.check_in_time.strftime('%I:%M %p')
            today_schedule.append({
                'title': 'Check In',
                'time': f"{check_in_str}",
                'location': 'Office',
                'type': 'checkin'
            })
        
        # Get upcoming leave requests for today
        today_leaves = LeaveRequest.objects.filter(
            user=request.user,
            start_date__lte=today,
            end_date__gte=today,
            status='Approved'
        ).first()
        
        if today_leaves:
            today_schedule.append({
                'title': f'On Leave - {today_leaves.leave_type}',
                'time': 'All Day',
                'location': 'Leave',
                'type': 'leave'
            })
    
    # Get notifications (upcoming project deadlines, newly assigned projects)
    notifications = []
    notification_count = 0
    
    # Check for projects due soon (within 7 days) and new projects
    for i, project in enumerate(projects):
        # Check due dates
        if project.get('due_date'):
            try:
                due = datetime.strptime(project['due_date'], '%b %d, %Y').date()
                days_until = (due - today).days
                if 0 <= days_until <= 7:
                    notification_count += 1
                    notifications.append({
                        'type': 'warning' if days_until <= 3 else 'info',
                        'title': 'Deadline approaching',
                        'message': f'"{project["name"]}" project due in {days_until} day(s)',
                        'time': f'{days_until} days ago' if days_until == 0 else f'Due in {days_until} days'
                    })
            except:
                pass
        
        # Check for new projects (created in last 7 days)
        if i < len(client_onboardings):
            onboarding = client_onboardings[i]
            if onboarding.created_at and (now.date() - onboarding.created_at.date()).days <= 7:
                notification_count += 1
                notifications.append({
                    'type': 'info',
                    'title': 'New project assigned',
                    'message': f'You have been assigned to "{project["name"]}" project',
                    'time': f'{(now.date() - onboarding.created_at.date()).days} days ago'
                })
    
    # Get weekly performance data for chart (last 7 days from attendance records)
    weekly_performance = {
        'tasks': [],
        'hours': [],
        'labels': []
    }
    if request.user.is_authenticated:
        # Get last 7 days data (Monday to Sunday of current week)
        # Start from Monday of current week
        start_of_week = today - timedelta(days=today.weekday())
        
        for i in range(7):
            day = start_of_week + timedelta(days=i)
            day_name = day.strftime('%a')  # Mon, Tue, Wed, etc.
            weekly_performance['labels'].append(day_name)
            
            # Priority 1: If employee_obj exists, match by employee foreign key first
            if employee_obj:
                day_attendance = Attendance.objects.filter(
                    employee=employee_obj,
                    date=day
                ).first()
            else:
                day_attendance = None
            
            # Priority 2: If not found by employee, try by employee_name
            if not day_attendance and employee_obj:
                day_attendance = Attendance.objects.filter(
                    employee_name__iexact=employee_name,
                    date=day
                ).first()
            
            # Priority 3: If not found, try by user
            if not day_attendance:
                day_attendance = Attendance.objects.filter(
                    user=request.user,
                    date=day
                ).first()
            
            if day_attendance:
                work_hours = day_attendance.calculate_work_hours()
                if work_hours:
                    # Calculate total hours (hours + minutes/60 + seconds/3600)
                    hours = work_hours['hours'] + (work_hours['minutes'] / 60) + (work_hours['seconds'] / 3600)
                    weekly_performance['hours'].append(round(hours, 2))
                else:
                    weekly_performance['hours'].append(0)
            else:
                weekly_performance['hours'].append(0)
            
            # Tasks completed (simplified - distribute tasks across week)
            # For now, use a simple distribution based on active projects
            daily_tasks = int(tasks_completed_total / 7) if tasks_completed_total > 0 else 0
            weekly_performance['tasks'].append(daily_tasks)
    else:
        # Default labels if not authenticated
        weekly_performance['labels'] = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        weekly_performance['hours'] = [0, 0, 0, 0, 0, 0, 0]
        weekly_performance['tasks'] = [0, 0, 0, 0, 0, 0, 0]
    
    # Convert weekly_performance to JSON for JavaScript
    weekly_performance_json = json.dumps(weekly_performance)
    
    # Get sidebar counts for badges
    # Unread Messages Count
    unread_messages_count = 0
    if request.user.is_authenticated:
        try:
            # Get user's employee ID or name for message filtering
            user_email = getattr(request.user, 'email', None)
            receiver_id = None
            
            # Try to get employee to get receiver_id
            if employee_obj:
                receiver_id = employee_obj.emp_code or str(employee_obj.id)
            elif user_email:
                # Try to find employee by email
                emp = Employee.objects.filter(email__iexact=user_email).first()
                if emp:
                    receiver_id = emp.emp_code or str(emp.id)
            
            if receiver_id:
                # Count unread messages for this employee
                unread_messages_count = EmployeeMessage.objects.filter(
                    receiver_id=receiver_id,
                    is_read=False
                ).count()
        except Exception as e:
            print(f"Error counting unread messages: {str(e)}")
            unread_messages_count = 0
    
    # New Projects Count (assigned after last visit)
    new_projects_count = 0
    if request.user.is_authenticated and user_name:
        try:
            # Get last visit timestamp from session
            last_visit_timestamp = request.session.get('last_visit_timestamp', None)
            
            if last_visit_timestamp:
                from datetime import datetime
                last_visit = datetime.fromtimestamp(last_visit_timestamp)
                # Count projects assigned after last visit
                new_projects_count = ClientOnboarding.objects.filter(
                    assigned_engineer__iexact=user_name,
                    created_at__gt=last_visit
                ).count()
            else:
                # First visit - show all active projects
                new_projects_count = ClientOnboarding.objects.filter(
                    assigned_engineer__iexact=user_name,
                    status='active'
                ).count()
        except Exception as e:
            print(f"Error counting new projects: {str(e)}")
            new_projects_count = 0
    
    # Sales-related counts for dashboard metrics
    leads_count = 0
    quotes_count = 0
    onboardings_count = 0
    try:
        # Show overall totals to ensure visibility; can be scoped later if needed
        leads_count = Lead.objects.filter(is_active=True).count()
        quotes_count = Quote.objects.all().count()
        onboardings_count = ClientOnboarding.objects.all().count()
    except Exception as e:
        print(f"Error computing sales counts: {str(e)}")
    
    # Pending Leave Requests Count
    pending_leaves_count = 0
    if request.user.is_authenticated:
        try:
            # Count pending leave requests for this user
            pending_leaves_count = LeaveRequest.objects.filter(
                user=request.user,
                status='Pending'
            ).count()
        except Exception as e:
            print(f"Error counting pending leaves: {str(e)}")
            pending_leaves_count = 0
    
    # Update last visit timestamp in session
    if request.user.is_authenticated:
        import time
        request.session['last_visit_timestamp'] = time.time()
    
    # Ensure employee details are set
    if not employee_first_name or employee_first_name == 'Guest':
        employee_first_name = employee_name.split()[0] if employee_name and employee_name != 'Guest User' else 'Guest'
    if not employee_initials or employee_initials == 'GU':
        if employee_name and employee_name != 'Guest User':
            name_parts = employee_name.split()
            if len(name_parts) > 0:
                employee_initials = (name_parts[0][0] + (name_parts[1][0] if len(name_parts) > 1 else name_parts[0][0])).upper()
            else:
                employee_initials = 'GU'
        else:
            employee_initials = 'GU'
    if not employee_designation or employee_designation == 'Employee':
        employee_designation = employee_role
    
    # Account Team Data (for Accounts department users)
    roc_count = 0
    gst_count = 0
    itr_count = 0
    bookkeeping_count = 0
    tds_count = 0
    total_account_records = 0
    
    if employee_department and employee_department.lower() == 'accounts' and request.user.is_authenticated and employee_obj:
        # Get counts for account team records from database
        # For accounts department, show only ASSIGNED records
        roc_count = ROCComplianceRecord.objects.filter(assigned_to=employee_obj).count()
        gst_count = GSTFilingRecord.objects.filter(assigned_to=employee_obj).count()
        itr_count = ITRFilingRecord.objects.filter(assigned_to=employee_obj).count()
        bookkeeping_count = BookkeepingChecklistRecord.objects.filter(assigned_to=employee_obj).count()
        tds_count = TDSComplianceRecord.objects.filter(assigned_to=employee_obj).count()
        total_account_records = roc_count + gst_count + itr_count + bookkeeping_count + tds_count
    
    # Back Office Data (for Backoffice department users)
    startup_count = 0
    fssai_count = 0
    msme_count = 0
    company_count = 0
    fire_count = 0
    iso_count = 0
    trademark_count = 0
    total_backoffice_records = 0
    
    # Check if user is in backoffice department (handle various formats: Backoffice, Back Office, backoffice, etc.)
    is_backoffice = False
    if employee_department:
        dept_normalized = employee_department.lower().strip().replace(' ', '').replace('-', '')
        if dept_normalized == 'backoffice':
            is_backoffice = True
    
    # Always calculate counts if user is authenticated (for backoffice users)
    if is_backoffice and request.user.is_authenticated and employee_obj:
        # Get counts for back office records from database
        # For backoffice department, show only ASSIGNED records
        startup_count = StartupIndiaRegistration.objects.filter(assigned_to=employee_obj).count()
        fssai_count = FSSAILicense.objects.filter(assigned_to=employee_obj).count()
        msme_count = MSMEUdyamRegistration.objects.filter(assigned_to=employee_obj).count()
        company_count = CompanyLLPRegistration.objects.filter(assigned_to=employee_obj).count()
        fire_count = FirePollutionLicense.objects.filter(assigned_to=employee_obj).count()
        iso_count = ISOCertification.objects.filter(assigned_to=employee_obj).count()
        trademark_count = TrademarkFiling.objects.filter(assigned_to=employee_obj).count() + TrademarkFilingCompliance.objects.filter(assigned_to=employee_obj).count() + TrademarkFilingInstant.objects.filter(assigned_to=employee_obj).count()
        total_backoffice_records = startup_count + fssai_count + msme_count + company_count + fire_count + iso_count + trademark_count
    
    context = {
        'employee_name': employee_name,
        'employee_first_name': employee_first_name,
        'employee_initials': employee_initials,
        'employee_role': employee_role,
        'employee_designation': employee_designation,
        'employee_department': employee_department,
        'employee_id': employee_id,
        'current_date': current_date,
        'current_time': current_time,
        'attendance_status': attendance_status,
        'active_projects': active_projects_count,
        'tasks_completed': tasks_completed_total,
        'hours_worked': round(hours_worked, 1),
        'attendance_percentage': attendance_percentage,
        # Sales metrics
        'leads_count': leads_count,
        'quotes_count': quotes_count,
        'onboardings_count': onboardings_count,
        'projects': projects,  # For dashboard projects table
        'recent_tasks': recent_tasks[:4],  # Top 4 recent tasks
        'today_schedule': today_schedule,
        'notifications': notifications[:3],  # Top 3 notifications
        'notification_count': notification_count,
        'weekly_performance': weekly_performance_json,  # JSON string for JavaScript
        # Sidebar counts
        'unread_messages_count': unread_messages_count,
        'new_projects_count': new_projects_count,
        'pending_leaves_count': pending_leaves_count,
        # Account Team metrics (for Accounts department)
        'roc_count': roc_count,
        'gst_count': gst_count,
        'itr_count': itr_count,
        'bookkeeping_count': bookkeeping_count,
        'tds_count': tds_count,
        'total_account_records': total_account_records,
        # Back Office metrics (for Backoffice department)
        'startup_count': startup_count,
        'fssai_count': fssai_count,
        'msme_count': msme_count,
        'company_count': company_count,
        'fire_count': fire_count,
        'iso_count': iso_count,
        'trademark_count': trademark_count,
        'total_backoffice_records': total_backoffice_records,
        'is_backoffice': is_backoffice,  # Flag to help template identify backoffice users
    }
    return render(request, 'employee/dashboard.html', context)

@login_required
def employee_projects(request):
    """Employee projects view - fetches data from myapp_clientonboarding table"""
    from datetime import timedelta
    
    # Get logged-in user's information and find employee
    employee_obj = None
    employee_name = None
    if request.user.is_authenticated:
        user_full_name = request.user.get_full_name() or request.user.username or ''
        
        # Try to match employee by name
        name_parts = user_full_name.strip().split(' ', 1)
        first_name = name_parts[0] if name_parts else ''
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        if first_name and last_name:
            employee_obj = Employee.objects.filter(
                first_name__iexact=first_name,
                last_name__iexact=last_name
            ).first()
        
        # If not found by name, try by email
        if not employee_obj:
            user_email = getattr(request.user, 'email', None)
            if user_email:
                employee_obj = Employee.objects.filter(
                    email__iexact=user_email
                ).first()
        
        # Set employee name
        if employee_obj:
            employee_name = employee_obj.get_full_name()
        else:
            employee_name = user_full_name
    
    # Fetch projects from ClientOnboarding table
    # Priority 1: Match by employee name if employee_obj exists
    client_onboardings = ClientOnboarding.objects.none()
    
    if employee_obj and employee_name:
        # Match by assigned_engineer with employee's full name
        client_onboardings = ClientOnboarding.objects.filter(
            assigned_engineer__iexact=employee_name
        ).only(
            'id',
            'project_name',
            'project_description',
            'status',
            'start_date',
            'project_duration',
            'duration_unit',
            'assigned_engineer',
            'client_name',
            'project_cost',
            'created_at',
            'updated_at'
        ).order_by('-created_at')
    
    # Priority 2: If no projects found and user is authenticated, try by user name
    if not client_onboardings.exists() and request.user.is_authenticated:
        user_name = request.user.get_full_name() or request.user.username or ''
        if user_name:
            client_onboardings = ClientOnboarding.objects.filter(
                assigned_engineer__iexact=user_name
            ).only(
                'id',
                'project_name',
                'project_description',
                'status',
                'start_date',
                'project_duration',
                'duration_unit',
                'assigned_engineer',
                'client_name',
                'project_cost',
                'created_at',
                'updated_at'
            ).order_by('-created_at')
    
    # Convert to project data structure
    projects = []
    today = date.today()
    next_week = today + timedelta(days=7)
    
    for onboarding in client_onboardings:
        # Calculate due date from start_date and duration
        due_date = None
        if onboarding.start_date:
            duration_days = 0
            if onboarding.duration_unit == 'days':
                duration_days = onboarding.project_duration
            elif onboarding.duration_unit == 'weeks':
                duration_days = onboarding.project_duration * 7
            elif onboarding.duration_unit == 'months':
                duration_days = onboarding.project_duration * 30
            elif onboarding.duration_unit == 'years':
                duration_days = onboarding.project_duration * 365
            
            due_date = onboarding.start_date + timedelta(days=duration_days)
        
        # Map status from ClientOnboarding to template status
        status_map = {
            'active': 'In Progress',
            'pending': 'Pending',
            'on_hold': 'On Hold',
            'completed': 'Completed'
        }
        template_status = status_map.get(onboarding.status, 'Pending')
        
        # Calculate progress based on status (simplified)
        progress_map = {
            'active': 50,
            'pending': 0,
            'on_hold': 30,
            'completed': 100
        }
        progress = progress_map.get(onboarding.status, 0)
        
        # Calculate tasks (simplified - not in model, using status-based estimates)
        tasks_map = {
            'active': {'total': 10, 'completed': 5, 'pending': 5},
            'pending': {'total': 8, 'completed': 0, 'pending': 8},
            'on_hold': {'total': 12, 'completed': 4, 'pending': 8},
            'completed': {'total': 10, 'completed': 10, 'pending': 0}
        }
        tasks = tasks_map.get(onboarding.status, {'total': 8, 'completed': 0, 'pending': 8})
        
        # Derive project type from description (simplified)
        project_type = 'Project'
        if onboarding.project_description:
            desc_lower = onboarding.project_description.lower()
            if 'web' in desc_lower or 'website' in desc_lower:
                project_type = 'Web Application'
            elif 'mobile' in desc_lower or 'app' in desc_lower:
                project_type = 'Mobile Application'
            elif 'database' in desc_lower or 'backend' in desc_lower:
                project_type = 'Backend Task'
            elif 'security' in desc_lower:
                project_type = 'Security Task'
            elif 'dashboard' in desc_lower or 'analytics' in desc_lower:
                project_type = 'Data Visualization'
            elif 'cloud' in desc_lower or 'infrastructure' in desc_lower:
                project_type = 'Infrastructure'
        
        # Format due_date for display
        due_date_display = None
        if due_date:
            due_date_display = due_date.strftime('%b %d, %Y')  # Format: "Dec 15, 2024"
        
        project_data = {
            'id': onboarding.id,
            'name': onboarding.project_name,
            'type': project_type,
            'progress': progress,
            'due_date': due_date_display,  # Formatted date string
            'due_date_raw': due_date.strftime('%Y-%m-%d') if due_date else None,  # For calculations
            'status': template_status,
            'tasks_total': tasks['total'],
            'tasks_completed': tasks['completed'],
            'tasks_pending': tasks['pending'],
            'priority': 'Medium',  # Default priority
            'description': onboarding.project_description or 'No description available.',
            # Additional fields from ClientOnboarding
            'client_name': onboarding.client_name or '',
            'project_cost': onboarding.project_cost or 0,
            'project_duration': onboarding.project_duration or 0,
            'duration_unit': onboarding.duration_unit or 'months',
            'assigned_engineer': onboarding.assigned_engineer or '',
            'start_date': onboarding.start_date.strftime('%Y-%m-%d') if onboarding.start_date else None,
            'start_date_display': onboarding.start_date.strftime('%b %d, %Y') if onboarding.start_date else 'N/A',
            'created_at': onboarding.created_at.strftime('%Y-%m-%d %H:%M:%S') if onboarding.created_at else '',
            'created_at_display': onboarding.created_at.strftime('%b %d, %Y') if onboarding.created_at else 'N/A',
        }
        projects.append(project_data)
    
    # Calculate stats
    total_projects = len(projects)
    completed_projects = len([p for p in projects if p['status'] == 'Completed'])
    in_progress_projects = len([p for p in projects if p['status'] == 'In Progress'])
    
    # Count projects due this week
    due_this_week = 0
    for p in projects:
        if p.get('due_date_raw'):
            try:
                due = datetime.strptime(p['due_date_raw'], '%Y-%m-%d').date()
                if today <= due <= next_week:
                    due_this_week += 1
            except:
                pass
    
    context = {
        'projects': projects,
        'total_projects': total_projects,
        'completed_projects': completed_projects,
        'in_progress_projects': in_progress_projects,
        'due_this_week': due_this_week,
    }
    return render(request, 'employee/projects.html', context)


@login_required
def employee_accounts(request):
    """Accounts team workspace with compliance forms and document checklists."""
    roc_form = ROCComplianceForm()
    gst_form = GSTFilingForm()
    itr_form = ITRFilingForm()
    bookkeeping_form = BookkeepingChecklistForm()
    tds_form = TDSComplianceForm()

    if request.method == 'POST':
        form_name = request.POST.get('form_name')

        if form_name == 'roc':
            roc_form = ROCComplianceForm(request.POST)
            if roc_form.is_valid():
                record = roc_form.save(commit=False)
                record.user = request.user
                record.documents = _store_uploaded_files(
                    request.FILES.getlist('roc_documents'),
                    'roc',
                )
                record.save()
                messages.success(request, 'ROC compliance details saved successfully.')
                return redirect('employee_accounts')
            messages.error(request, 'Please correct the highlighted errors in the ROC compliance form.')

        elif form_name == 'gst':
            gst_form = GSTFilingForm(request.POST)
            if gst_form.is_valid():
                record = gst_form.save(commit=False)
                record.user = request.user
                files_map = {
                    'outward_supplies': _store_uploaded_files(request.FILES.getlist('gst_outward_supplies'), 'gst/outward'),
                    'input_tax_credit': _store_uploaded_files(request.FILES.getlist('gst_input_tax_credit'), 'gst/input-credit'),
                    'reverse_charge': _store_uploaded_files(request.FILES.getlist('gst_reverse_charge'), 'gst/reverse-charge'),
                    'eway_bill_summary': _store_uploaded_files(request.FILES.getlist('gst_eway_bill'), 'gst/eway-bill'),
                }
                record.data_files = {key: paths for key, paths in files_map.items() if paths}
                record.save()
                messages.success(request, 'GST filing details saved successfully.')
                return redirect('employee_accounts')
            messages.error(request, 'Please correct the highlighted errors in the GST filing form.')

        elif form_name == 'itr':
            itr_form = ITRFilingForm(request.POST)
            if itr_form.is_valid():
                record = itr_form.save(commit=False)
                record.user = request.user
                record.documents = _store_uploaded_files(
                    request.FILES.getlist('itr_documents'),
                    'itr',
                )
                record.save()
                messages.success(request, 'ITR intake details saved successfully.')
                return redirect('employee_accounts')
            messages.error(request, 'Please correct the highlighted errors in the ITR intake form.')

        elif form_name == 'bookkeeping':
            bookkeeping_form = BookkeepingChecklistForm(request.POST)
            if bookkeeping_form.is_valid():
                record = bookkeeping_form.save(commit=False)
                record.user = request.user
                record.reconciliation_documents = _store_uploaded_files(
                    request.FILES.getlist('bookkeeping_documents'),
                    'bookkeeping',
                )
                record.save()
                messages.success(request, 'Bookkeeping checklist saved successfully.')
                return redirect('employee_accounts')
            messages.error(request, 'Please correct the highlighted errors in the bookkeeping checklist.')

        elif form_name == 'tds':
            tds_form = TDSComplianceForm(request.POST)
            if tds_form.is_valid():
                record = tds_form.save(commit=False)
                record.user = request.user
                record.proofs = _store_uploaded_files(
                    request.FILES.getlist('tds_proofs'),
                    'tds',
                )
                record.save()
                messages.success(request, 'TDS compliance details saved successfully.')
                return redirect('employee_accounts')
            messages.error(request, 'Please correct the highlighted errors in the TDS compliance form.')

        else:
            messages.error(request, 'Invalid submission. Please try again.')
    roc_required_docs = [
        {
            'name': 'Audited Financial Statements',
            'description': 'Balance sheet, profit & loss, cash-flow statements approved in AGM.',
            'due': 'Within 30 days of AGM',
        },
        {
            'name': 'Annual Return (Form MGT-7)',
            'description': 'Shareholding pattern, board report extracts, compliance confirmation.',
            'due': 'Within 60 days of AGM',
        },
        {
            'name': 'Director KYC (Form DIR-3 KYC)',
            'description': 'PAN, Aadhaar, passport size photo, digital signature of director.',
            'due': '30 September every year',
        },
        {
            'name': 'Form AOC-4',
            'description': 'Financial statements in XBRL or PDF along with notes and approval.',
            'due': 'Within 30 days of AGM',
        },
    ]

    gst_return_types = [
        {
            'code': 'GSTR-1',
            'frequency': 'Monthly / Quarterly (QRMP)',
            'purpose': 'Outward supplies summary, invoice-wise reporting.',
            'due_date': '11th of next month / 13th of quarter following',
        },
        {
            'code': 'GSTR-3B',
            'frequency': 'Monthly / Quarterly (QRMP)',
            'purpose': 'Tax liability, input tax credit, payment summary.',
            'due_date': '20th / 22nd / 24th of next month (state-wise)',
        },
        {
            'code': 'GSTR-9',
            'frequency': 'Annually',
            'purpose': 'Annual reconciliation statement for turnover and tax paid.',
            'due_date': '31st December following the financial year',
        },
        {
            'code': 'GSTR-9C',
            'frequency': 'Annually (if turnover > ₹5 Cr)',
            'purpose': 'GST audit report certified by CA/CMA.',
            'due_date': '31st December following the financial year',
        },
    ]

    for gst_item in gst_return_types:
        gst_item['next_due_dates'] = _get_gst_next_due(gst_item['code'])

    gst_upload_requirements = [
        'Sales register (B2B, B2C, exports, credit/debit notes)',
        'Purchase register with GSTIN and invoice details',
        'Input tax credit reconciliation summary',
        'Reverse charge mechanism (RCM) liabilities and payments',
        'E-way bills summary and transport documentation',
    ]

    itr_profiles = [
        {
            'form': 'ITR-1 (SAHAJ)',
            'applicable_for': 'Resident individuals with salary, one house property, other income up to ₹50L.',
            'documents': 'Form 16, rent receipts, interest certificates, 26AS, AIS/TIS.',
        },
        {
            'form': 'ITR-3',
            'applicable_for': 'Individuals/HUF with proprietary business or professional income.',
            'documents': 'Balance sheet, P&L, capital accounts, GST data, loan summaries.',
        },
        {
            'form': 'ITR-4 (SUGAM)',
            'applicable_for': 'Presumptive business income (Sec 44AD/ADA/AE) up to ₹2 Cr.',
            'documents': 'Turnover statement, presumptive computation, bank statements.',
        },
        {
            'form': 'ITR-6',
            'applicable_for': 'Companies other than those claiming exemption under Section 11.',
            'documents': 'Audited accounts, MAT computation, depreciation schedule.',
        },
    ]

    bookkeeping_streams = [
        {
            'title': 'Daily Bookkeeping & Cash Book',
            'inputs': ['Sales invoices', 'Purchase bills', 'Cash expense vouchers', 'Petty cash log'],
        },
        {
            'title': 'Bank Reconciliation',
            'inputs': ['Bank statements', 'Outstanding cheque list', 'Payment approvals', 'Deposit slips'],
        },
        {
            'title': 'Accounts Payable',
            'inputs': ['Vendor master data', 'GSTIN verification', 'PO/GRN match report', 'Payment advice'],
        },
        {
            'title': 'Accounts Receivable',
            'inputs': ['Customer ledger', 'Aging analysis', 'Credit notes approvals', 'Collection tracker'],
        },
    ]

    tds_categories = [
        {
            'section': '192 - Salary',
            'threshold': 'As per income tax slab',
            'due_date': 'Deposit by 7th of following month; Q4 return by 31 May',
            'documents': 'Salary register, investment proofs, Form 12BB, challan copy.',
        },
        {
            'section': '194C - Contractor Payments',
            'threshold': '₹30,000 single / ₹1,00,000 aggregate',
            'due_date': 'Deposit by 7th; return (Form 26Q) quarterly by 31st of month after quarter',
            'documents': 'Work orders, invoices, PAN copy, TDS deduction worksheet.',
        },
        {
            'section': '194J - Professional Fees',
            'threshold': '₹30,000 per payee annually',
            'due_date': 'Deposit by 7th; Form 26Q quarterly filing',
            'documents': 'Engagement letters, bills, PAN, nature of service classification.',
        },
        {
            'section': '194I - Rent',
            'threshold': '₹2,40,000 per annum',
            'due_date': 'Deposit by 7th; Form 26Q quarterly filing',
            'documents': 'Rental agreement, landlord PAN, TDS computation sheet.',
        },
    ]

    compliance_calendar = [
        {'title': 'GST GSTR-1 Filing', 'due': '11th / 13th of every month or quarter', 'priority': 'High'},
        {'title': 'GST GSTR-3B Payment', 'due': '20th / 22nd / 24th each month', 'priority': 'High'},
        {'title': 'ROC Form AOC-4', 'due': '30 days from AGM', 'priority': 'Medium'},
        {'title': 'ROC Form MGT-7', 'due': '60 days from AGM', 'priority': 'Medium'},
        {'title': 'TDS Deposit', 'due': '7th of every month', 'priority': 'High'},
        {'title': 'TDS Quarterly Return', 'due': '31 Jul / 31 Oct / 31 Jan / 31 May', 'priority': 'Medium'},
        {'title': 'Income Tax Return', 'due': '31 July (Individuals) / 31 October (Audit) / 30 November (TP)', 'priority': 'High'},
    ]

    support_contacts = [
        {'name': 'ROC Helpdesk', 'contact': '1800-111-555', 'email': 'roc.support@mca.gov.in'},
        {'name': 'GSTN Support', 'contact': '1800-103-4786', 'email': 'helpdesk@gst.gov.in'},
        {'name': 'Income Tax Helpline', 'contact': '1800-180-1961', 'email': 'ask@incometax.gov.in'},
        {'name': 'TDS CPC Support', 'contact': '1800-103-0344', 'email': 'contactus@tdscpc.gov.in'},
    ]

    # Get current employee
    employee_obj = None
    try:
        employee_obj = Employee.objects.get(email=request.user.email)
    except Employee.DoesNotExist:
        pass
    
    # Records owned by the logged-in user (for detailed tables)
    roc_records = ROCComplianceRecord.objects.filter(user=request.user).order_by('-created_at')
    gst_records = GSTFilingRecord.objects.filter(user=request.user).order_by('-created_at')
    itr_records = ITRFilingRecord.objects.filter(user=request.user).order_by('-created_at')
    bookkeeping_records = BookkeepingChecklistRecord.objects.filter(user=request.user).order_by('-created_at')
    tds_records = TDSComplianceRecord.objects.filter(user=request.user).order_by('-created_at')

    # Client from Website - Assigned records for current employee
    roc_clients_website = []
    gst_clients_website = []
    itr_clients_website = []
    bookkeeping_clients_website = []
    tds_clients_website = []
    
    if employee_obj:
        # Get assigned records from website (lead_source='website' or default)
        from django.db.models import Q
        roc_clients_website = ROCComplianceRecord.objects.filter(
            assigned_to=employee_obj
        ).filter(
            Q(lead_source='website') | Q(lead_source='') | Q(lead_source__isnull=True)
        ).order_by('-created_at')
        
        gst_clients_website = GSTFilingRecord.objects.filter(
            assigned_to=employee_obj
        ).filter(
            Q(lead_source='website') | Q(lead_source='') | Q(lead_source__isnull=True)
        ).order_by('-created_at')
        
        itr_clients_website = ITRFilingRecord.objects.filter(
            assigned_to=employee_obj
        ).filter(
            Q(lead_source='website') | Q(lead_source='') | Q(lead_source__isnull=True)
        ).order_by('-created_at')
        
        bookkeeping_clients_website = BookkeepingChecklistRecord.objects.filter(
            assigned_to=employee_obj
        ).filter(
            Q(lead_source='website') | Q(lead_source='') | Q(lead_source__isnull=True)
        ).order_by('-created_at')
        
        tds_clients_website = TDSComplianceRecord.objects.filter(
            assigned_to=employee_obj
        ).filter(
            Q(lead_source='website') | Q(lead_source='') | Q(lead_source__isnull=True)
        ).order_by('-created_at')

    # High-level metric counts (show assigned count for current employee)
    if employee_obj:
        roc_total_count = ROCComplianceRecord.objects.filter(assigned_to=employee_obj).count()
        gst_total_count = GSTFilingRecord.objects.filter(assigned_to=employee_obj).count()
        itr_total_count = ITRFilingRecord.objects.filter(assigned_to=employee_obj).count()
        bookkeeping_total_count = BookkeepingChecklistRecord.objects.filter(assigned_to=employee_obj).count()
        tds_total_count = TDSComplianceRecord.objects.filter(assigned_to=employee_obj).count()
    else:
        roc_total_count = 0
        gst_total_count = 0
        itr_total_count = 0
        bookkeeping_total_count = 0
        tds_total_count = 0

    website_leads = []

    def add_lead(record, service_key, service_label, entity_name, type_label):
        website_leads.append({
            'id': record.id,
            'service_key': service_key,
            'service_label': service_label,
            'entity_name': entity_name or '—',
            'type_label': type_label or '—',
            'status_key': record.status,
            'status_display': record.get_status_display(),
            'created_at': record.created_at,
            'modal_id': f'{service_key}LeadModal{record.id}',
        })

    for record in roc_clients_website:
        add_lead(
            record,
            'roc',
            'ROC Compliance',
            record.company_name,
            record.compliance_period or record.financial_year,
        )

    for record in gst_clients_website:
        add_lead(
            record,
            'gst',
            'GST Filing',
            record.gstin,
            record.return_type,
        )

    for record in itr_clients_website:
        add_lead(
            record,
            'itr',
            'ITR Filing',
            record.taxpayer_name,
            record.return_form,
        )

    for record in bookkeeping_clients_website:
        add_lead(
            record,
            'bookkeeping',
            'Accounts & Bookkeeping',
            record.prepared_by,
            record.closing_date.strftime('%d %b %Y') if record.closing_date else 'Daily Close',
        )

    for record in tds_clients_website:
        add_lead(
            record,
            'tds',
            'TDS Compliance',
            record.deductor_tan,
            record.section,
        )

    website_leads.sort(key=lambda lead: lead['created_at'], reverse=True)

    context = {
        'roc_required_docs': roc_required_docs,
        'gst_return_types': gst_return_types,
        'gst_upload_requirements': gst_upload_requirements,
        'itr_profiles': itr_profiles,
        'bookkeeping_streams': bookkeeping_streams,
        'tds_categories': tds_categories,
        'compliance_calendar': compliance_calendar,
        'support_contacts': support_contacts,
        'roc_form': roc_form,
        'gst_form': gst_form,
        'itr_form': itr_form,
        'bookkeeping_form': bookkeeping_form,
        'tds_form': tds_form,
        'roc_records': roc_records,
        'gst_records': gst_records,
        'itr_records': itr_records,
        'bookkeeping_records': bookkeeping_records,
        'tds_records': tds_records,
        # Client from Website - Assigned records
        'roc_clients_website': roc_clients_website,
        'gst_clients_website': gst_clients_website,
        'itr_clients_website': itr_clients_website,
        'bookkeeping_clients_website': bookkeeping_clients_website,
        'tds_clients_website': tds_clients_website,
        # Metric cards - assigned counts
        'roc_count': roc_total_count,
        'gst_count': gst_total_count,
        'itr_count': itr_total_count,
        'bookkeeping_count': bookkeeping_total_count,
        'tds_count': tds_total_count,
        'website_leads': website_leads,
    }
    return render(request, 'employee/accounts.html', context)


@login_required
def employee_accounts_edit(request, section, pk):
    config = _get_section_config(section)
    model = config['model']
    form_class = config['form']
    record = get_object_or_404(model, pk=pk, user=request.user)

    if request.method == 'POST':
        form = form_class(request.POST, instance=record)
        if form.is_valid():
            updated_record = form.save(commit=False)
            updated_record.user = request.user

            if section == 'roc':
                new_docs = _store_uploaded_files(request.FILES.getlist('roc_documents'), 'roc')
                if new_docs:
                    existing = updated_record.documents or []
                    updated_record.documents = existing + new_docs

            elif section == 'gst':
                files_map = {
                    'outward_supplies': _store_uploaded_files(request.FILES.getlist('gst_outward_supplies'), 'gst/outward'),
                    'input_tax_credit': _store_uploaded_files(request.FILES.getlist('gst_input_tax_credit'), 'gst/input-credit'),
                    'reverse_charge': _store_uploaded_files(request.FILES.getlist('gst_reverse_charge'), 'gst/reverse-charge'),
                    'eway_bill_summary': _store_uploaded_files(request.FILES.getlist('gst_eway_bill'), 'gst/eway-bill'),
                }
                if any(files_map.values()):
                    data_files = updated_record.data_files or {}
                    for key, paths in files_map.items():
                        if paths:
                            data_files[key] = (data_files.get(key, []) or []) + paths
                    updated_record.data_files = data_files

            elif section == 'itr':
                new_docs = _store_uploaded_files(request.FILES.getlist('itr_documents'), 'itr')
                if new_docs:
                    existing = updated_record.documents or []
                    updated_record.documents = existing + new_docs

            elif section == 'bookkeeping':
                new_docs = _store_uploaded_files(request.FILES.getlist('bookkeeping_documents'), 'bookkeeping')
                if new_docs:
                    existing = updated_record.reconciliation_documents or []
                    updated_record.reconciliation_documents = existing + new_docs

            elif section == 'tds':
                new_docs = _store_uploaded_files(request.FILES.getlist('tds_proofs'), 'tds')
                if new_docs:
                    existing = updated_record.proofs or []
                    updated_record.proofs = existing + new_docs

            updated_record.save()
            messages.success(request, config['success_message'])
            return redirect('employee_accounts')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = form_class(instance=record)

    context = {
        'form': form,
        'section': section,
        'record': record,
        'title': config['title'],
    }
    return render(request, 'employee/account_edit.html', context)


@login_required
@require_POST
def employee_accounts_delete(request, section, pk):
    config = _get_section_config(section)
    model = config['model']
    record = get_object_or_404(model, pk=pk, user=request.user)
    record.delete()
    messages.success(request, f"{config['title']} record deleted successfully.")
    return redirect('employee_accounts')


@login_required
def employee_backoffice(request):
    """Back Office Management workspace with form handling for Start-up India Registration."""
    
    # Handle Start-up India Registration form submission
    startup_form = StartupIndiaRegistrationForm()
    startup_registrations_all = StartupIndiaRegistration.objects.filter(user=request.user).order_by('-created_at')
    startup_paginator = Paginator(startup_registrations_all, 10)
    startup_page = request.GET.get('startup_page', 1)
    startup_registrations = startup_paginator.get_page(startup_page)
    
    # Handle FSSAI License form submission
    fssai_form = FSSAILicenseForm()
    fssai_licenses_all = FSSAILicense.objects.filter(user=request.user).order_by('-created_at')
    fssai_paginator = Paginator(fssai_licenses_all, 10)
    fssai_page = request.GET.get('fssai_page', 1)
    fssai_licenses = fssai_paginator.get_page(fssai_page)
    
    # Handle MSME / Udyam Registration form
    msme_form = MSMEUdyamRegistrationForm()
    msme_registrations_all = MSMEUdyamRegistration.objects.filter(user=request.user).order_by('-created_at')
    msme_paginator = Paginator(msme_registrations_all, 10)
    msme_page = request.GET.get('msme_page', 1)
    msme_registrations = msme_paginator.get_page(msme_page)

    # Handle Company / LLP Registration form
    company_form = CompanyLLPRegistrationForm()
    company_registrations_all = CompanyLLPRegistration.objects.filter(user=request.user).order_by('-created_at')
    company_paginator = Paginator(company_registrations_all, 10)
    company_page = request.GET.get('company_page', 1)
    company_registrations = company_paginator.get_page(company_page)

    # Handle Fire & Pollution Licence form
    fire_form = FirePollutionLicenseForm()
    fire_licenses_all = FirePollutionLicense.objects.filter(user=request.user).order_by('-created_at')
    fire_paginator = Paginator(fire_licenses_all, 10)
    fire_page = request.GET.get('fire_page', 1)
    fire_licenses = fire_paginator.get_page(fire_page)

    # Handle ISO Certification form
    iso_form = ISOCertificationForm()
    iso_certifications_all = ISOCertification.objects.filter(user=request.user).order_by('-created_at')
    iso_paginator = Paginator(iso_certifications_all, 10)
    iso_page = request.GET.get('iso_page', 1)
    iso_certifications = iso_paginator.get_page(iso_page)
    
    # Handle Trademark Filing form
    trademark_form = TrademarkFilingForm()
    # Fetch all trademark filings with pagination
    trademark_filings_all = TrademarkFiling.objects.all().order_by('-created_at')
    trademark_paginator = Paginator(trademark_filings_all, 10)
    trademark_page = request.GET.get('trademark_page', 1)
    trademark_filings = trademark_paginator.get_page(trademark_page)
    
    # Handle Trademark Filing + Compliance form
    trademark_compliance_form = TrademarkFilingComplianceForm()
    trademark_compliances_all = TrademarkFilingCompliance.objects.all().order_by('-created_at')
    trademark_compliance_paginator = Paginator(trademark_compliances_all, 10)
    trademark_compliance_page = request.GET.get('trademark_compliance_page', 1)
    trademark_compliances = trademark_compliance_paginator.get_page(trademark_compliance_page)
    
    # Handle Trademark Filing (Instant Process) form
    trademark_instant_form = TrademarkFilingInstantForm()
    trademark_instants_all = TrademarkFilingInstant.objects.all().order_by('-created_at')
    trademark_instant_paginator = Paginator(trademark_instants_all, 10)
    trademark_instant_page = request.GET.get('trademark_instant_page', 1)
    trademark_instants = trademark_instant_paginator.get_page(trademark_instant_page)
    
    # Handle Company Address Change form
    address_change_form = CompanyAddressChangeForm()
    address_changes_all = CompanyAddressChange.objects.all().order_by('-created_at')
    address_change_paginator = Paginator(address_changes_all, 10)
    address_change_page = request.GET.get('address_change_page', 1)
    address_changes = address_change_paginator.get_page(address_change_page)
    
    # Handle MOA Alteration form
    moa_alteration_form = MOAAlterationForm()
    moa_alterations_all = MOAAlteration.objects.all().order_by('-created_at')
    moa_alteration_paginator = Paginator(moa_alterations_all, 10)
    moa_alteration_page = request.GET.get('moa_alteration_page', 1)
    moa_alterations = moa_alteration_paginator.get_page(moa_alteration_page)
    
    if request.method == 'POST':
        form_name = request.POST.get('form_name')
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        if form_name == 'startup_india':
            startup_form = StartupIndiaRegistrationForm(request.POST, request.FILES)
            if startup_form.is_valid():
                record = startup_form.save(commit=False)
                record.user = request.user
                
                # Handle file uploads
                uploaded_files = request.FILES.getlist('startup_documents')
                if uploaded_files:
                    saved_paths = _store_uploaded_files(uploaded_files, 'startup_india')
                    record.documents = saved_paths
                
                # Set status based on button clicked
                if 'mark_ready' in request.POST:
                    record.status = 'ready'
                else:
                    record.status = 'draft'
                
                record.save()
                messages.success(request, 'Start-up India Registration saved successfully.')
                if is_ajax:
                    from django.http import JsonResponse
                    return JsonResponse({'success': True, 'message': 'Start-up India Registration saved successfully.'})
                return redirect('employee_backoffice')
            else:
                messages.error(request, 'Please correct the errors in the form.')
                if is_ajax:
                    from django.http import JsonResponse
                    return JsonResponse({'success': False, 'errors': startup_form.errors})
        
        elif form_name == 'fssai':
            fssai_form = FSSAILicenseForm(request.POST, request.FILES)
            if fssai_form.is_valid():
                record = fssai_form.save(commit=False)
                record.user = request.user
                
                # Handle file uploads
                uploaded_files = request.FILES.getlist('fssai_documents')
                if uploaded_files:
                    saved_paths = _store_uploaded_files(uploaded_files, 'fssai')
                    record.documents = saved_paths
                
                # Set status based on button clicked
                if 'mark_ready' in request.POST:
                    record.status = 'ready'
                else:
                    record.status = 'draft'
                
                record.save()
                messages.success(request, 'FSSAI License application saved successfully.')
                if is_ajax:
                    from django.http import JsonResponse
                    return JsonResponse({'success': True, 'message': 'FSSAI License application saved successfully.'})
                return redirect('employee_backoffice')
            else:
                messages.error(request, 'Please correct the errors in the form.')
                if is_ajax:
                    from django.http import JsonResponse
                    return JsonResponse({'success': False, 'errors': fssai_form.errors})
        
        elif form_name == 'msme':
            msme_form = MSMEUdyamRegistrationForm(request.POST)
            if msme_form.is_valid():
                record = msme_form.save(commit=False)
                record.user = request.user
                
                if 'mark_ready' in request.POST:
                    record.status = 'ready'
                else:
                    record.status = 'draft'
                
                record.save()
                messages.success(request, 'MSME / Udyam Registration saved successfully.')
                if is_ajax:
                    from django.http import JsonResponse
                    return JsonResponse({'success': True, 'message': 'MSME / Udyam Registration saved successfully.'})
                return redirect('employee_backoffice')
            else:
                messages.error(request, 'Please correct the errors in the form.')
                if is_ajax:
                    from django.http import JsonResponse
                    return JsonResponse({'success': False, 'errors': msme_form.errors})

        elif form_name == 'company_llp':
            company_form = CompanyLLPRegistrationForm(request.POST, request.FILES)
            if company_form.is_valid():
                record = company_form.save(commit=False)
                record.user = request.user

                uploaded_files = request.FILES.getlist('company_documents')
                if uploaded_files:
                    saved_paths = _store_uploaded_files(uploaded_files, 'company_llp')
                    record.documents = saved_paths

                if 'mark_ready' in request.POST:
                    record.status = 'ready'
                else:
                    record.status = 'draft'

                record.save()
                messages.success(request, 'Company / LLP Registration saved successfully.')
                if is_ajax:
                    from django.http import JsonResponse
                    return JsonResponse({'success': True, 'message': 'Company / LLP Registration saved successfully.'})
                return redirect('employee_backoffice')
            else:
                messages.error(request, 'Please correct the errors in the form.')
                if is_ajax:
                    from django.http import JsonResponse
                    return JsonResponse({'success': False, 'errors': company_form.errors})

        elif form_name == 'fire_pollution':
            fire_form = FirePollutionLicenseForm(request.POST, request.FILES)
            if fire_form.is_valid():
                record = fire_form.save(commit=False)
                record.user = request.user

                uploaded_files = request.FILES.getlist('fire_documents')
                if uploaded_files:
                    saved_paths = _store_uploaded_files(uploaded_files, 'fire_pollution')
                    record.documents = saved_paths

                if 'mark_ready' in request.POST:
                    record.status = 'ready'
                else:
                    record.status = 'draft'

                record.save()
                messages.success(request, 'Fire & Pollution Licence saved successfully.')
                if is_ajax:
                    from django.http import JsonResponse
                    return JsonResponse({'success': True, 'message': 'Fire & Pollution Licence saved successfully.'})
                return redirect('employee_backoffice')
            else:
                messages.error(request, 'Please correct the errors in the form.')
                if is_ajax:
                    from django.http import JsonResponse
                    return JsonResponse({'success': False, 'errors': fire_form.errors})

        elif form_name == 'iso':
            iso_form = ISOCertificationForm(request.POST, request.FILES)
            if iso_form.is_valid():
                record = iso_form.save(commit=False)
                record.user = request.user

                uploaded_files = request.FILES.getlist('iso_documents')
                if uploaded_files:
                    saved_paths = _store_uploaded_files(uploaded_files, 'iso')
                    record.documents = saved_paths

                if 'mark_ready' in request.POST:
                    record.status = 'ready'
                else:
                    record.status = 'draft'

                record.save()
                messages.success(request, 'ISO Certification saved successfully.')
                if is_ajax:
                    from django.http import JsonResponse
                    return JsonResponse({'success': True, 'message': 'ISO Certification saved successfully.'})
                return redirect('employee_backoffice')
            else:
                messages.error(request, 'Please correct the errors in the form.')
                if is_ajax:
                    from django.http import JsonResponse
                    return JsonResponse({'success': False, 'errors': iso_form.errors})
        
        elif form_name == 'trademark':
            trademark_form = TrademarkFilingForm(request.POST, request.FILES)
            if trademark_form.is_valid():
                record = trademark_form.save(commit=False)
                record.user = request.user

                uploaded_files = request.FILES.getlist('trademark_documents')
                if uploaded_files:
                    saved_paths = _store_uploaded_files(uploaded_files, 'trademark')
                    record.documents = saved_paths

                if 'mark_ready' in request.POST:
                    record.status = 'ready'
                else:
                    record.status = 'draft'

                record.save()
                messages.success(request, 'Trademark Filing saved successfully.')
                if is_ajax:
                    from django.http import JsonResponse
                    return JsonResponse({'success': True, 'message': 'Trademark Filing saved successfully.'})
                return redirect('employee_backoffice')
            else:
                messages.error(request, 'Please correct the errors in the form.')
                if is_ajax:
                    from django.http import JsonResponse
                    return JsonResponse({'success': False, 'errors': trademark_form.errors})
        
        elif form_name == 'trademark_compliance':
            trademark_compliance_form = TrademarkFilingComplianceForm(request.POST, request.FILES)
            if trademark_compliance_form.is_valid():
                record = trademark_compliance_form.save(commit=False)
                record.user = request.user

                uploaded_files = request.FILES.getlist('trademark_compliance_documents')
                if uploaded_files:
                    saved_paths = _store_uploaded_files(uploaded_files, 'trademark_compliance')
                    record.documents = saved_paths

                if 'mark_ready' in request.POST:
                    record.status = 'ready'
                else:
                    record.status = 'draft'

                record.save()
                messages.success(request, 'Trademark Filing + Compliance saved successfully.')
                if is_ajax:
                    from django.http import JsonResponse
                    return JsonResponse({'success': True, 'message': 'Trademark Filing + Compliance saved successfully.'})
                return redirect('employee_backoffice')
            else:
                messages.error(request, 'Please correct the errors in the form.')
                if is_ajax:
                    from django.http import JsonResponse
                    return JsonResponse({'success': False, 'errors': trademark_compliance_form.errors})
        
        elif form_name == 'trademark_instant':
            trademark_instant_form = TrademarkFilingInstantForm(request.POST, request.FILES)
            if trademark_instant_form.is_valid():
                record = trademark_instant_form.save(commit=False)
                record.user = request.user

                uploaded_files = request.FILES.getlist('trademark_instant_documents')
                if uploaded_files:
                    saved_paths = _store_uploaded_files(uploaded_files, 'trademark_instant')
                    record.documents = saved_paths

                if 'mark_ready' in request.POST:
                    record.status = 'ready'
                else:
                    record.status = 'draft'

                record.save()
                messages.success(request, 'Trademark Filing (Instant Process) saved successfully.')
                if is_ajax:
                    from django.http import JsonResponse
                    return JsonResponse({'success': True, 'message': 'Trademark Filing (Instant Process) saved successfully.'})
                return redirect('employee_backoffice')
            else:
                messages.error(request, 'Please correct the errors in the form.')
                if is_ajax:
                    from django.http import JsonResponse
                    return JsonResponse({'success': False, 'errors': trademark_instant_form.errors})
        
        elif form_name == 'address_change':
            address_change_form = CompanyAddressChangeForm(request.POST, request.FILES)
            if address_change_form.is_valid():
                record = address_change_form.save(commit=False)
                record.user = request.user

                uploaded_files = request.FILES.getlist('address_change_documents')
                if uploaded_files:
                    saved_paths = _store_uploaded_files(uploaded_files, 'address_change')
                    record.documents = saved_paths

                if 'mark_ready' in request.POST:
                    record.status = 'ready'
                else:
                    record.status = 'draft'

                record.save()
                messages.success(request, 'Company Address Change saved successfully.')
                if is_ajax:
                    from django.http import JsonResponse
                    return JsonResponse({'success': True, 'message': 'Company Address Change saved successfully.'})
                return redirect('employee_backoffice')
            else:
                messages.error(request, 'Please correct the errors in the form.')
                if is_ajax:
                    from django.http import JsonResponse
                    return JsonResponse({'success': False, 'errors': address_change_form.errors})
        
        elif form_name == 'moa_alteration':
            moa_alteration_form = MOAAlterationForm(request.POST, request.FILES)
            if moa_alteration_form.is_valid():
                record = moa_alteration_form.save(commit=False)
                record.user = request.user

                uploaded_files = request.FILES.getlist('moa_alteration_documents')
                if uploaded_files:
                    saved_paths = _store_uploaded_files(uploaded_files, 'moa_alteration')
                    record.documents = saved_paths

                if 'mark_ready' in request.POST:
                    record.status = 'ready'
                else:
                    record.status = 'draft'

                record.save()
                messages.success(request, 'MOA Alteration saved successfully.')
                if is_ajax:
                    from django.http import JsonResponse
                    return JsonResponse({'success': True, 'message': 'MOA Alteration saved successfully.'})
                return redirect('employee_backoffice')
            else:
                messages.error(request, 'Please correct the errors in the form.')
                if is_ajax:
                    from django.http import JsonResponse
                    return JsonResponse({'success': False, 'errors': moa_alteration_form.errors})
    
    backoffice_services = [
        {
            'id': 'startup',
            'title': 'Start-up India Registration',
            'icon': 'bi-rocket-takeoff',
            'summary': 'DPIIT recognition for eligibility to tax exemptions and procurement benefits.',
            'form_fields': [
                {'label': 'Legal Entity Name', 'type': 'text', 'placeholder': 'As per COI', 'col': 6},
                {'label': 'Incorporation Date', 'type': 'date', 'placeholder': '', 'col': 6},
                {'label': 'Entity Type', 'type': 'select', 'options': ['Pvt Ltd', 'LLP', 'Partnership', 'OPC', 'Section 8'], 'col': 6},
                {'label': 'Industry Sector', 'type': 'select', 'options': ['Tech', 'Manufacturing', 'Fintech', 'Healthcare', 'Other'], 'col': 6},
                {'label': 'Authorised Contact', 'type': 'text', 'placeholder': 'Founder / Director', 'col': 6},
                {'label': 'Email', 'type': 'email', 'placeholder': 'name@company.com', 'col': 6},
                {'label': 'Innovation / USP', 'type': 'textarea', 'placeholder': 'Summarise solution & uniqueness', 'col': 12},
            ],
            'documents': [
                'Certificate of Incorporation', 'PAN of entity', 'Director list with DIN/PAN',
                'Pitch deck/innovation note', 'Latest financials / projections'
            ],
        },
        {
            'id': 'fssai',
            'title': 'Food Licensing (FSSAI)',
            'icon': 'bi-egg-fried',
            'summary': 'Basic/State/Central licence and hygiene SOPs.',
            'form_fields': [
                {'label': 'Business / Brand Name', 'type': 'text', 'placeholder': 'Legal / Brand name', 'col': 6},
                {'label': 'Licence Type', 'type': 'select', 'options': ['Basic', 'State', 'Central', 'Import/Export'], 'col': 6},
                {'label': 'Business Nature', 'type': 'select', 'options': ['Manufacturing', 'Distributor', 'Storage', 'Catering'], 'col': 6},
                {'label': 'Premises Address', 'type': 'textarea', 'placeholder': 'Full address with PIN', 'col': 6},
                {'label': 'Employees', 'type': 'number', 'placeholder': 'Food handlers count', 'col': 6},
                {'label': 'Licence Tenure', 'type': 'select', 'options': ['1 Year', '2 Years', '3 Years', '5 Years'], 'col': 6},
            ],
            'documents': [
                'Promoter photos & KYC', 'Incorporation documents', 'Layout plan/photos',
                'Food category list', 'Municipal trade licence / rental agreement'
            ],
        },
        {
            'id': 'msme',
            'title': 'MSME / Udyam Registration',
            'icon': 'bi-building-gear',
            'summary': 'Udyam registration for MSME benefits and tender preferences.',
            'form_fields': [
                {'label': 'Entity Name', 'type': 'text', 'placeholder': 'As per PAN', 'col': 6},
                {'label': 'Organisation Type', 'type': 'select', 'options': ['Proprietorship', 'Partnership', 'LLP', 'Company'], 'col': 6},
                {'label': 'Plant & Machinery Investment (₹)', 'type': 'number', 'placeholder': '', 'col': 6},
                {'label': 'Annual Turnover (₹)', 'type': 'number', 'placeholder': '', 'col': 6},
                {'label': 'Principal Activity', 'type': 'textarea', 'placeholder': 'Goods/services description', 'col': 12},
            ],
            'documents': ['PAN & Aadhaar', 'Business address proof', 'Bank cancelled cheque'],
        },
        {
            'id': 'company-reg',
            'title': 'Company / LLP Registration',
            'icon': 'bi-diagram-3',
            'summary': 'Name approval, incorporation filing, and post-incorporation kit.',
            'form_fields': [
                {'label': 'Entity Type', 'type': 'select', 'options': ['Pvt Ltd', 'LLP', 'OPC', 'Section 8'], 'col': 6},
                {'label': 'Directors / Partners', 'type': 'number', 'placeholder': 'e.g. 2', 'col': 6},
                {'label': 'Proposed Names (3)', 'type': 'textarea', 'placeholder': 'In order of preference', 'col': 12},
                {'label': 'Authorised Capital (₹)', 'type': 'number', 'placeholder': 'Companies only', 'col': 6},
                {'label': 'Registered Office', 'type': 'textarea', 'placeholder': 'Address with PIN', 'col': 6},
            ],
            'documents': ['Promoters KYC & photos', 'Office utility bill', 'Owner NOC', 'Draft objects'],
        },
        {
            'id': 'fire-pollution',
            'title': 'Fire & Pollution Licences',
            'icon': 'bi-shield-check',
            'summary': 'Fire NOC and Pollution Control Board consents.',
            'form_fields': [
                {'label': 'Establishment Type', 'type': 'select', 'options': ['Manufacturing', 'Warehouse', 'Restaurant', 'Retail', 'Office'], 'col': 6},
                {'label': 'Built-up Area (sq.ft)', 'type': 'number', 'placeholder': 'e.g. 12000', 'col': 6},
                {'label': 'Pollution Category', 'type': 'select', 'options': ['White', 'Green', 'Orange', 'Red'], 'col': 6},
                {'label': 'Safety Installations', 'type': 'textarea', 'placeholder': 'Hydrants, sprinklers, ETP, etc.', 'col': 6},
            ],
            'documents': ['Building plan/OC', 'Equipment layout', 'Raw material list with SDS', 'Municipal NOC', 'Premises photographs'],
        },
        {
            'id': 'iso',
            'title': 'ISO Certification (9001/14001/27001)',
            'icon': 'bi-award',
            'summary': 'QMS/EMS/ISMS implementation and accredited certification.',
            'form_fields': [
                {'label': 'Standard', 'type': 'select', 'options': ['ISO 9001', 'ISO 14001', 'ISO 45001', 'ISO 27001'], 'col': 6},
                {'label': 'Locations', 'type': 'number', 'placeholder': 'No. of sites', 'col': 6},
                {'label': 'Employee Strength', 'type': 'number', 'placeholder': '', 'col': 6},
                {'label': 'Existing Certifications', 'type': 'textarea', 'placeholder': 'If any', 'col': 6},
            ],
            'documents': ['Org chart & process maps', 'Policies & procedures', 'Training records', 'Internal audit reports'],
        },
        {
            'id': 'tm-file',
            'title': 'Trademark Filing',
            'icon': 'bi-badge-tm',
            'summary': 'Search, class finalisation, and TM-A filing.',
            'form_fields': [
                {'label': 'Brand / Logo', 'type': 'textarea', 'placeholder': 'Describe or attach logo', 'col': 12},
                {'label': 'Applicant Type', 'type': 'select', 'options': ['Individual', 'Firm', 'Company/LLP', 'Trust/Society'], 'col': 6},
                {'label': 'Classes', 'type': 'text', 'placeholder': 'e.g. 35, 42', 'col': 6},
                {'label': 'First Use Date', 'type': 'date', 'placeholder': '', 'col': 6},
            ],
            'documents': ['Logo (JPEG)', 'Applicant KYC', 'COI / Deed', 'User affidavit (if applicable)', 'POA (TM-48)'],
        },
        {
            'id': 'tm-compliance',
            'title': 'Trademark Filing + Compliance',
            'icon': 'bi-bag-check',
            'summary': 'Filing with renewal tracking and watch services.',
            'form_fields': [
                {'label': 'Existing TM Numbers', 'type': 'textarea', 'placeholder': 'If any', 'col': 12},
                {'label': 'Portfolio Size', 'type': 'number', 'placeholder': '', 'col': 6},
                {'label': 'Watch Scope', 'type': 'select', 'options': ['Identical', 'Similar', 'Domains/Handles'], 'col': 6},
                {'label': 'Renewal Month', 'type': 'month', 'placeholder': '', 'col': 6},
            ],
            'documents': ['Existing certificates', 'Board resolution/POA', 'Usage guidelines', 'Invoices evidencing use'],
        },
        {
            'id': 'tm-instant',
            'title': 'Trademark Filing (Instant Process)',
            'icon': 'bi-lightning-charge',
            'summary': '24-hr express search, class finalisation and filing.',
            'form_fields': [
                {'label': 'Urgency Reason', 'type': 'textarea', 'placeholder': 'Launch / diligence / other', 'col': 12},
                {'label': 'Filing Window', 'type': 'select', 'options': ['Before 1 PM', 'Before 6 PM', 'Weekend'], 'col': 6},
                {'label': 'Contact Mobile', 'type': 'tel', 'placeholder': '+91XXXXXXXXXX', 'col': 6},
            ],
            'documents': ['Applicant KYC', 'Logo artwork (if any)', 'Signed TM-48'],
        },
        {
            'id': 'address-change',
            'title': 'Company Address Change',
            'icon': 'bi-geo-alt',
            'summary': 'Shift registered office within city/state/ROC.',
            'form_fields': [
                {'label': 'Entity Type', 'type': 'select', 'options': ['Company', 'LLP'], 'col': 6},
                {'label': 'Type of Shift', 'type': 'select', 'options': ['Within city', 'Within ROC', 'Inter-ROC / State'], 'col': 6},
                {'label': 'Effective Date', 'type': 'date', 'placeholder': '', 'col': 6},
                {'label': 'New Address', 'type': 'textarea', 'placeholder': 'Complete address', 'col': 6},
            ],
            'documents': ['Board/partner resolution', 'Altered MOA (if applicable)', 'Lease deed/ownership proof', 'Recent utility bill', 'Owner consent'],
        },
        {
            'id': 'moa-alter',
            'title': 'MOA Alteration',
            'icon': 'bi-file-earmark-text',
            'summary': 'Change objects/name/authorised capital clauses.',
            'form_fields': [
                {'label': 'Alteration Type', 'type': 'select', 'options': ['Object change', 'Name change', 'Authorised capital'], 'col': 6},
                {'label': 'Proposed Object/Name', 'type': 'textarea', 'placeholder': 'Draft text / options', 'col': 6},
                {'label': 'Effective Date', 'type': 'date', 'placeholder': '', 'col': 6},
            ],
            'documents': ['Altered MOA/AOA drafts', 'Board & shareholder resolutions', 'GM notice with explanatory statement', 'Lender consents (if any)'],
        },
    ]

    highlights = [
        'Project manager & SLA tracker per request',
        'Digital document locker with versioning',
        'Template library for resolutions, affidavits, and SOPs',
    ]

    # Check if this is an AJAX request for table refresh
    is_ajax_get = request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'GET'
    
    # Get assigned leads from website (assigned_to = current employee)
    assigned_leads = []
    try:
        employee_obj = Employee.objects.get(email=request.user.email)
        
        # Get all assigned leads from all backoffice services
        startup_assigned = StartupIndiaRegistration.objects.filter(assigned_to=employee_obj).order_by('-created_at')
        for record in startup_assigned:
            assigned_leads.append({
                'id': record.id,
                'service_type': 'startup',
                'service_name': 'Start-up India Registration',
                'legal_entity_name': record.legal_entity_name or 'N/A',
                'entity_type': record.entity_type or 'N/A',
                'industry_sector': record.industry_sector or 'N/A',
                'email': record.email or 'N/A',
                'status': record.status,
                'status_display': record.get_status_display(),
                'status_choices': StartupIndiaRegistration.STATUS_CHOICES,
                'status_badge_class': record.get_status_badge_class() if hasattr(record, 'get_status_badge_class') else 'secondary',
                'created_at': record.created_at,
                'lead_source': getattr(record, 'lead_source', 'website'),
                # Startup specific fields
                'incorporation_date': record.incorporation_date,
                'authorised_contact': record.authorised_contact or 'N/A',
                'innovation_usp': record.innovation_usp or 'N/A',
            })
        
        fssai_assigned = FSSAILicense.objects.filter(assigned_to=employee_obj).order_by('-created_at')
        for record in fssai_assigned:
            assigned_leads.append({
                'id': record.id,
                'service_type': 'fssai',
                'service_name': 'Food Licensing (FSSAI)',
                'legal_entity_name': record.business_brand_name or 'N/A',
                'entity_type': record.licence_type or 'N/A',
                'industry_sector': record.business_nature or 'N/A',
                'email': 'N/A',
                'status': record.status,
                'status_display': record.get_status_display(),
                'status_choices': FSSAILicense.STATUS_CHOICES,
                'status_badge_class': record.get_status_badge_class() if hasattr(record, 'get_status_badge_class') else 'secondary',
                'created_at': record.created_at,
                'lead_source': getattr(record, 'lead_source', 'website'),
                # FSSAI specific fields
                'premises_address': record.premises_address or 'N/A',
                'employees': record.employees or 'N/A',
                'licence_tenure': record.licence_tenure or 'N/A',
            })
        
        msme_assigned = MSMEUdyamRegistration.objects.filter(assigned_to=employee_obj).order_by('-created_at')
        for record in msme_assigned:
            assigned_leads.append({
                'id': record.id,
                'service_type': 'msme',
                'service_name': 'MSME / Udyam Registration',
                'legal_entity_name': record.entity_name or 'N/A',
                'entity_type': record.organisation_type or 'N/A',
                'industry_sector': 'N/A',
                'email': 'N/A',
                'status': record.status,
                'status_display': record.get_status_display(),
                'status_choices': MSMEUdyamRegistration.STATUS_CHOICES,
                'status_badge_class': record.get_status_badge_class() if hasattr(record, 'get_status_badge_class') else 'secondary',
                'created_at': record.created_at,
                'lead_source': getattr(record, 'lead_source', 'website'),
                # MSME specific fields
                'annual_turnover': record.annual_turnover or 0,
            })
        
        company_assigned = CompanyLLPRegistration.objects.filter(assigned_to=employee_obj).order_by('-created_at')
        for record in company_assigned:
            assigned_leads.append({
                'id': record.id,
                'service_type': 'company-llp',
                'service_name': 'Company / LLP Registration',
                'legal_entity_name': 'N/A',
                'entity_type': record.entity_type or 'N/A',
                'industry_sector': 'N/A',
                'email': 'N/A',
                'status': record.status,
                'status_display': record.get_status_display(),
                'status_choices': CompanyLLPRegistration.STATUS_CHOICES,
                'status_badge_class': record.get_status_badge_class() if hasattr(record, 'get_status_badge_class') else 'secondary',
                'created_at': record.created_at,
                'lead_source': getattr(record, 'lead_source', 'website'),
                # Company/LLP specific fields
                'directors_partners': record.directors_partners or 'N/A',
                'authorised_capital': record.authorised_capital or 0,
            })
        
        fire_assigned = FirePollutionLicense.objects.filter(assigned_to=employee_obj).order_by('-created_at')
        for record in fire_assigned:
            assigned_leads.append({
                'id': record.id,
                'service_type': 'fire-pollution',
                'service_name': 'Fire & Pollution Licences',
                'legal_entity_name': 'N/A',
                'entity_type': record.establishment_type or 'N/A',
                'industry_sector': record.pollution_category or 'N/A',
                'email': 'N/A',
                'status': record.status,
                'status_display': record.get_status_display(),
                'status_choices': FirePollutionLicense.STATUS_CHOICES,
                'status_badge_class': record.get_status_badge_class() if hasattr(record, 'get_status_badge_class') else 'secondary',
                'created_at': record.created_at,
                'lead_source': getattr(record, 'lead_source', 'website'),
                # Fire/Pollution specific fields
                'built_up_area': record.built_up_area or 'N/A',
            })
        
        iso_assigned = ISOCertification.objects.filter(assigned_to=employee_obj).order_by('-created_at')
        for record in iso_assigned:
            assigned_leads.append({
                'id': record.id,
                'service_type': 'iso',
                'service_name': 'ISO Certification',
                'legal_entity_name': 'N/A',
                'entity_type': record.standard or 'N/A',
                'industry_sector': record.locations or 'N/A',
                'email': 'N/A',
                'status': record.status,
                'status_display': record.get_status_display(),
                'status_choices': ISOCertification.STATUS_CHOICES,
                'status_badge_class': record.get_status_badge_class() if hasattr(record, 'get_status_badge_class') else 'secondary',
                'created_at': record.created_at,
                'lead_source': getattr(record, 'lead_source', 'website'),
                # ISO specific fields
                'employee_strength': record.employee_strength or 'N/A',
            })
        
        trademark_assigned = TrademarkFiling.objects.filter(assigned_to=employee_obj).order_by('-created_at')
        for record in trademark_assigned:
            assigned_leads.append({
                'id': record.id,
                'service_type': 'trademark',
                'service_name': 'Trademark Filing',
                'legal_entity_name': record.brand_logo[:50] if record.brand_logo else 'N/A',
                'entity_type': record.applicant_type or 'N/A',
                'industry_sector': record.classes or 'N/A',
                'email': 'N/A',
                'status': record.status,
                'status_display': record.get_status_display(),
                'status_choices': TrademarkFiling.STATUS_CHOICES,
                'status_badge_class': record.get_status_badge_class() if hasattr(record, 'get_status_badge_class') else 'secondary',
                'created_at': record.created_at,
                'lead_source': getattr(record, 'lead_source', 'website'),
                # Trademark specific fields
                'brand_logo': record.brand_logo or 'N/A',
            })
        
        trademark_compliance_assigned = TrademarkFilingCompliance.objects.filter(assigned_to=employee_obj).order_by('-created_at')
        for record in trademark_compliance_assigned:
            assigned_leads.append({
                'id': record.id,
                'service_type': 'trademark-compliance',
                'service_name': 'Trademark Filing + Compliance',
                'legal_entity_name': record.existing_tm_numbers[:50] if record.existing_tm_numbers else 'N/A',
                'entity_type': 'N/A',
                'industry_sector': record.portfolio_size or 'N/A',
                'email': 'N/A',
                'status': record.status,
                'status_display': record.get_status_display(),
                'status_choices': TrademarkFilingCompliance.STATUS_CHOICES,
                'status_badge_class': record.get_status_badge_class() if hasattr(record, 'get_status_badge_class') else 'secondary',
                'created_at': record.created_at,
                'lead_source': getattr(record, 'lead_source', 'website'),
                # Trademark Compliance specific fields
                'existing_tm_numbers': record.existing_tm_numbers or 'N/A',
                'watch_scope': record.watch_scope or 'N/A',
            })
        
        trademark_instant_assigned = TrademarkFilingInstant.objects.filter(assigned_to=employee_obj).order_by('-created_at')
        for record in trademark_instant_assigned:
            assigned_leads.append({
                'id': record.id,
                'service_type': 'trademark-instant',
                'service_name': 'Trademark Filing (Instant)',
                'legal_entity_name': record.urgency_reason[:50] if record.urgency_reason else 'N/A',
                'entity_type': record.filing_window or 'N/A',
                'industry_sector': record.contact_mobile or 'N/A',
                'email': 'N/A',
                'status': record.status,
                'status_display': record.get_status_display(),
                'status_choices': TrademarkFilingInstant.STATUS_CHOICES,
                'status_badge_class': record.get_status_badge_class() if hasattr(record, 'get_status_badge_class') else 'secondary',
                'created_at': record.created_at,
                'lead_source': getattr(record, 'lead_source', 'website'),
                # Trademark Instant specific fields
                'urgency_reason': record.urgency_reason or 'N/A',
                'contact_mobile': record.contact_mobile or 'N/A',
            })
        
        address_change_assigned = CompanyAddressChange.objects.filter(assigned_to=employee_obj).order_by('-created_at')
        for record in address_change_assigned:
            assigned_leads.append({
                'id': record.id,
                'service_type': 'address-change',
                'service_name': 'Company Address Change',
                'legal_entity_name': 'N/A',
                'entity_type': record.entity_type or 'N/A',
                'industry_sector': record.shift_type or 'N/A',
                'email': 'N/A',
                'status': record.status,
                'status_display': record.get_status_display(),
                'status_choices': CompanyAddressChange.STATUS_CHOICES,
                'status_badge_class': record.get_status_badge_class() if hasattr(record, 'get_status_badge_class') else 'secondary',
                'created_at': record.created_at,
                'lead_source': getattr(record, 'lead_source', 'website'),
                # Address Change specific fields
                'effective_date': record.effective_date,
            })
        
        moa_assigned = MOAAlteration.objects.filter(assigned_to=employee_obj).order_by('-created_at')
        for record in moa_assigned:
            assigned_leads.append({
                'id': record.id,
                'service_type': 'moa-alteration',
                'service_name': 'MOA Alteration',
                'legal_entity_name': record.proposed_object_name[:50] if record.proposed_object_name else 'N/A',
                'entity_type': record.alteration_type or 'N/A',
                'industry_sector': 'N/A',
                'email': 'N/A',
                'status': record.status,
                'status_display': record.get_status_display(),
                'status_choices': MOAAlteration.STATUS_CHOICES,
                'status_badge_class': record.get_status_badge_class() if hasattr(record, 'get_status_badge_class') else 'secondary',
                'created_at': record.created_at,
                'lead_source': getattr(record, 'lead_source', 'website'),
                # MOA Alteration specific fields
                'proposed_object_name': record.proposed_object_name or 'N/A',
                'effective_date': record.effective_date,
            })
        
        # Sort all assigned leads by created_at (newest first)
        assigned_leads.sort(key=lambda x: x['created_at'], reverse=True)
        
    except Employee.DoesNotExist:
        assigned_leads = []
    
    context = {
        'backoffice_services': backoffice_services,
        'highlights': highlights,
        'startup_form': startup_form,
        'startup_registrations': startup_registrations,
        'status_choices': StartupIndiaRegistration.STATUS_CHOICES,
        'fssai_form': fssai_form,
        'fssai_licenses': fssai_licenses,
        'fssai_status_choices': FSSAILicense.STATUS_CHOICES,
        'msme_form': msme_form,
        'msme_registrations': msme_registrations,
        'msme_status_choices': MSMEUdyamRegistration.STATUS_CHOICES,
        'company_form': company_form,
        'company_registrations': company_registrations,
        'company_status_choices': CompanyLLPRegistration.STATUS_CHOICES,
        'fire_form': fire_form,
        'fire_licenses': fire_licenses,
        'fire_status_choices': FirePollutionLicense.STATUS_CHOICES,
        'iso_form': iso_form,
        'iso_certifications': iso_certifications,
        'iso_status_choices': ISOCertification.STATUS_CHOICES,
        'trademark_form': trademark_form,
        'trademark_filings': trademark_filings,
        'trademark_status_choices': TrademarkFiling.STATUS_CHOICES,
        'trademark_compliance_form': trademark_compliance_form,
        'trademark_compliances': trademark_compliances,
        'trademark_compliance_status_choices': TrademarkFilingCompliance.STATUS_CHOICES,
        'trademark_instant_form': trademark_instant_form,
        'trademark_instants': trademark_instants,
        'trademark_instant_status_choices': TrademarkFilingInstant.STATUS_CHOICES,
        'address_change_form': address_change_form,
        'address_changes': address_changes,
        'address_change_status_choices': CompanyAddressChange.STATUS_CHOICES,
        'moa_alteration_form': moa_alteration_form,
        'moa_alterations': moa_alterations,
        'moa_alteration_status_choices': MOAAlteration.STATUS_CHOICES,
        'assigned_leads': assigned_leads,
    }
    return render(request, 'employee/backoffice.html', context)


@login_required
def get_lead_details(request):
    """Get lead details by service type and record ID"""
    if request.method == 'GET':
        try:
            service_type = request.GET.get('service_type')
            record_id = request.GET.get('record_id')
            
            if not service_type or not record_id:
                return JsonResponse({'success': False, 'error': 'Missing service_type or record_id'}, status=400)
            
            # Get current employee
            try:
                employee_obj = Employee.objects.get(email=request.user.email)
            except Employee.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Employee not found'}, status=403)
            
            # Map service types to models
            service_models = {
                'startup': StartupIndiaRegistration,
                'fssai': FSSAILicense,
                'msme': MSMEUdyamRegistration,
                'company-llp': CompanyLLPRegistration,
                'fire-pollution': FirePollutionLicense,
                'iso': ISOCertification,
                'trademark': TrademarkFiling,
                'trademark-compliance': TrademarkFilingCompliance,
                'trademark-instant': TrademarkFilingInstant,
                'address-change': CompanyAddressChange,
                'moa-alteration': MOAAlteration,
            }
            
            if service_type not in service_models:
                return JsonResponse({'success': False, 'error': 'Invalid service type'}, status=400)
            
            model_class = service_models[service_type]
            
            # Get record - check if assigned to current employee
            try:
                record = model_class.objects.get(id=record_id, assigned_to=employee_obj)
            except model_class.DoesNotExist:
                return JsonResponse({'success': False, 'error': f'No {model_class.__name__} matches the given query or not assigned to you'}, status=404)
            
            # Build response data based on service type
            data = {
                'success': True,
                'id': record.id,
                'service_type': service_type,
                'status': record.status,
                'status_display': record.get_status_display(),
                'status_badge_class': record.get_status_badge_class() if hasattr(record, 'get_status_badge_class') else 'secondary',
                'created_at': record.created_at.strftime('%d %b %Y, %I:%M %p') if record.created_at else 'N/A',
                'lead_source': getattr(record, 'lead_source', 'website'),
            }
            
            # Add service-specific fields
            if service_type == 'startup':
                data.update({
                    'legal_entity_name': record.legal_entity_name or 'N/A',
                    'incorporation_date': record.incorporation_date.strftime('%d %b %Y') if record.incorporation_date else 'N/A',
                    'entity_type': record.entity_type or 'N/A',
                    'industry_sector': record.industry_sector or 'N/A',
                    'authorised_contact': record.authorised_contact or 'N/A',
                    'email': record.email or 'N/A',
                    'innovation_usp': record.innovation_usp or 'N/A',
                })
            elif service_type == 'fssai':
                data.update({
                    'business_brand_name': record.business_brand_name or 'N/A',
                    'licence_type': record.licence_type or 'N/A',
                    'business_nature': record.business_nature or 'N/A',
                    'premises_address': record.premises_address or 'N/A',
                    'employees': record.employees or 'N/A',
                    'licence_tenure': record.licence_tenure or 'N/A',
                })
            elif service_type == 'msme':
                data.update({
                    'entity_name': record.entity_name or 'N/A',
                    'organisation_type': record.organisation_type or 'N/A',
                    'annual_turnover': str(record.annual_turnover or 0),
                })
            elif service_type == 'company-llp':
                data.update({
                    'entity_type': record.entity_type or 'N/A',
                    'directors_partners': record.directors_partners or 'N/A',
                    'authorised_capital': str(record.authorised_capital or 0),
                })
            elif service_type == 'fire-pollution':
                data.update({
                    'establishment_type': record.establishment_type or 'N/A',
                    'built_up_area': record.built_up_area or 'N/A',
                    'pollution_category': record.pollution_category or 'N/A',
                })
            elif service_type == 'iso':
                data.update({
                    'standard': record.standard or 'N/A',
                    'locations': record.locations or 'N/A',
                    'employee_strength': record.employee_strength or 'N/A',
                })
            elif service_type == 'trademark':
                data.update({
                    'brand_logo': record.brand_logo or 'N/A',
                    'applicant_type': record.applicant_type or 'N/A',
                    'classes': record.classes or 'N/A',
                })
            elif service_type == 'trademark-compliance':
                data.update({
                    'existing_tm_numbers': record.existing_tm_numbers or 'N/A',
                    'portfolio_size': record.portfolio_size or 'N/A',
                    'watch_scope': record.watch_scope or 'N/A',
                })
            elif service_type == 'trademark-instant':
                data.update({
                    'urgency_reason': record.urgency_reason or 'N/A',
                    'filing_window': record.filing_window or 'N/A',
                    'contact_mobile': record.contact_mobile or 'N/A',
                })
            elif service_type == 'address-change':
                data.update({
                    'entity_type': record.entity_type or 'N/A',
                    'shift_type': record.shift_type or 'N/A',
                    'effective_date': record.effective_date.strftime('%d %b %Y') if record.effective_date else 'N/A',
                })
            elif service_type == 'moa-alteration':
                data.update({
                    'alteration_type': record.alteration_type or 'N/A',
                    'proposed_object_name': record.proposed_object_name or 'N/A',
                    'effective_date': record.effective_date.strftime('%d %b %Y') if record.effective_date else 'N/A',
                })
            
            return JsonResponse(data)
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)


@login_required
@require_POST
@csrf_exempt
def update_startup_status(request, record_id):
    """Update status of Start-up India Registration record via AJAX."""
    try:
        # Get employee
        try:
            employee_obj = Employee.objects.get(email=request.user.email)
        except Employee.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Employee not found'}, status=403)
        
        # Get record - check if assigned to employee
        record = get_object_or_404(StartupIndiaRegistration, id=record_id, assigned_to=employee_obj)
        new_status = request.POST.get('status')
        
        if new_status not in dict(StartupIndiaRegistration.STATUS_CHOICES):
            return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)
        
        record.status = new_status
        record.save()
        
        return JsonResponse({
            'success': True,
            'status': new_status,
            'status_display': record.get_status_display()
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
@csrf_exempt
def update_fssai_status(request, record_id):
    """Update status of FSSAI License record via AJAX."""
    try:
        # Get employee
        try:
            employee_obj = Employee.objects.get(email=request.user.email)
        except Employee.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Employee not found'}, status=403)
        
        # Get record - check if assigned to employee
        record = get_object_or_404(FSSAILicense, id=record_id, assigned_to=employee_obj)
        new_status = request.POST.get('status')
        
        if new_status not in dict(FSSAILicense.STATUS_CHOICES):
            return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)
        
        record.status = new_status
        record.save()
        
        return JsonResponse({
            'success': True,
            'status': new_status,
            'status_display': record.get_status_display()
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
@csrf_exempt
def update_msme_status(request, record_id):
    """Update status of MSME / Udyam Registration record via AJAX."""
    try:
        # Get employee
        try:
            employee_obj = Employee.objects.get(email=request.user.email)
        except Employee.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Employee not found'}, status=403)
        
        # Get record - check if assigned to employee
        record = get_object_or_404(MSMEUdyamRegistration, id=record_id, assigned_to=employee_obj)
        new_status = request.POST.get('status')

        if new_status not in dict(MSMEUdyamRegistration.STATUS_CHOICES):
            return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)

        record.status = new_status
        record.save()

        return JsonResponse({
            'success': True,
            'status': new_status,
            'status_display': record.get_status_display()
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
@csrf_exempt
def update_company_llp_status(request, record_id):
    """Update status of Company / LLP Registration record via AJAX."""
    try:
        # Get employee
        try:
            employee_obj = Employee.objects.get(email=request.user.email)
        except Employee.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Employee not found'}, status=403)
        
        # Get record - check if assigned to employee
        record = get_object_or_404(CompanyLLPRegistration, id=record_id, assigned_to=employee_obj)
        new_status = request.POST.get('status')

        if new_status not in dict(CompanyLLPRegistration.STATUS_CHOICES):
            return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)

        record.status = new_status
        record.save()

        return JsonResponse({
            'success': True,
            'status': new_status,
            'status_display': record.get_status_display()
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
@csrf_exempt
def update_fire_pollution_status(request, record_id):
    """Update status of Fire & Pollution Licence record via AJAX."""
    try:
        # Get employee
        try:
            employee_obj = Employee.objects.get(email=request.user.email)
        except Employee.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Employee not found'}, status=403)
        
        # Get record - check if assigned to employee
        record = get_object_or_404(FirePollutionLicense, id=record_id, assigned_to=employee_obj)
        new_status = request.POST.get('status')

        if new_status not in dict(FirePollutionLicense.STATUS_CHOICES):
            return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)

        record.status = new_status
        record.save()

        return JsonResponse({
            'success': True,
            'status': new_status,
            'status_display': record.get_status_display()
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
@csrf_exempt
def update_iso_status(request, record_id):
    """Update status of ISO Certification record via AJAX."""
    try:
        # Get employee
        try:
            employee_obj = Employee.objects.get(email=request.user.email)
        except Employee.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Employee not found'}, status=403)
        
        # Get record - check if assigned to employee
        record = get_object_or_404(ISOCertification, id=record_id, assigned_to=employee_obj)
        new_status = request.POST.get('status')
        
        if new_status not in dict(ISOCertification.STATUS_CHOICES):
            return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)
        
        record.status = new_status
        record.save()
        
        return JsonResponse({
            'success': True,
            'status': new_status,
            'status_display': record.get_status_display()
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
@csrf_exempt
def update_trademark_status(request, record_id):
    """Update status of Trademark Filing record via AJAX."""
    try:
        # Get employee
        try:
            employee_obj = Employee.objects.get(email=request.user.email)
        except Employee.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Employee not found'}, status=403)
        
        # Get record - check if assigned to employee
        record = get_object_or_404(TrademarkFiling, id=record_id, assigned_to=employee_obj)
        new_status = request.POST.get('status')
        
        if new_status not in dict(TrademarkFiling.STATUS_CHOICES):
            return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)
        
        record.status = new_status
        record.save()
        
        return JsonResponse({
            'success': True,
            'status': new_status,
            'status_display': record.get_status_display()
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
@csrf_exempt
def update_trademark_compliance_status(request, record_id):
    """Update status of Trademark Filing + Compliance record via AJAX."""
    try:
        # Get employee
        try:
            employee_obj = Employee.objects.get(email=request.user.email)
        except Employee.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Employee not found'}, status=403)
        
        # Get record - check if assigned to employee
        record = get_object_or_404(TrademarkFilingCompliance, id=record_id, assigned_to=employee_obj)
        new_status = request.POST.get('status')
        
        if new_status not in dict(TrademarkFilingCompliance.STATUS_CHOICES):
            return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)
        
        record.status = new_status
        record.save()
        
        return JsonResponse({
            'success': True,
            'status': new_status,
            'status_display': record.get_status_display()
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
@csrf_exempt
def update_trademark_instant_status(request, record_id):
    """Update status of Trademark Filing (Instant Process) record via AJAX."""
    try:
        # Get employee
        try:
            employee_obj = Employee.objects.get(email=request.user.email)
        except Employee.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Employee not found'}, status=403)
        
        # Get record - check if assigned to employee
        record = get_object_or_404(TrademarkFilingInstant, id=record_id, assigned_to=employee_obj)
        new_status = request.POST.get('status')
        
        if new_status not in dict(TrademarkFilingInstant.STATUS_CHOICES):
            return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)
        
        record.status = new_status
        record.save()
        
        return JsonResponse({
            'success': True,
            'status': new_status,
            'status_display': record.get_status_display()
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
@csrf_exempt
def update_address_change_status(request, record_id):
    """Update status of Company Address Change record via AJAX."""
    try:
        # Get employee
        try:
            employee_obj = Employee.objects.get(email=request.user.email)
        except Employee.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Employee not found'}, status=403)
        
        # Get record - check if assigned to employee
        record = get_object_or_404(CompanyAddressChange, id=record_id, assigned_to=employee_obj)
        new_status = request.POST.get('status')
        
        if new_status not in dict(CompanyAddressChange.STATUS_CHOICES):
            return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)
        
        record.status = new_status
        record.save()
        
        return JsonResponse({
            'success': True,
            'status': new_status,
            'status_display': record.get_status_display()
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
@csrf_exempt
def update_moa_alteration_status(request, record_id):
    """Update status of MOA Alteration record via AJAX."""
    try:
        # Get employee
        try:
            employee_obj = Employee.objects.get(email=request.user.email)
        except Employee.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Employee not found'}, status=403)
        
        # Get record - check if assigned to employee
        record = get_object_or_404(MOAAlteration, id=record_id, assigned_to=employee_obj)
        new_status = request.POST.get('status')
        
        if new_status not in dict(MOAAlteration.STATUS_CHOICES):
            return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)
        
        record.status = new_status
        record.save()
        
        return JsonResponse({
            'success': True,
            'status': new_status,
            'status_display': record.get_status_display()
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def employee_in_out(request):
    """Employee check in/out view"""
    # Get logged-in user's name and find employee
    employee_obj = None
    if request.user.is_authenticated:
        employee_name = request.user.get_full_name() or request.user.username
        
        # Try to find employee by matching name
        name_parts = employee_name.strip().split(' ', 1)
        first_name = name_parts[0] if name_parts else ''
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        if first_name and last_name:
            employee_obj = Employee.objects.filter(
                first_name__iexact=first_name,
                last_name__iexact=last_name
            ).first()
        
        # If not found by name, try by email
        if not employee_obj:
            user_email = getattr(request.user, 'email', None)
            if user_email:
                employee_obj = Employee.objects.filter(
                    email__iexact=user_email
                ).first()
    else:
        employee_name = 'Guest User'
    
    # Check today's attendance status
    today = timezone.now().date()
    today_attendance = None
    
    # Priority 1: If employee_obj exists, match by employee foreign key first
    if employee_obj:
        today_attendance = Attendance.objects.filter(
            employee=employee_obj,
            date=today
        ).first()
    
    # Priority 2: If not found by employee, try by user
    if not today_attendance and request.user.is_authenticated:
        today_attendance = Attendance.objects.filter(
            user=request.user,
        date=today
    ).first()
    
    is_checked_in = False
    check_in_time = None
    if today_attendance and today_attendance.check_in_time and not today_attendance.check_out_time:
        is_checked_in = True
        check_in_time = today_attendance.check_in_time
    
    context = {
        'employee_name': employee_name,
        'is_checked_in': is_checked_in,
        'check_in_time': check_in_time,
    }
    return render(request, 'employee/in_out.html', context)

@login_required
def employee_settings(request):
    """Employee settings view"""
    user = request.user

    # Try to find the matching Employee record for the logged-in user
    employee_obj = None
    user_email = getattr(user, 'email', '') or ''
    if user_email:
        employee_obj = Employee.objects.filter(email__iexact=user_email).first()

    if not employee_obj:
        # Fallback: try to match on first and last name from user's profile
        user_full_name = user.get_full_name() or user.username or ''
        name_parts = user_full_name.strip().split(' ', 1)
        first_name = name_parts[0] if name_parts else ''
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        if first_name:
            qs = Employee.objects.filter(first_name__iexact=first_name)
            if last_name:
                qs = qs.filter(last_name__iexact=last_name)
            employee_obj = qs.first()

    # Build a simple dict for the template
    employee_dict = {
        'first_name': getattr(employee_obj, 'first_name', '') if employee_obj else '',
        'last_name': getattr(employee_obj, 'last_name', '') if employee_obj else '',
        'email': getattr(employee_obj, 'email', user_email) if employee_obj else user_email,
        'phone': getattr(employee_obj, 'phone', '') if employee_obj else '',
        'department': getattr(employee_obj, 'department', '') if employee_obj else '',
        'position': getattr(employee_obj, 'designation', '') if employee_obj else '',
        'employee_id': getattr(employee_obj, 'emp_code', '') if employee_obj else '',
        'username': getattr(user, 'username', ''),
        'bio': getattr(employee_obj, 'notes', '') if employee_obj else '',
        'avatar': (employee_obj.photo.url if (employee_obj and getattr(employee_obj, 'photo', None)) else 'https://via.placeholder.com/150')
    }

    # Static defaults for preferences/notifications/privacy (can be wired later)
    context = {
        'employee': employee_dict,
        'preferences': {
            'timezone': 'UTC-5',
            'language': 'en',
            'date_format': 'MM/DD/YYYY',
            'time_format': '12',
            'dashboard_layout': 'grid',
            'items_per_page': 25,
            'auto_refresh': True,
            'work_start_time': '09:00',
            'work_end_time': '18:00',
            'weekend_work': False,
            'overtime_work': True
        },
        'notifications': {
            'email_project_updates': True,
            'email_task_assignments': True,
            'email_deadlines': True,
            'email_meetings': False,
            'push_messages': True,
            'push_announcements': True,
            'push_system_alerts': True,
            'push_reminders': False
        },
        'privacy': {
            'profile_visibility': 'public',
            'share_work_hours': True,
            'share_projects': False,
            'share_availability': True,
            'share_location': False
        }
    }
    return render(request, 'employee/setting.html', context)

@login_required
def employee_leave(request):
    """Employee leave management view - fetches data from myapp_employee table"""
    from django.db.models import Q
    
    # Get logged-in user's information
    employee = None
    employee_name = None
    employee_department = None
    employee_designation = None
    
    if request.user.is_authenticated:
        # Get user's full name or username
        user_full_name = request.user.get_full_name() or request.user.username or ''
        
        # Try to match employee by name
        # Split user full name into first and last name
        name_parts = user_full_name.strip().split(' ', 1)
        first_name = name_parts[0] if name_parts else ''
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        # Try to find employee by matching name
        if first_name and last_name:
            employee = Employee.objects.filter(
                first_name__iexact=first_name,
                last_name__iexact=last_name
            ).first()
        
        # If not found by name, try by email
        if not employee and request.user.email:
            employee = Employee.objects.filter(
                email__iexact=request.user.email
            ).first()
            
        # If still not found, try by partial name match
        if not employee and user_full_name:
            # Try to match any part of the name
            employees = Employee.objects.filter(
                Q(first_name__icontains=first_name) |
                Q(last_name__icontains=first_name) |
                Q(email__icontains=request.user.email if request.user.email else '')
            )
            employee = employees.first()
    
    # Get leave balance from matched employee or set to "NA"
    if employee:
        leave_balance = {
            'annual_leave': employee.annual_leave if employee.annual_leave is not None else 'NA',
            'sick_leave': employee.sick_leave if employee.sick_leave is not None else 'NA',
            'personal_leave': employee.personal_leave if employee.personal_leave is not None else 'NA',
            'maternity_leave': employee.maternity_leave if employee.maternity_leave is not None else 'NA',
            'paternity_leave': employee.paternity_leave if employee.paternity_leave is not None else 'NA',
            'emergency_leave': employee.emergency_leave if employee.emergency_leave is not None else 'NA'
        }
        employee_name = employee.get_full_name()
        employee_department = employee.department or 'N/A'
        employee_designation = employee.designation or 'N/A'
    else:
        # No match found - show "NA" for all cards
        leave_balance = {
            'annual_leave': 'NA',
            'sick_leave': 'NA',
            'personal_leave': 'NA',
            'maternity_leave': 'NA',
            'paternity_leave': 'NA',
            'emergency_leave': 'NA'
        }
        employee_name = request.user.get_full_name() if request.user.is_authenticated else 'N/A'
        employee_department = 'N/A'
        employee_designation = 'N/A'
    
    # Load pending requests - filter by matched employee's applicant_name if found
    qs = LeaveRequest.objects.filter(status='Pending')
    if employee:
        # Filter by employee's full name
        qs = qs.filter(applicant_name__iexact=employee_name)
    elif request.user.is_authenticated:
        # Fallback to user-based filtering
        qs = qs.filter(user=request.user)
    qs = qs.order_by('-applied_at')

    pending_requests = [
        {
            'id': lr.id,
            'type': lr.leave_type,
            'start_date': lr.start_date.strftime('%Y-%m-%d'),
            'end_date': lr.end_date.strftime('%Y-%m-%d'),
            'days': lr.days,
            'reason': lr.reason,
            'status': lr.status,
            'applied_date': lr.applied_at.strftime('%Y-%m-%d'),
            'manager': ''
        }
        for lr in qs
    ]

    # Leave history: show all statuses except pending (filtered by matched employee)
    hist_qs = LeaveRequest.objects.exclude(status='Pending')
    if employee:
        # Filter by employee's full name
        hist_qs = hist_qs.filter(applicant_name__iexact=employee_name)
    elif request.user.is_authenticated:
        # Fallback to user-based filtering
        hist_qs = hist_qs.filter(user=request.user)
    hist_qs = hist_qs.order_by('-applied_at')
    leave_history = [
        {
            'id': lr.id,
            'type': lr.leave_type,
            'start_date': lr.start_date.strftime('%Y-%m-%d'),
            'end_date': lr.end_date.strftime('%Y-%m-%d'),
            'days': lr.days,
            'reason': lr.reason,
            'status': lr.status,
            'applied_date': lr.applied_at.strftime('%Y-%m-%d')
        }
        for lr in hist_qs
    ]

    context = {
        'employee_name': employee_name,
        'employee_id': employee.emp_code if employee else 'N/A',
        'employee_department': employee_department,
        'employee_designation': employee_designation,
        'leave_balance': leave_balance,
        'pending_requests': pending_requests,
        'leave_history': leave_history,
        'leave_types': [
            {'value': 'annual', 'label': 'Annual Leave', 'max_days': 20, 'description': 'Vacation and personal time off'},
            {'value': 'sick', 'label': 'Sick Leave', 'max_days': 12, 'description': 'Medical appointments and illness'},
            {'value': 'personal', 'label': 'Personal Leave', 'max_days': 5, 'description': 'Personal emergencies and urgent matters'},
            {'value': 'maternity', 'label': 'Maternity Leave', 'max_days': 90, 'description': 'Maternity and childbirth related leave'},
            {'value': 'paternity', 'label': 'Paternity Leave', 'max_days': 15, 'description': 'Paternity and newborn care leave'},
            {'value': 'emergency', 'label': 'Emergency Leave', 'max_days': 3, 'description': 'Emergency situations and unforeseen circumstances'}
        ]
    }
    return render(request, 'employee/leave.html', context)


@login_required
def employee_leave_view(request, leave_id):
    """Get leave request details as JSON"""
    try:
        leave = LeaveRequest.objects.get(id=leave_id)
        # Check if user owns this leave request or is admin
        if request.user.is_authenticated and leave.user != request.user and not request.user.is_staff:
            return JsonResponse({'error': 'You do not have permission to view this leave request'}, status=403)
        
        return JsonResponse({
            'id': leave.id,
            'leave_type': leave.leave_type,
            'start_date': leave.start_date.strftime('%Y-%m-%d'),
            'start_date_display': leave.start_date.strftime('%d %b %Y'),
            'end_date': leave.end_date.strftime('%Y-%m-%d'),
            'end_date_display': leave.end_date.strftime('%d %b %Y'),
            'days': leave.days,
            'reason': leave.reason,
            'status': leave.status,
            'contact': leave.contact or '',
            'handover': leave.handover or '',
            'applied_at': leave.applied_at.strftime('%Y-%m-%d %I:%M %p') if leave.applied_at else '',
            'updated_at': leave.updated_at.strftime('%Y-%m-%d %I:%M %p') if leave.updated_at else '',
            'applicant_name': leave.applicant_name or (leave.user.get_full_name() if leave.user else '') or 'N/A'
        })
    except LeaveRequest.DoesNotExist:
        return JsonResponse({'error': 'Leave request not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_POST
@login_required
def employee_leave_cancel(request, leave_id):
    """Cancel a leave request"""
    try:
        leave = LeaveRequest.objects.get(id=leave_id)
        # Check if user owns this leave request or is admin
        if request.user.is_authenticated and leave.user != request.user and not request.user.is_staff:
            return JsonResponse({'success': False, 'error': 'You do not have permission to cancel this leave request'}, status=403)
        
        if leave.status != 'Pending':
            return JsonResponse({'success': False, 'error': 'Only pending leave requests can be cancelled'}, status=400)
        
        leave.status = 'Cancelled'
        leave.save()
        
        messages.success(request, f'Leave request #{leave_id} has been cancelled successfully!')
        return JsonResponse({'success': True, 'message': 'Leave request cancelled successfully!'})
    except LeaveRequest.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Leave request not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def employee_leave_apply(request):
    """Create a leave request from employee/leave page (AJAX or form POST)."""
    try:
        leave_type = request.POST.get('type') or request.POST.get('leaveType') or request.POST.get('modalLeaveType')
        start_date = request.POST.get('startDate') or request.POST.get('modalStartDate')
        end_date = request.POST.get('endDate') or request.POST.get('modalEndDate')
        days = request.POST.get('days') or request.POST.get('modalDays')
        reason = request.POST.get('reason') or request.POST.get('modalReason')
        contact = request.POST.get('contact') or request.POST.get('modalContact')
        handover = request.POST.get('handover') or request.POST.get('modalHandover')
        
        # Get applicant name from form or user
        applicant_name = request.POST.get('applicantName', '').strip()
        
        if not applicant_name:
            if request.user.is_authenticated:
                applicant_name = request.user.get_full_name() or request.user.username or ''
            else:
                applicant_name = request.POST.get('applicant_name', '').strip()
        
        # Fallback: ensure we have a name
        if not applicant_name:
            applicant_name = request.POST.get('applicant_name', 'Unknown User').strip()

        if not (leave_type and start_date and end_date and reason):
            return JsonResponse({'success': False, 'error': 'Missing required fields.'}, status=400)

        # Parse dates and compute days if missing
        from datetime import datetime
        sd = datetime.strptime(start_date, '%Y-%m-%d').date()
        ed = datetime.strptime(end_date, '%Y-%m-%d').date()
        total_days = int(days) if str(days).isdigit() else (ed - sd).days + 1
        if total_days <= 0:
            return JsonResponse({'success': False, 'error': 'Invalid date range.'}, status=400)

        full_name = applicant_name
        if not full_name and request.user.is_authenticated:
            full_name = request.user.get_full_name() or request.user.username or ''

        # Find employee by applicant_name to check leave balance
        employee_obj = None
        if full_name:
            # Split name into first and last
            name_parts = full_name.strip().split(' ', 1)
            first_name = name_parts[0] if name_parts else ''
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            
            if first_name and last_name:
                employee_obj = Employee.objects.filter(
                    first_name__iexact=first_name,
                    last_name__iexact=last_name
                ).first()
            
            # If not found, try by email
            if not employee_obj and request.user.is_authenticated and request.user.email:
                employee_obj = Employee.objects.filter(email__iexact=request.user.email).first()
        
        # Map leave_type to Employee model field name
        leave_type_mapping = {
            'annual': 'annual_leave',
            'sick': 'sick_leave',
            'personal': 'personal_leave',
            'maternity': 'maternity_leave',
            'paternity': 'paternity_leave',
            'emergency': 'emergency_leave',
            # Also handle display names
            'Annual Leave': 'annual_leave',
            'Sick Leave': 'sick_leave',
            'Personal Leave': 'personal_leave',
            'Maternity': 'maternity_leave',
            'Paternity': 'paternity_leave',
            'Emergency': 'emergency_leave',
        }
        
        employee_field = leave_type_mapping.get(leave_type.lower() if leave_type else '', None)
        
        # Check available leave balance if employee found
        if employee_obj and employee_field:
            available_balance = getattr(employee_obj, employee_field, None) or 0
            if total_days > available_balance:
                leave_type_display = leave_type.replace('_', ' ').title()
                return JsonResponse({
                    'success': False, 
                    'error': f'Insufficient leave balance. You have {available_balance} days available for {leave_type_display}, but requested {total_days} days.'
                }, status=400)
        
        # Create leave request
        lr = LeaveRequest.objects.create(
            user=request.user if request.user.is_authenticated else None,
            applicant_name=full_name.strip() if full_name else None,
            leave_type=leave_type,
            start_date=sd,
            end_date=ed,
            days=total_days,
            reason=reason,
            contact=contact.strip() if contact else None,
            handover=handover.strip() if handover else None,
            status='Pending'
        )
        
        return JsonResponse({'success': True, 'id': lr.id, 'message': f'Leave request submitted successfully!'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def employee_new_project(request):
    """Employee new project creation view"""
    if request.method == 'POST':
        # Handle project creation logic here
        # For now, just redirect back to projects page
        return redirect('employee_projects')
    
    context = {
        'project_types': [
            {'value': 'web', 'label': 'Web Application'},
            {'value': 'mobile', 'label': 'Mobile Application'},
            {'value': 'backend', 'label': 'Backend Task'},
            {'value': 'security', 'label': 'Security Task'},
            {'value': 'data', 'label': 'Data Visualization'},
            {'value': 'infrastructure', 'label': 'Infrastructure'}
        ],
        'priorities': [
            {'value': 'low', 'label': 'Low'},
            {'value': 'medium', 'label': 'Medium'},
            {'value': 'high', 'label': 'High'},
            {'value': 'urgent', 'label': 'Urgent'}
        ]
    }
    return render(request, 'employee/new_project.html', context)

@login_required
def employee_project_detail(request, project_id):
    """Employee project detail view - fetches data from myapp_clientonboarding table"""
    from datetime import timedelta
    
    # Get logged-in user's information and find employee
    employee_obj = None
    employee_name = None
    if request.user.is_authenticated:
        user_full_name = request.user.get_full_name() or request.user.username or ''
        
        # Try to match employee by name
        name_parts = user_full_name.strip().split(' ', 1)
        first_name = name_parts[0] if name_parts else ''
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        if first_name and last_name:
            employee_obj = Employee.objects.filter(
                first_name__iexact=first_name,
                last_name__iexact=last_name
            ).first()
        
        # If not found by name, try by email
        if not employee_obj:
            user_email = getattr(request.user, 'email', None)
            if user_email:
                employee_obj = Employee.objects.filter(
                    email__iexact=user_email
                ).first()
        
        # Set employee name
        if employee_obj:
            employee_name = employee_obj.get_full_name()
        else:
            employee_name = user_full_name
    
    # Fetch project from ClientOnboarding table
    try:
        onboarding = ClientOnboarding.objects.get(id=project_id)
        
        # Verify that this project is assigned to the logged-in user
        if employee_name and onboarding.assigned_engineer:
            if onboarding.assigned_engineer.lower() != employee_name.lower():
                messages.error(request, 'You do not have permission to view this project.')
                return redirect('employee_projects')
        elif not onboarding.assigned_engineer:
            messages.error(request, 'Project assignment not found.')
            return redirect('employee_projects')
    except ClientOnboarding.DoesNotExist:
        messages.error(request, 'Project not found.')
        return redirect('employee_projects')
    
    # Calculate due date from start_date and duration
    due_date = None
    if onboarding.start_date:
        duration_days = 0
        if onboarding.duration_unit == 'days':
            duration_days = onboarding.project_duration
        elif onboarding.duration_unit == 'weeks':
            duration_days = onboarding.project_duration * 7
        elif onboarding.duration_unit == 'months':
            duration_days = onboarding.project_duration * 30
        elif onboarding.duration_unit == 'years':
            duration_days = onboarding.project_duration * 365
        
        due_date = onboarding.start_date + timedelta(days=duration_days)
    
    # Map status from ClientOnboarding to template status
    status_map = {
        'active': 'In Progress',
        'pending': 'Pending',
        'on_hold': 'On Hold',
        'completed': 'Completed'
    }
    template_status = status_map.get(onboarding.status, 'Pending')
    
    # Calculate progress based on status
    progress_map = {
        'active': 50,
        'pending': 0,
        'on_hold': 30,
        'completed': 100
    }
    progress = progress_map.get(onboarding.status, 0)
    
    # Calculate tasks (simplified - not in model, using status-based estimates)
    tasks_map = {
        'active': {'total': 10, 'completed': 5, 'pending': 5},
        'pending': {'total': 8, 'completed': 0, 'pending': 8},
        'on_hold': {'total': 12, 'completed': 4, 'pending': 8},
        'completed': {'total': 10, 'completed': 10, 'pending': 0}
    }
    tasks = tasks_map.get(onboarding.status, {'total': 8, 'completed': 0, 'pending': 8})
    
    # Derive project type from description
    project_type = 'Project'
    if onboarding.project_description:
        desc_lower = onboarding.project_description.lower()
        if 'web' in desc_lower or 'website' in desc_lower:
            project_type = 'Web Application'
        elif 'mobile' in desc_lower or 'app' in desc_lower:
            project_type = 'Mobile Application'
        elif 'database' in desc_lower or 'backend' in desc_lower:
            project_type = 'Backend Task'
        elif 'security' in desc_lower:
            project_type = 'Security Task'
        elif 'dashboard' in desc_lower or 'analytics' in desc_lower:
            project_type = 'Data Visualization'
        elif 'cloud' in desc_lower or 'infrastructure' in desc_lower:
            project_type = 'Infrastructure'
    
    # Format dates for display
    due_date_display = None
    if due_date:
        due_date_display = due_date.strftime('%b %d, %Y')
    
    start_date_display = None
    if onboarding.start_date:
        start_date_display = onboarding.start_date.strftime('%b %d, %Y')
    
    # Build project data
    project = {
        'id': onboarding.id,
        'name': onboarding.project_name,
        'type': project_type,
        'progress': progress,
        'due_date': due_date_display,
        'due_date_raw': due_date.strftime('%Y-%m-%d') if due_date else None,
        'status': template_status,
        'tasks_total': tasks['total'],
        'tasks_completed': tasks['completed'],
        'tasks_pending': tasks['pending'],
        'priority': 'Medium',
        'description': onboarding.project_description or 'No description available.',
        'client_name': onboarding.client_name or '',
        'company_name': onboarding.company_name or '',
        'client_email': onboarding.client_email or '',
        'client_phone': onboarding.client_phone or '',
        'project_cost': onboarding.project_cost or 0,
        'project_duration': onboarding.project_duration or 0,
        'duration_unit': onboarding.duration_unit or 'months',
        'assigned_engineer': onboarding.assigned_engineer or '',
        'start_date': onboarding.start_date.strftime('%Y-%m-%d') if onboarding.start_date else None,
        'start_date_display': start_date_display,
        'created_at': onboarding.created_at.strftime('%Y-%m-%d %H:%M:%S') if onboarding.created_at else '',
        'created_at_display': onboarding.created_at.strftime('%b %d, %Y') if onboarding.created_at else 'N/A',
        'updated_at': onboarding.updated_at.strftime('%Y-%m-%d %H:%M:%S') if onboarding.updated_at else '',
        'updated_at_display': onboarding.updated_at.strftime('%b %d, %Y') if onboarding.updated_at else 'N/A',
    }
    
    # Mock tasks for now (can be replaced with actual task model later)
    tasks_list = [
        {'id': 1, 'title': 'Project Setup', 'status': 'Completed', 'assignee': onboarding.assigned_engineer or 'N/A', 'due_date': start_date_display or 'N/A'},
        {'id': 2, 'title': 'Requirements Gathering', 'status': 'Completed' if onboarding.status == 'active' or onboarding.status == 'completed' else 'Pending', 'assignee': onboarding.assigned_engineer or 'N/A', 'due_date': start_date_display or 'N/A'},
        {'id': 3, 'title': 'Development', 'status': 'In Progress' if onboarding.status == 'active' else 'Pending', 'assignee': onboarding.assigned_engineer or 'N/A', 'due_date': due_date_display or 'N/A'},
        {'id': 4, 'title': 'Testing & Deployment', 'status': 'Pending', 'assignee': onboarding.assigned_engineer or 'N/A', 'due_date': due_date_display or 'N/A'},
    ]
    
    context = {
        'project': project,
        'tasks': tasks_list
    }
    return render(request, 'employee/project_detail.html', context)

@login_required
@require_POST
@csrf_exempt
def employee_update_project_status(request, project_id):
    """Update project status"""
    import json
    
    try:
        data = json.loads(request.body)
        new_status = data.get('status', '').lower()
        
        # Validate status
        valid_statuses = ['active', 'pending', 'on_hold', 'completed']
        if new_status not in valid_statuses:
            return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)
        
        # Get project from ClientOnboarding
        onboarding = ClientOnboarding.objects.get(id=project_id)
        
        # Verify that this project is assigned to the logged-in user
        employee_obj = None
        employee_name = None
        if request.user.is_authenticated:
            user_full_name = request.user.get_full_name() or request.user.username or ''
            
            # Try to match employee by name
            name_parts = user_full_name.strip().split(' ', 1)
            first_name = name_parts[0] if name_parts else ''
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            
            if first_name and last_name:
                employee_obj = Employee.objects.filter(
                    first_name__iexact=first_name,
                    last_name__iexact=last_name
                ).first()
            
            # If not found by name, try by email
            if not employee_obj:
                user_email = getattr(request.user, 'email', None)
                if user_email:
                    employee_obj = Employee.objects.filter(
                        email__iexact=user_email
                    ).first()
            
            # Set employee name
            if employee_obj:
                employee_name = employee_obj.get_full_name()
            else:
                employee_name = user_full_name
        
        # Verify assignment
        if employee_name and onboarding.assigned_engineer:
            if onboarding.assigned_engineer.lower() != employee_name.lower():
                return JsonResponse({'success': False, 'error': 'You do not have permission to update this project.'}, status=403)
        elif not onboarding.assigned_engineer:
            return JsonResponse({'success': False, 'error': 'Project assignment not found.'}, status=403)
        
        # Update status
        onboarding.status = new_status
        onboarding.save()
        
        return JsonResponse({'success': True, 'message': 'Project status updated successfully'})
        
    except ClientOnboarding.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Project not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def employee_start_project(request, project_id):
    """Start a project"""
    # In real app, update project status in database
    # For now, just redirect back to projects with success message
    return redirect('employee_projects')

@login_required
def employee_continue_project(request, project_id):
    """Continue working on a project"""
    # In real app, log activity or update project status
    # For now, just redirect back to projects with success message
    return redirect('employee_projects')

@login_required
def employee_finish_project(request, project_id):
    """Finish a project"""
    # In real app, update project status to completed
    # For now, just redirect back to projects with success message
    return redirect('employee_projects')

@login_required
def employee_profile(request):
    """Employee profile view - fetches data from myapp_employee table"""
    from django.db.models import Q
    from datetime import datetime, date
    
    # Get logged-in user's information
    employee_obj = None
    employee_name = None
    
    if request.user.is_authenticated:
        # Get user's full name or username
        user_full_name = request.user.get_full_name() or request.user.username or ''
        
        # Try to match employee by name, designation, and department
        # Split user full name into first and last name
        name_parts = user_full_name.strip().split(' ', 1)
        first_name = name_parts[0] if name_parts else ''
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        # Try to find employee by matching name first
        if first_name and last_name:
            employee_obj = Employee.objects.filter(
                first_name__iexact=first_name,
                last_name__iexact=last_name
            ).first()
        
        # If not found by name, try by email
        if not employee_obj and request.user.email:
            employee_obj = Employee.objects.filter(
                email__iexact=request.user.email
            ).first()
            
        # If still not found, try by partial name match
        if not employee_obj and user_full_name:
            # Try to match any part of the name
            employees = Employee.objects.filter(
                Q(first_name__icontains=first_name) |
                Q(last_name__icontains=first_name) |
                Q(email__icontains=request.user.email if request.user.email else '')
            )
            employee_obj = employees.first()
    
    # Build employee data from matched employee or use defaults
    if employee_obj:
        # Calculate experience from joining date
        experience_years = None
        if employee_obj.joining_date:
            try:
                today = date.today()
                delta = today - employee_obj.joining_date
                years = delta.days // 365
                months = (delta.days % 365) // 30
                if years > 0:
                    experience_years = f"{years}+ Years"
                elif months > 0:
                    experience_years = f"{months} Months"
                else:
                    experience_years = "Less than a month"
            except:
                experience_years = "N/A"
        else:
            experience_years = "N/A"
        
        employee_data = {
            'first_name': employee_obj.first_name or 'N/A',
            'last_name': employee_obj.last_name or 'N/A',
            'email': employee_obj.email or 'N/A',
            'phone': employee_obj.phone or 'N/A',
            'department': employee_obj.department or 'N/A',
            'position': employee_obj.designation or 'N/A',
            'employee_id': employee_obj.emp_code or 'N/A',
            'username': request.user.username if request.user.is_authenticated else 'N/A',
            'bio': employee_obj.notes or 'No bio available.',
            'avatar': 'https://via.placeholder.com/150',
            'experience': experience_years,
            'address_current': employee_obj.address_current or 'N/A',
            'address_permanent': employee_obj.address_permanent or 'N/A',
            'gender': employee_obj.gender if employee_obj.gender else 'N/A',
            'dob': employee_obj.dob.strftime('%d %b %Y') if employee_obj.dob else 'N/A',
            'joining_date': employee_obj.joining_date.strftime('%d %b %Y') if employee_obj.joining_date else 'N/A',
            'manager': employee_obj.manager or 'N/A',
            'location': employee_obj.location or 'N/A',
            'employment_type': employee_obj.employment_type if employee_obj.employment_type else 'N/A',
            'status': employee_obj.status if employee_obj.status else 'N/A',
            'work_email': employee_obj.work_email or 'N/A',
            'pan': employee_obj.pan or 'N/A',
            'aadhaar': employee_obj.aadhaar or 'N/A',
            'bank_name': employee_obj.bank_name or 'N/A',
            'account_number': employee_obj.account_number or 'N/A',
            'ifsc': employee_obj.ifsc or 'N/A',
        }
        employee_name = employee_obj.get_full_name()
    else:
        # No match found - use defaults
        employee_data = {
            'first_name': request.user.first_name if request.user.is_authenticated and hasattr(request.user, 'first_name') else 'N/A',
            'last_name': request.user.last_name if request.user.is_authenticated and hasattr(request.user, 'last_name') else 'N/A',
            'email': request.user.email if request.user.is_authenticated else 'N/A',
            'phone': 'N/A',
            'department': 'N/A',
            'position': 'N/A',
            'employee_id': 'N/A',
            'username': request.user.username if request.user.is_authenticated else 'N/A',
            'bio': 'No employee record found. Please contact HR.',
            'avatar': 'https://via.placeholder.com/150',
            'experience': 'N/A',
            'address_current': 'N/A',
            'address_permanent': 'N/A',
            'gender': 'N/A',
            'dob': 'N/A',
            'joining_date': 'N/A',
            'manager': 'N/A',
            'location': 'N/A',
            'employment_type': 'N/A',
            'status': 'N/A',
            'work_email': 'N/A',
            'pan': 'N/A',
            'aadhaar': 'N/A',
            'bank_name': 'N/A',
            'account_number': 'N/A',
            'ifsc': 'N/A',
        }
        employee_name = request.user.get_full_name() if request.user.is_authenticated else 'N/A'
    
    # Default preferences (can be enhanced later with user preferences model)
    preferences = {
        'timezone': 'UTC+5:30',
            'language': 'en',
        'date_format': 'DD/MM/YYYY',
            'time_format': '12',
            'dashboard_layout': 'grid',
            'items_per_page': 25,
            'auto_refresh': True,
            'work_start_time': '09:00',
            'work_end_time': '18:00',
            'weekend_work': False,
            'overtime_work': True
        }
    
    context = {
        'employee': employee_data,
        'preferences': preferences
    }
    return render(request, 'employee/profile.html', context)

@login_required
def employee_documents(request):
    """Employee documents view - fetch from DB"""
    qs = Document.objects.all()
    if request.user.is_authenticated:
        qs = qs.filter(user=request.user)

    def human_size(n):
        for unit in ['B','KB','MB','GB']:
            if n < 1024 or unit == 'GB':
                return f"{n:.0f} {unit}" if unit in ['B'] else f"{n/1024:.1f} {unit}" if unit!='B' else f"{n} B"
            n /= 1024

    def file_type(name, mime):
        name = (name or '').lower()
        if name.endswith('.pdf') or (mime and 'pdf' in mime):
            return 'pdf'
        if name.endswith(('.jpg','.jpeg','.png','.gif')) or (mime and 'image' in mime):
            return 'image'
        if name.endswith(('.doc','.docx')):
            return 'word'
        if name.endswith(('.xls','.xlsx')):
            return 'excel'
        return 'other'

    category_label = {
        'personal': ('Personal', 'success'),
        'work': ('Work', 'info'),
        'contracts': ('Contracts', 'primary'),
        'certificates': ('Certificates', 'warning'),
        'other': ('Other', 'secondary'),
    }

    documents = []
    for d in qs:
        label, color = category_label.get(d.category, ('Other','secondary'))
        documents.append({
            'id': d.id,
            'name': d.original_name,
            'type': file_type(d.original_name, d.mime_type),
            'size': human_size(d.size_bytes or 0),
            'description': d.description or '',
            'upload_date': d.uploaded_at.strftime('%b %d, %Y'),
            'modified_date': d.updated_at.strftime('%b %d, %Y'),
            'category': label,
            'category_color': color,
            'url': request.build_absolute_uri(d.file.url) if d.file else ''
        })

    context = {
        'documents': documents,
        'pdf_count': len([x for x in documents if x['type']=='pdf']),
        'image_count': len([x for x in documents if x['type']=='image']),
        'word_count': len([x for x in documents if x['type']=='word']),
        'excel_count': len([x for x in documents if x['type']=='excel'])
    }
    return render(request, 'employee/documents.html', context)


@require_POST
@login_required
def employee_documents_upload(request):
    """Handle document uploads (multiple)."""
    try:
        category = request.POST.get('category','personal')
        privacy = request.POST.get('privacy','private')
        description = request.POST.get('description','')
        files = request.FILES.getlist('files')
        if not files:
            return JsonResponse({'success': False, 'error': 'No files uploaded.'}, status=400)

        created = []
        for f in files:
            doc = Document(
                user=request.user if request.user.is_authenticated else None,
                file=f,
                original_name=f.name,
                size_bytes=f.size,
                mime_type=getattr(f, 'content_type', None),
                category=category,
                privacy=privacy,
                description=description or ''
            )
            doc.save()
            created.append(doc.id)

        return JsonResponse({'success': True, 'count': len(created), 'ids': created})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_POST
@login_required
def employee_documents_delete(request, doc_id):
    """Delete a document if it belongs to the current user (or no user)."""
    try:
        doc = Document.objects.get(id=doc_id)
        if request.user.is_authenticated and doc.user and doc.user != request.user:
            return JsonResponse({'success': False, 'error': 'Not allowed.'}, status=403)
        # Delete file from storage then DB row
        storage = doc.file.storage
        name = doc.file.name
        doc.delete()
        try:
            if name and storage.exists(name):
                storage.delete(name)
        except Exception:
            pass
        return JsonResponse({'success': True})
    except Document.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Not found.'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def employee_payroll(request):
    """Employee payroll view - fetches data from myapp_employee table"""
    from django.db.models import Q
    from decimal import Decimal
    
    # Get logged-in user's information
    employee_obj = None
    
    if request.user.is_authenticated:
        # Get user's full name or username
        user_full_name = request.user.get_full_name() or request.user.username or ''
        
        # Try to match employee by name, designation, department, and phone
        # Split user full name into first and last name
        name_parts = user_full_name.strip().split(' ', 1)
        first_name = name_parts[0] if name_parts else ''
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        # Get user's phone if available (from profile or request)
        user_phone = None
        if hasattr(request.user, 'phone'):
            user_phone = request.user.phone
        elif hasattr(request.user, 'profile') and hasattr(request.user.profile, 'phone'):
            user_phone = request.user.profile.phone
        
        # Get user's department and designation if available (from user model or profile)
        user_department = None
        user_designation = None
        if hasattr(request.user, 'department'):
            user_department = request.user.department
        if hasattr(request.user, 'designation'):
            user_designation = request.user.designation
        elif hasattr(request.user, 'profile'):
            if hasattr(request.user.profile, 'department'):
                user_department = request.user.profile.department
            if hasattr(request.user.profile, 'designation'):
                user_designation = request.user.profile.designation
        
        # First try: Match by exact name + designation + department + phone (most specific)
        if first_name and last_name:
            query = Q(first_name__iexact=first_name, last_name__iexact=last_name)
            
            # Add additional filters if available
            if user_designation:
                query &= Q(designation__iexact=user_designation)
            if user_department:
                query &= Q(department__iexact=user_department)
            if user_phone:
                query &= Q(phone__iexact=user_phone)
            
            employee_obj = Employee.objects.filter(query).first()
        
        # Second try: Match by exact name + designation + department (without phone)
        if not employee_obj and first_name and last_name:
            query = Q(first_name__iexact=first_name, last_name__iexact=last_name)
            if user_designation:
                query &= Q(designation__iexact=user_designation)
            if user_department:
                query &= Q(department__iexact=user_department)
            employee_obj = Employee.objects.filter(query).first()
        
        # Third try: Match by exact name + phone
        if not employee_obj and first_name and last_name and user_phone:
            employee_obj = Employee.objects.filter(
                first_name__iexact=first_name,
                last_name__iexact=last_name,
                phone__iexact=user_phone
            ).first()
        
        # Fourth try: Match by exact name only
        if not employee_obj and first_name and last_name:
            employee_obj = Employee.objects.filter(
                first_name__iexact=first_name,
                last_name__iexact=last_name
            ).first()
        
        # Fifth try: Match by email
        if not employee_obj and request.user.email:
            employee_obj = Employee.objects.filter(
                email__iexact=request.user.email
            ).first()
            
        # Sixth try: Match by partial name + designation + department
        if not employee_obj and user_full_name:
            query = Q(first_name__icontains=first_name) | Q(last_name__icontains=first_name)
            if user_designation:
                query = query & Q(designation__icontains=user_designation)
            if user_department:
                query = query & Q(department__icontains=user_department)
            employees = Employee.objects.filter(query)
            employee_obj = employees.first()
    
    # Decimal helper
    def to_decimal(value):
        if value is None or value == '':
            return Decimal('0')
        if isinstance(value, Decimal):
            return value
        try:
            return Decimal(str(value))
        except Exception:
            return Decimal('0')
    
    def build_snapshot_filter(name, department):
        filters = []
        if name:
            filters.append(Q(employee_name__iexact=name.strip()))
        if department:
            filters.append(Q(employee_department__iexact=department.strip()))
        if not filters:
            return None
        query = filters[0]
        for condition in filters[1:]:
            query &= condition
        return query
    
    # Get account last 4 digits helper
    def get_account_last4(account_number):
        if account_number and len(str(account_number)) >= 4:
            return str(account_number)[-4:]
        return 'N/A'
    
    def get_next_payment_date(payment_date):
        if not payment_date:
            return None
        year = payment_date.year + (1 if payment_date.month == 12 else 0)
        month = 1 if payment_date.month == 12 else payment_date.month + 1
        from calendar import monthrange
        day = min(payment_date.day, monthrange(year, month)[1])
        try:
            return date(year, month, day)
        except ValueError:
            return None
    
    snapshot_name = ''
    snapshot_department = ''
    if employee_obj:
        snapshot_name = (employee_obj.get_full_name() or '').strip()
        snapshot_department = (employee_obj.department or '').strip()
    else:
        snapshot_name = (request.user.get_full_name() or request.user.username or '').strip()
        if hasattr(request.user, 'department') and request.user.department:
            snapshot_department = request.user.department.strip()
        elif hasattr(request.user, 'profile') and hasattr(request.user.profile, 'department') and request.user.profile.department:
            snapshot_department = request.user.profile.department.strip()
    
    transactions_qs = PaymentTransaction.objects.none()
    if employee_obj:
        base_filter = Q(employee=employee_obj)
        snapshot_filter = build_snapshot_filter(snapshot_name, snapshot_department)
        if snapshot_filter:
            base_filter |= snapshot_filter
        transactions_qs = PaymentTransaction.objects.filter(base_filter)
    else:
        snapshot_filter = build_snapshot_filter(snapshot_name, snapshot_department)
        if snapshot_filter:
            transactions_qs = PaymentTransaction.objects.filter(snapshot_filter)
    
    transactions_qs = transactions_qs.select_related('employee').order_by('-payment_date', '-created_at')
    
    latest_transaction = transactions_qs.first()
    ytd_earnings = transactions_qs.filter(payment_year=timezone.now().year).aggregate(total=Sum('amount')).get('total') or Decimal('0')
    
    current_basic = to_decimal(latest_transaction.basic) if latest_transaction else Decimal('0')
    current_hra = to_decimal(latest_transaction.hra) if latest_transaction else Decimal('0')
    current_allowances = to_decimal(latest_transaction.allowances) if latest_transaction else Decimal('0')
    current_variable = to_decimal(latest_transaction.variable) if latest_transaction else Decimal('0')
    current_deductions = to_decimal(latest_transaction.deductions) if latest_transaction else Decimal('0')
    net_pay = to_decimal(latest_transaction.amount) if latest_transaction else Decimal('0')
    
    gross_pay = current_basic + current_hra + current_allowances + current_variable
    if latest_transaction and gross_pay == Decimal('0'):
        gross_pay = net_pay + current_deductions
    
    last_payment_date_display = latest_transaction.payment_date.strftime('%d %b %Y') if latest_transaction and latest_transaction.payment_date else None
    next_payment_date_obj = get_next_payment_date(latest_transaction.payment_date) if latest_transaction else None
    next_payment_date_display = next_payment_date_obj.strftime('%d %b %Y') if next_payment_date_obj else None
    current_period = latest_transaction.get_payment_period() if latest_transaction else None
    current_payment_method = latest_transaction.get_payment_method_display() if latest_transaction else None
    current_payment_date_display = latest_transaction.payment_date.strftime('%d %b %Y') if latest_transaction and latest_transaction.payment_date else None
    current_employee_department = latest_transaction.get_employee_department() if latest_transaction else (employee_obj.department if employee_obj else snapshot_department)
    current_employee_name = latest_transaction.get_employee_name() if latest_transaction else snapshot_name
    
    status_class_map = {
        'completed': 'bg-success',
        'pending': 'bg-warning text-dark',
        'failed': 'bg-danger',
        'cancelled': 'bg-secondary',
    }
    
    pay_history = []
    for transaction in transactions_qs:
        ph_basic = to_decimal(transaction.basic)
        ph_hra = to_decimal(transaction.hra)
        ph_allowances = to_decimal(transaction.allowances)
        ph_variable = to_decimal(transaction.variable)
        ph_deductions = to_decimal(transaction.deductions)
        ph_net = to_decimal(transaction.amount)
        ph_gross = ph_basic + ph_hra + ph_allowances + ph_variable
        if ph_gross == Decimal('0'):
            ph_gross = ph_net + ph_deductions
        
        pay_history.append({
            'id': transaction.id,
            'period': transaction.get_payment_period(),
            'gross_pay': ph_gross,
            'deductions': ph_deductions,
            'net_pay': ph_net,
            'status': transaction.get_status_display(),
            'status_class': status_class_map.get(transaction.status, 'secondary'),
            'payment_method': transaction.get_payment_method_display(),
            'payment_date_display': transaction.payment_date.strftime('%d %b %Y') if transaction.payment_date else None,
            'basic': ph_basic,
            'hra': ph_hra,
            'allowances': ph_allowances,
            'variable': ph_variable,
            'department': transaction.get_employee_department(),
            'employee_name': transaction.get_employee_name(),
            'transaction_id': transaction.transaction_id,
            'reference_number': transaction.reference_number,
            'notes': transaction.notes,
        })
    
    has_transactions = len(pay_history) > 0
    
    context = {
        'current_salary': net_pay if has_transactions else None,
        'current_gross_pay': gross_pay if has_transactions else None,
        'last_payment': net_pay if has_transactions else None,
        'last_payment_date': last_payment_date_display,
        'ytd_earnings': ytd_earnings if has_transactions else None,
        'next_payment_date': next_payment_date_display,
        'current_period': current_period,
        'current_basic': current_basic if has_transactions else None,
        'current_hra': current_hra if has_transactions else None,
        'current_allowances': current_allowances if has_transactions else None,
        'current_variable': current_variable if has_transactions else None,
        'current_deductions': current_deductions if has_transactions else None,
        'net_pay': net_pay if has_transactions else None,
        'current_payment_method': current_payment_method,
        'current_payment_date_display': current_payment_date_display,
        'current_employee_department': current_employee_department,
        'current_employee_name': current_employee_name,
        'employee_id': employee_obj.emp_code if employee_obj and employee_obj.emp_code else 'N/A',
        'pay_frequency': employee_obj.pay_cycle if employee_obj and employee_obj.pay_cycle else 'Monthly',
        'pay_method': current_payment_method or ('Direct Deposit' if employee_obj and employee_obj.bank_name and employee_obj.account_number else 'N/A'),
        'bank_account_last4': get_account_last4(employee_obj.account_number) if employee_obj and employee_obj.account_number else 'N/A',
        'tax_filing_status': 'N/A',
        'exemptions': 'N/A',
        'pay_history': pay_history,
        'has_transactions': has_transactions,
        }
    
    return render(request, 'employee/payroll.html', context)

@ensure_csrf_cookie
@login_required
def employee_messages(request):
    """Employee messages view - allows messaging between employees and admin"""
    from django.contrib.auth.models import User
    from .models import EmployeeMessage
    
    # Get current user
    current_user = request.user
    contacts = []
    current_user_employee = None
    
    print("=" * 50)
    print("DEBUG: Starting employee_messages view")
    print(f"DEBUG: Current user authenticated: {current_user.is_authenticated}")
    
    if current_user.is_authenticated:
        print(f"DEBUG: Current user - Username: {current_user.username}, Email: {getattr(current_user, 'email', 'N/A')}, Name: {current_user.get_full_name()}")
        
        # STEP 1: Get all employees from myapp_employee table
        all_employees = Employee.objects.all().order_by('first_name', 'last_name')
        print(f"DEBUG: STEP 1 - Total employees in myapp_employee table: {all_employees.count()}")
        
        # STEP 2: Try to find current user's employee record
        try:
            current_user_employee = Employee.objects.filter(
                Q(email=current_user.email) | 
                Q(first_name__iexact=current_user.first_name) |
                Q(last_name__iexact=current_user.last_name)
            ).first()
            
            if current_user_employee:
                print(f"DEBUG: STEP 2 - Found matching employee for current user: {current_user_employee.get_full_name()} (ID: {current_user_employee.id})")
                print(f"DEBUG: Current user email: {getattr(current_user, 'email', 'N/A')}")
                print(f"DEBUG: Employee email: {current_user_employee.email}")
            else:
                print(f"DEBUG: STEP 2 - No matching employee found for current user")
        except Exception as e:
            print(f"DEBUG: STEP 2 - Error finding current user employee: {e}")
        
        # STEP 3: Show ALL employees (temporarily no exclusion for testing)
        # TODO: Later we can exclude current user if needed
        employees_to_show = all_employees
        print(f"DEBUG: STEP 3 - Showing ALL employees (no exclusion) - Count: {employees_to_show.count()}")
        
        # STEP 4: Add all employees to contacts list
        print(f"DEBUG: STEP 4 - Adding employees to contacts list...")
        
        # Get current user's receiver_id (for counting unread messages)
        current_user_receiver_id = None
        if current_user_employee:
            current_user_receiver_id = current_user_employee.emp_code or str(current_user_employee.id)
        else:
            # Fallback - use user ID
            current_user_receiver_id = str(current_user.id)
        
        for emp in employees_to_show:
            # Count unread messages FROM this contact TO current user
            # Get sender User object for this employee
            sender_user = None
            if emp.email:
                try:
                    sender_user = User.objects.get(email=emp.email)
                except User.DoesNotExist:
                    pass
            
            sender_id = emp.emp_code or str(emp.id)  # Keep for receiver_id matching
            
            # Count unread messages - use receiver_id (CharField) for matching
            unread_count = EmployeeMessage.objects.filter(
                receiver_id=current_user_receiver_id,
                receiver_name__icontains=emp.get_full_name(),
                is_read=False
            ).count()
            
            # If we have sender_user, also filter by sender FK
            if sender_user:
                unread_count = EmployeeMessage.objects.filter(
                    receiver_id=current_user_receiver_id,
                    sender=sender_user,
                    is_read=False
                ).count()
            
            # Get latest message time for sorting
            if sender_user:
                latest_message = EmployeeMessage.objects.filter(
                    Q(receiver_id=current_user_receiver_id, sender=sender_user) |
                    Q(receiver_id=sender_id, sender=current_user)
                ).order_by('-created_at').first()
            else:
                # Fallback: use receiver_id matching only
                latest_message = EmployeeMessage.objects.filter(
                    Q(receiver_id=current_user_receiver_id) |
                    Q(receiver_id=sender_id)
                ).order_by('-created_at').first()
            
            latest_message_time = latest_message.created_at if latest_message else None
            
            # Create contact with first name, last name, designation, and department
            # Use emp_code as ID for consistency with EmployeeMessage receiver_id
            contact_data = {
                'id': emp.emp_code or str(emp.id),  # Use emp_code if available, otherwise use ID as string
                'name': emp.get_full_name(),  # Full name (first_name + last_name)
                'first_name': emp.first_name or '',
                'last_name': emp.last_name or '',
                'role': emp.designation or 'Employee',
                'designation': emp.designation or '',
                'department': emp.department or '',
                'email': emp.email or '',
                'unread_count': unread_count,
                'latest_message_time': latest_message_time
            }
            contacts.append(contact_data)
            print(f"DEBUG: Added contact - ID: {contact_data['id']}, Name: {contact_data['name']}, First: {contact_data['first_name']}, Last: {contact_data['last_name']}, Designation: {contact_data['designation']}, Department: {contact_data['department']}")
        
        print(f"DEBUG: STEP 4 - Total contacts added from employees: {len(contacts)}")
        
        # STEP 5: Add admin users as contacts
        admin_users = User.objects.filter(is_staff=True, is_active=True).exclude(
            id=current_user.id if hasattr(current_user, 'id') else None
        ).order_by('first_name', 'last_name', 'username')
        
        print(f"DEBUG: STEP 5 - Admin users found: {admin_users.count()}")
        for admin in admin_users:
            admin_name = admin.get_full_name() or admin.username
            admin_id = f'admin_{admin.id}'
            
            # Count unread messages FROM this admin TO current user
            # Admin sender is a User (ForeignKey), so use sender FK
            unread_count = EmployeeMessage.objects.filter(
                receiver_id=current_user_receiver_id,
                sender=admin,
                is_read=False
            ).count()
            
            # Get latest message time for sorting
            latest_message = EmployeeMessage.objects.filter(
                Q(receiver_id=current_user_receiver_id, sender=admin) |
                Q(receiver_id=admin_id, sender=current_user)
            ).order_by('-created_at').first()
            
            latest_message_time = latest_message.created_at if latest_message else None
            
            contacts.append({
                'id': admin_id,
                'name': admin_name,
                'first_name': admin.first_name or '',
                'last_name': admin.last_name or '',
                'role': 'Admin',
                'designation': 'Admin',
                'department': '',
                'email': admin.email if hasattr(admin, 'email') else '',
                'unread_count': unread_count,
                'latest_message_time': latest_message_time
            })
    else:
        print("DEBUG: User not authenticated!")
    
    # Get selected contact ID from query params
    selected_contact_id = request.GET.get('contact_id', None)
    
    # Final debug summary
    print("=" * 50)
    print(f"DEBUG: FINAL SUMMARY")
    print(f"DEBUG: Total contacts in list: {len(contacts)}")
    print(f"DEBUG: Employee contacts: {len([c for c in contacts if not str(c.get('id', '')).startswith('admin_')])}")
    print(f"DEBUG: Admin contacts: {len([c for c in contacts if str(c.get('id', '')).startswith('admin_')])}")
    
    if contacts:
        print("DEBUG: First 3 contacts:")
        for contact in contacts[:3]:
            print(f"  - ID: {contact.get('id')}, Name: {contact.get('name')}, Designation: {contact.get('designation')}, Department: {contact.get('department')}")
    else:
        print("DEBUG: WARNING - Contacts list is EMPTY!")
        # Emergency fallback - show all employees without exclusion
        all_emps_emergency = Employee.objects.all()
        print(f"DEBUG: Emergency - Total employees available: {all_emps_emergency.count()}")
        if all_emps_emergency.count() > 0:
            print("DEBUG: Emergency fallback - Adding all employees without exclusion")
            for emp in all_emps_emergency:
                contact_data = {
                    'id': emp.emp_code or str(emp.id),  # Use emp_code if available, otherwise use ID as string
                    'name': emp.get_full_name(),
                    'first_name': emp.first_name or '',
                    'last_name': emp.last_name or '',
                    'role': emp.designation or 'Employee',
                    'designation': emp.designation or '',
                    'department': emp.department or '',
                    'email': emp.email or '',
                    'unread_count': 0,
                    'latest_message_time': None
                }
                contacts.append(contact_data)
            print(f"DEBUG: Emergency - Added {len(contacts)} contacts")
    
    print("=" * 50)
    
    # Sort contacts: unread messages first, then by latest message time
    from django.utils import timezone
    contacts.sort(key=lambda x: (
        -(x.get('unread_count', 0) > 0),  # Unread first (True = 1, False = 0)
        -(x.get('latest_message_time') or timezone.now() - timezone.timedelta(days=365)).timestamp() if x.get('latest_message_time') else 0  # Latest first
    ), reverse=True)
    
    # Sort contacts: Recently messaged contacts at top, then alphabetically
    # Contacts with messages (latest_message_time) come first, sorted by most recent
    # Contacts without messages come after, sorted alphabetically
    from datetime import datetime
    from django.utils import timezone as django_timezone
    
    contacts_with_messages = []
    contacts_without_messages = []
    
    for contact in contacts:
        if contact.get('latest_message_time'):
            contacts_with_messages.append(contact)
        else:
            contacts_without_messages.append(contact)
    
    # Sort contacts with messages by latest_message_time (most recent first)
    # Handle timezone-aware and naive datetimes
    def get_sort_time(contact):
        msg_time = contact.get('latest_message_time')
        if msg_time:
            # If it's timezone-aware, use as is; if naive, assume UTC
            if django_timezone.is_aware(msg_time):
                return msg_time
            else:
                return django_timezone.make_aware(msg_time)
        return django_timezone.make_aware(datetime.min)
    
    contacts_with_messages.sort(key=get_sort_time, reverse=True)
    
    # Sort contacts without messages alphabetically by name
    contacts_without_messages.sort(key=lambda x: x.get('name', '').lower())
    
    # Combine: messages first, then no messages
    sorted_contacts = contacts_with_messages + contacts_without_messages
    
    # Show welcome message only on first visit after login
    show_welcome = False
    if current_user.is_authenticated:
        welcome_key = f'welcome_shown_{current_user.id}'
        if not request.session.get(welcome_key, False):
            # First visit - show welcome message
            show_welcome = True
            request.session[welcome_key] = True
            messages.success(request, f'Welcome back, {current_user.get_full_name() or current_user.username}! 👋')
    
    context = {
        'contacts': sorted_contacts,  # Use sorted contacts
        'selected_contact_id': selected_contact_id,
        'employee_name': current_user.get_full_name() if current_user.is_authenticated else 'Guest',
        'current_user_employee': current_user_employee,
        'show_welcome': show_welcome,
    }
    
    print(f"DEBUG: Context passed with {len(context.get('contacts', []))} contacts")
    return render(request, 'employee/messages.html', context)

def admin_messages(request):
    """Admin messages view - allows messaging between admin and employees"""
    from django.contrib.auth.models import User
    from .models import EmployeeMessage
    
    # Get current user
    current_user = request.user
    contacts = []
    current_user_employee = None
    
    if current_user.is_authenticated:
        # Get all employees from myapp_employee table
        all_employees = Employee.objects.all().order_by('first_name', 'last_name')
        
        # Try to find current user's employee record
        try:
            current_user_employee = Employee.objects.filter(
                Q(email=current_user.email) | 
                Q(first_name__iexact=current_user.first_name) |
                Q(last_name__iexact=current_user.last_name)
            ).first()
        except Exception as e:
            pass
        
        # Get current user's receiver_id (for counting unread messages)
        current_user_receiver_id = None
        if current_user_employee:
            current_user_receiver_id = current_user_employee.emp_code or str(current_user_employee.id)
        else:
            # Fallback - use user ID
            current_user_receiver_id = str(current_user.id)
        
        # Add all employees to contacts list
        for emp in all_employees:
            # Get sender User object for this employee
            sender_user = None
            if emp.email:
                try:
                    sender_user = User.objects.get(email=emp.email)
                except User.DoesNotExist:
                    pass
            
            sender_id = emp.emp_code or str(emp.id)
            
            # Count unread messages FROM this contact TO current user
            unread_count = EmployeeMessage.objects.filter(
                receiver_id=current_user_receiver_id,
                receiver_name__icontains=emp.get_full_name(),
                is_read=False
            ).count()
            
            # If we have sender_user, also filter by sender FK
            if sender_user:
                unread_count = EmployeeMessage.objects.filter(
                    receiver_id=current_user_receiver_id,
                    sender=sender_user,
                    is_read=False
                ).count()
            
            # Get latest message time for sorting
            if sender_user:
                latest_message = EmployeeMessage.objects.filter(
                    Q(receiver_id=current_user_receiver_id, sender=sender_user) |
                    Q(receiver_id=sender_id, sender=current_user)
                ).order_by('-created_at').first()
            else:
                latest_message = EmployeeMessage.objects.filter(
                    Q(receiver_id=current_user_receiver_id) |
                    Q(receiver_id=sender_id)
                ).order_by('-created_at').first()
            
            latest_message_time = latest_message.created_at if latest_message else None
            
            # Create contact data
            contact_data = {
                'id': emp.emp_code or str(emp.id),
                'name': emp.get_full_name(),
                'first_name': emp.first_name or '',
                'last_name': emp.last_name or '',
                'role': emp.designation or 'Employee',
                'designation': emp.designation or '',
                'department': emp.department or '',
                'email': emp.email or '',
                'unread_count': unread_count,
                'latest_message_time': latest_message_time
            }
            contacts.append(contact_data)
        
        # Add other admin users as contacts
        admin_users = User.objects.filter(is_staff=True, is_active=True).exclude(
            id=current_user.id if hasattr(current_user, 'id') else None
        ).order_by('first_name', 'last_name', 'username')
        
        for admin in admin_users:
            admin_name = admin.get_full_name() or admin.username
            admin_id = f'admin_{admin.id}'
            
            # Count unread messages FROM this admin TO current user
            unread_count = EmployeeMessage.objects.filter(
                receiver_id=current_user_receiver_id,
                sender=admin,
                is_read=False
            ).count()
            
            # Get latest message time for sorting
            latest_message = EmployeeMessage.objects.filter(
                Q(receiver_id=current_user_receiver_id, sender=admin) |
                Q(receiver_id=admin_id, sender=current_user)
            ).order_by('-created_at').first()
            
            latest_message_time = latest_message.created_at if latest_message else None
            
            contacts.append({
                'id': admin_id,
                'name': admin_name,
                'first_name': admin.first_name or '',
                'last_name': admin.last_name or '',
                'role': 'Admin',
                'designation': 'Admin',
                'department': '',
                'email': admin.email if hasattr(admin, 'email') else '',
                'unread_count': unread_count,
                'latest_message_time': latest_message_time
            })
    
    # Get selected contact ID from query params
    selected_contact_id = request.GET.get('contact_id', None)
    
    # Sort contacts: unread messages first, then by latest message time
    from django.utils import timezone
    from datetime import datetime
    from django.utils import timezone as django_timezone
    
    contacts_with_messages = []
    contacts_without_messages = []
    
    for contact in contacts:
        if contact.get('latest_message_time'):
            contacts_with_messages.append(contact)
        else:
            contacts_without_messages.append(contact)
    
    # Sort contacts with messages by latest_message_time (most recent first)
    def get_sort_time(contact):
        msg_time = contact.get('latest_message_time')
        if msg_time:
            if django_timezone.is_aware(msg_time):
                return msg_time
            else:
                return django_timezone.make_aware(msg_time)
        return django_timezone.make_aware(datetime.min)
    
    contacts_with_messages.sort(key=get_sort_time, reverse=True)
    contacts_without_messages.sort(key=lambda x: x.get('name', '').lower())
    sorted_contacts = contacts_with_messages + contacts_without_messages
    
    context = {
        'contacts': sorted_contacts,
        'selected_contact_id': selected_contact_id,
        'employee_name': current_user.get_full_name() if current_user.is_authenticated else 'Guest',
        'current_user_employee': current_user_employee,
        'show_welcome': False,
    }
    
    return render(request, 'dashboard/messages.html', context)

@csrf_exempt
@require_POST
@login_required
def employee_send_message(request):
    """Send a message to another employee or admin - Authentication not required"""
    try:
        # Get user from session if available, otherwise use default
        user = None
        if request.user.is_authenticated:
            user = request.user
        else:
            # Try to get user from session
            user_id = None
            if hasattr(request, 'session'):
                user_id = request.session.get('_auth_user_id')
            
            if user_id:
                from django.contrib.auth import get_user_model
                UserModel = get_user_model()
                try:
                    user = UserModel.objects.get(id=user_id)
                except UserModel.DoesNotExist:
                    pass
        
        # If still no user, try to get from request.POST or use anonymous
        if not user:
            # Try to get username from POST data as fallback
            username = request.POST.get('username') or request.POST.get('sender_name')
            if username:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                try:
                    user = User.objects.filter(username=username).first()
                except:
                    pass
        
        # If no user found, create a message anyway with default sender
        # This allows messages to be saved even without authentication
        
        receiver_id = request.POST.get('receiver_id')
        message_text = request.POST.get('message', '').strip()
        
        # Get uploaded files
        image_file = request.FILES.get('image')
        attachment_file = request.FILES.get('attachment')
        
        # At least one of message, image, or attachment must be provided
        if not receiver_id or (not message_text and not image_file and not attachment_file):
            return JsonResponse({'success': False, 'error': 'Receiver ID and at least message, image, or attachment is required'}, status=400)
        
        # Get sender name and employee details
        sender_name = 'Guest User'
        sender_designation = ''
        sender_department = ''
        
        if user:
            # Get current user's employee record to get designation and department
            current_user_employee = Employee.objects.filter(
                Q(email=user.email) |
                Q(first_name__iexact=user.first_name) |
                Q(last_name__iexact=user.last_name)
            ).first()
            
            # Get sender name - use full name or username, but ensure it's consistent
            sender_name = user.get_full_name() or user.username or 'Guest User'
            # Ensure sender_name is not empty
            if not sender_name or sender_name.strip() == '':
                sender_name = user.username or 'Guest User'
            sender_designation = current_user_employee.designation if current_user_employee else ''
            sender_department = current_user_employee.department if current_user_employee else ''
        else:
            # Try to get sender name from POST data
            sender_name = request.POST.get('sender_name', 'Guest User')
        
        # Get receiver name
        receiver_name = 'Unknown'
        if receiver_id.startswith('admin_'):
            # Admin user
            from django.contrib.auth.models import User
            admin_id = int(receiver_id.replace('admin_', ''))
            try:
                admin_user = User.objects.get(id=admin_id, is_staff=True)
                receiver_name = admin_user.get_full_name() or admin_user.username
            except User.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Admin user not found'}, status=404)
        else:
            # Employee - handle both ID and emp_code
            try:
                # Try to get by ID if receiver_id is numeric
                if receiver_id.isdigit():
                    receiver_employee = Employee.objects.get(id=int(receiver_id), status='active')
                else:
                    # Try to get by emp_code
                    receiver_employee = Employee.objects.get(emp_code=receiver_id, status='active')
                receiver_name = receiver_employee.get_full_name()
            except Employee.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Employee not found'}, status=404)
            except ValueError:
                # If receiver_id is not a valid ID or emp_code format
                return JsonResponse({'success': False, 'error': 'Invalid receiver ID format'}, status=400)
        
        # Create message (allow null sender for unauthenticated users)
        message = EmployeeMessage.objects.create(
            sender=user,  # Can be None if user not authenticated
            receiver_id=receiver_id,
            receiver_name=receiver_name,
            sender_name=sender_name,
            sender_designation=sender_designation or '',
            sender_department=sender_department or '',
            message=message_text if message_text else '',
            is_read=False
        )
        
        # Handle image upload
        if image_file:
            message.image = image_file
            message.save()
        
        # Handle attachment upload
        if attachment_file:
            message.attachment = attachment_file
            message.attachment_name = attachment_file.name
            message.save()
        
        # Prepare response data with is_sender flag
        # Determine if current user is sender for immediate display
        is_sender_response = False
        if user:
            is_sender_response = (message.sender == user) if message.sender else False
        
        # Prepare response data
        response_data = {
            'id': message.id,
            'message': message.message or '',
            'sender_name': message.sender_name,
            'created_at': message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'is_sender': is_sender_response  # Add is_sender flag for immediate display
        }
        
        # Add image URL if exists
        if message.image:
            response_data['image_url'] = message.image.url
        
        # Add attachment URL if exists
        if message.attachment:
            response_data['attachment_url'] = message.attachment.url
            response_data['attachment_name'] = message.attachment_name or message.attachment.name
        
        return JsonResponse({
            'success': True,
            'message': response_data
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
@login_required
def employee_get_messages(request):
    """Get messages between current user and a contact - Authentication not required"""
    try:
        receiver_id = request.GET.get('receiver_id')
        
        if not receiver_id:
            return JsonResponse({'success': False, 'error': 'Receiver ID is required'}, status=400)
        
        # Get user from session if available
        user = None
        if request.user.is_authenticated:
            user = request.user
        else:
            # Try to get user from session
            user_id = None
            if hasattr(request, 'session'):
                user_id = request.session.get('_auth_user_id')
            
            if user_id:
                from django.contrib.auth import get_user_model
                UserModel = get_user_model()
                try:
                    user = UserModel.objects.get(id=user_id)
                except UserModel.DoesNotExist:
                    pass
        
        # Get current user's ID for receiver matching
        current_user_id = None
        if user:
            # Check if current user is an employee
            current_user_employee = Employee.objects.filter(
                Q(email=user.email) | 
                Q(first_name__iexact=user.first_name) |
                Q(last_name__iexact=user.last_name)
            ).first()
            
            if current_user_employee:
                # Use emp_code if available, otherwise use ID as string
                current_user_id = current_user_employee.emp_code or str(current_user_employee.id)
            else:
                # If user is admin
                current_user_id = f'admin_{user.id}'
        
        # Get pagination parameters
        limit = int(request.GET.get('limit', 50))  # Default 50 messages per load
        before_id = request.GET.get('before_id')  # Load messages before this ID
        
        # Get messages between current user and receiver
        # Get messages where:
        # 1. Current user sent to receiver_id, OR
        # 2. Receiver sent to current user (receiver_id = current_user_id)
        if user and current_user_id:
            # Get all potential messages - both sent and received
            messages = EmployeeMessage.objects.filter(
                # Current user sent to receiver
                (Q(sender=user) & Q(receiver_id=receiver_id)) |
                # Messages received by current user (need to check if sender matches receiver_id)
                Q(receiver_id=current_user_id) |
                # Also get messages sent to receiver_id (in case sender matches receiver_id we're looking for)
                Q(receiver_id=receiver_id)
            )
            
            # Filter to show only relevant conversation messages
            filtered_messages = []
            for msg in messages:
                include = False
                
                # Case 1: Current user sent to receiver_id
                if msg.sender == user and msg.receiver_id == receiver_id:
                    include = True
                # Case 2: Message received by current user, check if sender's employee_id matches receiver_id
                elif msg.receiver_id == current_user_id:
                    if msg.sender:
                        sender_employee = Employee.objects.filter(
                            Q(email=msg.sender.email) |
                            Q(first_name__iexact=msg.sender.first_name) |
                            Q(last_name__iexact=msg.sender.last_name)
                        ).first()
                        if sender_employee:
                            # Check if receiver_id matches employee ID or emp_code
                            if str(sender_employee.id) == receiver_id or sender_employee.emp_code == receiver_id:
                                include = True
                # Case 3: Message sent to receiver_id, check if sender is current user
                elif msg.receiver_id == receiver_id and msg.sender == user:
                    include = True
                
                if include:
                    filtered_messages.append(msg.id)
            
            # Get final queryset
            if filtered_messages:
                messages = EmployeeMessage.objects.filter(id__in=filtered_messages)
            else:
                messages = EmployeeMessage.objects.none()
            
            # Mark unread messages as read when chat is opened
            if receiver_id and current_user_id:
                # Get sender User object from receiver_id
                # receiver_id can be emp_code or admin_{id} or integer ID
                sender_user = None
                if receiver_id.startswith('admin_'):
                    admin_user_id = int(receiver_id.replace('admin_', ''))
                    try:
                        sender_user = User.objects.get(id=admin_user_id, is_staff=True)
                    except (User.DoesNotExist, ValueError):
                        pass
                elif receiver_id.isdigit():
                    # Try to find employee and get their User
                    try:
                        emp = Employee.objects.get(id=int(receiver_id))
                        if emp.email:
                            sender_user = User.objects.filter(email=emp.email).first()
                    except (Employee.DoesNotExist, ValueError):
                        pass
                else:
                    # Try emp_code
                    try:
                        emp = Employee.objects.get(emp_code=receiver_id)
                        if emp.email:
                            sender_user = User.objects.filter(email=emp.email).first()
                    except Employee.DoesNotExist:
                        pass
                
                # Mark all unread messages FROM sender TO current_user as read
                if sender_user:
                    EmployeeMessage.objects.filter(
                        receiver_id=current_user_id,
                        sender=sender_user,
                        is_read=False
                    ).update(is_read=True)
                else:
                    # Fallback: use receiver_id matching
                    EmployeeMessage.objects.filter(
                        receiver_id=current_user_id,
                        receiver_name__icontains=receiver_id,
                        is_read=False
                    ).update(is_read=True)
        else:
            # If no user authenticated, get all messages for this receiver_id
            messages = EmployeeMessage.objects.filter(
                Q(receiver_id=receiver_id)
            )
        
        # Apply pagination: if before_id is provided, load messages before that ID
        if before_id:
            try:
                before_id_int = int(before_id)
                messages = messages.filter(id__lt=before_id_int)
            except (ValueError, TypeError):
                pass
        
        # Order by created_at (oldest first for lazy loading, then reverse at end if needed)
        messages = messages.order_by('-created_at')[:limit]
        
        # Reverse to get chronological order (oldest to newest)
        messages = list(reversed(messages))
        
        print(f"DEBUG: Found {len(messages)} messages between user and receiver {receiver_id} (limit={limit}, before_id={before_id})")
        
        # Mark messages as read where current user is receiver
        if current_user_id and user:
            EmployeeMessage.objects.filter(
                receiver_id=current_user_id,
                sender__isnull=False,
                is_read=False
            ).exclude(sender=user).update(is_read=True)
        
        messages_list = []
        # Get current user's name for comparison (important for when sender is None)
        current_user_name = None
        current_user_names = []  # List of possible names to match
        if user:
            full_name = user.get_full_name() or ''
            username = user.username or ''
            first_name = getattr(user, 'first_name', '') or ''
            last_name = getattr(user, 'last_name', '') or ''
            
            # Build list of possible names to match
            if full_name:
                current_user_names.append(full_name.strip().lower())
            if username:
                current_user_names.append(username.strip().lower())
            if first_name and last_name:
                current_user_names.append(f'{first_name} {last_name}'.strip().lower())
            
            # Use the first available name as primary
            current_user_name = current_user_names[0] if current_user_names else None
        
        for msg in messages:
            # Determine if current user is the sender (WhatsApp-style: sent = right/green, received = left/white)
            is_sender = False
            
            if user and current_user_id:
                # PRIORITY 1: Check if sender is current user (by sender object - most reliable)
                if msg.sender and msg.sender.id == user.id:
                    # Current user is the sender
                    if msg.receiver_id == receiver_id:
                        # Sent to the contact we're viewing → right side (sent)
                        is_sender = True
                    elif msg.receiver_id == current_user_id:
                        # This shouldn't happen, but if it does, it's received
                        is_sender = False
                    else:
                        # Sent to someone else (shouldn't be in this conversation, but mark as sent)
                        is_sender = True
                # PRIORITY 2: Check if we received this message (receiver_id is current_user_id)
                elif msg.receiver_id == current_user_id:
                    # We received this message → left side (received)
                    is_sender = False
                # PRIORITY 3: Check by sender_name if sender is None (for unauthenticated messages)
                # This is CRITICAL because messages might have sender=None but sender_name filled
                elif not msg.sender or msg.sender is None:
                    if msg.sender_name and current_user_names:
                        sender_name_lower = msg.sender_name.strip().lower()
                        # Check if sender_name matches any of current user's possible names
                        name_matches = sender_name_lower in current_user_names
                        
                        if name_matches:
                            # Sender name matches current user → it's a sent message
                            if msg.receiver_id == receiver_id:
                                # Sent to the contact we're viewing → right side (sent)
                                is_sender = True
                            elif msg.receiver_id == current_user_id:
                                # This shouldn't happen, but mark as received
                                is_sender = False
                            else:
                                # Sent to someone else, but based on name match, it's sent
                                is_sender = True
                        else:
                            # Sender name doesn't match current user → it's a received message
                            if msg.receiver_id == current_user_id:
                                # Received message (sender_name doesn't match, and we're the receiver)
                                is_sender = False
                            elif msg.receiver_id == receiver_id:
                                # Message sent to the contact we're viewing, but sender_name doesn't match us
                                # This means someone else sent it to this contact → received from our perspective
                                is_sender = False
            
            # Debug: Print sender info
            print(f"DEBUG Message {msg.id}: sender={msg.sender}, sender.id={msg.sender.id if msg.sender else None}, user.id={user.id if user else None}, sender_name={msg.sender_name}, receiver_id={msg.receiver_id}, receiver_id_param={receiver_id}, current_user_id={current_user_id}, is_sender={is_sender}")
            
            message_data = {
                'id': msg.id,
                'message': msg.message or '',
                'sender_name': msg.sender_name,
                'sender_designation': msg.sender_designation or '',
                'sender_department': msg.sender_department or '',
                'is_sender': is_sender,
                'created_at': msg.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'time_ago': get_time_ago(msg.created_at)
            }
            
            # Add image URL if exists
            if msg.image:
                message_data['image_url'] = msg.image.url
            
            # Add attachment URL if exists
            if msg.attachment:
                message_data['attachment_url'] = msg.attachment.url
                message_data['attachment_name'] = msg.attachment_name or msg.attachment.name
            
            messages_list.append(message_data)
        
        # Return pagination info
        has_more = False
        oldest_message_id = None
        if messages_list:
            oldest_message_id = messages_list[0]['id']
            # Check if there are more messages before this one
            if user and current_user_id:
                if filtered_messages:
                    remaining = EmployeeMessage.objects.filter(
                        id__in=filtered_messages,
                        id__lt=oldest_message_id
                    ).exists()
                    has_more = remaining
                else:
                    has_more = False
            else:
                remaining = EmployeeMessage.objects.filter(
                    Q(receiver_id=receiver_id),
                    id__lt=oldest_message_id
                ).exists()
                has_more = remaining
        
        return JsonResponse({
            'success': True,
            'messages': messages_list,
            'has_more': has_more,
            'oldest_message_id': oldest_message_id
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

def get_time_ago(dt):
    """Get human-readable time ago string"""
    from datetime import datetime
    from django.utils import timezone
    
    now = timezone.now()
    diff = now - dt
    
    if diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds >= 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds >= 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "Just now"

@login_required
def employee_achievements(request):
    """Employee achievements view"""
    achievements = [
        {
            'id': 1,
            'title': 'Employee of the Month',
            'description': 'Recognized for outstanding performance and dedication to project delivery',
            'date': 'November 2024',
            'category': 'Work',
            'type': 'award',
            'points': 100,
            'certificate_url': '#'
        },
        {
            'id': 2,
            'title': 'AWS Cloud Practitioner',
            'description': 'Successfully completed AWS Cloud Practitioner certification',
            'date': 'October 2024',
            'category': 'Certification',
            'type': 'certification',
            'points': 150,
            'certificate_url': '#'
        },
        {
            'id': 3,
            'title': 'Project Completion Milestone',
            'description': 'Successfully delivered 5 major projects on time',
            'date': 'September 2024',
            'category': 'Work',
            'type': 'milestone',
            'points': 200,
            'certificate_url': None
        },
        {
            'id': 4,
            'title': 'Team Recognition',
            'description': 'Recognized by team members for excellent collaboration',
            'date': 'August 2024',
            'category': 'Personal',
            'type': 'recognition',
            'points': 75,
            'certificate_url': None
        },
        {
            'id': 5,
            'title': 'PMP Certification',
            'description': 'Project Management Professional certification completed',
            'date': 'July 2024',
            'category': 'Certification',
            'type': 'certification',
            'points': 300,
            'certificate_url': '#'
        },
        {
            'id': 6,
            'title': 'Innovation Award',
            'description': 'Awarded for innovative solution in CRM development',
            'date': 'June 2024',
            'category': 'Work',
            'type': 'award',
            'points': 250,
            'certificate_url': '#'
        }
    ]
    
    certifications = [
        {
            'name': 'AWS Cloud Practitioner',
            'provider': 'Amazon Web Services',
            'earned_date': '2024-10-15',
            'expiry_date': '2027-10-15',
            'status': 'Active',
            'description': 'Cloud computing fundamentals'
        },
        {
            'name': 'Project Management Professional (PMP)',
            'provider': 'Project Management Institute',
            'earned_date': '2024-07-20',
            'expiry_date': '2027-07-20',
            'status': 'Active',
            'description': 'Project management best practices'
        },
        {
            'name': 'Certified Scrum Master',
            'provider': 'Scrum Alliance',
            'earned_date': '2023-12-10',
            'expiry_date': '2025-12-10',
            'status': 'Active',
            'description': 'Agile project management'
        }
    ]
    
    recent_activities = [
        {
            'type': 'achievement',
            'title': 'Employee of the Month',
            'date': 'Nov 30, 2024'
        },
        {
            'type': 'certification',
            'title': 'AWS Cloud Practitioner',
            'date': 'Oct 15, 2024'
        },
        {
            'type': 'milestone',
            'title': '5 Projects Completed',
            'date': 'Sep 25, 2024'
        }
    ]
    
    context = {
        'achievements': achievements,
        'certifications': certifications,
        'recent_activities': recent_activities,
        'this_year_achievements': len([a for a in achievements if '2024' in a['date']]),
        'work_achievements_count': len([a for a in achievements if a['category'] == 'Work']),
        'personal_achievements_count': len([a for a in achievements if a['category'] == 'Personal']),
        'work_achievements_percentage': 60,
        'personal_achievements_percentage': 40,
        'certifications_percentage': 75,
        'total_points': sum([a['points'] for a in achievements]),
        'performance_score': 92
    }
    return render(request, 'employee/achievements.html', context)

@login_required
def employee_leads(request):
    # Same data/loading as public leads(), but using employee-styled template
    leads_list = Lead.objects.filter(is_active=True).order_by('-created_at')

    search_query = request.GET.get('search', '')
    if search_query:
        leads_list = leads_list.filter(
            Q(name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(company__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(owner__icontains=search_query)
        )

    paginator = Paginator(leads_list, 10)
    page_number = request.GET.get('page')
    leads_page = paginator.get_page(page_number)

    if request.method == 'POST':
        form = LeadForm(request.POST)
        if form.is_valid():
            try:
                lead = form.save(commit=False)
                # If owner not provided, default to logged-in user's name/username
                if not lead.owner and request.user.is_authenticated:
                    lead.owner = request.user.get_full_name() or request.user.username
                lead.save()
                messages.success(request, f'Lead "{lead.name}" created successfully!')
                return redirect('employee_leads')
            except Exception as e:
                messages.error(request, f'Error creating lead: {str(e)}')
        else:
            messages.error(request, 'Please fix the form errors below.')
    else:
        initial = {}
        if request.user.is_authenticated:
            initial['owner'] = request.user.get_full_name() or request.user.username
        form = LeadForm(initial=initial)

    context = {
        'leads': leads_page,
        'form': form,
        'search_query': search_query,
        'total_leads': leads_list.count(),
    }

    return render(request, 'employee/leads.html', context)

@csrf_exempt
@require_POST
@login_required
def employee_attendance_check_in(request):
    """Handle check-in submission"""
    try:
        photo_data = request.POST.get('photo')
        if not photo_data:
            return JsonResponse({'success': False, 'error': 'Photo is required'}, status=400)
        
        # Get logged-in user's name and find employee
        employee_obj = None
        if request.user.is_authenticated:
            employee_name = request.user.get_full_name() or request.user.username
            user = request.user
            
            # Try to find employee by matching name
            name_parts = employee_name.strip().split(' ', 1)
            first_name = name_parts[0] if name_parts else ''
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            
            if first_name and last_name:
                employee_obj = Employee.objects.filter(
                    first_name__iexact=first_name,
                    last_name__iexact=last_name
                ).first()
            
            # If not found by name, try by email
            if not employee_obj:
                user_email = getattr(request.user, 'email', None)
                if user_email:
                    employee_obj = Employee.objects.filter(
                        email__iexact=user_email
                    ).first()
        else:
            employee_name = request.POST.get('employee_name', 'Guest User')
            user = None
        
        today = timezone.now().date()
        
        # Get or create today's attendance record
        # Try by employee first, then by user
        attendance = None
        created = False
        
        if employee_obj:
            attendance, created = Attendance.objects.get_or_create(
                employee=employee_obj,
                date=today,
                defaults={
                    'user': user,
                    'employee_name': employee_name,
                    'check_in_time': timezone.now(),
                    'check_in_photo': photo_data,
                }
            )
        
        if not attendance:
            attendance, created = Attendance.objects.get_or_create(
                user=user,
                date=today,
                defaults={
                    'employee': employee_obj,
                    'employee_name': employee_name,
                    'check_in_time': timezone.now(),
                    'check_in_photo': photo_data,
                }
            )
        
        if not created:
            # Update existing record if check-in not done yet
            if not attendance.check_in_time:
                attendance.check_in_time = timezone.now()
                attendance.check_in_photo = photo_data
                attendance.employee_name = employee_name
                if employee_obj and not attendance.employee:
                    attendance.employee = employee_obj
                attendance.save()
            else:
                return JsonResponse({'success': False, 'error': 'Already checked in today'}, status=400)
        
        return JsonResponse({
            'success': True,
            'check_in_time': attendance.check_in_time.isoformat(),
            'message': 'Check-in successful'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_POST
@login_required
def employee_attendance_check_out(request):
    """Handle check-out submission"""
    try:
        photo_data = request.POST.get('photo')
        if not photo_data:
            return JsonResponse({'success': False, 'error': 'Photo is required'}, status=400)
        
        # Get logged-in user's name and find employee
        employee_obj = None
        if request.user.is_authenticated:
            employee_name = request.user.get_full_name() or request.user.username
            user = request.user
            
            # Try to find employee by matching name
            name_parts = employee_name.strip().split(' ', 1)
            first_name = name_parts[0] if name_parts else ''
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            
            if first_name and last_name:
                employee_obj = Employee.objects.filter(
                    first_name__iexact=first_name,
                    last_name__iexact=last_name
                ).first()
            
            # If not found by name, try by email
            if not employee_obj:
                user_email = getattr(request.user, 'email', None)
                if user_email:
                    employee_obj = Employee.objects.filter(
                        email__iexact=user_email
                    ).first()
        else:
            employee_name = request.POST.get('employee_name', 'Guest User')
            user = None
        
        today = timezone.now().date()
        
        # Get today's attendance record - try by employee first, then by user
        attendance = None
        if employee_obj:
            try:
                attendance = Attendance.objects.get(employee=employee_obj, date=today)
            except Attendance.DoesNotExist:
                pass
        
        if not attendance:
            try:
                attendance = Attendance.objects.get(user=user, date=today)
            except Attendance.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'No check-in found for today'}, status=400)
        
        if not attendance.check_in_time:
            return JsonResponse({'success': False, 'error': 'No check-in found for today'}, status=400)
        
        if attendance.check_out_time:
            return JsonResponse({'success': False, 'error': 'Already checked out today'}, status=400)
        
        # Update check-out
        attendance.check_out_time = timezone.now()
        attendance.check_out_photo = photo_data
        attendance.employee_name = employee_name
        if employee_obj and not attendance.employee:
            attendance.employee = employee_obj
        attendance.save()
        
        # Calculate work hours
        work_hours = attendance.calculate_work_hours()
        
        return JsonResponse({
            'success': True,
            'check_out_time': attendance.check_out_time.isoformat(),
            'work_hours': work_hours,
            'message': 'Check-out successful'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def employee_attendance_records(request):
    """Get attendance records for the logged-in user with pagination"""
    try:
        filter_date = request.GET.get('date', '')
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 10))
        
        # Filter by employee or user
        if request.user.is_authenticated:
            # Try to find employee first
            employee_obj = None
            employee_name = request.user.get_full_name() or request.user.username
            
            # Try to find employee by matching name
            name_parts = employee_name.strip().split(' ', 1)
            first_name = name_parts[0] if name_parts else ''
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            
            if first_name and last_name:
                employee_obj = Employee.objects.filter(
                    first_name__iexact=first_name,
                    last_name__iexact=last_name
                ).first()
            
            # If not found by name, try by email
            if not employee_obj:
                user_email = getattr(request.user, 'email', None)
                if user_email:
                    employee_obj = Employee.objects.filter(
                        email__iexact=user_email
                    ).first()
            
            # Priority 1: Filter by employee foreign key
            if employee_obj:
                qs = Attendance.objects.filter(employee=employee_obj)
            else:
                # Priority 2: Filter by user
                qs = Attendance.objects.filter(user=request.user)
        else:
            # For guest users, filter by employee name if provided
            employee_name = request.GET.get('employee_name', '')
            if employee_name:
                qs = Attendance.objects.filter(employee_name=employee_name)
            else:
                qs = Attendance.objects.none()
        
        # Filter by date if provided
        if filter_date:
            qs = qs.filter(date=filter_date)
        
        # Get recent records (last 30 days)
        if not filter_date:
            from datetime import timedelta
            thirty_days_ago = timezone.now().date() - timedelta(days=30)
            qs = qs.filter(date__gte=thirty_days_ago)
        
        # Get total count
        total_count = qs.count()
        
        # Calculate pagination
        total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
        start = (page - 1) * per_page
        end = start + per_page
        
        # Get paginated records
        records = []
        for att in qs.order_by('-date', '-check_in_time')[start:end]:
            work_hours = att.calculate_work_hours()
            records.append({
                'id': att.id,
                'employee_name': att.employee_name,
                'date': att.date.isoformat(),
                'check_in_time': att.check_in_time.isoformat() if att.check_in_time else None,
                'check_in_photo': att.check_in_photo,
                'check_out_time': att.check_out_time.isoformat() if att.check_out_time else None,
                'check_out_photo': att.check_out_photo,
                'work_hours': work_hours
            })
        
        return JsonResponse({
            'success': True,
            'records': records,
            'pagination': {
                'current_page': page,
                'total_pages': total_pages,
                'total_count': total_count,
                'per_page': per_page,
                'has_next': page < total_pages,
                'has_prev': page > 1
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)



@login_required
def employee_quotes(request):
    """Employee portal quotation management"""
    
    # Handle Quote Creation
    if request.method == 'POST' and 'quote_submit' in request.POST:
        try:
            # Generate quote number if not provided
            quote_no = request.POST.get('quote_number', '').strip()
            if not quote_no:
                last_quote = Quote.objects.order_by('-id').first()
                if last_quote and last_quote.quote_number.startswith('Q-'):
                    try:
                        last_num = int(last_quote.quote_number.split('-')[1])
                        quote_no = f'Q-{last_num + 1:04d}'
                    except:
                        quote_no = f'Q-{Quote.objects.count() + 1:04d}'
                else:
                    quote_no = 'Q-1001'
            
            # Check if quote number already exists
            if Quote.objects.filter(quote_number=quote_no).exists():
                counter = 1
                original_no = quote_no
                while Quote.objects.filter(quote_number=quote_no).exists():
                    quote_no = f'{original_no}-{counter}'
                    counter += 1
            
            # Extract currency code
            currency_input = request.POST.get('currency', 'INR')
            currency_code = currency_input.split()[0] if ' ' in currency_input else currency_input
            
            # Validate required fields
            client_name = request.POST.get('client_name', '').strip()
            owner = request.POST.get('owner', '').strip()
            valid_until_str = request.POST.get('valid_until', '').strip()
            
            if not client_name or not owner or not valid_until_str:
                if not client_name:
                    messages.error(request, 'Client name is required!')
                elif not owner:
                    messages.error(request, 'Owner is required!')
                elif not valid_until_str:
                    messages.error(request, 'Valid Until date is required!')
                return redirect('employee_quotes')
            
            # Block duplicate send: if a Sent quote already exists for this client
            if Quote.objects.filter(client_name__iexact=client_name, status__iexact='Sent').exists():
                messages.error(request, f'Quote already sent to "{client_name}". You cannot send again.')
                return redirect('employee_quotes')
            
            # Parse valid_until date
            try:
                valid_until = datetime.strptime(valid_until_str, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                messages.error(request, 'Invalid Valid Until date format!')
                return redirect('employee_quotes')
            
            # Prepare optional fields
            company = request.POST.get('company', '').strip() or None
            email = request.POST.get('email', '').strip() or None
            phone = request.POST.get('phone', '').strip() or None
            notes = request.POST.get('notes', '').strip() or None
            terms = request.POST.get('terms', '').strip() or None
            
            # Create Quote
            quote = Quote.objects.create(
                quote_number=quote_no,
                client_name=client_name,
                company=company,
                email=email,
                phone=phone,
                owner=owner,
                status=request.POST.get('status', 'Sent'),
                currency=currency_code,
                valid_until=valid_until,
                notes=notes,
                terms=terms,
                subtotal=Decimal(request.POST.get('subtotal', '0')),
                discount=Decimal(request.POST.get('discount', '0')),
                total=Decimal(request.POST.get('total', '0'))
            )
            
            # Parse and save items as JSON
            items_data = request.POST.get('items_data', '[]')
            try:
                items = json.loads(items_data)
                if not isinstance(items, list):
                    items = []
            except (json.JSONDecodeError, ValueError):
                items = []
            
            formatted_items = []
            for item in items:
                if item.get('description', '').strip():
                    formatted_items.append({
                        'description': item.get('description', ''),
                        'quantity': int(item.get('quantity', 1)),
                        'unit_price': str(item.get('unit_price', '0')),
                        'gst_percent': str(item.get('gst_percent', '0')),
                        'amount': str(item.get('amount', '0'))
                    })
            
            quote.items = formatted_items
            
            # Handle PDF upload
            if 'project_pdf' in request.FILES:
                quote.project_pdf = request.FILES['project_pdf']
            
            quote.save()
            messages.success(request, f'Quote {quote_no} created successfully!')
            return redirect('employee_quotes')
        except Exception as e:
            messages.error(request, f'Error creating quote: {str(e)}')
            return redirect('employee_quotes')
    
    # Handle Onboarding Creation
    if request.method == 'POST' and 'onboard_submit' in request.POST:
        try:
            client_name = request.POST.get('client_name', '').strip()
            project_name = request.POST.get('project_name', '').strip()
            project_duration = request.POST.get('project_duration', '').strip()
            project_cost = request.POST.get('project_cost', '').strip()
            assigned_engineer = request.POST.get('assigned_engineer', '').strip()
            
            if not client_name or not project_name or not project_duration or not project_cost or not assigned_engineer:
                messages.error(request, 'Please fill in all required fields!')
                return redirect('employee_quotes')
            
            # Parse start_date if provided
            start_date = None
            start_date_str = request.POST.get('start_date', '').strip()
            if start_date_str:
                try:
                    from django.utils.dateparse import parse_date
                    start_date = parse_date(start_date_str)
                except (ValueError, TypeError):
                    start_date = None
            
            # Prepare optional fields
            company_name = request.POST.get('company_name', '').strip() or None
            client_email = request.POST.get('client_email', '').strip() or None
            client_phone = request.POST.get('client_phone', '').strip() or None
            project_description = request.POST.get('project_description', '').strip() or None
            
                # Create new onboarding
            onboard = ClientOnboarding.objects.create(
                    client_name=client_name,
                company_name=company_name,
                client_email=client_email,
                client_phone=client_phone,
                    project_name=project_name,
                project_description=project_description,
                    project_duration=int(project_duration),
                    duration_unit=request.POST.get('duration_unit', 'months'),
                    project_cost=Decimal(str(project_cost)),
                    assigned_engineer=assigned_engineer,
                    start_date=start_date,
                    status=request.POST.get('status', 'active')
                )
            
            messages.success(request, f'Client {client_name} onboarded successfully!')
            return redirect('employee_quotes')
        except Exception as e:
            messages.error(request, f'Error onboarding client: {str(e)}')
            return redirect('employee_quotes')
    
    # Fetch all quotes and onboardings
    quotes_list = Quote.objects.all().order_by('-created_at')
    onboardings_list = ClientOnboarding.objects.all().order_by('-created_at')
    
    # Get available client names from Leads table (excluding already onboarded ones)
    onboarded_client_names = set(ClientOnboarding.objects.values_list('client_name', flat=True).distinct())
    # Get clients from Leads (not yet onboarded)
    leads_for_onboarding = Lead.objects.filter(
        is_active=True
    ).exclude(name__in=onboarded_client_names).order_by('name')
    
    available_clients = []
    for lead in leads_for_onboarding:
        available_clients.append((
            lead.name,
            lead.company or '',
            lead.email or '',
            lead.phone or ''
        ))
    
    # Get engineers from Employee table where department = "Engineering"
    # Include project count for each engineer
    engineers = Employee.objects.filter(
        department__iexact='Engineering',
        status='active'
    ).order_by('first_name', 'last_name')
    
    engineers_with_count = []
    for engineer in engineers:
        engineer_name = engineer.get_full_name()
        # Count assigned projects for this engineer
        project_count = ClientOnboarding.objects.filter(assigned_engineer__iexact=engineer_name).count()
        engineers_with_count.append({
            'id': engineer.id,
            'name': engineer_name,
            'designation': engineer.designation or '',
            'project_count': project_count
        })
    
    # Paginate quotes (10 per page)
    quotes_paginator = Paginator(quotes_list, 10)
    quotes_page = request.GET.get('quote_page', 1)
    try:
        quotes = quotes_paginator.page(quotes_page)
    except PageNotAnInteger:
        quotes = quotes_paginator.page(1)
    except EmptyPage:
        quotes = quotes_paginator.page(quotes_paginator.num_pages)
    
    # Paginate onboardings (10 per page)
    onboardings_paginator = Paginator(onboardings_list, 10)
    onboardings_page = request.GET.get('onboard_page', 1)
    try:
        onboardings = onboardings_paginator.page(onboardings_page)
    except PageNotAnInteger:
        onboardings = onboardings_paginator.page(1)
    except EmptyPage:
        onboardings = onboardings_paginator.page(onboardings_paginator.num_pages)
    
    # Build Leads for Create Quote dropdown (from myapp_lead)
    leads_qs = Lead.objects.filter(is_active=True).order_by('name')
    leads_for_quote = []
    for lead in leads_qs:
        has_sent = Quote.objects.filter(client_name__iexact=lead.name, status__iexact='Sent').exists()
        leads_for_quote.append({
            'name': lead.name,
            'company': lead.company or '',
            'email': lead.email or '',
            'phone': lead.phone or '',
            'has_sent': has_sent,
        })
    
    context = {
        'quotes': quotes,
        'onboardings': onboardings,
        'available_clients': available_clients,  # List of tuples: (client_name, company, email, phone)
        'engineers': engineers_with_count,  # List of dicts with engineer info and project count
        'leads_for_quote': leads_for_quote,  # Leads dropdown data
    }
    
    return render(request, 'employee/quotes.html', context)


@login_required
def employee_clients(request):
    """Employee portal clients page with onboarding and client section tabs"""
    from django.core.paginator import Paginator
    from django.db.models import Sum, Q
    from decimal import Decimal
    
    # Handle Onboarding Creation
    if request.method == 'POST' and 'onboard_submit' in request.POST:
        try:
            client_name = request.POST.get('client_name', '').strip()
            project_name = request.POST.get('project_name', '').strip()
            project_duration = request.POST.get('project_duration', '').strip()
            project_cost = request.POST.get('project_cost', '').strip()
            assigned_engineer = request.POST.get('assigned_engineer', '').strip()
            
            if not client_name or not project_name or not project_duration or not project_cost or not assigned_engineer:
                messages.error(request, 'Please fill in all required fields!')
                return redirect('employee_clients')
            
            # Parse start_date if provided
            start_date = None
            start_date_str = request.POST.get('start_date', '').strip()
            if start_date_str:
                try:
                    from django.utils.dateparse import parse_date
                    start_date = parse_date(start_date_str)
                except (ValueError, TypeError):
                    start_date = None
            
            # Prepare optional fields
            company_name = request.POST.get('company_name', '').strip() or None
            client_email = request.POST.get('client_email', '').strip() or None
            client_phone = request.POST.get('client_phone', '').strip() or None
            project_description = request.POST.get('project_description', '').strip() or None
            
            # Create new onboarding
            onboard = ClientOnboarding.objects.create(
                client_name=client_name,
                company_name=company_name,
                client_email=client_email,
                client_phone=client_phone,
                project_name=project_name,
                project_description=project_description,
                project_duration=int(project_duration),
                duration_unit=request.POST.get('duration_unit', 'months'),
                project_cost=Decimal(str(project_cost)),
                assigned_engineer=assigned_engineer,
                start_date=start_date,
                status=request.POST.get('status', 'active')
            )
            
            messages.success(request, f'Client {client_name} onboarded successfully!')
            return redirect('employee_clients')
        except Exception as e:
            messages.error(request, f'Error onboarding client: {str(e)}')
            return redirect('employee_clients')
    
    # ONBOARDING SECTION DATA
    # Search functionality for onboardings
    search_query = request.GET.get('onboard_search', '').strip()
    onboardings_list = ClientOnboarding.objects.all().order_by('-created_at')
    
    if search_query:
        onboardings_list = onboardings_list.filter(
            Q(client_name__icontains=search_query) |
            Q(company_name__icontains=search_query) |
            Q(client_email__icontains=search_query) |
            Q(client_phone__icontains=search_query) |
            Q(project_name__icontains=search_query) |
            Q(assigned_engineer__icontains=search_query)
        )
    
    # Get onboarding status counts
    onboarding_status_counts = {
        'total': ClientOnboarding.objects.count(),
        'active': ClientOnboarding.objects.filter(status='active').count(),
        'pending': ClientOnboarding.objects.filter(status='pending').count(),
        'on_hold': ClientOnboarding.objects.filter(status='on_hold').count(),
        'completed': ClientOnboarding.objects.filter(status='completed').count(),
    }
    
    # Filter onboardings by status for tabs
    active_onboardings = onboardings_list.filter(status='active')
    pending_onboardings = onboardings_list.filter(status='pending')
    on_hold_onboardings = onboardings_list.filter(status='on_hold')
    completed_onboardings = onboardings_list.filter(status='completed')
    
    # Paginate onboardings by status (10 per page)
    active_paginator = Paginator(active_onboardings, 10)
    pending_paginator = Paginator(pending_onboardings, 10)
    on_hold_paginator = Paginator(on_hold_onboardings, 10)
    completed_paginator = Paginator(completed_onboardings, 10)
    
    active_page = request.GET.get('active_page', 1)
    pending_page = request.GET.get('pending_page', 1)
    on_hold_page = request.GET.get('on_hold_page', 1)
    completed_page = request.GET.get('completed_page', 1)
    
    try:
        active_onboardings_paged = active_paginator.page(active_page)
    except PageNotAnInteger:
        active_onboardings_paged = active_paginator.page(1)
    except EmptyPage:
        active_onboardings_paged = active_paginator.page(active_paginator.num_pages)
    
    try:
        pending_onboardings_paged = pending_paginator.page(pending_page)
    except PageNotAnInteger:
        pending_onboardings_paged = pending_paginator.page(1)
    except EmptyPage:
        pending_onboardings_paged = pending_paginator.page(pending_paginator.num_pages)
    
    try:
        on_hold_onboardings_paged = on_hold_paginator.page(on_hold_page)
    except PageNotAnInteger:
        on_hold_onboardings_paged = on_hold_paginator.page(1)
    except EmptyPage:
        on_hold_onboardings_paged = on_hold_paginator.page(on_hold_paginator.num_pages)
    
    try:
        completed_onboardings_paged = completed_paginator.page(completed_page)
    except PageNotAnInteger:
        completed_onboardings_paged = completed_paginator.page(1)
    except EmptyPage:
        completed_onboardings_paged = completed_paginator.page(completed_paginator.num_pages)
    
    # Get available client names from Leads table (excluding already onboarded ones)
    onboarded_client_names = set(ClientOnboarding.objects.values_list('client_name', flat=True).distinct())
    leads_for_onboarding = Lead.objects.filter(
        is_active=True
    ).exclude(name__in=onboarded_client_names).order_by('name')
    
    available_clients = []
    for lead in leads_for_onboarding:
        available_clients.append((
            lead.name,
            lead.company or '',
            lead.email or '',
            lead.phone or ''
        ))
    
    # Get engineers from Employee table where department = "Engineering"
    engineers = Employee.objects.filter(
        department__iexact='Engineering',
        status='active'
    ).order_by('first_name', 'last_name')
    
    engineers_with_count = []
    for engineer in engineers:
        engineer_name = engineer.get_full_name()
        project_count = ClientOnboarding.objects.filter(assigned_engineer__iexact=engineer_name).count()
        engineers_with_count.append({
            'id': engineer.id,
            'name': engineer_name,
            'designation': engineer.designation or '',
            'project_count': project_count
        })
    
    # CLIENT SECTION DATA (like accounts page)
    # Get all clients from ClientOnboarding
    clients_onboarding = ClientOnboarding.objects.all().order_by('-created_at')
    
    # Prepare client accounts data
    client_accounts = []
    for client in clients_onboarding:
        # Get all quotes for this client (match by client_name)
        client_quotes = Quote.objects.filter(client_name__iexact=client.client_name)
        
        # Calculate financial metrics
        total_quoted = client_quotes.aggregate(total=Sum('total'))['total'] or Decimal('0')
        
        # Amount invoiced = sum of accepted quotes
        amount_invoiced = client_quotes.filter(status='Accepted').aggregate(
            total=Sum('total')
        )['total'] or Decimal('0')
        
        # If no quotes, use project_cost from ClientOnboarding
        if total_quoted == 0 and client.project_cost:
            total_quoted = client.project_cost
            # If status is active or completed, consider it as invoiced
            if client.status in ['active', 'completed']:
                amount_invoiced = client.project_cost
        
        # Amount received - check Invoice model
        amount_received = Decimal('0')
        invoices = Invoice.objects.filter(client_name__iexact=client.client_name)
        if invoices.exists():
            amount_received = invoices.aggregate(total=Sum('amount_received'))['total'] or Decimal('0')
        elif client.status == 'completed':
            amount_received = amount_invoiced  # Assume full payment for completed projects
        
        # Outstanding = Invoiced - Received
        outstanding = amount_invoiced - amount_received
        
        # Get last payment date
        last_payment = None
        if invoices.exists():
            last_invoice = invoices.order_by('-updated_at').first()
            if last_invoice and last_invoice.updated_at:
                last_payment = last_invoice.updated_at.date()
        elif client.status == 'completed' and client.updated_at:
            last_payment = client.updated_at.date()
        
        # Get status for display
        if outstanding == 0 and amount_invoiced > 0:
            payment_status = 'Paid'  # Paid
            status_badge = 'bg-success'
        elif amount_received > 0 and outstanding > 0:
            payment_status = 'Partially Paid'  # Partially Paid
            status_badge = 'bg-warning text-dark'
        elif amount_invoiced > 0:
            payment_status = 'Unpaid'  # Unpaid
            status_badge = 'bg-danger'
        else:
            payment_status = 'Pending'  # Pending
            status_badge = 'bg-secondary'
        
        client_accounts.append({
            'id': client.id,
            'client_name': client.client_name,
            'company_name': client.company_name,
            'email': client.client_email,
            'phone': client.client_phone,
            'total_quoted': total_quoted,
            'amount_invoiced': amount_invoiced,
            'amount_received': amount_received,
            'outstanding': outstanding,
            'last_payment': last_payment,
            'status': payment_status,
            'status_badge': status_badge,
            'project_name': client.project_name,
            'project_cost': client.project_cost,
        })
    
    # Search for client section
    client_search_query = request.GET.get('client_search', '').strip()
    if client_search_query:
        client_accounts = [acc for acc in client_accounts if 
                          client_search_query.lower() in acc['client_name'].lower() or
                          (acc['company_name'] and client_search_query.lower() in acc['company_name'].lower()) or
                          (acc['email'] and client_search_query.lower() in acc['email'].lower()) or
                          (acc['phone'] and client_search_query.lower() in acc['phone'].lower())]
    
    # Pagination for clients
    clients_page_num = request.GET.get('client_page', 1)
    clients_paginator = Paginator(client_accounts, 10)
    try:
        clients_page = clients_paginator.page(clients_page_num)
    except PageNotAnInteger:
        clients_page = clients_paginator.page(1)
    except EmptyPage:
        clients_page = clients_paginator.page(clients_paginator.num_pages)
    
    context = {
        # Onboarding section
        'active_onboardings': active_onboardings_paged,
        'pending_onboardings': pending_onboardings_paged,
        'on_hold_onboardings': on_hold_onboardings_paged,
        'completed_onboardings': completed_onboardings_paged,
        'onboarding_status_counts': onboarding_status_counts,
        'onboard_search_query': search_query,
        'available_clients': available_clients,
        'engineers': engineers_with_count,
        # Client section
        'client_accounts': clients_page,
        'client_search_query': client_search_query,
    }
    
    return render(request, 'employee/clients.html', context)


@login_required
def employee_quote_view(request, quote_id):
    """Get quote details as JSON"""
    try:
        quote = Quote.objects.get(id=quote_id)
        return JsonResponse({
            'quote_number': quote.quote_number,
            'client_name': quote.client_name,
            'company': quote.company or '',
            'owner': quote.owner,
            'status': quote.status,
            'currency': quote.currency,
            'subtotal': str(quote.subtotal),
            'discount': str(quote.discount),
            'total': str(quote.total),
            'valid_until': quote.valid_until.strftime('%Y-%m-%d'),
            'valid_until_display': quote.valid_until.strftime('%d %b %Y'),
            'email': quote.email or '',
            'phone': quote.phone or '',
            'notes': quote.notes or '',
            'terms': quote.terms or '',
            'project_pdf': quote.project_pdf.url if quote.project_pdf else None,
            'items': quote.items if quote.items else [],
            'created_at': quote.created_at.strftime('%d %b %Y %I:%M %p') if quote.created_at else '',
            'updated_at': quote.updated_at.strftime('%d %b %Y %I:%M %p') if quote.updated_at else ''
        })
    except Quote.DoesNotExist:
        return JsonResponse({'error': 'Quote not found'}, status=404)


@require_POST
@login_required
def employee_quote_delete(request, quote_id):
    """Delete a quote"""
    try:
        quote = Quote.objects.get(id=quote_id)
        quote_number = quote.quote_number
        quote.delete()
        messages.success(request, f'Quote {quote_number} deleted successfully!')
        return JsonResponse({'success': True, 'message': f'Quote {quote_number} deleted successfully!'})
    except Quote.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Quote not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def employee_onboard_view(request, onboard_id):
    """Get onboarding details as JSON"""
    try:
        onboard = ClientOnboarding.objects.get(id=onboard_id)
        return JsonResponse({
            'client_name': onboard.client_name,
            'company_name': onboard.company_name or '',
            'client_email': onboard.client_email or '',
            'client_phone': onboard.client_phone or '',
            'project_name': onboard.project_name,
            'project_description': onboard.project_description or '',
            'project_duration': onboard.project_duration,
            'duration_unit': onboard.duration_unit,
            'duration_display': f"{onboard.project_duration} {onboard.get_duration_unit_display()}",
            'project_cost': str(onboard.project_cost),
            'assigned_engineer': onboard.assigned_engineer,
            'status': onboard.status,
            'status_display': onboard.get_status_display(),
            'start_date': onboard.start_date.strftime('%Y-%m-%d') if onboard.start_date else None,
            'start_date_display': onboard.start_date.strftime('%d %b %Y') if onboard.start_date else 'Not set',
            'created_at': onboard.created_at.strftime('%d %b %Y %I:%M %p') if onboard.created_at else '',
            'updated_at': onboard.updated_at.strftime('%d %b %Y %I:%M %p') if onboard.updated_at else ''
        })
    except ClientOnboarding.DoesNotExist:
        return JsonResponse({'error': 'Onboarding not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
@login_required
def employee_onboard_delete(request, onboard_id):
    """Delete an onboarding"""
    try:
        onboard = ClientOnboarding.objects.get(id=onboard_id)
        client_name = onboard.client_name
        onboard.delete()
        messages.success(request, f'Onboarding for {client_name} deleted successfully!')
        return JsonResponse({'success': True, 'message': f'Onboarding for {client_name} deleted successfully!'})
    except ClientOnboarding.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Onboarding not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def _format_display_date(value):
    return value.strftime('%d %b %Y') if value else None


def _next_month_due(day_of_month):
    today = timezone.now().date()
    month = today.month + 1
    year = today.year
    if month > 12:
        month = 1
        year += 1
    last_day = calendar.monthrange(year, month)[1]
    due_day = min(day_of_month, last_day)
    return date(year, month, due_day)


def _next_quarter_due(day_of_month):
    today = timezone.now().date()
    current_quarter = (today.month - 1) // 3 + 1
    next_quarter = current_quarter + 1
    year = today.year
    if next_quarter == 5:
        next_quarter = 1
        year += 1
    quarter_end_month = next_quarter * 3
    due_month = quarter_end_month + 1
    if due_month > 12:
        due_month -= 12
        year += 1
    last_day = calendar.monthrange(year, due_month)[1]
    due_day = min(day_of_month, last_day)
    return date(year, due_month, due_day)


def _next_annual_due(month=12, day=31):
    today = timezone.now().date()
    year = today.year
    due = date(year, month, day)
    if due <= today:
        due = date(year + 1, month, day)
    return due


def _get_gst_next_due(code):
    if code == 'GSTR-1':
        monthly_due = _format_display_date(_next_month_due(11))
        quarterly_due = _format_display_date(_next_quarter_due(13))
        return [d for d in [monthly_due, quarterly_due] if d]
    if code == 'GSTR-3B':
        due_20 = _format_display_date(_next_month_due(20))
        due_22 = _format_display_date(_next_month_due(22))
        due_24 = _format_display_date(_next_month_due(24))
        return [d for d in [due_20, due_22, due_24] if d]
    if code == 'GSTR-9':
        return [_format_display_date(_next_annual_due(12, 31))]
    if code == 'GSTR-9C':
        return [_format_display_date(_next_annual_due(12, 31))]
    return []


