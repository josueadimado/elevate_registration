# Merge parallel branches: program/cohort pricing (0010) and participant_id help text (0011).

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('registrations', '0010_program_cohort_pricing'),
        ('registrations', '0011_alter_registration_participant_id'),
    ]

    operations = []
