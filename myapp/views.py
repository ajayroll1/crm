from django.shortcuts import render
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