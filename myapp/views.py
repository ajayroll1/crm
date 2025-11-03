from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, date
from decimal import Decimal
import json
from .models import Lead, LeaveRequest, Document, Attendance, Quote, ClientOnboarding, Employee
from .forms import LeadForm, LeadFilterForm
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

def home(request):
  return render(request,'pages/homepage.html')

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


def dashboard(request):
  return render(request, 'dashboard/dashboard.html')

def dashboard_leaves(request):
    """Dashboard view to manage all leave requests"""
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
    
    context = {
        'leave_requests': page_obj,
        'status_counts': status_counts,
        'search_query': search_query,
        'status_filter': status_filter,
    }
    return render(request, 'dashboard/leaves.html', context)

@require_POST
def leave_status_update(request, leave_id):
    """Update leave request status"""
    try:
        leave = LeaveRequest.objects.get(id=leave_id)
        new_status = request.POST.get('status', '').strip()
        
        if new_status not in ['Pending', 'Approved', 'Rejected', 'Cancelled']:
            return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)
        
        old_status = leave.status
        leave.status = new_status
        leave.save()
        
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






def accounts(request):
  return render(request, 'accounnts/accounts.html')
## Kanban removed


def leads_import_export(request):
  export_fields = ['name','email','phone','company','owner','source','priority','stage','use_case','next_action','due_date','due_time','city','country','industry','tags']
  return render(request, 'leads_section/leads_import_export.html', { 'export_fields': export_fields })


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
            
            # Check if employee with this code exists (for update)
            employee = None
            if emp_code:
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
            for field in ['ctc', 'basic', 'hra', 'allowances', 'deductions', 'variable']:
                value = request.POST.get(field, '').strip()
                if value:
                    try:
                        setattr(employee, field, Decimal(value))
                    except (InvalidOperation, ValueError):
                        pass
            employee.pay_cycle = request.POST.get('pay_cycle', '').strip() or None
            
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
            
            # Leave Balances
            for field in ['annual_leave', 'sick_leave', 'personal_leave', 'maternity_leave', 'paternity_leave', 'emergency_leave']:
                value = request.POST.get(field, '').strip()
                if value and value.isdigit():
                    setattr(employee, field, int(value))
            
            # Status
            employee.status = request.POST.get('status', 'active').strip() or 'active'
            
            employee.save()
            
            messages.success(request, f'Employee "{employee.get_full_name()}" saved successfully!')
            return redirect('employees')
        except Exception as e:
            messages.error(request, f'Error saving employee: {str(e)}')
            print(f"Error saving employee: {str(e)}")
    
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
        }
        return JsonResponse({'success': True, 'employee': data})
    except Employee.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Employee not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@require_POST
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

def reports(request):
    return render(request, 'dashboard/reports.html')
    

def settings_view(request):
  return render(request, 'setting.html')

def in_out(request):
  return render(request, 'human_resource/in_out.html')


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
  
  context = {
    'client_onboarding_list': page_obj,
    'status_counts': status_counts,
    'search_query': search_query,
    'status_filter': status_filter,
  }
  return render(request, "project_managemnet'/project.html", context)

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
    """Employee dashboard view"""
    context = {
        'employee_name': 'John Doe',
        'employee_role': 'Software Developer',
        'employee_id': 'EMP001',
        'current_date': '2024-12-10',
        'current_time': '09:30 AM',
        'attendance_status': 'Present',
        'active_projects': 3,
        'tasks_completed': 12,
        'hours_worked': 32.5,
        'attendance_percentage': 95,
    }
    return render(request, 'employee/dashboard.html', context)

def employee_projects(request):
    """Employee projects view"""
    projects = [
        {
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
            'description': 'A comprehensive Customer Relationship Management system for managing leads, accounts, and projects.'
        },
        {
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
            'description': 'Design and develop a modern mobile application with intuitive user interface and experience.'
        },
        {
            'id': 3,
            'name': 'Database Optimization',
            'type': 'Backend Task',
            'progress': 90,
            'due_date': '2024-12-10',
            'status': 'Almost Done',
            'tasks_total': 6,
            'tasks_completed': 5,
            'tasks_pending': 1,
            'priority': 'High',
            'description': 'Optimize database performance and implement efficient query strategies for better system performance.'
        },
        {
            'id': 4,
            'name': 'Security Audit',
            'type': 'Security Task',
            'progress': 100,
            'due_date': '2024-11-28',
            'status': 'Completed',
            'tasks_total': 10,
            'tasks_completed': 10,
            'tasks_pending': 0,
            'priority': 'High',
            'description': 'Comprehensive security audit and implementation of security best practices across all systems.'
        },
        {
            'id': 5,
            'name': 'Analytics Dashboard',
            'type': 'Data Visualization',
            'progress': 30,
            'due_date': '2025-02-15',
            'status': 'On Hold',
            'tasks_total': 15,
            'tasks_completed': 4,
            'tasks_pending': 11,
            'priority': 'Low',
            'description': 'Create interactive dashboards and reports for business intelligence and data analysis.'
        },
        {
            'id': 6,
            'name': 'Cloud Migration',
            'type': 'Infrastructure',
            'progress': 60,
            'due_date': '2025-03-10',
            'status': 'In Progress',
            'tasks_total': 20,
            'tasks_completed': 12,
            'tasks_pending': 8,
            'priority': 'Medium',
            'description': 'Migrate existing infrastructure to cloud platforms for better scalability and performance.'
        }
    ]
    
    context = {
        'projects': projects,
        'total_projects': len(projects),
        'completed_projects': len([p for p in projects if p['status'] == 'Completed']),
        'in_progress_projects': len([p for p in projects if p['status'] == 'In Progress']),
        'due_this_week': len([p for p in projects if p['due_date'] <= '2024-12-17']),
    }
    return render(request, 'employee/projects.html', context)

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

def employee_leave(request):
    """Employee leave management view"""
    # Load pending requests from DB for current user (or all if not authenticated)
    qs = LeaveRequest.objects.filter(status='Pending')
    if request.user.is_authenticated:
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

    # Leave history: show approved requests (user-scoped)
    hist_qs = LeaveRequest.objects.filter(status='Approved')
    if request.user.is_authenticated:
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
        'employee_name': 'John Doe',
        'employee_id': 'EMP001',
        'leave_balance': {
            'sick_leave': 12,
            'annual_leave': 20,
            'personal_leave': 5,
            'maternity_leave': 90,
            'paternity_leave': 15,
            'emergency_leave': 3
        },
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
        print(f"\n🔍 DEBUG: Received applicantName from form: '{applicant_name}'")
        
        if not applicant_name:
            if request.user.is_authenticated:
                applicant_name = request.user.get_full_name() or request.user.username or ''
                print(f"🔍 DEBUG: Got name from authenticated user: '{applicant_name}'")
            else:
                applicant_name = request.POST.get('applicant_name', '').strip()
                print(f"🔍 DEBUG: Got name from POST (not authenticated): '{applicant_name}'")
        
        # Fallback: ensure we have a name
        if not applicant_name:
            applicant_name = request.POST.get('applicant_name', 'Unknown User').strip()

        print(f"🔍 DEBUG: Final applicant_name to save: '{applicant_name}'")

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
        print(f"\n✅ Leave Request saved to database (myapp_leaverequest):")
        print(f"   ID: {lr.id}")
        print(f"   Applicant Name: '{lr.applicant_name}'")
        print(f"   Leave Type: {lr.leave_type}")
        print(f"   Days: {lr.days}")
        print(f"   Status: {lr.status}")
        
        # Verify it was saved correctly
        saved_lr = LeaveRequest.objects.get(id=lr.id)
        print(f"🔍 VERIFICATION: Saved applicant_name = '{saved_lr.applicant_name}'")
        
        return JsonResponse({'success': True, 'id': lr.id, 'message': f'Leave request saved. Name: {lr.applicant_name}'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

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

def employee_start_project(request, project_id):
    """Start a project"""
    # In real app, update project status in database
    # For now, just redirect back to projects with success message
    return redirect('employee_projects')

def employee_continue_project(request, project_id):
    """Continue working on a project"""
    # In real app, log activity or update project status
    # For now, just redirect back to projects with success message
    return redirect('employee_projects')

def employee_finish_project(request, project_id):
    """Finish a project"""
    # In real app, update project status to completed
    # For now, just redirect back to projects with success message
    return redirect('employee_projects')

def employee_profile(request):
    """Employee profile view"""
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
        }
    }
    return render(request, 'employee/profile.html', context)

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

def employee_payroll(request):
    """Employee payroll view"""
    context = {
        'current_salary': '7,500',
        'last_payment': '7,200',
        'last_payment_date': 'Dec 01, 2024',
        'ytd_earnings': '90,000',
        'next_payment_date': 'Dec 15, 2024',
        'current_period': 'Dec 01 - Dec 15, 2024',
        'regular_hours': 80,
        'regular_pay': '6,000',
        'overtime_hours': 8,
        'overtime_pay': '1,200',
        'bonus': '500',
        'commission': '0',
        'total_earnings': '7,700',
        'federal_tax': '1,200',
        'state_tax': '400',
        'social_security': '477',
        'medicare': '112',
        'health_insurance': '200',
        'retirement_contribution': '385',
        'total_deductions': '2,774',
        'net_pay': '4,926',
        'employee_id': 'EMP001',
        'pay_frequency': 'Bi-weekly',
        'pay_method': 'Direct Deposit',
        'bank_account_last4': '1234',
        'tax_filing_status': 'Single',
        'exemptions': 1,
        'pay_history': [
            {
                'id': 1,
                'period': 'Nov 15 - Nov 30, 2024',
                'gross_pay': '7,200',
                'deductions': '2,650',
                'net_pay': '4,550',
                'status': 'Paid',
                'regular_pay': '6,000',
                'overtime_pay': '1,200',
                'bonus': '0',
                'federal_tax': '1,150',
                'state_tax': '380',
                'social_security': '446',
                'medicare': '104',
                'health_insurance': '200',
                'retirement_contribution': '360'
            },
            {
                'id': 2,
                'period': 'Nov 01 - Nov 15, 2024',
                'gross_pay': '7,000',
                'deductions': '2,580',
                'net_pay': '4,420',
                'status': 'Paid',
                'regular_pay': '6,000',
                'overtime_pay': '1,000',
                'bonus': '0',
                'federal_tax': '1,120',
                'state_tax': '370',
                'social_security': '434',
                'medicare': '101',
                'health_insurance': '200',
                'retirement_contribution': '355'
            }
        ]
    }
    return render(request, 'employee/payroll.html', context)

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


