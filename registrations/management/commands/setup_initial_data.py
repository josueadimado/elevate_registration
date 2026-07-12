"""
Management command to set up initial program data.
Run this after migrations: python manage.py setup_initial_data
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from registrations.models import (
    Program, Cohort, Dimension, PricingConfig, ProgramSettings
)


class Command(BaseCommand):
    help = 'Sets up initial program data (programs, cohorts, dimensions, pricing, settings)'

    def handle(self, *args, **options):
        self.stdout.write('Setting up initial program data...')

        try:
            with transaction.atomic():
                settings, created = ProgramSettings.objects.get_or_create(
                    pk=1,
                    defaults={
                        'site_name': 'ASPIRE Mentorship Program',
                        'site_tagline': 'A step-by-step journey to Purpose, Excellence & Leadership',
                        'group1_min_age': 10,
                        'group1_max_age': 15,
                        'group2_min_age': 16,
                        'group2_max_age': 22,
                        'guardian_required_age': 16,
                    },
                )
                if created:
                    self.stdout.write(self.style.SUCCESS('✓ Created Program Settings'))
                else:
                    self.stdout.write(self.style.WARNING('Program Settings already exists'))

                aspire, _ = Program.objects.get_or_create(
                    slug='aspire',
                    defaults={
                        'name': 'ASPIRE',
                        'id_prefix': 'ASPIR',
                        'description': 'ASPIRE Mentorship Program',
                        'is_active': True,
                        'display_order': 1,
                        'show_tribe_member_pricing': True,
                    },
                )
                data_analytics, _ = Program.objects.get_or_create(
                    slug='data-analytics',
                    defaults={
                        'name': 'Data Analytics',
                        'id_prefix': 'DATA',
                        'description': 'Data Analytics program',
                        'is_active': True,
                        'display_order': 2,
                        'show_tribe_member_pricing': True,
                        'require_full_payment': True,
                    },
                )
                self.stdout.write(self.style.SUCCESS(f'✓ Programs ready: {aspire.name}, {data_analytics.name}'))

                dim_p = Dimension.objects.filter(code='P').first()
                dim_s = Dimension.objects.filter(code='S').first()
                dim_a = Dimension.objects.filter(code='A').first()

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
                        defaults=dim_data,
                    )
                    if created:
                        self.stdout.write(self.style.SUCCESS(f'✓ Created Dimension: {dimension.code}'))
                    if dim_data['code'] == 'P':
                        dim_p = dimension
                    elif dim_data['code'] == 'S':
                        dim_s = dimension
                    elif dim_data['code'] == 'A':
                        dim_a = dimension

                aspire_cohorts = [
                    {
                        'code': 'C1', 'name': 'Cohort 1', 'track_name': 'Purpose Discovery',
                        'registration_fee': Decimal('20'), 'course_fee': Decimal('100'),
                        'default_enrollment_type': 'RETURNING', 'display_order': 1,
                        'linked_dimension': dim_p,
                    },
                    {
                        'code': 'C2', 'name': 'Cohort 2', 'track_name': 'Spiritual Excellence',
                        'registration_fee': Decimal('20'), 'course_fee': Decimal('100'),
                        'default_enrollment_type': 'RETURNING', 'display_order': 2,
                        'linked_dimension': dim_s,
                    },
                    {
                        'code': 'C3', 'name': 'Cohort 3', 'track_name': 'Academic Excellence',
                        'registration_fee': Decimal('50'), 'course_fee': Decimal('100'),
                        'default_enrollment_type': 'NEW', 'display_order': 3,
                        'linked_dimension': dim_a,
                        'tribe_member_registration_fee': Decimal('50'),
                        'tribe_member_course_fee': Decimal('100'),
                    },
                ]
                for data in aspire_cohorts:
                    linked = data.pop('linked_dimension', None)
                    cohort, created = Cohort.objects.get_or_create(
                        program=aspire,
                        code=data['code'],
                        defaults={**data, 'is_active': True, 'currency': 'USD'},
                    )
                    if created:
                        self.stdout.write(self.style.SUCCESS(f'✓ Created Cohort: ASPIRE {cohort.display_label}'))
                    if linked and not cohort.linked_dimension_id:
                        cohort.linked_dimension = linked
                        cohort.save(update_fields=['linked_dimension'])

                da_cohort, created = Cohort.objects.get_or_create(
                    program=data_analytics,
                    code='C1',
                    defaults={
                        'name': 'Cohort 1',
                        'track_name': 'Data Analytics',
                        'registration_fee': Decimal('50'),
                        'course_fee': Decimal('150'),
                        'currency': 'USD',
                        'is_active': True,
                        'display_order': 1,
                        'default_enrollment_type': 'NEW',
                        'tribe_member_registration_fee': Decimal('50'),
                        'tribe_member_course_fee': Decimal('100'),
                    },
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'✓ Created Cohort: Data Analytics {da_cohort.display_label}'))

                pricing_data = [
                    {
                        'enrollment_type': 'NEW',
                        'registration_fee': 50.00,
                        'course_fee': 100.00,
                        'currency': 'USD',
                        'is_active': True,
                    },
                    {
                        'enrollment_type': 'RETURNING',
                        'registration_fee': 20.00,
                        'course_fee': 100.00,
                        'currency': 'USD',
                        'is_active': True,
                    },
                ]
                for price_data in pricing_data:
                    pricing, created = PricingConfig.objects.get_or_create(
                        enrollment_type=price_data['enrollment_type'],
                        defaults=price_data,
                    )
                    if created:
                        self.stdout.write(self.style.SUCCESS(
                            f'✓ Created Pricing: {pricing.get_enrollment_type_display()} - ${pricing.total_amount}'
                        ))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error setting up initial data: {str(e)}'))
            raise

        self.stdout.write(self.style.SUCCESS('\n✓ Initial data setup complete!'))
        self.stdout.write(self.style.SUCCESS('Manage programs and cohorts in Admin → Settings.'))
