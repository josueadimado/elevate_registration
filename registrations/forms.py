"""
Django forms for registration.
"""
from django import forms
from .models import Registration, Cohort, Dimension, PricingConfig, ProgramSettings

# Complete alphabetically sorted country list
COUNTRIES = [
    ('', 'Select Country'),
    ('Afghanistan', 'Afghanistan'),
    ('Albania', 'Albania'),
    ('Algeria', 'Algeria'),
    ('Andorra', 'Andorra'),
    ('Angola', 'Angola'),
    ('Antigua and Barbuda', 'Antigua and Barbuda'),
    ('Argentina', 'Argentina'),
    ('Armenia', 'Armenia'),
    ('Australia', 'Australia'),
    ('Austria', 'Austria'),
    ('Azerbaijan', 'Azerbaijan'),
    ('Bahamas', 'Bahamas'),
    ('Bahrain', 'Bahrain'),
    ('Bangladesh', 'Bangladesh'),
    ('Barbados', 'Barbados'),
    ('Belarus', 'Belarus'),
    ('Belgium', 'Belgium'),
    ('Belize', 'Belize'),
    ('Benin', 'Benin'),
    ('Bhutan', 'Bhutan'),
    ('Bolivia', 'Bolivia'),
    ('Bosnia and Herzegovina', 'Bosnia and Herzegovina'),
    ('Botswana', 'Botswana'),
    ('Brazil', 'Brazil'),
    ('Brunei', 'Brunei'),
    ('Bulgaria', 'Bulgaria'),
    ('Burkina Faso', 'Burkina Faso'),
    ('Burundi', 'Burundi'),
    ('Cambodia', 'Cambodia'),
    ('Cameroon', 'Cameroon'),
    ('Canada', 'Canada'),
    ('Cape Verde', 'Cape Verde'),
    ('Central African Republic', 'Central African Republic'),
    ('Chad', 'Chad'),
    ('Chile', 'Chile'),
    ('China', 'China'),
    ('Colombia', 'Colombia'),
    ('Comoros', 'Comoros'),
    ('Congo', 'Congo'),
    ('Costa Rica', 'Costa Rica'),
    ('Croatia', 'Croatia'),
    ('Cuba', 'Cuba'),
    ('Cyprus', 'Cyprus'),
    ('Czech Republic', 'Czech Republic'),
    ('Denmark', 'Denmark'),
    ('Djibouti', 'Djibouti'),
    ('Dominica', 'Dominica'),
    ('Dominican Republic', 'Dominican Republic'),
    ('Ecuador', 'Ecuador'),
    ('Egypt', 'Egypt'),
    ('El Salvador', 'El Salvador'),
    ('Equatorial Guinea', 'Equatorial Guinea'),
    ('Eritrea', 'Eritrea'),
    ('Estonia', 'Estonia'),
    ('Eswatini', 'Eswatini'),
    ('Ethiopia', 'Ethiopia'),
    ('Fiji', 'Fiji'),
    ('Finland', 'Finland'),
    ('France', 'France'),
    ('Gabon', 'Gabon'),
    ('Gambia', 'Gambia'),
    ('Georgia', 'Georgia'),
    ('Germany', 'Germany'),
    ('Ghana', 'Ghana'),
    ('Greece', 'Greece'),
    ('Grenada', 'Grenada'),
    ('Guatemala', 'Guatemala'),
    ('Guinea', 'Guinea'),
    ('Guinea-Bissau', 'Guinea-Bissau'),
    ('Guyana', 'Guyana'),
    ('Haiti', 'Haiti'),
    ('Honduras', 'Honduras'),
    ('Hungary', 'Hungary'),
    ('Iceland', 'Iceland'),
    ('India', 'India'),
    ('Indonesia', 'Indonesia'),
    ('Iran', 'Iran'),
    ('Iraq', 'Iraq'),
    ('Ireland', 'Ireland'),
    ('Israel', 'Israel'),
    ('Italy', 'Italy'),
    ('Ivory Coast', 'Ivory Coast'),
    ('Jamaica', 'Jamaica'),
    ('Japan', 'Japan'),
    ('Jordan', 'Jordan'),
    ('Kazakhstan', 'Kazakhstan'),
    ('Kenya', 'Kenya'),
    ('Kiribati', 'Kiribati'),
    ('Kosovo', 'Kosovo'),
    ('Kuwait', 'Kuwait'),
    ('Kyrgyzstan', 'Kyrgyzstan'),
    ('Laos', 'Laos'),
    ('Latvia', 'Latvia'),
    ('Lebanon', 'Lebanon'),
    ('Lesotho', 'Lesotho'),
    ('Liberia', 'Liberia'),
    ('Libya', 'Libya'),
    ('Liechtenstein', 'Liechtenstein'),
    ('Lithuania', 'Lithuania'),
    ('Luxembourg', 'Luxembourg'),
    ('Madagascar', 'Madagascar'),
    ('Malawi', 'Malawi'),
    ('Malaysia', 'Malaysia'),
    ('Maldives', 'Maldives'),
    ('Mali', 'Mali'),
    ('Malta', 'Malta'),
    ('Marshall Islands', 'Marshall Islands'),
    ('Mauritania', 'Mauritania'),
    ('Mauritius', 'Mauritius'),
    ('Mexico', 'Mexico'),
    ('Micronesia', 'Micronesia'),
    ('Moldova', 'Moldova'),
    ('Monaco', 'Monaco'),
    ('Mongolia', 'Mongolia'),
    ('Montenegro', 'Montenegro'),
    ('Morocco', 'Morocco'),
    ('Mozambique', 'Mozambique'),
    ('Myanmar', 'Myanmar'),
    ('Namibia', 'Namibia'),
    ('Nauru', 'Nauru'),
    ('Nepal', 'Nepal'),
    ('Netherlands', 'Netherlands'),
    ('New Zealand', 'New Zealand'),
    ('Nicaragua', 'Nicaragua'),
    ('Niger', 'Niger'),
    ('Nigeria', 'Nigeria'),
    ('North Korea', 'North Korea'),
    ('North Macedonia', 'North Macedonia'),
    ('Norway', 'Norway'),
    ('Oman', 'Oman'),
    ('Pakistan', 'Pakistan'),
    ('Palau', 'Palau'),
    ('Palestine', 'Palestine'),
    ('Panama', 'Panama'),
    ('Papua New Guinea', 'Papua New Guinea'),
    ('Paraguay', 'Paraguay'),
    ('Peru', 'Peru'),
    ('Philippines', 'Philippines'),
    ('Poland', 'Poland'),
    ('Portugal', 'Portugal'),
    ('Qatar', 'Qatar'),
    ('Romania', 'Romania'),
    ('Russia', 'Russia'),
    ('Rwanda', 'Rwanda'),
    ('Saint Kitts and Nevis', 'Saint Kitts and Nevis'),
    ('Saint Lucia', 'Saint Lucia'),
    ('Saint Vincent and the Grenadines', 'Saint Vincent and the Grenadines'),
    ('Samoa', 'Samoa'),
    ('San Marino', 'San Marino'),
    ('Sao Tome and Principe', 'Sao Tome and Principe'),
    ('Saudi Arabia', 'Saudi Arabia'),
    ('Senegal', 'Senegal'),
    ('Serbia', 'Serbia'),
    ('Seychelles', 'Seychelles'),
    ('Sierra Leone', 'Sierra Leone'),
    ('Singapore', 'Singapore'),
    ('Slovakia', 'Slovakia'),
    ('Slovenia', 'Slovenia'),
    ('Solomon Islands', 'Solomon Islands'),
    ('Somalia', 'Somalia'),
    ('South Africa', 'South Africa'),
    ('South Korea', 'South Korea'),
    ('South Sudan', 'South Sudan'),
    ('Spain', 'Spain'),
    ('Sri Lanka', 'Sri Lanka'),
    ('Sudan', 'Sudan'),
    ('Suriname', 'Suriname'),
    ('Sweden', 'Sweden'),
    ('Switzerland', 'Switzerland'),
    ('Syria', 'Syria'),
    ('Taiwan', 'Taiwan'),
    ('Tajikistan', 'Tajikistan'),
    ('Tanzania', 'Tanzania'),
    ('Thailand', 'Thailand'),
    ('Timor-Leste', 'Timor-Leste'),
    ('Togo', 'Togo'),
    ('Tonga', 'Tonga'),
    ('Trinidad and Tobago', 'Trinidad and Tobago'),
    ('Tunisia', 'Tunisia'),
    ('Turkey', 'Turkey'),
    ('Turkmenistan', 'Turkmenistan'),
    ('Tuvalu', 'Tuvalu'),
    ('Uganda', 'Uganda'),
    ('Ukraine', 'Ukraine'),
    ('United Arab Emirates', 'United Arab Emirates'),
    ('United Kingdom', 'United Kingdom'),
    ('United States', 'United States'),
    ('Uruguay', 'Uruguay'),
    ('Uzbekistan', 'Uzbekistan'),
    ('Vanuatu', 'Vanuatu'),
    ('Vatican City', 'Vatican City'),
    ('Venezuela', 'Venezuela'),
    ('Vietnam', 'Vietnam'),
    ('Yemen', 'Yemen'),
    ('Zambia', 'Zambia'),
    ('Zimbabwe', 'Zimbabwe'),
]


class RegistrationForm(forms.ModelForm):
    """
    Form for ASPIR program registration.
    Guardian fields are required for all registrations.
    """
    
    # Honeypot field for spam protection (hidden from users)
    website = forms.CharField(required=False, widget=forms.HiddenInput(), label='')
    
    class Meta:
        model = Registration
        fields = [
            'full_name', 'email', 'phone', 'country', 'age',
            'group', 'cohort', 'dimension', 'enrollment_type',
            'guardian_name', 'guardian_phone', 'referral_source',
            'website'  # honeypot
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. John Doe'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. john@example.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. +233 20 956 9399',
                'inputmode': 'tel',
                'autocomplete': 'tel'
            }),
            'country': forms.Select(attrs={
                'class': 'form-input',
                'style': 'cursor: pointer'
            }, choices=COUNTRIES),
            'age': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. 18',
                'min': '10',
                'max': '22'
            }),
            'group': forms.Select(attrs={
                'class': 'form-input',
                'style': 'cursor: pointer'
            }),
            'cohort': forms.Select(attrs={
                'class': 'form-input',
                'style': 'cursor: pointer'
            }),
            'dimension': forms.HiddenInput(attrs={'id': 'id_dimension'}),
            'enrollment_type': forms.HiddenInput(attrs={'id': 'id_enrollment_type'}),
            'guardian_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Guardian Name'
            }),
            'guardian_phone': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. +233 20 956 9399',
                'inputmode': 'tel',
                'autocomplete': 'tel'
            }),
            'referral_source': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Optional'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make guardian fields required for all registrations
        self.fields['guardian_name'].required = True
        self.fields['guardian_phone'].required = True
        self.fields['referral_source'].required = False
        
        # Set querysets for ForeignKey fields
        self.fields['cohort'].queryset = Cohort.objects.filter(is_active=True)
        
        # Dimension and enrollment_type are auto-assigned based on cohort
        # They are hidden fields that will be set in clean() method
        self.fields['cohort'].required = True
        self.fields['dimension'].required = False  # Will be auto-assigned in clean()
        self.fields['dimension'].widget = forms.HiddenInput()
        self.fields['enrollment_type'].required = False  # Will be auto-assigned in clean()
        self.fields['enrollment_type'].widget = forms.HiddenInput()
    
    def clean(self):
        """
        Custom validation:
        1. Check honeypot field (spam protection)
        2. Require guardian fields if age < 16
        3. Auto-calculate amount based on enrollment type
        """
        cleaned_data = super().clean()
        
        # Spam protection: honeypot field should be empty
        website = cleaned_data.get('website')
        if website:
            raise forms.ValidationError("Spam detected.")
        
        # Guardian fields are now required for all registrations
        guardian_name = cleaned_data.get('guardian_name')
        guardian_phone = cleaned_data.get('guardian_phone')
        
        if not guardian_name:
            self.add_error('guardian_name', 'Guardian name is required.')
        if not guardian_phone:
            self.add_error('guardian_phone', 'Guardian phone is required.')
        
        # Auto-assign dimension and enrollment_type based on cohort
        cohort = cleaned_data.get('cohort')
        if not cohort:
            self.add_error('cohort', 'Please select a cohort.')
            return cleaned_data
        
        if cohort:
            # Get cohort code (C1 or C2)
            cohort_code = cohort.code.upper()
            
            # Auto-assign dimension based on cohort
            # Cohort 1 (C1) → Spiritual Growth (S)
            # Cohort 2 (C2) → Academic Excellence (A)
            if cohort_code == 'C1' or '1' in cohort_code:
                dimension_code = 'S'
                enrollment_type = 'RETURNING'
            elif cohort_code == 'C2' or '2' in cohort_code:
                dimension_code = 'A'
                enrollment_type = 'NEW'
            else:
                # Fallback: try to determine from cohort name
                cohort_name_lower = cohort.name.lower()
                if 'cohort 1' in cohort_name_lower or '1' in cohort_name_lower:
                    dimension_code = 'S'
                    enrollment_type = 'RETURNING'
                elif 'cohort 2' in cohort_name_lower or '2' in cohort_name_lower:
                    dimension_code = 'A'
                    enrollment_type = 'NEW'
                else:
                    self.add_error('cohort', 'Unable to determine dimension and enrollment type for this cohort.')
                    return cleaned_data
            
            # Set dimension
            try:
                dimension = Dimension.objects.get(code=dimension_code, is_active=True)
                cleaned_data['dimension'] = dimension
                cleaned_data['dimension_code'] = dimension_code
            except Dimension.DoesNotExist:
                self.add_error('cohort', f'Dimension with code {dimension_code} not found.')
                return cleaned_data
            
            # Set enrollment_type
            cleaned_data['enrollment_type'] = enrollment_type
            
            # Auto-calculate amount from PricingConfig
            try:
                pricing_config = PricingConfig.objects.get(enrollment_type=enrollment_type, is_active=True)
                cleaned_data['amount'] = pricing_config.total_amount
            except PricingConfig.DoesNotExist:
                self.add_error('cohort', f'Pricing configuration not found for enrollment type {enrollment_type}.')
            
            # Store cohort code for backward compatibility
            cleaned_data['cohort_code'] = cohort.code
        else:
            self.add_error('cohort', 'Cohort selection is required.')
        
        return cleaned_data
    
    def clean_age(self):
        """Validate age based on ProgramSettings."""
        age = self.cleaned_data.get('age')
        if age:
            settings = ProgramSettings.load()
            min_age = min(settings.group1_min_age, settings.group2_min_age)
            max_age = max(settings.group1_max_age, settings.group2_max_age)
            if age < min_age or age > max_age:
                raise forms.ValidationError(f'Age must be between {min_age} and {max_age} years.')
        return age
