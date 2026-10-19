from django.contrib import admin
from .models import (
    Movie,
    Cinema,
    CinemaHall,
    CinemaHallAuditorium,
    Seat,
    Show,
    Reservation,
    MasterReservation,
)


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "genre")


@admin.register(Cinema)
class CinemaAdmin(admin.ModelAdmin):
    list_display = ("id", "name")


@admin.register(CinemaHall)
class CinemaHallAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "cinema", "location")


@admin.register(CinemaHallAuditorium)
class CinemaHallAuditoriumAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "cinemahall")


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "cinemahallauditorium",
        "name",
        "row",
        "number",
    )
    list_filter = ("cinemahallauditorium",)
    search_fields = ("name", "row")


@admin.register(Show)
class ShowAdmin(admin.ModelAdmin):
    list_display = (
        "cinemahallauditorium",
        "movie",
        "showtime",
        "price",
    )
    list_filter = ("cinemahallauditorium", "movie")
    search_fields = ("movie__name",)


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer",
        "show",
        "seat",
        "status",
        "created_at",
        "expires_at",
    )
    list_filter = ("status",)
    search_fields = ("customer__username", "seat__name")


@admin.register(MasterReservation)
class MasterReservationAdmin(admin.ModelAdmin):
    list_display = ("id", "session_id", "payment_id", "status")
