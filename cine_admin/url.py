
from django.urls import path
from . import views

app_name = "cine_admin"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),

    path("venues/", views.venue_list, name="venue_list"),
    path("venues/add/", views.venue_create, name="venue_create"),

    path("auditoriums/", views.auditorium_list, name="auditorium_list"),
    path("auditoriums/add/", views.auditorium_create, name="auditorium_create"),
    path(
        "auditoriums/<int:auditorium_id>/design/",
        views.auditorium_designer,
        name="auditorium_designer",
    ),
    path(
        "auditoriums/<int:auditorium_id>/seats/",
        views.seat_manager,
        name="seat_manager",
    ),

    path("shows/", views.show_list, name="show_list"),
    path("shows/add/", views.show_create, name="show_create"),
    path("movies/add/", views.movie_create, name="movie_create"),
path("staff/", views.staff_list, name="staff_list"),
path("staff/add/", views.support_staff_create, name="support_staff_create"),
path("movies/", views.movie_list, name="movie_list"),
path("users/bookings/", views.user_booking_list, name="user_booking_list"),
path("bookings/", views.booking_list, name="booking_list"),
path("reports/movies/", views.movie_booking_report, name="movie_booking_report"),
path("reports/halls/", views.hall_booking_report, name="hall_booking_report"),
path("payments/", views.payment_list, name="payment_list"),
]
