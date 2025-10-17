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
  

  


  # // this is for footer urls 

 ]

