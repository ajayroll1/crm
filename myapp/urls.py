from django.urls import path
from .import views 

urlpatterns =[
  path('', views.home,name='home'),
  path('about/',views.about,name='about'),
  path('services/',views.services,name='services'),
  path('projects/',views.projects,name='projects'),
  path('careers/',views.careers,name='careers'),
  path('contact/',views.contact,name='contact'),
  path('quote/',views.quote,name='quote'),
  path('dashboard/',views.dashboard,name='dashboard'),
  path('leads/',views.leads,name='leads'),
  path('leads/<int:lead_id>/',views.lead_detail,name='lead_detail'),
  path('leads/<int:lead_id>/edit/',views.lead_edit,name='lead_edit'),
  path('leads/<int:lead_id>/delete/',views.lead_delete,name='lead_delete'),
  path('leads/<int:lead_id>/get-data/',views.lead_get_data,name='lead_get_data'),
  path('leads/filter/',views.lead_filter,name='lead_filter'),
  path('leads/export/',views.lead_export,name='lead_export'),
  path('leads/import/',views.lead_import,name='lead_import'),
  path('leads/import-export/',views.leads_import_export,name='leads_import_export'),
  path('quotes/',views.quotes,name='quotes'),
  path('accounts/',views.accounts,name='accounts'),
  path('employees/',views.employees,name='employees'),
  path('attendance/',views.attendance,name='attendance'),
  path('in-out/',views.in_out,name='in_out'),
  path('leave/',views.leave,name='leave'),
  path('reports/',views.reports,name='reports'),
  path('settings/',views.settings_view,name='settings'),
  path('project-management/',views.project_management,name='project_management'),
  
  # Employee Portal URLs
  path('employee/',views.employee_dashboard,name='employee_dashboard'),
  path('employee/dashboard/',views.employee_dashboard,name='employee_dashboard'),
  path('employee/projects/',views.employee_projects,name='employee_projects'),
  path('employee/projects/new/',views.employee_new_project,name='employee_new_project'),
  path('employee/projects/<int:project_id>/',views.employee_project_detail,name='employee_project_detail'),
  path('employee/projects/<int:project_id>/start/',views.employee_start_project,name='employee_start_project'),
  path('employee/projects/<int:project_id>/continue/',views.employee_continue_project,name='employee_continue_project'),
  path('employee/projects/<int:project_id>/finish/',views.employee_finish_project,name='employee_finish_project'),
  path('employee/in-out/',views.employee_in_out,name='employee_in_out'),
  path('employee/settings/',views.employee_settings,name='employee_settings'),
  path('employee/leave/',views.employee_leave,name='employee_leave'),
  path('employee/leave/apply/',views.employee_leave_apply,name='employee_leave_apply'),
  path('employee/leads/',views.employee_leads,name='employee_leads'),
  path('employee/quotes/',views.employee_quotes,name='employee_quotes'),
  
  # Personal Section URLs
  path('employee/profile/',views.employee_profile,name='employee_profile'),
  path('employee/documents/',views.employee_documents,name='employee_documents'),
  path('employee/documents/upload/',views.employee_documents_upload,name='employee_documents_upload'),
  path('employee/documents/<int:doc_id>/delete/',views.employee_documents_delete,name='employee_documents_delete'),
  path('employee/payroll/',views.employee_payroll,name='employee_payroll'),
  path('employee/achievements/',views.employee_achievements,name='employee_achievements'),
  
  path('leads/<int:lead_id>/assign_engineer/', views.assign_engineer, name='assign_engineer'),

  


  # // this is for footer urls 

 ]

