"""
Management command to normalize existing participant IDs to canonical format.
Format: ET/ASPIR/C1/003 (cohort + 3-digit sequence: 001, 002, 003, ...).

Converts old formats like:
  - ET/ASPIR/C1/0001  -> ET/ASPIR/C1/001
  - ET/ASPIR/C1/S/0016 -> ET/ASPIR/C1/016
  - ET/ASPIR/C1/1     -> ET/ASPIR/C1/001

Run: python manage.py normalize_participant_ids
Use --dry-run to only print what would be changed.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from registrations.models import Registration
from registrations.utils import (
    parse_participant_id_to_canonical,
    format_participant_id_canonical,
    get_next_available_sequence,
)


class Command(BaseCommand):
    help = 'Normalize all participant IDs to canonical form ET/ASPIR/C1/003 (3-digit sequence)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Only show what would be updated, do not save.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        if dry_run:
            self.stdout.write(self.style.WARNING('Dry run: no changes will be saved.'))

        regs = Registration.objects.exclude(
            participant_id__isnull=True
        ).exclude(
            participant_id=''
        ).order_by('created_at')

        updated = 0
        skipped_already = 0
        skipped_invalid = 0
        conflicts = 0

        for reg in regs:
            current = reg.participant_id
            canonical = parse_participant_id_to_canonical(current)

            if not canonical:
                skipped_invalid += 1
                self.stdout.write(self.style.WARNING(f'  Invalid ID (skipped): {reg.full_name} -> "{current}"'))
                continue

            if canonical == current:
                skipped_already += 1
                continue

            # Check if canonical is already taken by another registration
            taken = Registration.objects.filter(participant_id=canonical).exclude(id=reg.id).exists()

            if not taken:
                new_id = canonical
            else:
                # Assign next available sequence for this cohort (e.g. C1 from ET/ASPIR/C1/003)
                cohort_code = canonical.split('/')[2] if len(canonical.split('/')) >= 3 else None
                if not cohort_code:
                    skipped_invalid += 1
                    continue
                next_seq = get_next_available_sequence(cohort_code)
                new_id = format_participant_id_canonical(cohort_code, next_seq)
                conflicts += 1
                self.stdout.write(
                    self.style.NOTICE(f'  Conflict: {reg.full_name} "{current}" -> "{new_id}" (canonical {canonical} already taken)')
                )

            if not dry_run:
                with transaction.atomic():
                    reg.participant_id = new_id
                    reg.save(update_fields=['participant_id'])
            updated += 1
            self.stdout.write(f'  {reg.full_name}: "{current}" -> "{new_id}"')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Done. Updated: {updated}, already canonical: {skipped_already}, invalid: {skipped_invalid}, conflicts reassigned: {conflicts}'))
        if dry_run and updated:
            self.stdout.write(self.style.WARNING('Run without --dry-run to apply changes.'))
