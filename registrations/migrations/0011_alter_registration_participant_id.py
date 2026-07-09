# Align participant_id help text with ET/ASPIR/{cohort}/{NNN} format.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('registrations', '0009_add_moodle_default_password'),
    ]

    operations = [
        migrations.AlterField(
            model_name='registration',
            name='participant_id',
            field=models.CharField(
                blank=True,
                help_text='Generated ID e.g. ET/ASPIR/C1/003 (cohort + 3-digit sequence)',
                max_length=50,
                null=True,
                unique=True,
            ),
        ),
    ]
