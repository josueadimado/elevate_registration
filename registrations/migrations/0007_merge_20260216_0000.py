# No-op migration after 0006_add_participant_id.
# If you had two 0006 migrations (merge conflict), add the other as a second dependency.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('registrations', '0006_add_participant_id'),
    ]

    operations = [
    ]
