# No-op merge migration (ensures 0008_merge has two parents in graph).

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('registrations', '0006_add_participant_id'),
    ]

    operations = [
    ]
