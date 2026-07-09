# Server merge migration (PythonAnywhere).

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('registrations', '0009_add_moodle_default_password'),
        ('registrations', '0009_merge_20260216_0418'),
    ]

    operations = []
