"""
API URL patterns for registrations app (Squad integration).
"""
from django.urls import path
from . import views

urlpatterns = [
    path('registrations/initialize-payment/', views.initialize_payment, name='initialize_payment'),
    path('registrations/verify/', views.verify_payment, name='verify_payment'),
    path('squad/webhook/', views.squad_webhook, name='squad_webhook'),
]
