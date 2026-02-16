"""
URL patterns for custom admin dashboard.
"""
from django.urls import path
from . import admin_views

urlpatterns = [
    path('login/', admin_views.admin_login, name='admin_login'),
    path('logout/', admin_views.admin_logout, name='admin_logout'),
    path('dashboard/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('registrations/', admin_views.admin_registrations, name='admin_registrations'),
    path('registrations/export/', admin_views.export_registrations, name='export_registrations'),
    path('registrations/import/', admin_views.import_registrations, name='admin_import_registrations'),
    path('registrations/template/', admin_views.download_registrations_template, name='download_registrations_template'),
    path('registrations/add/', admin_views.add_registration, name='add_registration'),
    path('registrations/<uuid:registration_id>/', admin_views.view_registration, name='view_registration'),
    path('registrations/<uuid:registration_id>/send-participant-id/', admin_views.send_participant_id_email_view, name='send_participant_id_email'),
    path('registrations/<uuid:registration_id>/edit/', admin_views.edit_registration, name='edit_registration'),
    path('registrations/<uuid:registration_id>/delete/', admin_views.delete_registration, name='delete_registration'),
    path('transactions/', admin_views.admin_transactions, name='admin_transactions'),
    path('payment-activity/', admin_views.admin_payment_activity, name='admin_payment_activity'),
    path('reconcile-payment/', admin_views.admin_reconcile_payment, name='admin_reconcile_payment'),
    path('settings/', admin_views.admin_settings, name='admin_settings'),
    path('settings/cohort/add/', admin_views.add_cohort, name='add_cohort'),
    path('settings/cohort/<int:cohort_id>/edit/', admin_views.edit_cohort, name='edit_cohort'),
    path('settings/cohort/<int:cohort_id>/delete/', admin_views.delete_cohort, name='delete_cohort'),
    path('settings/cohort/<int:cohort_id>/toggle/', admin_views.toggle_cohort, name='toggle_cohort'),
    path('settings/dimension/add/', admin_views.add_dimension, name='add_dimension'),
    path('settings/dimension/<int:dimension_id>/edit/', admin_views.edit_dimension, name='edit_dimension'),
    path('settings/dimension/<int:dimension_id>/delete/', admin_views.delete_dimension, name='delete_dimension'),
    path('settings/dimension/<int:dimension_id>/toggle/', admin_views.toggle_dimension, name='toggle_dimension'),
    path('settings/pricing/add/', admin_views.add_pricing, name='add_pricing'),
    path('settings/pricing/<int:pricing_id>/edit/', admin_views.edit_pricing, name='edit_pricing'),
    path('settings/pricing/<int:pricing_id>/delete/', admin_views.delete_pricing, name='delete_pricing'),
    path('settings/pricing/<int:pricing_id>/toggle/', admin_views.toggle_pricing, name='toggle_pricing'),
    path('settings/program/edit/', admin_views.edit_program_settings, name='edit_program_settings'),
]
