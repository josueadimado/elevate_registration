# Server merge migration (PythonAnywhere).

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('registrations', '0008_merge_20260216_0357'),
        ('registrations', '0008_merge_20260216_0001'),
    ]

    operations = []
