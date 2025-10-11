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



