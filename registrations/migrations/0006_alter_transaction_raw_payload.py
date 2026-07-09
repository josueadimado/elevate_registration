# Server migration: update Transaction.raw_payload help text (Squad webhooks).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('registrations', '0005_add_payment_activity'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transaction',
            name='raw_payload',
            field=models.JSONField(default=dict, help_text='Raw webhook payload'),
        ),
    ]
