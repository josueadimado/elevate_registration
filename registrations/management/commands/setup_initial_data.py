"""
Management command to set up initial program data.
Run this after migrations: python manage.py setup_initial_data
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from registrations.models import (
    Cohort, Dimension, PricingConfig, ProgramSettings
)


class Command(BaseCommand):
    help = 'Sets up initial program data (cohorts, dimensions, pricing, settings)'

    def handle(self, *args, **options):
        self.stdout.write('Setting up initial program data...')
        
        try:
            with transaction.atomic():
                # Create Program Settings using the load() method
                settings, created = ProgramSettings.objects.get_or_create(
                    pk=1,
                    defaults={
                        'site_name': "ASPIR Mentorship Program",
                        'site_tagline': "A step-by-step journey to Purpose, Excellence & Leadership",
                        'group1_min_age': 10,
                        'group1_max_age': 15,
                        'group2_min_age': 16,
                        'group2_max_age': 22,
                        'guardian_required_age': 16
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS('✓ Created Program Settings'))
                else:
                    self.stdout.write(self.style.WARNING('Program Settings already exists'))
                
                # Create Cohorts
                cohorts_data = [
                    {'name': 'Cohort 1', 'code': 'C1', 'is_new_intake': False, 'is_active': True},
                    {'name': 'Cohort 2', 'code': 'C2', 'is_new_intake': True, 'is_active': True},
                ]
                
                for cohort_data in cohorts_data:
                    cohort, created = Cohort.objects.get_or_create(
                        code=cohort_data['code'],
                        defaults=cohort_data
                    )
                    if created:
                        self.stdout.write(self.style.SUCCESS(f'✓ Created Cohort: {cohort.name}'))
                    else:
                        self.stdout.write(self.style.WARNING(f'Cohort {cohort.name} already exists'))
                
                # Create Dimensions
                dimensions_data = [
                    {'code': 'A', 'name': 'Academic Excellence (Redefined)', 'display_order': 1, 'is_active': True},
                    {'code': 'S', 'name': 'Spiritual Growth', 'display_order': 2, 'is_active': True},
                    {'code': 'P', 'name': 'Purpose Discovery', 'display_order': 3, 'is_active': True},
                    {'code': 'I', 'name': 'Impactful Leadership', 'display_order': 4, 'is_active': True},
                    {'code': 'R', 'name': 'Refined Communication', 'display_order': 5, 'is_active': True},
                ]
                
                for dim_data in dimensions_data:
                    dimension, created = Dimension.objects.get_or_create(
                        code=dim_data['code'],
                        defaults=dim_data
                    )
                    if created:
                        self.stdout.write(self.style.SUCCESS(f'✓ Created Dimension: {dimension.code} - {dimension.name}'))
                    else:
                        self.stdout.write(self.style.WARNING(f'Dimension {dimension.code} already exists'))
                
                # Create Pricing Configurations
                pricing_data = [
                    {
                        'enrollment_type': 'NEW',
                        'registration_fee': 50.00,
                        'course_fee': 100.00,
                        'currency': 'USD',
                        'is_active': True
                    },
                    {
                        'enrollment_type': 'RETURNING',
                        'registration_fee': 20.00,
                        'course_fee': 100.00,
                        'currency': 'USD',
                        'is_active': True
                    },
                ]
                
                for price_data in pricing_data:
                    pricing, created = PricingConfig.objects.get_or_create(
                        enrollment_type=price_data['enrollment_type'],
                        defaults=price_data
                    )
                    if created:
                        self.stdout.write(self.style.SUCCESS(f'✓ Created Pricing: {pricing.get_enrollment_type_display()} - ${pricing.total_amount}'))
                    else:
                        self.stdout.write(self.style.WARNING(f'Pricing for {pricing.get_enrollment_type_display()} already exists'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error setting up initial data: {str(e)}'))
            raise
        
        self.stdout.write(self.style.SUCCESS('\n✓ Initial data setup complete!'))
        self.stdout.write(self.style.SUCCESS('You can now access the admin panel to manage these settings.'))
