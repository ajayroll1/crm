"""Context processors for employee templates"""
from .models import Employee, EmployeeMessage, ClientOnboarding, LeaveRequest
from django.db.models import Q

def employee_sidebar_counts(request):
    """Add sidebar counts to all employee templates"""
    counts = {
        'unread_messages_count': 0,
        'new_projects_count': 0,
        'pending_leaves_count': 0,
    }
    
    if request.user.is_authenticated:
        try:
            # Get employee
            user_email = getattr(request.user, 'email', None)
            employee_obj = None
            
            if user_email:
                employee_obj = Employee.objects.filter(email__iexact=user_email).first()
            
            # Unread Messages Count
            if employee_obj:
                receiver_id = employee_obj.emp_code or str(employee_obj.id)
                counts['unread_messages_count'] = EmployeeMessage.objects.filter(
                    receiver_id=receiver_id,
                    is_read=False
                ).count()
            
            # User name for projects
            user_name = None
            if employee_obj:
                user_name = employee_obj.get_full_name()
            else:
                user_name = request.user.get_full_name() or request.user.username or ''
            
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
    
    return counts

