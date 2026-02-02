"""
API URL patterns for registrations app (Squad and Paystack).
"""
from django.urls import path
from . import views

urlpatterns = [
    path('check-email/', views.check_email, name='check_email'),
    path('registrations/initialize-payment/', views.initialize_payment, name='initialize_payment'),
    path('registrations/verify/', views.verify_payment, name='verify_payment'),
    path('squad/webhook/', views.squad_webhook, name='squad_webhook'),
    path('paystack/webhook/', views.paystack_webhook, name='paystack_webhook'),
]
