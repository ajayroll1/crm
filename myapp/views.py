from django.shortcuts import render, redirect
from django.http import HttpResponse

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
  return render(request, 'leads_section/leads.html')

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
        'pending_requests': [
            {
                'id': 1,
                'type': 'Annual Leave',
                'start_date': '2024-12-20',
                'end_date': '2024-12-25',
                'days': 5,
                'reason': 'Family vacation',
                'status': 'Pending',
                'applied_date': '2024-12-05',
                'manager': 'Sarah Johnson'
            },
            {
                'id': 2,
                'type': 'Sick Leave',
                'start_date': '2024-12-12',
                'end_date': '2024-12-12',
                'days': 1,
                'reason': 'Medical appointment',
                'status': 'Approved',
                'applied_date': '2024-12-10',
                'manager': 'Sarah Johnson'
            }
        ],
        'leave_history': [
            {
                'id': 3,
                'type': 'Annual Leave',
                'start_date': '2024-11-15',
                'end_date': '2024-11-17',
                'days': 3,
                'reason': 'Personal work',
                'status': 'Approved',
                'applied_date': '2024-11-10',
                'approved_date': '2024-11-12',
                'manager': 'Sarah Johnson'
            },
            {
                'id': 4,
                'type': 'Sick Leave',
                'start_date': '2024-10-20',
                'end_date': '2024-10-20',
                'days': 1,
                'reason': 'Fever',
                'status': 'Approved',
                'applied_date': '2024-10-20',
                'approved_date': '2024-10-20',
                'manager': 'Sarah Johnson'
            }
        ],
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
    """Employee documents view"""
    documents = [
        {
            'id': 1,
            'name': 'Employee Contract.pdf',
            'type': 'pdf',
            'size': '2.5 MB',
            'description': 'Signed employment contract and terms',
            'upload_date': 'Dec 01, 2024',
            'modified_date': 'Dec 01, 2024',
            'category': 'Contracts',
            'category_color': 'primary'
        },
        {
            'id': 2,
            'name': 'ID Card.jpg',
            'type': 'image',
            'size': '1.2 MB',
            'description': 'Employee identification card',
            'upload_date': 'Nov 28, 2024',
            'modified_date': 'Nov 28, 2024',
            'category': 'Personal',
            'category_color': 'success'
        },
        {
            'id': 3,
            'name': 'Resume.docx',
            'type': 'word',
            'size': '850 KB',
            'description': 'Updated resume and CV',
            'upload_date': 'Nov 25, 2024',
            'modified_date': 'Nov 25, 2024',
            'category': 'Personal',
            'category_color': 'success'
        },
        {
            'id': 4,
            'name': 'Certification.pdf',
            'type': 'pdf',
            'size': '3.1 MB',
            'description': 'AWS Cloud Practitioner Certification',
            'upload_date': 'Nov 20, 2024',
            'modified_date': 'Nov 20, 2024',
            'category': 'Certificates',
            'category_color': 'warning'
        },
        {
            'id': 5,
            'name': 'Performance Review.xlsx',
            'type': 'excel',
            'size': '1.8 MB',
            'description': 'Q3 2024 Performance Review',
            'upload_date': 'Nov 15, 2024',
            'modified_date': 'Nov 15, 2024',
            'category': 'Work',
            'category_color': 'info'
        },
        {
            'id': 6,
            'name': 'Training Certificate.pdf',
            'type': 'pdf',
            'size': '2.2 MB',
            'description': 'Project Management Professional Certificate',
            'upload_date': 'Nov 10, 2024',
            'modified_date': 'Nov 10, 2024',
            'category': 'Certificates',
            'category_color': 'warning'
        }
    ]
    
    context = {
        'documents': documents,
        'pdf_count': len([d for d in documents if d['type'] == 'pdf']),
        'image_count': len([d for d in documents if d['type'] == 'image']),
        'word_count': len([d for d in documents if d['type'] == 'word']),
        'excel_count': len([d for d in documents if d['type'] == 'excel'])
    }
    return render(request, 'employee/documents.html', context)

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