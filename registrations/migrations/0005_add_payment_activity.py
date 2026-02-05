# Generated manually for PaymentActivity

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('registrations', '0004_alter_pricingconfig_currency'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentActivity',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('reference', models.CharField(db_index=True, max_length=100)),
                ('status', models.CharField(choices=[('initiated', 'Initiated'), ('success', 'Success'), ('failed', 'Failed')], db_index=True, max_length=20)),
                ('payment_type', models.CharField(choices=[('registration_fee', 'Registration Fee'), ('course_fee', 'Course Fee'), ('full_payment', 'Full Payment')], default='registration_fee', max_length=20)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('currency', models.CharField(default='USD', max_length=3)),
                ('gateway', models.CharField(default='squad', max_length=20)),
                ('message', models.CharField(blank=True, max_length=255, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('registration', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payment_activities', to='registrations.registration')),
            ],
            options={
                'verbose_name': 'Payment Activity',
                'verbose_name_plural': 'Payment Activities',
                'ordering': ['-created_at'],
            },
        ),
    ]
