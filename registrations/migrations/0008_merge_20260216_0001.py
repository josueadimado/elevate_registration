# Merge migration: resolves two leaf nodes (0007_merge_* and 0007_merge_*).

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('registrations', '0007_merge_20260216_0000'),
        ('registrations', '0007_merge_20260216_0339'),
    ]

    operations = [
    ]
