"""
Database models for the ASPIR Mentorship Program registrations.
"""
import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class Registration(models.Model):
    """
    Stores registration information for ASPIR program participants.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending Payment'),
        ('PAID', 'Paid'),
        ('FAILED', 'Payment Failed'),
    ]
    
    GROUP_CHOICES = [
        ('G1', 'Group 1 (10-15 years)'),
        ('G2', 'Group 2 (16-22 years)'),
    ]
    
    COHORT_CHOICES = [
        ('C1', 'Cohort 1 (Returning)'),
        ('C2', 'Cohort 2 (New Intake)'),
    ]
    
    DIMENSION_CHOICES = [
        ('A', 'Academic Excellence (Redefined)'),
        ('S', 'Spiritual Growth'),
        ('P', 'Purpose Discovery'),
        ('I', 'Impactful Leadership'),
        ('R', 'Refined Communication'),
    ]
    
    ENROLLMENT_TYPE_CHOICES = [
        ('NEW', 'New Learner'),
        ('RETURNING', 'Returning Learner'),
    ]
    
    # Primary identifier
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Student information
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    age = models.IntegerField(validators=[MinValueValidator(10), MaxValueValidator(22)])
    
    # Program selection (now using ForeignKeys to admin-configured models)
    program = models.ForeignKey('Program', on_delete=models.PROTECT, null=True, blank=True, related_name='registrations')
    group = models.CharField(max_length=2, choices=GROUP_CHOICES)
    cohort = models.ForeignKey('Cohort', on_delete=models.PROTECT, null=True, blank=True, related_name='registrations')
    dimension = models.ForeignKey('Dimension', on_delete=models.PROTECT, null=True, blank=True, related_name='registrations')
    enrollment_type = models.CharField(max_length=10, choices=ENROLLMENT_TYPE_CHOICES)
    is_elevate_tribe_member = models.BooleanField(
        default=False,
        help_text="Elevate Tribe member — may use tribe member pricing when configured on cohort"
    )
    
    # Legacy fields for backward compatibility
    cohort_code = models.CharField(max_length=2, blank=True, null=True)
    dimension_code = models.CharField(max_length=1, blank=True, null=True)
    
    # Guardian information (optional, required if age < 16)
    guardian_name = models.CharField(max_length=200, blank=True, null=True)
    guardian_phone = models.CharField(max_length=20, blank=True, null=True)
    
    # Optional fields
    referral_source = models.CharField(max_length=200, blank=True, null=True, 
                                     help_text="How did you hear about us?")
    
    # Payment information
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # Total amount (registration_fee + course_fee)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    squad_reference = models.CharField(max_length=100, unique=True, blank=True, null=True)
    paystack_reference = models.CharField(max_length=100, unique=True, blank=True, null=True)  # Legacy field for backward compatibility
    
    # Partial payment tracking
    registration_fee_paid = models.BooleanField(default=False, help_text="Whether registration fee has been paid")
    course_fee_paid = models.BooleanField(default=False, help_text="Whether course fee has been paid")
    registration_fee_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Registration fee amount")
    course_fee_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Course fee amount")
    
    # Participant ID: ET/ASPIR/{cohort_code}/{sequence} e.g. ET/ASPIR/C1/003 (3-digit sequence: 001, 002, ...)
    participant_id = models.CharField(
        max_length=50, unique=True, blank=True, null=True,
        help_text="Generated ID e.g. ET/ASPIR/C1/003 (cohort + 3-digit sequence)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Registration'
        verbose_name_plural = 'Registrations'
    
    def __str__(self):
        dimension_name = self.dimension.name if self.dimension else (self.dimension_code or 'N/A')
        return f"{self.full_name} - {dimension_name} - {self.status}"
    
    def calculate_amount(self):
        """Calculate total from cohort pricing if set, else enrollment-type defaults."""
        if self.cohort_id:
            _, _, total = self.cohort.get_fees(is_tribe_member=self.is_elevate_tribe_member)
            if total:
                return float(total)
        if self.enrollment_type == 'NEW':
            return 150.00
        elif self.enrollment_type == 'RETURNING':
            return 120.00
        return 0.00
    
    def get_registration_fee(self):
        """Get registration fee amount from PricingConfig"""
        try:
            from .models import PricingConfig
            pricing = PricingConfig.objects.get(enrollment_type=self.enrollment_type, is_active=True)
            return pricing.registration_fee
        except PricingConfig.DoesNotExist:
            # Fallback to default values
            return 50.00 if self.enrollment_type == 'NEW' else 20.00
    
    def get_course_fee(self):
        """Get course fee amount from PricingConfig"""
        try:
            from .models import PricingConfig
            pricing = PricingConfig.objects.get(enrollment_type=self.enrollment_type, is_active=True)
            return pricing.course_fee
        except PricingConfig.DoesNotExist:
            # Fallback to default value
            return 100.00
    
    def get_remaining_balance(self):
        """Calculate remaining balance to be paid"""
        remaining = 0
        if not self.registration_fee_paid:
            remaining += self.get_registration_fee()
        if not self.course_fee_paid:
            remaining += self.get_course_fee()
        return remaining
    
    def is_fully_paid(self):
        """Check if both registration and course fees are paid"""
        return self.registration_fee_paid and self.course_fee_paid


class Transaction(models.Model):
    """
    Stores successful payment details (from Squad webhook).
    """
    id = models.BigAutoField(primary_key=True)
    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='transactions')
    reference = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    paid_at = models.DateTimeField(null=True, blank=True)
    channel = models.CharField(max_length=50, blank=True, null=True)
    raw_payload = models.JSONField(default=dict, help_text="Raw webhook payload")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'
    
    def __str__(self):
        return f"Transaction {self.reference} - {self.amount} {self.currency}"


class PaymentActivity(models.Model):
    """
    Logs every payment-related event: initiated (checkout created), success, failed.
    Use this to see all activity; Transaction only stores successful payments.
    """
    STATUS_CHOICES = [
        ('initiated', 'Initiated'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]
    PAYMENT_TYPE_CHOICES = [
        ('registration_fee', 'Registration Fee'),
        ('course_fee', 'Course Fee'),
        ('full_payment', 'Full Payment'),
    ]
    id = models.BigAutoField(primary_key=True)
    registration = models.ForeignKey(
        Registration, on_delete=models.CASCADE, related_name='payment_activities'
    )
    reference = models.CharField(max_length=100, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, db_index=True)
    payment_type = models.CharField(
        max_length=20, choices=PAYMENT_TYPE_CHOICES, default='registration_fee'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    gateway = models.CharField(max_length=20, default='squad')
    message = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Payment Activity'
        verbose_name_plural = 'Payment Activities'
    
    def __str__(self):
        return f"{self.reference} – {self.get_status_display()} – ${self.amount}"


class Program(models.Model):
    """
    A learning program (e.g. ASPIRE, Data Analytics). Each program has its own cohorts and pricing.
    """
    name = models.CharField(max_length=150, help_text="e.g. ASPIRE, Data Analytics")
    slug = models.SlugField(max_length=50, unique=True, help_text="Short code e.g. aspire, data-analytics")
    description = models.TextField(blank=True, null=True)
    id_prefix = models.CharField(
        max_length=20, default='ASPIR',
        help_text="Used in participant IDs e.g. ET/ASPIR/C1/003"
    )
    is_active = models.BooleanField(default=True, help_text="Only active programs appear on the registration form")
    display_order = models.IntegerField(default=0)
    show_tribe_member_pricing = models.BooleanField(
        default=False,
        help_text="Show Elevate Tribe member pricing option on registration (ASPIRE only)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = 'Program'
        verbose_name_plural = 'Programs'

    def __str__(self):
        return self.name


class Cohort(models.Model):
    """
    Admin-configurable cohort within a program (e.g. ASPIRE Cohort 1 – Purpose Discovery).
    """
    program = models.ForeignKey(
        'Program', on_delete=models.PROTECT, null=True, blank=True,
        related_name='cohorts', help_text="Which program this cohort belongs to"
    )
    name = models.CharField(max_length=100, help_text="e.g. Cohort 1")
    code = models.CharField(max_length=10, help_text="e.g. C1, C2, C3 (unique within program)")
    track_name = models.CharField(
        max_length=150, blank=True, default='',
        help_text="Learning track e.g. Purpose Discovery, Spiritual Excellence"
    )
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True, help_text="Only active cohorts appear in registration")
    is_new_intake = models.BooleanField(default=False, help_text="Is this a new intake cohort?")
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    display_order = models.IntegerField(default=0, help_text="Order within the program on registration form")
    # Per-cohort pricing (shown on front-end registration)
    registration_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Registration fee for this cohort (USD unless currency set)"
    )
    course_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Course fee for this cohort"
    )
    currency = models.CharField(max_length=3, default='USD', choices=[('USD', 'USD'), ('NGN', 'NGN')])
    tribe_member_registration_fee = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Optional: registration fee for Elevate Tribe members"
    )
    tribe_member_course_fee = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Optional: course fee for Elevate Tribe members"
    )
    linked_dimension = models.ForeignKey(
        'Dimension', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='cohorts', help_text="Optional dimension linked to this cohort"
    )
    default_enrollment_type = models.CharField(
        max_length=10, blank=True, default='',
        choices=[('', '—'), ('NEW', 'New Learner'), ('RETURNING', 'Returning Learner')],
        help_text="Optional default enrollment type for this cohort"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = 'Cohort'
        verbose_name_plural = 'Cohorts'
        unique_together = [['program', 'code']]

    def __str__(self):
        label = self.display_label
        return f"{label} ({'Active' if self.is_active else 'Inactive'})"

    @property
    def display_label(self):
        """Label for registration dropdown e.g. Cohort 1 – Purpose Discovery."""
        if self.track_name:
            return f"{self.name} – {self.track_name}"
        return self.name

    @property
    def total_amount(self):
        return (self.registration_fee or 0) + (self.course_fee or 0)

    def get_fees(self, is_tribe_member=False):
        """Return (registration_fee, course_fee, total) for this cohort."""
        if is_tribe_member and self.program and self.program.show_tribe_member_pricing:
            reg = self.tribe_member_registration_fee if self.tribe_member_registration_fee is not None else self.registration_fee
            course = self.tribe_member_course_fee if self.tribe_member_course_fee is not None else self.course_fee
        else:
            reg = self.registration_fee or 0
            course = self.course_fee or 0
        return reg, course, reg + course


class Dimension(models.Model):
    """
    Admin-configurable ASPIR dimensions.
    """
    code = models.CharField(max_length=1, unique=True, help_text="Single letter code: A, S, P, I, R")
    name = models.CharField(max_length=200, help_text="Full name of the dimension")
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True, help_text="Only active dimensions appear in registration")
    display_order = models.IntegerField(default=0, help_text="Order in which dimensions appear")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['display_order', 'code']
        verbose_name = 'Dimension'
        verbose_name_plural = 'Dimensions'
    
    def __str__(self):
        return f"{self.code}: {self.name}"


class PricingConfig(models.Model):
    """
    Admin-configurable pricing for the program.
    """
    enrollment_type = models.CharField(
        max_length=10,
        choices=[('NEW', 'New Learner'), ('RETURNING', 'Returning Learner')],
        unique=True
    )
    registration_fee = models.DecimalField(max_digits=10, decimal_places=2, help_text="Registration fee amount")
    course_fee = models.DecimalField(max_digits=10, decimal_places=2, help_text="Course fee amount")
    CURRENCY_CHOICES = [
        ('USD', 'USD - US Dollar'),
        ('NGN', 'NGN - Nigerian Naira'),
    ]
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default='USD',
        help_text="Currency for this pricing configuration"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Pricing Configuration'
        verbose_name_plural = 'Pricing Configurations'
    
    def __str__(self):
        return f"{self.get_enrollment_type_display()} - ${self.total_amount}"
    
    @property
    def total_amount(self):
        """Calculate total amount (registration + course fee)"""
        return self.registration_fee + self.course_fee


class ProgramSettings(models.Model):
    """
    General program settings managed by admin.
    """
    site_name = models.CharField(max_length=200, default="ASPIRE Mentorship Program")
    site_tagline = models.CharField(max_length=300, default="A step-by-step journey to Purpose, Excellence & Leadership")
    group1_min_age = models.IntegerField(default=10, help_text="Minimum age for Group 1")
    group1_max_age = models.IntegerField(default=15, help_text="Maximum age for Group 1")
    group2_min_age = models.IntegerField(default=16, help_text="Minimum age for Group 2")
    group2_max_age = models.IntegerField(default=22, help_text="Maximum age for Group 2")
    guardian_required_age = models.IntegerField(default=16, help_text="Age below which guardian info is required")
    maintenance_mode = models.BooleanField(default=False, help_text="Enable maintenance mode")
    maintenance_message = models.TextField(blank=True, null=True)
    moodle_default_password = models.CharField(
        max_length=128, blank=True, null=True,
        default='TribeMentee@1#',
        help_text="Default password for Moodle user export; users should be forced to change on first login."
    )
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Program Settings'
        verbose_name_plural = 'Program Settings'
    
    def save(self, *args, **kwargs):
        """Ensure only one settings instance exists"""
        self.pk = 1
        super().save(*args, **kwargs)
    
    @classmethod
    def load(cls):
        """Load or create the settings instance"""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj
    
    def __str__(self):
        return "Program Settings"
