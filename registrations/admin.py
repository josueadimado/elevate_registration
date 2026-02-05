"""
Django admin configuration for registrations app.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
import csv
from django.http import HttpResponse
from .models import (
    Registration, Transaction, PaymentActivity, Cohort, Dimension, 
    PricingConfig, ProgramSettings
)


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    """
    Admin interface for managing registrations.
    Includes filtering, search, and CSV export functionality.
    """
    list_display = [
        'full_name', 'email', 'phone', 'age', 'group', 'cohort',
        'dimension', 'enrollment_type', 'amount', 'status', 'created_at'
    ]
    list_filter = [
        'status', 'cohort', 'group', 'dimension', 'enrollment_type', 'created_at'
    ]
    search_fields = ['full_name', 'email', 'phone', 'paystack_reference']
    readonly_fields = ['id', 'created_at', 'updated_at', 'paystack_reference']
    fieldsets = (
        ('Student Information', {
            'fields': ('full_name', 'email', 'phone', 'country', 'age')
        }),
        ('Program Selection', {
            'fields': ('group', 'cohort', 'dimension', 'enrollment_type')
        }),
        ('Guardian Information', {
            'fields': ('guardian_name', 'guardian_phone'),
            'classes': ('collapse',)
        }),
        ('Payment Information', {
            'fields': ('amount', 'currency', 'status', 'paystack_reference')
        }),
        ('Additional Information', {
            'fields': ('referral_source', 'id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['export_as_csv']
    
    def export_as_csv(self, request, queryset):
        """
        Export selected registrations as CSV.
        """
        meta = self.model._meta
        field_names = [
            'full_name', 'email', 'phone', 'country', 'age',
            'group', 'cohort', 'dimension', 'enrollment_type',
            'guardian_name', 'guardian_phone', 'amount', 'status',
            'paystack_reference', 'created_at'
        ]
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename={meta}.csv'
        writer = csv.writer(response)
        
        writer.writerow(field_names)
        for obj in queryset:
            row = [getattr(obj, field) for field in field_names]
            writer.writerow(row)
        
        return response
    
    export_as_csv.short_description = "Export selected registrations as CSV"


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """
    Admin interface for viewing successful transactions.
    """
    list_display = ['reference', 'registration', 'amount', 'currency', 'channel', 'paid_at', 'created_at']
    list_filter = ['currency', 'channel', 'created_at']
    search_fields = ['reference', 'registration__full_name', 'registration__email']
    readonly_fields = ['id', 'created_at', 'raw_payload']
    
    fieldsets = (
        ('Transaction Details', {
            'fields': ('registration', 'reference', 'amount', 'currency', 'channel', 'paid_at')
        }),
        ('Raw Data', {
            'fields': ('raw_payload', 'id', 'created_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PaymentActivity)
class PaymentActivityAdmin(admin.ModelAdmin):
    """
    Admin interface for viewing all payment activity (initiated, success, failed).
    """
    list_display = ['created_at', 'reference', 'status', 'registration', 'payment_type', 'amount', 'gateway']
    list_filter = ['status', 'payment_type', 'gateway', 'created_at']
    search_fields = ['reference', 'registration__full_name', 'registration__email', 'message']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'


@admin.register(Cohort)
class CohortAdmin(admin.ModelAdmin):
    """
    Admin interface for managing cohorts.
    """
    list_display = ['name', 'code', 'is_new_intake', 'is_active', 'start_date', 'end_date']
    list_filter = ['is_active', 'is_new_intake', 'created_at']
    search_fields = ['name', 'code', 'description']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'description')
        }),
        ('Status', {
            'fields': ('is_active', 'is_new_intake')
        }),
        ('Dates', {
            'fields': ('start_date', 'end_date')
        }),
    )


@admin.register(Dimension)
class DimensionAdmin(admin.ModelAdmin):
    """
    Admin interface for managing dimensions.
    """
    list_display = ['code', 'name', 'is_active', 'display_order']
    list_filter = ['is_active', 'created_at']
    search_fields = ['code', 'name', 'description']
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'name', 'description')
        }),
        ('Display', {
            'fields': ('is_active', 'display_order')
        }),
    )


@admin.register(PricingConfig)
class PricingConfigAdmin(admin.ModelAdmin):
    """
    Admin interface for managing pricing.
    """
    list_display = ['enrollment_type', 'registration_fee', 'course_fee', 'total_amount', 'currency', 'is_active']
    list_filter = ['is_active', 'currency']
    
    fieldsets = (
        ('Pricing Information', {
            'fields': ('enrollment_type', 'registration_fee', 'course_fee', 'currency', 'is_active')
        }),
    )
    
    def total_amount(self, obj):
        return f"${obj.total_amount}"
    total_amount.short_description = 'Total Amount'


@admin.register(ProgramSettings)
class ProgramSettingsAdmin(admin.ModelAdmin):
    """
    Admin interface for program settings.
    """
    fieldsets = (
        ('Site Information', {
            'fields': ('site_name', 'site_tagline')
        }),
        ('Age Groups', {
            'fields': (
                ('group1_min_age', 'group1_max_age'),
                ('group2_min_age', 'group2_max_age'),
                'guardian_required_age'
            )
        }),
        ('Maintenance', {
            'fields': ('maintenance_mode', 'maintenance_message')
        }),
    )
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
