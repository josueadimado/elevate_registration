# Data Analytics and similar programs: require full payment (no partial registration fee).

from django.db import migrations, models


def enable_data_analytics_full_payment(apps, schema_editor):
    Program = apps.get_model('registrations', 'Program')
    Program.objects.filter(slug='data-analytics').update(require_full_payment=True)


class Migration(migrations.Migration):

    dependencies = [
        ('registrations', '0013_data_analytics_tribe_pricing'),
    ]

    operations = [
        migrations.AddField(
            model_name='program',
            name='require_full_payment',
            field=models.BooleanField(
                default=False,
                help_text='If checked, students must pay the full fee now (no registration-fee-only option). Use for Data Analytics.',
            ),
        ),
        migrations.RunPython(enable_data_analytics_full_payment, migrations.RunPython.noop),
    ]
