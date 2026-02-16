# Merge migration to resolve conflicting 0006 migrations (multiple leaf nodes).
#
# You must have TWO 0006 files (e.g. 0006_add_participant_id and 0006_alter_...).
# Set the second dependency below to the OTHER 0006 filename without .py.
# To see the exact name, run:  ls registrations/migrations/0006*.py

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('registrations', '0006_add_participant_id'),
        ('registrations', '0006_alter_REGISTER_OTHER'),  # TODO: replace with other 0006 name, e.g. 0006_alter_dimension_...
    ]

    operations = [
    ]
