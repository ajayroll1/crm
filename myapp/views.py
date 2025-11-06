from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.contrib.auth import logout as auth_logout, login as auth_login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Count
from django.utils import timezone
from datetime import datetime, date
from decimal import Decimal
import json
from .models import Lead, LeaveRequest, Document, Attendance, Quote, ClientOnboarding, Employee, EmployeeMessage
from .forms import LeadForm, LeadFilterForm
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie

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
  """Login view - authenticate user with email (from Employee) and phone number (as password) and redirect based on role"""
  if request.method == 'POST':
    email = request.POST.get('email', '').strip()
    phone_number = request.POST.get('password', '').strip()  # Password field contains phone number
    
    if not email or not phone_number:
      messages.error(request, 'Please provide both email and phone number.')
      return redirect('home')
    
    # Find Employee by email
    try:
      employee = Employee.objects.get(email=email)
    except Employee.DoesNotExist:
      messages.error(request, 'Invalid email address. Please check your email and try again.')
      return redirect('home')
    
    # Verify phone number matches
    # Normalize phone numbers for comparison (remove spaces, dashes, etc.)
    employee_phone = ''.join(filter(str.isdigit, employee.phone or ''))
    input_phone = ''.join(filter(str.isdigit, phone_number))
    
    if employee_phone != input_phone:
      messages.error(request, 'Invalid phone number. Please check and try again.')
      return redirect('home')
    
    # Check if employee is active
    if employee.status != 'active':
      messages.error(request, 'Your account has been deactivated. Please contact administrator.')
      return redirect('home')
    
    # Get or create User account for this employee
    user = None
    try:
      # Try to find existing user by email
      user = User.objects.get(email=email)
    except User.DoesNotExist:
      # Create User account for Employee if it doesn't exist
      username = email.split('@')[0]  # Use email prefix as username
      # Ensure username is unique
      base_username = username
      counter = 1
      while User.objects.filter(username=username).exists():
        username = f"{base_username}{counter}"
        counter += 1
      
      # Create user with phone number as password
      user = User.objects.create_user(
        username=username,
        email=email,
        password=phone_number,  # Use phone number as password
        first_name=employee.first_name,
        last_name=employee.last_name,
        is_staff=(employee.role == 'Admin')
      )
    
    # Authenticate user
    authenticated_user = authenticate(request, username=user.username, password=phone_number)
    
    if authenticated_user is not None:
      if authenticated_user.is_active:
        # Login the user
        auth_login(request, authenticated_user)
        
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
      # Authentication failed - update user password (phone might have changed)
      if user is not None:
        user.set_password(phone_number)
        user.save()
        authenticated_user = authenticate(request, username=user.username, password=phone_number)
        if authenticated_user:
          auth_login(request, authenticated_user)
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
  return render(request, 'accounnts/accounts.html')
## Kanban removed


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

def leave(request):
    return render(request,'human_resource/leave.html')

@login_required
def reports(request):
    return render(request, 'dashboard/reports.html')
    

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
    'employee': employee,
  }
  
  return render(request, 'setting.html', context)

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
def employee_dashboard(request):
    """Employee dashboard view - fetches data from employee tables"""
    from datetime import timedelta
    from django.db.models import Q, Sum
    from django.utils import timezone
    
    # Get logged-in user's information
    employee_obj = None
    employee_name = 'Guest User'
    employee_role = 'Employee'
    employee_id = 'N/A'
    
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
            employee_role = employee_obj.designation or 'Employee'
            employee_id = employee_obj.emp_code or 'N/A'
        else:
            employee_name = user_full_name
            employee_role = 'Employee'
    
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
        
        # Get total working days (excluding weekends - simplified)
        total_days = (today - start_of_month).days + 1
        working_days = sum(1 for i in range(total_days) if (start_of_month + timedelta(days=i)).weekday() < 5)
        
        # Get present days
        present_days = Attendance.objects.filter(
            user=request.user,
            date__gte=start_of_month,
            date__lte=today,
            check_in_time__isnull=False
        ).count()
        
        if working_days > 0:
            attendance_percentage = round((present_days / working_days) * 100, 1)
    
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
    
    context = {
        'employee_name': employee_name,
        'employee_role': employee_role,
        'employee_id': employee_id,
        'current_date': current_date,
        'current_time': current_time,
        'attendance_status': attendance_status,
        'active_projects': active_projects_count,
        'tasks_completed': tasks_completed_total,
        'hours_worked': round(hours_worked, 1),
        'attendance_percentage': attendance_percentage,
        'projects': projects,  # For dashboard projects table
        'recent_tasks': recent_tasks[:4],  # Top 4 recent tasks
        'today_schedule': today_schedule,
        'notifications': notifications[:3],  # Top 3 notifications
        'notification_count': notification_count,
        'weekly_performance': weekly_performance_json,  # JSON string for JavaScript
    }
    return render(request, 'employee/dashboard.html', context)

@login_required
def employee_projects(request):
    """Employee projects view - fetches data from myapp_clientonboarding table"""
    from datetime import timedelta
    
    # Get logged-in user's name to match with assigned_engineer
    user_name = None
    if request.user.is_authenticated:
        user_name = request.user.get_full_name() or request.user.username or ''
    
    # Fetch only required fields from ClientOnboarding for fast indexing
    # Match with assigned_engineer field
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
            'description': onboarding.project_description or 'No description available.'
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
def employee_in_out(request):
    """Employee check in/out view"""
    # Get logged-in user's name
    if request.user.is_authenticated:
        employee_name = request.user.get_full_name() or request.user.username
    else:
        employee_name = 'Guest User'
    
    # Check today's attendance status
    today = timezone.now().date()
    today_attendance = Attendance.objects.filter(
        user=request.user if request.user.is_authenticated else None,
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
    context = {
        'employee': {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@sujataassociates.com',
            'phone': '+1 (555) 123-4567',
            'department': 'Information Technology',
            'position': 'Software Developer',
            'employee_id': 'EMP001',
            'username': 'john.doe',
            'bio': 'Experienced software developer with 5+ years in web development and mobile applications.',
            'avatar': 'https://via.placeholder.com/150'
        },
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
    """Employee project detail view"""
    # Mock project data - in real app, fetch from database
    projects = {
        1: {
            'id': 1,
            'name': 'CRM System Development',
            'type': 'Web Application',
            'progress': 75,
            'due_date': '2024-12-15',
            'status': 'In Progress',
            'tasks_total': 12,
            'tasks_completed': 9,
            'tasks_pending': 3,
            'priority': 'High',
            'description': 'A comprehensive Customer Relationship Management system for managing leads, accounts, and projects.',
            'team_members': ['John Doe', 'Sarah Johnson', 'Mike Wilson'],
            'client': 'ABC Corporation',
            'budget': '$50,000',
            'start_date': '2024-10-01'
        },
        2: {
            'id': 2,
            'name': 'Mobile App UI/UX',
            'type': 'Mobile Application',
            'progress': 45,
            'due_date': '2025-01-20',
            'status': 'Pending',
            'tasks_total': 8,
            'tasks_completed': 3,
            'tasks_pending': 5,
            'priority': 'Medium',
            'description': 'Design and develop a modern mobile application with intuitive user interface and experience.',
            'team_members': ['John Doe', 'Lisa Chen'],
            'client': 'XYZ Tech',
            'budget': '$30,000',
            'start_date': '2024-11-15'
        }
    }
    
    project = projects.get(project_id)
    if not project:
        return redirect('employee_projects')
    
    context = {
        'project': project,
        'tasks': [
            {'id': 1, 'title': 'Database Design', 'status': 'Completed', 'assignee': 'John Doe', 'due_date': '2024-10-15'},
            {'id': 2, 'title': 'API Development', 'status': 'Completed', 'assignee': 'Sarah Johnson', 'due_date': '2024-10-20'},
            {'id': 3, 'title': 'Frontend Development', 'status': 'In Progress', 'assignee': 'Mike Wilson', 'due_date': '2024-12-10'},
            {'id': 4, 'title': 'Testing', 'status': 'Pending', 'assignee': 'John Doe', 'due_date': '2024-12-12'},
        ]
    }
    return render(request, 'employee/project_detail.html', context)

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
    
    # Format currency helper
    def format_currency(value):
        if value is None:
            return '0.00'
        if isinstance(value, Decimal):
            return f"{value:,.2f}"
        try:
            return f"{float(value):,.2f}"
        except:
            return str(value) if value else '0.00'
    
    # Get account last 4 digits helper
    def get_account_last4(account_number):
        if account_number and len(str(account_number)) >= 4:
            return str(account_number)[-4:]
        return 'N/A'
    
    # Build payroll data from matched employee or use defaults
    if employee_obj:
        # Calculate monthly salary from CTC or basic
        monthly_salary = None
        if employee_obj.ctc:
            monthly_salary = employee_obj.ctc / Decimal('12')
        elif employee_obj.basic:
            monthly_salary = employee_obj.basic
        
        # Payroll Information Section
        payroll_info = {
            'employee_id': employee_obj.emp_code or 'N/A',
            'pay_frequency': employee_obj.pay_cycle or 'Monthly',
            'pay_method': 'Direct Deposit' if employee_obj.bank_name and employee_obj.account_number else 'N/A',
            'bank_account_last4': get_account_last4(employee_obj.account_number) if employee_obj.account_number else 'N/A',
            'tax_filing_status': 'Single',  # Default, can be enhanced later
            'exemptions': 1,  # Default, can be enhanced later
        }
        
        # Calculate current salary (monthly basic + HRA + allowances)
        current_salary = Decimal('0')
        if employee_obj.basic:
            current_salary += employee_obj.basic
        if employee_obj.hra:
            current_salary += employee_obj.hra
        if employee_obj.allowances:
            current_salary += employee_obj.allowances
        
        # Use CTC if available, otherwise calculated salary
        if employee_obj.ctc:
            current_salary = employee_obj.ctc / Decimal('12')
        
        # For demo purposes, set some calculated values
        # In real scenario, these would come from a payroll transactions table
        context = {
            'current_salary': format_currency(current_salary),
            'last_payment': format_currency(current_salary * Decimal('0.96')),  # Approximate after deductions
            'last_payment_date': 'Dec 01, 2024',  # Would come from last payroll record
            'ytd_earnings': format_currency(current_salary * Decimal('12') * Decimal('0.9')),  # Approximate YTD
            'next_payment_date': 'Dec 15, 2024',  # Would be calculated from pay_cycle
            'current_period': 'Dec 01 - Dec 15, 2024',
            'regular_hours': 80,
            'regular_pay': format_currency(current_salary * Decimal('0.8')) if current_salary else '0.00',
            'overtime_hours': 8,
            'overtime_pay': format_currency(current_salary * Decimal('0.1')) if current_salary else '0.00',
            'bonus': format_currency(employee_obj.variable) if employee_obj.variable else '0.00',
            'commission': '0.00',
            'total_earnings': format_currency(current_salary),
            'federal_tax': format_currency(current_salary * Decimal('0.15')) if current_salary else '0.00',
            'state_tax': format_currency(current_salary * Decimal('0.05')) if current_salary else '0.00',
            'social_security': format_currency(current_salary * Decimal('0.062')) if current_salary else '0.00',
            'medicare': format_currency(current_salary * Decimal('0.0145')) if current_salary else '0.00',
            'health_insurance': '200.00',
            'retirement_contribution': format_currency(current_salary * Decimal('0.05')) if current_salary else '0.00',
            'total_deductions': format_currency(employee_obj.deductions) if employee_obj.deductions else format_currency(current_salary * Decimal('0.35')) if current_salary else '0.00',
            'net_pay': format_currency(current_salary - (employee_obj.deductions if employee_obj.deductions else current_salary * Decimal('0.35'))) if current_salary else '0.00',
            # Payroll Information Section - from Employee table
            'employee_id': payroll_info['employee_id'],
            'pay_frequency': payroll_info['pay_frequency'],
            'pay_method': payroll_info['pay_method'],
            'bank_account_last4': payroll_info['bank_account_last4'],
            'tax_filing_status': payroll_info['tax_filing_status'],
            'exemptions': payroll_info['exemptions'],
            'pay_history': [
                {
                    'id': 1,
                    'period': 'Nov 15 - Nov 30, 2024',
                    'gross_pay': format_currency(current_salary * Decimal('0.96')),
                    'deductions': format_currency(current_salary * Decimal('0.35')),
                    'net_pay': format_currency(current_salary * Decimal('0.61')),
                    'status': 'Paid',
                    'regular_pay': format_currency(current_salary * Decimal('0.8')),
                    'overtime_pay': format_currency(current_salary * Decimal('0.1')),
                    'bonus': format_currency(employee_obj.variable) if employee_obj.variable else '0.00',
                    'federal_tax': format_currency(current_salary * Decimal('0.15')),
                    'state_tax': format_currency(current_salary * Decimal('0.05')),
                    'social_security': format_currency(current_salary * Decimal('0.062')),
                    'medicare': format_currency(current_salary * Decimal('0.0145')),
                    'health_insurance': '200.00',
                    'retirement_contribution': format_currency(current_salary * Decimal('0.05'))
                },
                {
                    'id': 2,
                    'period': 'Nov 01 - Nov 15, 2024',
                    'gross_pay': format_currency(current_salary * Decimal('0.96')),
                    'deductions': format_currency(current_salary * Decimal('0.35')),
                    'net_pay': format_currency(current_salary * Decimal('0.61')),
                    'status': 'Paid',
                    'regular_pay': format_currency(current_salary * Decimal('0.8')),
                    'overtime_pay': format_currency(current_salary * Decimal('0.1')),
                    'bonus': '0.00',
                    'federal_tax': format_currency(current_salary * Decimal('0.15')),
                    'state_tax': format_currency(current_salary * Decimal('0.05')),
                    'social_security': format_currency(current_salary * Decimal('0.062')),
                    'medicare': format_currency(current_salary * Decimal('0.0145')),
                    'health_insurance': '200.00',
                    'retirement_contribution': format_currency(current_salary * Decimal('0.05'))
                }
            ] if current_salary else []
        }
    else:
        # No match found - use defaults with N/A
        context = {
            'current_salary': 'N/A',
            'last_payment': 'N/A',
            'last_payment_date': 'N/A',
            'ytd_earnings': 'N/A',
            'next_payment_date': 'N/A',
            'current_period': 'N/A',
            'regular_hours': 'N/A',
            'regular_pay': 'N/A',
            'overtime_hours': 'N/A',
            'overtime_pay': 'N/A',
            'bonus': 'N/A',
            'commission': 'N/A',
            'total_earnings': 'N/A',
            'federal_tax': 'N/A',
            'state_tax': 'N/A',
            'social_security': 'N/A',
            'medicare': 'N/A',
            'health_insurance': 'N/A',
            'retirement_contribution': 'N/A',
            'total_deductions': 'N/A',
            'net_pay': 'N/A',
            'employee_id': 'N/A',
            'pay_frequency': 'N/A',
            'pay_method': 'N/A',
            'bank_account_last4': 'N/A',
            'tax_filing_status': 'N/A',
            'exemptions': 'N/A',
            'pay_history': []
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
        for emp in employees_to_show:
            # Count unread messages
            unread_count = EmployeeMessage.objects.filter(
                receiver_id=str(emp.id),
                sender=current_user,
                is_read=False
            ).count()
            
            # Create contact with first name, last name, designation, and department
            contact_data = {
                'id': emp.id,
                'name': emp.get_full_name(),  # Full name (first_name + last_name)
                'first_name': emp.first_name or '',
                'last_name': emp.last_name or '',
                'role': emp.designation or 'Employee',
                'designation': emp.designation or '',
                'department': emp.department or '',
                'email': emp.email or '',
                'unread_count': unread_count
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
            
            # Count unread messages
            unread_count = EmployeeMessage.objects.filter(
                receiver_id=admin_id,
                sender=current_user,
                is_read=False
            ).count()
            
            contacts.append({
                'id': admin_id,
                'name': admin_name,
                'first_name': admin.first_name or '',
                'last_name': admin.last_name or '',
                'role': 'Admin',
                'designation': 'Admin',
                'department': '',
                'email': admin.email if hasattr(admin, 'email') else '',
                'unread_count': unread_count
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
                    'id': emp.id,
                    'name': emp.get_full_name(),
                    'first_name': emp.first_name or '',
                    'last_name': emp.last_name or '',
                    'role': emp.designation or 'Employee',
                    'designation': emp.designation or '',
                    'department': emp.department or '',
                    'email': emp.email or '',
                    'unread_count': 0
                }
                contacts.append(contact_data)
            print(f"DEBUG: Emergency - Added {len(contacts)} contacts")
    
    print("=" * 50)
    
    context = {
        'contacts': contacts,
        'selected_contact_id': selected_contact_id,
        'employee_name': current_user.get_full_name() if current_user.is_authenticated else 'Guest',
        'current_user_employee': current_user_employee,
    }
    
    print(f"DEBUG: Context passed with {len(context.get('contacts', []))} contacts")
    return render(request, 'employee/messages.html', context)

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
                User = get_user_model()
                try:
                    user = User.objects.get(id=user_id)
                except User.DoesNotExist:
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
            # Employee
            try:
                receiver_employee = Employee.objects.get(id=receiver_id, status='active')
                receiver_name = receiver_employee.get_full_name()
            except Employee.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Employee not found'}, status=404)
        
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
                User = get_user_model()
                try:
                    user = User.objects.get(id=user_id)
                except User.DoesNotExist:
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
                current_user_id = str(current_user_employee.id)
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
                        if sender_employee and str(sender_employee.id) == receiver_id:
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
        
        # Get logged-in user's name
        if request.user.is_authenticated:
            employee_name = request.user.get_full_name() or request.user.username
            user = request.user
        else:
            employee_name = request.POST.get('employee_name', 'Guest User')
            user = None
        
        today = timezone.now().date()
        
        # Get or create today's attendance record
        attendance, created = Attendance.objects.get_or_create(
            user=user,
            date=today,
            defaults={
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
        
        # Get logged-in user's name
        if request.user.is_authenticated:
            employee_name = request.user.get_full_name() or request.user.username
            user = request.user
        else:
            employee_name = request.POST.get('employee_name', 'Guest User')
            user = None
        
        today = timezone.now().date()
        
        # Get today's attendance record
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
        
        # Filter by user
        if request.user.is_authenticated:
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
    
    context = {
        'quotes': quotes,
        'onboardings': onboardings,
    }
    
    return render(request, 'employee/quotes.html', context)


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
            'duration_display': f"{onboard.project_duration} {onboard.duration_unit}",
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


