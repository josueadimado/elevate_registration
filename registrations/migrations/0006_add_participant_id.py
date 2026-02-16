# Generated for participant ID (ET/ASPIR/C1/A/1001)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('registrations', '0005_add_payment_activity'),
    ]

    operations = [
        migrations.AddField(
            model_name='registration',
            name='participant_id',
            field=models.CharField(
                blank=True,
                help_text='Generated ID e.g. ET/ASPIR/C1/A/1001 (cohort + dimension + sequence)',
                max_length=50,
                null=True,
                unique=True,
            ),
        ),
    ]
