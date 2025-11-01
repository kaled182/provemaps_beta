import json
import os
import time
from contextlib import contextmanager
from django.core.management.base import BaseCommand
from maps_view.models import FiberCable, FiberEvent
from maps_view.services.fiber_status import (
    evaluate_cable_status_for_cable,
)

LOCK_FILE = "/tmp/update_fiber_status.lock"
LOCK_STALE_SECONDS = 60 * 10  # 10 minutes


@contextmanager
def file_lock(path: str, force: bool = False):
    """Simple file-based lock to avoid concurrent executions.

    Removes the lock if it is stale. When ``force`` is True the existing lock
    is ignored.
    """
    if os.path.exists(path) and not force:
        try:
            mtime = os.path.getmtime(path)
            age = time.time() - mtime
            if age < LOCK_STALE_SECONDS:
                raise RuntimeError(
                    "Lock active: another execution is running "
                    "(use --force to ignore)"
                )
            else:
                # Stale lock
                os.remove(path)
        except OSError:
            pass
    try:
        with open(path, 'w') as f:
            f.write(str(os.getpid()))
        yield
    finally:
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass


class Command(BaseCommand):
    help = "Update fiber cable statuses by querying Zabbix."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Do not persist changes; only show the planned updates.',
        )
        parser.add_argument(
            '--cable',
            type=str,
            help='Cable name or specific ID to limit the update.',
        )
        parser.add_argument(
            '--verbose-json',
            action='store_true',
            help='Print detailed JSON output for inspection.',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Ignore an existing lock and force execution.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        cable_filter = options.get('cable')
        verbose_json = options['verbose_json']
        force = options['force']

        qs = FiberCable.objects.select_related(
            'origin_port__device', 'origin_port__device__site',
            'destination_port__device', 'destination_port__device__site'
        )
        if cable_filter:
            if cable_filter.isdigit():
                qs = qs.filter(id=int(cable_filter))
            else:
                qs = qs.filter(name__icontains=cable_filter)

        total = qs.count()
        if total == 0:
            self.stdout.write(
                self.style.WARNING('No cables found to update.')
            )
            return

        try:
            with file_lock(LOCK_FILE, force=force):
                results = []
                updated = 0
                unknown_after = 0
                for cable in qs:
                    eval_data = evaluate_cable_status_for_cable(cable)
                    new_status = eval_data['combined_status']
                    old_status = eval_data['previous_status']
                    changed = eval_data['changed']
                    if new_status == 'unknown':
                        unknown_after += 1
                    if changed and not dry_run:
                        prev = cable.status
                        cable.update_status(new_status)
                        FiberEvent.objects.create(
                            fiber=cable,
                            previous_status=prev,
                            new_status=new_status,
                            detected_reason=json.dumps({
                                'origin': eval_data['origin_reason'],
                                'destination': eval_data['destination_reason'],
                                'combined': new_status,
                            }, ensure_ascii=False)
                        )
                        updated += 1
                    results.append({
                        'cable_id': cable.id,
                        'cable': cable.name,
                        'old_status': old_status,
                        'new_status': new_status,
                        'origin_interface_status': eval_data['origin_status'],
                        'destination_interface_status': (
                            eval_data['destination_status']
                        ),
                        'changed': changed,
                        'origin_reason': eval_data['origin_reason'],
                        'destination_reason': eval_data['destination_reason'],
                    })
        except RuntimeError as e:
            self.stdout.write(self.style.WARNING(str(e)))
            return

        if verbose_json:
            self.stdout.write(
                json.dumps(
                    {'updated': updated, 'total': total, 'results': results},
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return

        for r in results:
            mark = '*' if r['changed'] else '-'
            self.stdout.write(
                f"{mark} {r['cable']} {r['old_status']} -> {r['new_status']} "
                f"(orig={r['origin_interface_status']} "
                f"dest={r['destination_interface_status']})"
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Cables processed: {total} | Updated: {updated}"
            )
        )
        unknown_after = sum(1 for r in results if r['new_status'] == 'unknown')
        if unknown_after:
            self.stdout.write(
                self.style.WARNING(
                    f"Cables still in 'unknown' status: {unknown_after}"
                )
            )
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    'Executed in --dry-run mode; no changes were persisted.'
                )
            )
