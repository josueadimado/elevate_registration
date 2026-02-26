# Add default password for Moodle user export (Program Settings).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('registrations', '0008_merge_20260216_0001'),
    ]

    operations = [
        migrations.AddField(
            model_name='programsettings',
            name='moodle_default_password',
            field=models.CharField(
                blank=True,
                default='TribeMentee@1#',
                help_text='Default password for Moodle user export; users should be forced to change on first login.',
                max_length=128,
                null=True
            ),
        ),
    ]
