
from string import ascii_uppercase

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from core.models import (
    CinemaHall,
    CinemaHallAuditorium,
    Reservation,
    Seat,
    Show,
    MasterReservation,
)

from .forms import AuditoriumForm, ShowForm, VenueForm
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import user_passes_test
from django.db import IntegrityError
from django.shortcuts import redirect, render
from django.contrib import messages

from core.models import Movie
from .forms import MovieForm, SupportStaffCreationForm

User = get_user_model()


def superuser_required(view_func):
    """Restrict a view to authenticated superusers."""
    return user_passes_test(
        lambda user: user.is_authenticated and user.is_superuser,
        login_url="cine_admin:dashboard",
    )(view_func)

@staff_member_required
@superuser_required
def movie_create(request):
    form = MovieForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        try:
            form.save()
            messages.success(request, "Movie added successfully.")
            return redirect("cine_admin:movie_create")
        except IntegrityError:
            form.add_error(
                None,
                "The movie could not be saved because of a database conflict.",
            )

    return render(
        request,
        "cine_admin/movie_form.html",
        {"form": form},
    )


@staff_member_required
@superuser_required
def support_staff_create(request):
    form = SupportStaffCreationForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        try:
            form.save()
            messages.success(
                request,
                "Support staff account created successfully.",
            )
            return redirect("cine_admin:staff_list")
        except IntegrityError:
            form.add_error(
                None,
                "This account could not be created because of a database conflict.",
            )

    return render(
        request,
        "cine_admin/staff_form.html",
        {"form": form},
    )


@staff_member_required
@superuser_required
def staff_list(request):
    admins = User.objects.filter(
        is_superuser=True
    ).order_by("username")

    support_staff = User.objects.filter(
        is_staff=True,
        is_superuser=False,
    ).order_by("username")

    return render(
        request,
        "cine_admin/staff_list.html",
        {
            "admins": admins,
            "support_staff": support_staff,
        },
    )


@staff_member_required
def dashboard(request):
    context = {
        # Existing dashboard statistics
        "venue_count": CinemaHall.objects.count(),
        "auditorium_count": CinemaHallAuditorium.objects.count(),
        "show_count": Show.objects.count(),
        "movie_count": Movie.objects.count(),
        "admin_count": User.objects.filter(is_superuser=True).count(),
        "staff_count": User.objects.filter(
            is_staff=True,
            is_superuser=False,
        ).count(),

        # New dashboard statistics
        "active_user_count": User.objects.filter(is_active=True).count(),
        "booking_count": Reservation.objects.count(),
        "confirmed_booking_count": Reservation.objects.filter(
            status=Reservation.STATUS_CHOICES.CONFIRMED
        ).count(),
        "pending_booking_count": Reservation.objects.filter(
            status=Reservation.STATUS_CHOICES.PENDING
        ).count(),
        "successful_payment_count": MasterReservation.objects.filter(
            status="success"
        ).count(),
        "payment_attention_count": MasterReservation.objects.filter(
            status="success",
            reservation__status=Reservation.STATUS_CHOICES.PENDING,
        ).distinct().count(),
    }

    return render(request, "cine_admin/dashboard.html", context)

# -------------------- VENUES --------------------

@staff_member_required
def venue_list(request):
    venues = (
        CinemaHall.objects.select_related("cinema")
        .annotate(auditorium_count=Count("auditoriums"))
        .order_by("name")
    )

    return render(
        request,
        "cine_admin/venue_list.html",
        {"venues": venues},
    )


@staff_member_required
@require_http_methods(["GET", "POST"])
def venue_create(request):
    form = VenueForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        try:
            form.save()
        except (IntegrityError, ValidationError):
            form.add_error(
                None,
                "The venue could not be saved. Check the entered "
                "information and any database uniqueness constraints.",
            )
        else:
            messages.success(request, "Venue created successfully.")
            return redirect("cine_admin:venue_list")

    return render(
        request,
        "cine_admin/venue_form.html",
        {"form": form},
    )

@staff_member_required
def movie_list(request):
    movies = Movie.objects.all().order_by("name")

    context = {
        "movies": movies,
        "movie_count": movies.count(),
    }

    return render(request, "cine_admin/movie_list.html", context)
# -------------------- AUDITORIUMS --------------------

@staff_member_required
def auditorium_list(request):
    auditoriums = (
        CinemaHallAuditorium.objects.select_related(
            "cinemahall",
            "cinemahall__cinema",
        )
        .annotate(seat_count=Count("seats"))
        .order_by("cinemahall__name", "name")
    )

    return render(
        request,
        "cine_admin/auditorium_list.html",
        {"auditoriums": auditoriums},
    )


@staff_member_required
@require_http_methods(["GET", "POST"])
def auditorium_create(request):
    form = AuditoriumForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        try:
            form.save()
        except (IntegrityError, ValidationError):
            form.add_error(
                None,
                "The auditorium could not be saved. Check whether an "
                "auditorium with this name already exists at the venue.",
            )
        else:
            messages.success(
                request,
                "Auditorium created successfully. You can now design its seats.",
            )
            return redirect("cine_admin:auditorium_list")

    return render(
        request,
        "cine_admin/auditorium_form.html",
        {"form": form},
    )


@staff_member_required
@require_http_methods(["GET", "POST"])
@staff_member_required
def auditorium_designer(request, auditorium_id):
    auditorium = get_object_or_404(
        CinemaHallAuditorium.objects.select_related("cinemahall"),
        pk=auditorium_id,
    )

    if request.method == "POST":
        try:
            rows = int(request.POST.get("rows", 0))
            seats_per_row = int(request.POST.get("seats_per_row", 0))
        except (TypeError, ValueError):
            messages.error(request, "Please enter valid numbers of rows and seats.")
            return redirect(
                "cine_admin:auditorium_designer",
                auditorium_id=auditorium.pk,
            )

        if not 1 <= rows <= 26 or not 1 <= seats_per_row <= 50:
            messages.error(
                request,
                "Rows must be between 1 and 26, and seats per row between 1 and 50.",
            )
            return redirect(
                "cine_admin:auditorium_designer",
                auditorium_id=auditorium.pk,
            )

        existing_seats = Seat.objects.filter(
            cinemahallauditorium=auditorium
        )

        # Never replace seats referenced by reservations.
        if Reservation.objects.filter(seat__in=existing_seats).exists():
            messages.error(
                request,
                "This auditorium has seats linked to reservations. "
                "Its existing layout cannot be replaced.",
            )
            return redirect(
                "cine_admin:seat_manager",
                auditorium_id=auditorium.pk,
            )

        seats_to_create = []

        for row_index in range(rows):
            row_label = ascii_uppercase[row_index]

            for seat_number in range(1, seats_per_row + 1):
                seat_name = f"{row_label}{seat_number}"

                seats_to_create.append(
                    Seat(
                        cinemahall=auditorium.cinemahall,
                        cinemahallauditorium=auditorium,
                        name=seat_name,
                        row=row_label,
                        number=seat_number,
                    )
                )

        try:
            with transaction.atomic():
                # Recheck reservation references immediately before replacement.
                if Reservation.objects.filter(seat__in=existing_seats).exists():
                    messages.error(
                        request,
                        "Seats have reservations and cannot be replaced.",
                    )
                    return redirect(
                        "cine_admin:seat_manager",
                        auditorium_id=auditorium.pk,
                    )

                existing_seats.delete()
                Seat.objects.bulk_create(seats_to_create)

        except IntegrityError as exc:
            print(f"SEAT LAYOUT INTEGRITY ERROR: {exc}")
            messages.error(
                request,
                "The database rejected the layout. Seat names may already "
                "exist in another auditorium at this same venue.",
            )
            return redirect(
                "cine_admin:auditorium_designer",
                auditorium_id=auditorium.pk,
            )

        except Exception as exc:
            print(f"SEAT LAYOUT ERROR: {type(exc).__name__}: {exc}")
            messages.error(
                request,
                f"Could not save seats: {type(exc).__name__}: {exc}",
            )
            return redirect(
                "cine_admin:auditorium_designer",
                auditorium_id=auditorium.pk,
            )

        messages.success(
            request,
            f"Successfully generated {len(seats_to_create)} seats "
            f"for {auditorium.name}.",
        )

        return redirect("cine_admin:dashboard")



    return render(
        request,
        "cine_admin/auditorium_designer.html",
        {"auditorium": auditorium},
    )

# -------------------- SEAT MANAGEMENT --------------------

@staff_member_required
def seat_manager(request, auditorium_id):
    auditorium = get_object_or_404(
        CinemaHallAuditorium.objects.select_related("cinemahall"),
        pk=auditorium_id,
    )

    seats = Seat.objects.filter(
        cinemahallauditorium=auditorium
    ).order_by("row", "number", "name")

    return render(
        request,
        "cine_admin/seat_manager.html",
        {
            "auditorium": auditorium,
            "seats": seats,
        },
    )


# -------------------- SHOWS --------------------

@staff_member_required
def show_list(request):
    shows = Show.objects.select_related(
        "movie",
        "cinemahallauditorium",
        "cinemahallauditorium__cinemahall",
        "cinemahallauditorium__cinemahall__cinema",
    ).order_by("showtime")

    return render(
        request,
        "cine_admin/show_list.html",
        {"shows": shows},
    )


@staff_member_required
@require_http_methods(["GET", "POST"])
def show_create(request):
    form = ShowForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        show = form.save(commit=False)

        # Keep the legacy venue field synchronized if it is still present
        # and required in the current Show model.
        show.cinemahall = show.cinemahallauditorium.cinemahall

        try:
            with transaction.atomic():
                show.save()
                form.save_m2m()
        except (IntegrityError, ValidationError):
            form.add_error(
                None,
                "The show could not be saved. Check the scheduled time, "
                "auditorium, and existing database constraints.",
            )
        else:
            messages.success(request, "Show scheduled successfully.")
            return redirect("cine_admin:show_list")

    return render(
        request,
        "cine_admin/show_form.html",
        {"form": form},
    )

@staff_member_required
def user_booking_list(request):
    users = User.objects.filter(
        is_active=True,
    ).order_by("-date_joined")

    user_rows = []

    for user in users:
        user_rows.append({
            "user": user,
            "booking_count": Reservation.objects.filter(
                customer=user
            ).count(),
            "confirmed_count": Reservation.objects.filter(
                customer=user,
                status=Reservation.STATUS_CHOICES.CONFIRMED,
            ).count(),
        })

    return render(
        request,
        "cine_admin/user_bookings.html",
        {"user_rows": user_rows},
    )

@staff_member_required
def booking_list(request):
    bookings = Reservation.objects.select_related(
        "customer",
        "show",
        "show__movie",
        "show__cinemahallauditorium",
        "show__cinemahallauditorium__cinemahall",
        "seat",
        "master_reservation",
    ).order_by("-id")

    movie_id = request.GET.get("movie")
    hall_id = request.GET.get("hall")
    reservation_status = request.GET.get("reservation_status")
    payment_status = request.GET.get("payment_status")

    if movie_id:
        bookings = bookings.filter(show__movie_id=movie_id)

    if hall_id:
        bookings = bookings.filter(
            show__cinemahallauditorium__cinemahall_id=hall_id
        )

    if reservation_status:
        bookings = bookings.filter(status=reservation_status)

    if payment_status:
        bookings = bookings.filter(
            master_reservation__status=payment_status
        )

    context = {
        "bookings": bookings,
        "movies": Movie.objects.order_by("name"),
        "halls": CinemaHall.objects.select_related("cinema").order_by("name"),
        "reservation_statuses": Reservation.STATUS_CHOICES.choices,
        "selected_movie": movie_id or "",
        "selected_hall": hall_id or "",
        "selected_reservation_status": reservation_status or "",
        "selected_payment_status": payment_status or "",
        "payment_statuses": [
            ("pending", "Pending"),
            ("success", "Successful"),
            ("checkout_failed", "Checkout failed"),
        ],
    }

    return render(request, "cine_admin/booking_list.html", context)

@staff_member_required
def movie_booking_report(request):
    movies = Movie.objects.annotate(
        booking_count=Count("shows__reservation")
    ).order_by("-booking_count", "name")

    return render(
        request,
        "cine_admin/movie_booking_report.html",
        {"movies": movies},
    )

@staff_member_required
def hall_booking_report(request):
    halls = CinemaHall.objects.select_related("cinema").annotate(
        booking_count=Count(
            "auditoriums__shows__reservation",
            distinct=True,
        )
    ).order_by("-booking_count", "name")

    return render(
        request,
        "cine_admin/hall_booking_report.html",
        {"halls": halls},
    )

@staff_member_required
def payment_list(request):
    payments = MasterReservation.objects.prefetch_related(
        "reservation__customer",
        "reservation__show__movie",
    ).order_by("-id")

    payment_status = request.GET.get("status")

    if payment_status:
        payments = payments.filter(status=payment_status)

    # Alert on successful payments with at least one unconfirmed reservation.
    reconciliation_alerts = payments.filter(
        status="success",
        reservation__status=Reservation.STATUS_CHOICES.PENDING,
    ).distinct()

    return render(
        request,
        "cine_admin/payment_list.html",
        {
            "payments": payments,
            "payment_status": payment_status or "",
            "payment_statuses": [
                ("pending", "Pending"),
                ("success", "Successful"),
                ("checkout_failed", "Checkout failed"),
            ],
            "reconciliation_alerts": reconciliation_alerts,
        },
    )
