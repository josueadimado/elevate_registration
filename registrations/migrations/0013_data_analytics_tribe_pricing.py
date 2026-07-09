# Enable Elevate Tribe member pricing for Data Analytics program.

from decimal import Decimal
from django.db import migrations


def enable_data_analytics_tribe_pricing(apps, schema_editor):
    Program = apps.get_model('registrations', 'Program')
    Cohort = apps.get_model('registrations', 'Cohort')

    da = Program.objects.filter(slug='data-analytics').first()
    if not da:
        return

    da.show_tribe_member_pricing = True
    da.save(update_fields=['show_tribe_member_pricing'])

    for cohort in Cohort.objects.filter(program=da):
        if cohort.tribe_member_registration_fee is None:
            cohort.tribe_member_registration_fee = Decimal('50')
        if cohort.tribe_member_course_fee is None:
            cohort.tribe_member_course_fee = Decimal('100')
        cohort.save(update_fields=['tribe_member_registration_fee', 'tribe_member_course_fee'])


class Migration(migrations.Migration):

    dependencies = [
        ('registrations', '0012_program_cohort_pricing'),
    ]

    operations = [
        migrations.RunPython(enable_data_analytics_tribe_pricing, migrations.RunPython.noop),
    ]
