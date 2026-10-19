from celery import shared_task
from core/models import Reservation
from django.utils import timezone


@shared_task
def cleanup_expired_and_cancelled_reservations():
    # Delete cancelled reservations
    Reservation.objects.filter(
        status=Reservation.STATUS_CHOICES.CANCELLED
    ).delete()

    # Get current time
    now = timezone.now()

    # Delete expired pending reservations
    expired_delete_count, _ = Reservation.objects.filter(
        status=Reservation.STATUS_CHOICES.PENDING,
        expires_at__lte=now
    ).delete()

    return {
        "expired_reservations_deleted": expired_delete_count
    }
