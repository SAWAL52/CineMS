import os
import sys
from pathlib import Path

# Make the project root importable and start Django (must happen before importing models)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.utils import timezone
from core.models import MasterReservation, Reservation


def main(dry_run=False):
    # 1. Held seats whose time ran out (only 'pd', confirmed 'cm' is never touched)
    stale = Reservation.objects.filter(status="pd", expires_at__lt=timezone.now())
    stale_count = stale.count()
    if not dry_run:
        stale.update(status="ex")

    # 2. Pending payments with no active reservation left
    active = Reservation.objects.filter(
        status__in=["pd", "cm"], master_reservation__isnull=False
    ).values("master_reservation_id")
    orphans = MasterReservation.objects.filter(status="pending").exclude(id__in=active)
    orphan_count = orphans.count()
    if not dry_run:
        orphans.update(status="expired")

    label = "Would expire" if dry_run else "Expired"
    print(f"{label} {stale_count} reservation(s); closed {orphan_count} pending payment(s).")


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)
