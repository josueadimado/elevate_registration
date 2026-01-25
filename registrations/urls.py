"""
URL patterns for the registrations app (frontend views).
"""
from django.urls import path
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('success/', views.success, name='success'),
    path('check-status/', views.check_status, name='check_status'),
    path('pay-registration-fee/<uuid:registration_id>/', views.pay_registration_fee, name='pay_registration_fee'),
    path('pay-course-fee/<uuid:registration_id>/', views.pay_course_fee, name='pay_course_fee'),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain'), name='robots'),
]
