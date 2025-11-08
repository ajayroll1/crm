"""Context processors for employee templates"""
from .models import Employee, EmployeeMessage, ClientOnboarding, LeaveRequest
from django.db.models import Q

def employee_sidebar_counts(request):
    """Add sidebar counts and employee information to all employee templates"""
    counts = {
        'unread_messages_count': 0,
        'new_projects_count': 0,
        'pending_leaves_count': 0,
    }
    
    # Employee information defaults
    employee_info = {
        'employee_name': 'Guest User',
        'employee_first_name': 'Guest',
        'employee_initials': 'GU',
        'employee_role': 'Employee',
        'employee_designation': 'Employee',
        'employee_id': 'N/A',
    }
    
    if request.user.is_authenticated:
        try:
            # Get user's full name or username safely
            try:
                user_full_name = request.user.get_full_name() or request.user.username or ''
            except AttributeError:
                # Fallback if get_full_name doesn't exist
                user_full_name = getattr(request.user, 'first_name', '') + ' ' + getattr(request.user, 'last_name', '')
                user_full_name = user_full_name.strip() or request.user.username or ''
            
            # Try to match employee by name first
            name_parts = user_full_name.strip().split(' ', 1)
            first_name = name_parts[0] if name_parts else ''
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            
            employee_obj = None
            
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
                employee_info['employee_name'] = employee_obj.get_full_name()
                employee_info['employee_first_name'] = employee_obj.first_name or ''
                employee_info['employee_initials'] = employee_obj.get_initials() or 'GU'
                employee_info['employee_role'] = employee_obj.designation or 'Employee'
                employee_info['employee_designation'] = employee_obj.designation or 'Employee'
                employee_info['employee_id'] = employee_obj.emp_code or 'N/A'
                user_name = employee_obj.get_full_name()
            else:
                employee_info['employee_name'] = user_full_name
                employee_info['employee_first_name'] = first_name or user_full_name.split()[0] if user_full_name else 'Guest'
                employee_info['employee_initials'] = (employee_info['employee_first_name'][0] + (last_name[0] if last_name else employee_info['employee_first_name'][0])).upper() if employee_info['employee_first_name'] else 'GU'
                user_name = user_full_name
            
            # Unread Messages Count
            if employee_obj:
                receiver_id = employee_obj.emp_code or str(employee_obj.id)
                counts['unread_messages_count'] = EmployeeMessage.objects.filter(
                    receiver_id=receiver_id,
                    is_read=False
                ).count()
            
            # New Projects Count (assigned after last visit)
            if user_name:
                last_visit_timestamp = request.session.get('last_visit_timestamp', None)
                if last_visit_timestamp:
                    from datetime import datetime
                    import time
                    last_visit = datetime.fromtimestamp(last_visit_timestamp)
                    counts['new_projects_count'] = ClientOnboarding.objects.filter(
                        assigned_engineer__iexact=user_name,
                        created_at__gt=last_visit
                    ).count()
                else:
                    # First visit - show all active projects
                    counts['new_projects_count'] = ClientOnboarding.objects.filter(
                        assigned_engineer__iexact=user_name,
                        status='active'
                    ).count()
            
            # Pending Leave Requests Count
            counts['pending_leaves_count'] = LeaveRequest.objects.filter(
                user=request.user,
                status='Pending'
            ).count()
            
            # Update last visit timestamp in session (only if not already set recently)
            if 'last_visit_timestamp' not in request.session:
                import time
                request.session['last_visit_timestamp'] = time.time()
            
        except Exception as e:
            print(f"Error in employee_sidebar_counts: {str(e)}")
    
    # Merge counts and employee info
    return {**counts, **employee_info}

