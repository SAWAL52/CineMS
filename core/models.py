
from datetime import timedelta
import uuid

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    phone_number = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.user.username

class Movie(models.Model):
    name = models.CharField(max_length=50)
    genre = models.CharField(max_length=50)
    poster = models.ImageField(
        upload_to="movie_posters/",
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.name


class Cinema(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class CinemaHall(models.Model):
    cinema = models.ForeignKey(
        Cinema,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="halls",
    )
    name = models.CharField(max_length=100)
    location = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    def __str__(self):
        return self.name


class CinemaHallAuditorium(models.Model):
    cinemahall = models.ForeignKey(
        CinemaHall,
        on_delete=models.PROTECT,
        related_name="auditoriums",
    )
    name = models.CharField(max_length=100)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["cinemahall", "name"],
                name="unique_auditorium_name_per_hall",
            )
        ]

    def __str__(self):
        return f"{self.cinemahall.name} - {self.name}"



class Seat(models.Model):
    name = models.CharField(max_length=10)

    cinemahall = models.ForeignKey(
        CinemaHall,
        on_delete=models.CASCADE,
        related_name="seats",
    )

    cinemahallauditorium = models.ForeignKey(
        CinemaHallAuditorium,
        on_delete=models.CASCADE,
        related_name="seats",
        null=True,
        blank=True,
    )

    row = models.CharField(max_length=5, blank=True, default="")
    number = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["cinemahall", "name"],
                condition=models.Q(cinemahallauditorium__isnull=True),
                name="unique_legacy_seat_name_per_hall",
            ),
            models.UniqueConstraint(
                fields=["cinemahallauditorium", "name"],
                condition=models.Q(cinemahallauditorium__isnull=False),
                name="unique_seat_name_per_auditorium",
            ),
        ]

    def __str__(self):
        return self.name


class Show(models.Model):
    movie = models.ForeignKey(
        Movie,
        on_delete=models.PROTECT,
        related_name="shows",
    )

    # Existing relationship: preserve current show data
    cinemahall = models.ForeignKey(
        CinemaHall,
        on_delete=models.PROTECT,
    )

    # New relationship: populate through a data migration
    cinemahallauditorium = models.ForeignKey(
        CinemaHallAuditorium,
        on_delete=models.PROTECT,
        related_name="shows",
        null=True,
        blank=True,
    )

    showtime = models.DateTimeField()
    price = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["cinemahall", "movie", "showtime"],
                name="unique_movie_showtime_per_hall",
            ),
        ]

    def __str__(self):
        return f"{self.movie} - {self.cinemahall} - {self.showtime}"


class MasterReservation(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    session_id = models.CharField(max_length=60, default="")
    payment_id = models.CharField(max_length=60, default="")
    status = models.CharField(max_length=20, default="")

    def __str__(self):
        return str(self.id)


class Reservation(models.Model):

    class STATUS_CHOICES(models.TextChoices):
        PENDING = "pd", "Pending"
        CONFIRMED = "cm", "Confirmed"
        CANCELLED = "cl", "Cancelled"
        EXPIRED = "ex", "Expired"

    customer = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
    )
    show = models.ForeignKey(
        Show,
        on_delete=models.PROTECT,
        related_name="reservation",
    )
    seat = models.ForeignKey(
        Seat,
        on_delete=models.PROTECT,
        related_name="reservation",
    )
    master_reservation = models.ForeignKey(
        MasterReservation,
        on_delete=models.PROTECT,
        null=True,
        related_name="reservation",
    )
    status = models.CharField(
        max_length=2,
        choices=STATUS_CHOICES,
        default=STATUS_CHOICES.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self._state.adding and self.expires_at is None:
            self.expires_at = (
                timezone.now()
                + timedelta(
                    minutes=settings.RESERVATION_WINDOW_TIME
                )
            )
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()

        if (
            self.show_id
            and self.seat_id
            and self.show.cinemahallauditorium_id
            != self.seat.cinemahallauditorium_id
        ):
            raise ValidationError({
                "seat": (
                    "The selected seat does not belong to "
                    "the auditorium for this show."
                )
            })

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["show", "seat"],
                condition=models.Q(status__in=["pd", "cm"]),
                name="unique_seat_per_show",
            )
        ]

    def __str__(self):
        return f"{self.show} - {self.seat} ({self.get_status_display()})"
