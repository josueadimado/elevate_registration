"""
Admin forms for editing models in the custom admin panel.
"""
from django import forms
from .models import Registration, Cohort, Dimension, PricingConfig, ProgramSettings
from .forms import COUNTRIES  # Import country list from forms.py


class AdminEditRegistrationForm(forms.ModelForm):
    """
    Form for editing registrations in admin panel.
    """
    class Meta:
        model = Registration
        fields = [
            'full_name', 'email', 'phone', 'country', 'age',
            'group', 'cohort', 'dimension', 'enrollment_type',
            'guardian_name', 'guardian_phone', 'referral_source',
            'amount', 'currency', 'status', 'squad_reference', 'paystack_reference',
            'registration_fee_paid', 'course_fee_paid',
            'registration_fee_amount', 'course_fee_amount',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'admin-form-input',
                'placeholder': 'Full name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'admin-form-input',
                'placeholder': 'Email address'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'admin-form-input',
                'placeholder': 'Phone number'
            }),
            'country': forms.Select(attrs={
                'class': 'admin-form-input',
            }, choices=COUNTRIES),
            'age': forms.NumberInput(attrs={
                'class': 'admin-form-input',
                'min': '10',
                'max': '22'
            }),
            'group': forms.Select(attrs={
                'class': 'admin-form-input',
            }, choices=Registration.GROUP_CHOICES),
            'cohort': forms.Select(attrs={
                'class': 'admin-form-input',
            }),
            'dimension': forms.Select(attrs={
                'class': 'admin-form-input',
            }),
            'enrollment_type': forms.Select(attrs={
                'class': 'admin-form-input',
            }),
            'currency': forms.Select(attrs={
                'class': 'admin-form-input',
            }),
            'status': forms.Select(attrs={
                'class': 'admin-form-input',
            }),
            'guardian_name': forms.TextInput(attrs={
                'class': 'admin-form-input',
                'placeholder': 'Guardian name'
            }),
            'guardian_phone': forms.TextInput(attrs={
                'class': 'admin-form-input',
                'placeholder': 'Guardian phone'
            }),
            'referral_source': forms.TextInput(attrs={
                'class': 'admin-form-input',
                'placeholder': 'How did you hear about us?'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'admin-form-input',
                'step': '0.01'
            }),
            'squad_reference': forms.TextInput(attrs={
                'class': 'admin-form-input',
                'readonly': True
            }),
            'paystack_reference': forms.TextInput(attrs={
                'class': 'admin-form-input',
                'readonly': True
            }),
            'registration_fee_paid': forms.CheckboxInput(attrs={
                'class': 'admin-form-checkbox',
            }),
            'course_fee_paid': forms.CheckboxInput(attrs={
                'class': 'admin-form-checkbox',
            }),
            'registration_fee_amount': forms.NumberInput(attrs={
                'class': 'admin-form-input',
                'step': '0.01',
                'placeholder': 'e.g. 50.00',
            }),
            'course_fee_amount': forms.NumberInput(attrs={
                'class': 'admin-form-input',
                'step': '0.01',
                'placeholder': 'e.g. 100.00',
            }),
        }

    def save(self, commit=True):
        # Keep status in sync with fee checkboxes (for offline payments)
        instance = super().save(commit=False)
        if instance.registration_fee_paid and instance.course_fee_paid:
            instance.status = 'PAID'
        elif instance.registration_fee_paid or instance.course_fee_paid:
            instance.status = 'PENDING'
        if commit:
            instance.save()
            # Auto-generate participant ID when cohort is set and ID is missing (dimension not in ID)
            if instance.cohort and not instance.participant_id:
                from .utils import generate_participant_id
                generate_participant_id(instance)
        return instance

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set querysets for ForeignKey fields
        self.fields['cohort'].queryset = Cohort.objects.all()
        self.fields['dimension'].queryset = Dimension.objects.all()
        # Set choices for select fields
        self.fields['country'].choices = COUNTRIES
        self.fields['group'].choices = Registration.GROUP_CHOICES
        self.fields['enrollment_type'].choices = Registration.ENROLLMENT_TYPE_CHOICES
        self.fields['status'].choices = Registration.STATUS_CHOICES
        self.fields['currency'].choices = [('USD', 'USD'), ('NGN', 'NGN')]
        # Make reference fields readonly
        self.fields['squad_reference'].widget.attrs['readonly'] = True
        self.fields['paystack_reference'].widget.attrs['readonly'] = True


class AdminEditCohortForm(forms.ModelForm):
    """
    Form for editing cohorts in admin panel.
    """
    class Meta:
        model = Cohort
        fields = ['name', 'code', 'description', 'is_active', 'is_new_intake', 'start_date', 'end_date']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'admin-form-input',
                'placeholder': 'e.g., Cohort 1'
            }),
            'code': forms.TextInput(attrs={
                'class': 'admin-form-input',
                'placeholder': 'e.g., C1'
            }),
            'description': forms.Textarea(attrs={
                'class': 'admin-form-input',
                'rows': 4,
                'placeholder': 'Cohort description'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'admin-checkbox'
            }),
            'is_new_intake': forms.CheckboxInput(attrs={
                'class': 'admin-checkbox'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'admin-form-input',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'admin-form-input',
                'type': 'date'
            }),
        }


class AdminEditDimensionForm(forms.ModelForm):
    """
    Form for editing dimensions in admin panel.
    """
    class Meta:
        model = Dimension
        fields = ['code', 'name', 'description', 'is_active', 'display_order']
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'admin-form-input',
                'placeholder': 'e.g., A',
                'maxlength': 1
            }),
            'name': forms.TextInput(attrs={
                'class': 'admin-form-input',
                'placeholder': 'e.g., Academic Excellence'
            }),
            'description': forms.Textarea(attrs={
                'class': 'admin-form-input',
                'rows': 4,
                'placeholder': 'Dimension description'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'admin-checkbox'
            }),
            'display_order': forms.NumberInput(attrs={
                'class': 'admin-form-input',
                'min': 0
            }),
        }


class AdminEditPricingForm(forms.ModelForm):
    """
    Form for editing pricing configurations in admin panel.
    """
    class Meta:
        model = PricingConfig
        fields = ['enrollment_type', 'registration_fee', 'course_fee', 'currency', 'is_active']
        widgets = {
            'enrollment_type': forms.Select(attrs={
                'class': 'admin-form-input',
            }),
            'registration_fee': forms.NumberInput(attrs={
                'class': 'admin-form-input',
                'step': '0.01',
                'min': '0'
            }),
            'course_fee': forms.NumberInput(attrs={
                'class': 'admin-form-input',
                'step': '0.01',
                'min': '0'
            }),
            'currency': forms.Select(attrs={
                'class': 'admin-form-input',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'admin-checkbox'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set choices for select fields
        self.fields['enrollment_type'].choices = PricingConfig._meta.get_field('enrollment_type').choices
        
        # Explicitly set currency field as Select widget with choices
        from django import forms
        self.fields['currency'].widget = forms.Select(attrs={
            'class': 'admin-form-input',
        })
        # Use model choices if available, otherwise use default
        currency_field = PricingConfig._meta.get_field('currency')
        if hasattr(currency_field, 'choices') and currency_field.choices:
            self.fields['currency'].choices = currency_field.choices
        else:
            self.fields['currency'].choices = [
                ('USD', 'USD - US Dollar'),
                ('NGN', 'NGN - Nigerian Naira'),
            ]
        
        # Set default currency if this is a new form (no instance)
        if not self.instance.pk:
            self.fields['currency'].initial = 'USD'


class AdminEditProgramSettingsForm(forms.ModelForm):
    """
    Form for editing program settings in admin panel.
    """
    class Meta:
        model = ProgramSettings
        fields = [
            'site_name', 'site_tagline',
            'group1_min_age', 'group1_max_age',
            'group2_min_age', 'group2_max_age',
            'guardian_required_age',
            'maintenance_mode', 'maintenance_message',
            'moodle_default_password'
        ]
        widgets = {
            'site_name': forms.TextInput(attrs={
                'class': 'admin-form-input',
            }),
            'site_tagline': forms.TextInput(attrs={
                'class': 'admin-form-input',
            }),
            'group1_min_age': forms.NumberInput(attrs={
                'class': 'admin-form-input',
                'min': 0
            }),
            'group1_max_age': forms.NumberInput(attrs={
                'class': 'admin-form-input',
                'min': 0
            }),
            'group2_min_age': forms.NumberInput(attrs={
                'class': 'admin-form-input',
                'min': 0
            }),
            'group2_max_age': forms.NumberInput(attrs={
                'class': 'admin-form-input',
                'min': 0
            }),
            'guardian_required_age': forms.NumberInput(attrs={
                'class': 'admin-form-input',
                'min': 0
            }),
            'maintenance_mode': forms.CheckboxInput(attrs={
                'class': 'admin-checkbox'
            }),
            'maintenance_message': forms.Textarea(attrs={
                'class': 'admin-form-input',
                'rows': 4
            }),
            'moodle_default_password': forms.TextInput(attrs={
                'class': 'admin-form-input',
                'placeholder': 'TribeMentee@1#',
                'autocomplete': 'off'
            }),
        }
