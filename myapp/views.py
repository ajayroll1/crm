from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, date
from .models import Lead, LeaveRequest, Document
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

def quotes(request):
  return render(request, 'dashboard/quotes.html')





def accounts(request):
  return render(request, 'accounnts/accounts.html')
## Kanban removed


def leads_import_export(request):
  export_fields = ['name','email','phone','company','owner','source','priority','stage','use_case','next_action','due_date','due_time','city','country','industry','tags']
  return render(request, 'leads_section/leads_import_export.html', { 'export_fields': export_fields })


def employees(request):
  return render(request, 'human_resource/employee.html')


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
  # UI-only projects dashboard (localStorage demo)
  return render(request, "project_managemnet'/project.html")

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
    context = {
        'employee_name': 'John Doe',
        'current_date': '2024-12-10',
        'current_time': '09:30 AM',
        'is_checked_in': False,
        'check_in_time': None,
        'check_out_time': None,
        'hours_worked_today': '0h 0m',
        'hours_worked_week': 32.5,
        'attendance_percentage': 95,
        'recent_checkins': [
            {
                'date': '2024-12-09',
                'day': 'Monday',
                'check_in': '9:15 AM',
                'check_out': '6:30 PM',
                'hours': '8h 15m',
                'status': 'On time',
                'location': 'Office',
                'work_type': 'Regular'
            },
            {
                'date': '2024-12-08',
                'day': 'Sunday',
                'check_in': '10:00 AM',
                'check_out': '4:00 PM',
                'hours': '6h 0m',
                'status': 'Weekend',
                'location': 'Remote',
                'work_type': 'Overtime'
            },
            {
                'date': '2024-12-07',
                'day': 'Saturday',
                'check_in': '9:00 AM',
                'check_out': '5:30 PM',
                'hours': '8h 30m',
                'status': 'On time',
                'location': 'Office',
                'work_type': 'Regular'
            },
            {
                'date': '2024-12-06',
                'day': 'Friday',
                'check_in': '9:10 AM',
                'check_out': '6:00 PM',
                'hours': '8h 50m',
                'status': 'On time',
                'location': 'Client Site',
                'work_type': 'Regular'
            }
        ],
        'todays_schedule': [
            {'time': '9:00 AM - 9:30 AM', 'event': 'Team Standup', 'location': 'Conference Room A', 'type': 'meeting'},
            {'time': '11:00 AM - 12:00 PM', 'event': 'Code Review Session', 'location': 'Online Meeting', 'type': 'review'},
            {'time': '2:00 PM - 3:00 PM', 'event': 'Client Presentation', 'location': 'Main Conference Room', 'type': 'presentation'},
            {'time': '4:00 PM - 5:00 PM', 'event': 'Project Planning', 'location': 'Team Room', 'type': 'planning'}
        ],
        'weekly_stats': {
            'days_present': 5,
            'total_hours': 32.5,
            'late_arrivals': 2,
            'overtime_days': 1,
            'weekly_target': 40,
            'target_percentage': 81
        }
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


@require_POST
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

        if not (leave_type and start_date and end_date and reason):
            return JsonResponse({'success': False, 'error': 'Missing required fields.'}, status=400)

        # Parse dates and compute days if missing
        from datetime import datetime
        sd = datetime.strptime(start_date, '%Y-%m-%d').date()
        ed = datetime.strptime(end_date, '%Y-%m-%d').date()
        total_days = int(days) if str(days).isdigit() else (ed - sd).days + 1
        if total_days <= 0:
            return JsonResponse({'success': False, 'error': 'Invalid date range.'}, status=400)

        full_name = ''
        if request.user.is_authenticated:
            full_name = request.user.get_full_name() or request.user.username or ''

        lr = LeaveRequest.objects.create(
            user=request.user if request.user.is_authenticated else None,
            applicant_name=full_name or None,
            leave_type=leave_type,
            start_date=sd,
            end_date=ed,
            days=total_days,
            reason=reason,
            contact=contact or None,
            handover=handover or None,
            status='Pending'
        )
        return JsonResponse({'success': True, 'id': lr.id})
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

def employee_quotes(request):
    """Employee portal quotation management"""
    from .models import Quote, QuoteItem, ClientOnboarding
    from decimal import Decimal
    import json
    
    # Handle Quote Creation
    if request.method == 'POST' and 'quote_submit' in request.POST:
        try:
            # Generate quote number if not provided
            quote_no = request.POST.get('quote_no', '').strip()
            if not quote_no:
                # Auto-generate quote number
                last_quote = Quote.objects.order_by('-id').first()
                if last_quote and last_quote.quote_number.startswith('Q-'):
                    try:
                        last_num = int(last_quote.quote_number.split('-')[1])
                        quote_no = f'Q-{last_num + 1:04d}'
                    except:
                        quote_no = f'Q-{Quote.objects.count() + 1:04d}'
                else:
                    quote_no = 'Q-1001'
            
            # Create Quote
            quote = Quote.objects.create(
                quote_number=quote_no,
                client_name=request.POST.get('client'),
                company=request.POST.get('company', ''),
                email=request.POST.get('email', ''),
                phone=request.POST.get('phone', ''),
                owner=request.POST.get('owner'),
                status=request.POST.get('status', 'Sent'),
                currency=request.POST.get('currency', 'INR').split()[0],  # Extract 'INR' from 'INR (₹)'
                valid_until=request.POST.get('valid_until'),
                notes=request.POST.get('notes', ''),
                terms=request.POST.get('terms', ''),
                subtotal=Decimal(request.POST.get('subtotal', '0')),
                discount=Decimal(request.POST.get('discount', '0')),
                total=Decimal(request.POST.get('total', '0'))
            )
            
            # Handle PDF upload
            if 'project_pdf' in request.FILES:
                quote.project_pdf = request.FILES['project_pdf']
                quote.save()
            
            # Create Quote Items
            items_data = request.POST.get('items_data', '[]')
            items = json.loads(items_data)
            for item in items:
                QuoteItem.objects.create(
                    quote=quote,
                    description=item.get('description', ''),
                    quantity=int(item.get('quantity', 1)),
                    unit_price=Decimal(item.get('unit_price', '0')),
                    gst_percent=Decimal(item.get('gst_percent', '0')),
                    amount=Decimal(item.get('amount', '0'))
                )
            
            messages.success(request, f'Quote {quote_no} created successfully!')
            return redirect('employee_quotes')
        except Exception as e:
            messages.error(request, f'Error creating quote: {str(e)}')
    
    # Handle Onboarding Creation
    if request.method == 'POST' and 'onboard_submit' in request.POST:
        try:
            ClientOnboarding.objects.create(
                client_name=request.POST.get('client_name'),
                company_name=request.POST.get('company_name', ''),
                client_email=request.POST.get('client_email', ''),
                client_phone=request.POST.get('client_phone', ''),
                project_name=request.POST.get('project_name'),
                project_description=request.POST.get('project_description', ''),
                project_duration=int(request.POST.get('project_duration')),
                duration_unit=request.POST.get('duration_unit', 'months'),
                project_cost=Decimal(request.POST.get('project_cost')),
                assigned_engineer=request.POST.get('assigned_engineer'),
                start_date=request.POST.get('start_date') or None,
                status=request.POST.get('status', 'active')
            )
            
            messages.success(request, f'Client {request.POST.get("client_name")} onboarded successfully!')
            return redirect('employee_quotes')
        except Exception as e:
            messages.error(request, f'Error onboarding client: {str(e)}')
    
    # Fetch all quotes and onboardings
    quotes = Quote.objects.all().prefetch_related('items')
    onboardings = ClientOnboarding.objects.all()
    
    context = {
        'quotes': quotes,
        'onboardings': onboardings,
    }
    
    return render(request, 'employee/quotes.html', context)