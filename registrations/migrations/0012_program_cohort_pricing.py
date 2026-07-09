# Programs, per-cohort pricing, and registration program/tribe fields.

from decimal import Decimal
from django.db import migrations, models
import django.db.models.deletion


def seed_programs_and_cohorts(apps, schema_editor):
    Program = apps.get_model('registrations', 'Program')
    Cohort = apps.get_model('registrations', 'Cohort')
    Dimension = apps.get_model('registrations', 'Dimension')
    ProgramSettings = apps.get_model('registrations', 'ProgramSettings')

    aspire, _ = Program.objects.get_or_create(
        slug='aspire',
        defaults={
            'name': 'ASPIRE',
            'id_prefix': 'ASPIR',
            'description': 'ASPIRE Mentorship Program',
            'is_active': True,
            'display_order': 1,
            'show_tribe_member_pricing': True,
        },
    )
    data_analytics, _ = Program.objects.get_or_create(
        slug='data-analytics',
        defaults={
            'name': 'Data Analytics',
            'id_prefix': 'DATA',
            'description': 'Data Analytics program',
            'is_active': True,
            'display_order': 2,
            'show_tribe_member_pricing': False,
        },
    )

    # Attach existing cohorts to ASPIRE so codes stay unique per program
    for legacy in Cohort.objects.filter(program__isnull=True):
        legacy.program = aspire
        legacy.save(update_fields=['program'])

    dim_p = Dimension.objects.filter(code='P').first()
    dim_s = Dimension.objects.filter(code='S').first()
    dim_a = Dimension.objects.filter(code='A').first()

    aspire_cohorts = [
        {'code': 'C1', 'name': 'Cohort 1', 'track_name': 'Purpose Discovery',
         'registration_fee': Decimal('20'), 'course_fee': Decimal('100'),
         'default_enrollment_type': 'RETURNING', 'display_order': 1, 'linked_dimension': dim_p},
        {'code': 'C2', 'name': 'Cohort 2', 'track_name': 'Spiritual Excellence',
         'registration_fee': Decimal('20'), 'course_fee': Decimal('100'),
         'default_enrollment_type': 'RETURNING', 'display_order': 2, 'linked_dimension': dim_s},
        {'code': 'C3', 'name': 'Cohort 3', 'track_name': 'Academic Excellence',
         'registration_fee': Decimal('50'), 'course_fee': Decimal('100'),
         'default_enrollment_type': 'NEW', 'display_order': 3, 'linked_dimension': dim_a,
         'tribe_member_registration_fee': Decimal('50'), 'tribe_member_course_fee': Decimal('100')},
    ]
    for data in aspire_cohorts:
        linked = data.pop('linked_dimension', None)
        cohort, created = Cohort.objects.get_or_create(
            program=aspire, code=data['code'],
            defaults={**data, 'is_active': True, 'currency': 'USD'},
        )
        if not created:
            for k, v in data.items():
                setattr(cohort, k, v)
            cohort.program = aspire
            cohort.is_active = True
            cohort.save()
        if linked and not cohort.linked_dimension_id:
            cohort.linked_dimension = linked
            cohort.save(update_fields=['linked_dimension'])

    da_cohort, _ = Cohort.objects.get_or_create(
        program=data_analytics, code='C1',
        defaults={
            'name': 'Cohort 1',
            'track_name': 'Data Analytics',
            'registration_fee': Decimal('50'),
            'course_fee': Decimal('150'),
            'currency': 'USD',
            'is_active': True,
            'display_order': 1,
            'default_enrollment_type': 'NEW',
        },
    )

    settings = ProgramSettings.objects.filter(pk=1).first()
    if settings and 'ASPIR' in (settings.site_name or ''):
        settings.site_name = settings.site_name.replace('ASPIR', 'ASPIRE')
        settings.save(update_fields=['site_name'])


class Migration(migrations.Migration):

    dependencies = [
        ('registrations', '0011_alter_registration_participant_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='Program',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='e.g. ASPIRE, Data Analytics', max_length=150)),
                ('slug', models.SlugField(help_text='Short code e.g. aspire, data-analytics', unique=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('id_prefix', models.CharField(default='ASPIR', help_text='Used in participant IDs e.g. ET/ASPIR/C1/003', max_length=20)),
                ('is_active', models.BooleanField(default=True, help_text='Only active programs appear on the registration form')),
                ('display_order', models.IntegerField(default=0)),
                ('show_tribe_member_pricing', models.BooleanField(default=False, help_text='Show Elevate Tribe member pricing option on registration (ASPIRE only)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Program',
                'verbose_name_plural': 'Programs',
                'ordering': ['display_order', 'name'],
            },
        ),
        migrations.AddField(
            model_name='registration',
            name='is_elevate_tribe_member',
            field=models.BooleanField(default=False, help_text='Elevate Tribe member — may use tribe member pricing when configured on cohort'),
        ),
        migrations.AddField(
            model_name='registration',
            name='program',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='registrations', to='registrations.program'),
        ),
        migrations.AddField(
            model_name='cohort',
            name='program',
            field=models.ForeignKey(blank=True, help_text='Which program this cohort belongs to', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='cohorts', to='registrations.program'),
        ),
        migrations.AddField(
            model_name='cohort',
            name='track_name',
            field=models.CharField(blank=True, default='', help_text='Learning track e.g. Purpose Discovery, Spiritual Excellence', max_length=150),
        ),
        migrations.AddField(
            model_name='cohort',
            name='display_order',
            field=models.IntegerField(default=0, help_text='Order within the program on registration form'),
        ),
        migrations.AddField(
            model_name='cohort',
            name='registration_fee',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Registration fee for this cohort (USD unless currency set)', max_digits=10),
        ),
        migrations.AddField(
            model_name='cohort',
            name='course_fee',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Course fee for this cohort', max_digits=10),
        ),
        migrations.AddField(
            model_name='cohort',
            name='currency',
            field=models.CharField(choices=[('USD', 'USD'), ('NGN', 'NGN')], default='USD', max_length=3),
        ),
        migrations.AddField(
            model_name='cohort',
            name='tribe_member_registration_fee',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Optional: registration fee for Elevate Tribe members', max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='cohort',
            name='tribe_member_course_fee',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Optional: course fee for Elevate Tribe members', max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='cohort',
            name='linked_dimension',
            field=models.ForeignKey(blank=True, help_text='Optional dimension linked to this cohort', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cohorts', to='registrations.dimension'),
        ),
        migrations.AddField(
            model_name='cohort',
            name='default_enrollment_type',
            field=models.CharField(blank=True, choices=[('', '—'), ('NEW', 'New Learner'), ('RETURNING', 'Returning Learner')], default='', help_text='Optional default enrollment type for this cohort', max_length=10),
        ),
        migrations.AlterField(
            model_name='cohort',
            name='name',
            field=models.CharField(help_text='e.g. Cohort 1', max_length=100, unique=False),
        ),
        migrations.AlterField(
            model_name='cohort',
            name='code',
            field=models.CharField(help_text='e.g. C1, C2, C3 (unique within program)', max_length=10, unique=False),
        ),
        migrations.AlterModelOptions(
            name='cohort',
            options={'ordering': ['display_order', 'name'], 'verbose_name': 'Cohort', 'verbose_name_plural': 'Cohorts'},
        ),
        migrations.AlterUniqueTogether(
            name='cohort',
            unique_together={('program', 'code')},
        ),
        migrations.RunPython(seed_programs_and_cohorts, migrations.RunPython.noop),
    ]
