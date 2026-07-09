# Server merge migration (PythonAnywhere).

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('registrations', '0007_merge_20260216_0339'),
        ('registrations', '0006_alter_transaction_raw_payload'),
    ]

    operations = []
