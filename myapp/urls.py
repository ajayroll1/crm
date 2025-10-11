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
  

  


  # // this is for footer urls 

 ]

