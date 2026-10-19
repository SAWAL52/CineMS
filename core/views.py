
import io
import logging
import os
from datetime import timedelta
from email.mime.image import MIMEImage

import qrcode
from paybridge_np import PayBridgeNP
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import (
    getSampleStyleSheet,
    ParagraphStyle,
)
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as PDFImage,
)

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.db import IntegrityError, models, transaction
from django.http import Http404, HttpResponse
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.urls import reverse
from django.utils import timezone

from .forms import RegisterForm
from .models import (
    CinemaHallAuditorium,
    MasterReservation,
    Movie,
    Reservation,
    Seat,
    Show,
)

logger = logging.getLogger(__name__)

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.forms import AuthenticationForm
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .forms import RegisterForm
from .models import Movie, UserProfile


User = get_user_model()


# =========================================================
# REGISTRATION WITH EMAIL OTP
# =========================================================


@require_http_methods(["GET", "POST"])
def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = None

            try:
                with transaction.atomic():
                    user = form.save(commit=False)
                    user.is_active = False
                    user.save()

                    UserProfile.objects.create(
                        user=user,
                        phone_number=form.cleaned_data["phone_number"],
                    )

                otp = f"{secrets.randbelow(1_000_000):06d}"

                request.session["registration_otp_user_id"] = user.pk
                request.session["registration_otp_hash"] = (
                    hashlib.sha256(otp.encode()).hexdigest()
                )
                request.session["registration_otp_expires"] = (
                    int(timezone.now().timestamp()) + 300
                )
                request.session["registration_otp_attempts"] = 0

                send_mail(
                    subject="Verify Your CineMS Account",
                    message=(
                        f"Hello {user.username},\n\n"
                        f"Your verification code is: {otp}\n\n"
                        "This code expires in 5 minutes."
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )

            except Exception:
                logger.exception("CineMS registration/email failed")

                # Remove the newly created inactive account if setup
                # or email delivery fails.
                if user is not None:
                    user.delete()

                for key in (
                    "registration_otp_user_id",
                    "registration_otp_hash",
                    "registration_otp_expires",
                    "registration_otp_attempts",
                ):
                    request.session.pop(key, None)

                form.add_error(
                    None,
                    "Registration or email delivery failed. "
                    "Please try again.",
                )

                return render(
                    request,
                    "core/register.html",
                    {"form": form},
                )

            messages.success(
                request,
                "A verification code has been sent to your email.",
            )
            return redirect("verify_registration_otp")

    else:
        form = RegisterForm()

    return render(
        request,
        "core/register.html",
        {"form": form},
    )



# =========================================================
# VERIFY REGISTRATION EMAIL OTP
# =========================================================


import hashlib
import secrets

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods

User = get_user_model()


# =========================================================
# VERIFY REGISTRATION EMAIL OTP
# =========================================================

@require_http_methods(["GET", "POST"])
def verify_registration_otp(request):
    user_id = request.session.get("registration_otp_user_id")
    stored_hash = request.session.get("registration_otp_hash")
    expires_at = request.session.get("registration_otp_expires")

    if not user_id or not stored_hash or not expires_at:
        messages.error(
            request,
            "No pending verification found. Please register again."
        )
        return redirect("register")

    if request.method == "POST":
        otp = request.POST.get("otp", "").strip()
        attempts = request.session.get("registration_otp_attempts", 0)

        if attempts >= 5:
            for key in (
                "registration_otp_user_id",
                "registration_otp_hash",
                "registration_otp_expires",
                "registration_otp_attempts",
            ):
                request.session.pop(key, None)

            messages.error(
                request,
                "Too many incorrect attempts. Please register again."
            )
            return redirect("register")

        if int(timezone.now().timestamp()) > expires_at:
            for key in (
                "registration_otp_user_id",
                "registration_otp_hash",
                "registration_otp_expires",
                "registration_otp_attempts",
            ):
                request.session.pop(key, None)

            messages.error(
                request,
                "Your OTP has expired. Please register again."
            )
            return redirect("register")

        submitted_hash = hashlib.sha256(otp.encode()).hexdigest()

        if secrets.compare_digest(submitted_hash, stored_hash):
            try:
                user = User.objects.get(
                    pk=user_id,
                    is_active=False,
                )
            except User.DoesNotExist:
                messages.error(
                    request,
                    "Account not found. Please register again."
                )
                return redirect("register")

            # Activate the account after successful email verification.
            user.is_active = True
            user.save(update_fields=["is_active"])

            for key in (
                "registration_otp_user_id",
                "registration_otp_hash",
                "registration_otp_expires",
                "registration_otp_attempts",
            ):
                request.session.pop(key, None)

            messages.success(
                request,
                "Email verified successfully! You can now log in."
            )
            return redirect("login")

        request.session["registration_otp_attempts"] = attempts + 1
        messages.error(request, "Invalid verification code.")

    return render(
        request,
        "core/verify_registration_otp.html",
    )



# =========================================================
# AUTHENTICATION
# =========================================================

def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)

        if form.is_valid():
            login(request, form.get_user())
            return redirect("home")
    else:
        form = AuthenticationForm(request)

    return render(request, "core/login.html", {"form": form})


def logout_view(request):
    if request.method == "POST":
        logout(request)

    return redirect("home")


import hashlib
import secrets

from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import render, redirect
from django.utils import timezone

from .forms import RegisterForm
from .models import UserProfile


from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Reservation, UserProfile


@login_required
def user_profile(request):
    profile = UserProfile.objects.filter(user=request.user).first()

    reservations = (
        Reservation.objects
        .filter(customer=request.user)
        .select_related(
            "show",
            "show__movie",
            "show__cinemahall",
            "seat",
        )
        .order_by("-id")
    )

    return render(
        request,
        "core/user_profile.html",
        {
            "profile": profile,
            "reservations": reservations,
        },
    )


def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = None

            try:
                with transaction.atomic():
                    # Create inactive user.
                    user = form.save(commit=False)
                    user.is_active = False
                    user.save()

                    # Save phone number in the profile.
                    UserProfile.objects.create(
                        user=user,
                        phone_number=form.cleaned_data["phone_number"],
                    )

                # Generate a six-digit OTP.
                otp = f"{secrets.randbelow(1_000_000):06d}"

                # Store OTP hash and expiry in the session.
                request.session["registration_otp_user_id"] = user.pk
                request.session["registration_otp_hash"] = (
                    hashlib.sha256(otp.encode()).hexdigest()
                )
                request.session["registration_otp_expires"] = (
                    int(timezone.now().timestamp()) + 300
                )
                request.session["registration_otp_attempts"] = 0

                # Send OTP to the registered email address.
                send_mail(
                    subject="Verify Your CineMS Account",
                    message=(
                        f"Hello {user.username},\n\n"
                        f"Your CineMS verification code is: {otp}\n\n"
                        "This code expires in 5 minutes."
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )

                messages.success(
                    request,
                    "A verification code has been sent to your email.",
                )
                return redirect("verify_registration_otp")

            except Exception:
                # Remove the account if registration/email delivery fails.
                if user is not None:
                    user.delete()

                for key in (
                    "registration_otp_user_id",
                    "registration_otp_hash",
                    "registration_otp_expires",
                    "registration_otp_attempts",
                ):
                    request.session.pop(key, None)

                form.add_error(
                    None,
                    "We could not complete registration or send the "
                    "verification email. Please try again.",
                )

    else:
        form = RegisterForm()

    return render(
        request,
        "core/register.html",
        {"form": form},
    )


# =========================================================
# HOME AND MOVIE DETAILS
# =========================================================


def home(request):
    movies = Movie.objects.order_by("name")

    return render(
        request,
        "core/home.html",
        {"movies": movies},
    )



def movie_detail(request, pk):
    movie = get_object_or_404(Movie, pk=pk)

    shows = (
        Show.objects.filter(
            movie=movie,
            showtime__gte=timezone.now(),
            cinemahallauditorium__isnull=False,
        )
        .select_related(
            "movie",
            "cinemahallauditorium",
            "cinemahallauditorium__cinemahall",
            "cinemahallauditorium__cinemahall__cinema",
        )
        .order_by("showtime")
    )

    return render(
        request,
        "core/movie_detail.html",
        {
            "movie": movie,
            "shows": shows,
        },
    )


# =========================================================
# HELPERS
# =========================================================

def get_occupied_seat_ids(show, now=None):
    """
    Return seat IDs that are confirmed or currently held
    by pending reservations.
    """
    if now is None:
        now = timezone.now()

    # Release expired pending reservations.
    Reservation.objects.filter(
        show=show,
        status=Reservation.STATUS_CHOICES.PENDING,
        expires_at__lte=now,
    ).update(
        status=Reservation.STATUS_CHOICES.EXPIRED
    )

    occupied = Reservation.objects.filter(
        show=show,
    ).filter(
        models.Q(
            status=Reservation.STATUS_CHOICES.CONFIRMED,
        )
        | models.Q(
            status=Reservation.STATUS_CHOICES.PENDING,
            expires_at__gt=now,
        )
        | models.Q(
            status=Reservation.STATUS_CHOICES.PENDING,
            expires_at__isnull=True,
        )
    )

    return set(occupied.values_list("seat_id", flat=True))


def build_booking_qr(master):
    """Return PNG bytes for a booking QR code."""
    qr_data = (
        f"CineMS-Booking-ID:{master.pk}"
        f"-Ref:{master.payment_id}"
    )

    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=2,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)

    image = qr.make_image(
        fill_color="black",
        back_color="white",
    )

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


# =========================================================
# SEAT SELECTION AND CHECKOUT
# =========================================================

@login_required
def hall_seats_view(request, show_id):
    show = get_object_or_404(
        Show.objects.select_related(
            "movie",
            "cinemahallauditorium",
            "cinemahallauditorium__cinemahall",
            "cinemahallauditorium__cinemahall__cinema",
        ),
        pk=show_id,
    )

    auditorium = show.cinemahallauditorium

    # The show must have an auditorium assigned by the cinema.
    if auditorium is None:
        messages.error(
            request,
            "This show has not been assigned an auditorium yet.",
        )
        return redirect("movie_detail", pk=show.movie_id)

    if show.showtime <= timezone.now():
        messages.error(
            request,
            "Seat booking is unavailable for a show that has started.",
        )
        return redirect("movie_detail", pk=show.movie_id)

    seats = Seat.objects.filter(
        cinemahallauditorium=auditorium,
    ).order_by("row", "number", "name")

    if request.method != "POST":
        occupied_ids = get_occupied_seat_ids(show)

        return render(
            request,
            "core/hall_seats.html",
            {
                "show": show,
                "seats": seats,
                "occupied_seat_ids": occupied_ids,
                "auditorium": auditorium,
                "hall": auditorium.cinemahall,
            },
        )

    # JavaScript submits seat_ids as a comma-separated string.
    seat_ids = [
        value.strip()
        for value in request.POST.get("seat_ids", "").split(",")
        if value.strip()
    ]

    if not seat_ids:
        messages.error(
            request,
            "Please select at least one seat.",
        )
        return redirect(request.path)

    if len(set(seat_ids)) != len(seat_ids):
        messages.error(
            request,
            "Duplicate seats were selected.",
        )
        return redirect(request.path)

    if not all(value.isdecimal() for value in seat_ids):
        messages.error(
            request,
            "Invalid seat selection.",
        )
        return redirect(request.path)

    selected_seats = list(
        Seat.objects.filter(
            pk__in=seat_ids,
            cinemahallauditorium=auditorium,
        )
    )

    if len(selected_seats) != len(seat_ids):
        messages.error(
            request,
            "One or more selected seats do not belong to this auditorium.",
        )
        return redirect(request.path)

    master = None

    try:
        # Create the pending reservations and master booking.
        with transaction.atomic():
            now = timezone.now()
            occupied_ids = get_occupied_seat_ids(show, now)

            selected_ids = {
                seat.pk for seat in selected_seats
            }

            if occupied_ids.intersection(selected_ids):
                messages.error(
                    request,
                    "One or more seats are no longer available.",
                )
                return redirect(request.path)

            master = MasterReservation.objects.create(
                session_id="",
                payment_id="",
                status="pending",
            )

            for seat in selected_seats:
                reservation = Reservation(
                    customer=request.user,
                    show=show,
                    seat=seat,
                    master_reservation=master,
                    status=Reservation.STATUS_CHOICES.PENDING,
                )

                # Validate that the seat belongs to the show's auditorium.
                reservation.full_clean()
                reservation.save()

        # Call the payment provider after the database transaction.
        # This avoids keeping a database transaction open during network I/O.
        total_paisa = int(
            show.price * len(selected_seats) * 100
        )

        client = PayBridgeNP(
            api_key=os.environ["PAYBRIDGENP_API_KEY"],
        )

        session = client.checkout.create({
            "amount": total_paisa,
            "currency": "NPR",
            "returnUrl": request.build_absolute_uri(
                reverse("payment_return")
            ),
            "cancelUrl": request.build_absolute_uri(
                reverse("payment_cancel")
            ),
            "customer": {
                "name": (
                    request.user.get_full_name()
                    or request.user.get_username()
                ),
                "email": request.user.email,
            },
            "metadata": {
                "show_id": str(show.pk),
                "user_id": str(request.user.pk),
                "seat_ids": ",".join(
                    str(seat.pk) for seat in selected_seats
                ),
            },
        })

        if not session.get("id") or not session.get("checkout_url"):
            raise ValueError(
                "Payment provider returned an incomplete checkout session."
            )

        master.session_id = session["id"]
        master.save(update_fields=["session_id"])

        return redirect(session["checkout_url"])

    except IntegrityError:
        logger.exception("Reservation database constraint error")

        messages.error(
            request,
            "A selected seat has already been reserved.",
        )

    except Exception:
        logger.exception("Failed to initiate booking checkout")

        messages.error(
            request,
            "Unable to initiate payment. Please try again.",
        )

    # If checkout setup failed, release this booking's pending seats.
    # Do not cancel a booking that has already been paid.
    if master is not None:
        with transaction.atomic():
            master = MasterReservation.objects.select_for_update().get(
                pk=master.pk,
            )

            if master.status != "success":
                Reservation.objects.filter(
                    master_reservation=master,
                    status=Reservation.STATUS_CHOICES.PENDING,
                ).update(
                    status=Reservation.STATUS_CHOICES.CANCELLED,
                )

                master.status = "checkout_failed"
                master.save(update_fields=["status"])

    return redirect(request.path)


# =========================================================
# PAYMENT RETURN AND VERIFICATION
# =========================================================



def payment_return(request):
    session_id = request.GET.get("session_id")
    payment_id = request.GET.get("payment_id")

    print("========== PAYMENT CALLBACK ==========")
    print("Session ID:", request.GET.get("session_id"))
    print("Payment ID:", request.GET.get("payment_id"))
    print("Callback status:", request.GET.get("status"))
    print("======================================")

    if not session_id or not payment_id:
        return HttpResponse(
            "Missing payment details.",
            status=400,
        )

    try:
        master = MasterReservation.objects.get(
            session_id=session_id,
        )

        if master.payment_id and master.payment_id != payment_id:
            return HttpResponse(
                "Payment ID mismatch.",
                status=400,
            )

        client = PayBridgeNP(
            api_key=os.environ["PAYBRIDGENP_API_KEY"],
        )

        # Never trust the browser redirect alone.
        payment = client.payments.retrieve(payment_id)
                # DEBUG: Inspect the payment response from PayBridgeNP
        print("\n========== PAYBRIDGENP PAYMENT RESPONSE ==========")
        print("Response type:", type(payment))
        print("Response:", repr(payment))

        if isinstance(payment, dict):
            print("Response keys:", list(payment.keys()))
            print("Status:", payment.get("status"))
            print("Amount:", payment.get("amount"))
            print("Currency:", payment.get("currency"))
            print("Checkout Session ID:", payment.get("checkoutSessionId"))

        print("==================================================\n")



        if payment.get("checkoutSessionId") != session_id:
            return HttpResponse(
                "Payment session mismatch.",
                status=400,
            )

        if payment.get("status") != "success":
            return HttpResponse(
                f"Payment not successful: {payment.get('status')}",
                status=400,
            )

        if payment.get("currency") != "NPR":
            return HttpResponse(
                "Invalid payment currency.",
                status=400,
            )

        reservations = list(
            master.reservation.select_related(
                "customer",
                "show",
                "show__movie",
                "show__cinemahallauditorium",
                "show__cinemahallauditorium__cinemahall",
                "seat",
            )
        )

        if not reservations:
            return HttpResponse(
                "No seats are linked to this booking.",
                status=400,
            )

        # Every reservation in a master booking must use the same show.
        show_ids = {
            reservation.show_id
            for reservation in reservations
        }

        if len(show_ids) != 1:
            return HttpResponse(
                "Invalid booking: multiple shows in one payment.",
                status=400,
            )

        expected_amount = sum(
            reservation.show.price * 100
            for reservation in reservations
        )

        try:
            paid_amount = int(payment.get("amount"))
        except (TypeError, ValueError):
            return HttpResponse(
                "Invalid payment amount.",
                status=400,
            )

        if paid_amount != expected_amount:
            return HttpResponse(
                "Payment amount mismatch.",
                status=400,
            )

        # Confirm only after provider-side payment verification.
        with transaction.atomic():
            master = MasterReservation.objects.select_for_update().get(
                pk=master.pk,
            )

            if master.payment_id and master.payment_id != payment_id:
                return HttpResponse(
                    "Payment ID mismatch.",
                    status=400,
                )

            # Make repeated payment-return visits idempotent.
            if master.status != "success":
                current_reservations = list(
                    Reservation.objects.select_for_update().filter(
                        master_reservation=master,
                    )
                )

                if not current_reservations:
                    return HttpResponse(
                        "No seats are linked to this booking.",
                        status=400,
                    )

                if any(
                    reservation.status
                    in (
                        Reservation.STATUS_CHOICES.CANCELLED,
                        Reservation.STATUS_CHOICES.EXPIRED,
                    )
                    for reservation in current_reservations
                ):
                    return HttpResponse(
                        "This booking has been cancelled or expired. "
                        "Contact support for payment assistance.",
                        status=409,
                    )

                # Do not confirm if the seats are now assigned to
                # another active reservation for this show.
                for reservation in current_reservations:
                    conflicting = Reservation.objects.filter(
                        show_id=reservation.show_id,
                        seat_id=reservation.seat_id,
                        status=Reservation.STATUS_CHOICES.CONFIRMED,
                    ).exclude(pk=reservation.pk).exists()

                    if conflicting:
                        logger.error(
                            "Seat conflict after payment for reservation %s",
                            reservation.pk,
                        )
                        return HttpResponse(
                            "A seat conflict was detected. Contact support.",
                            status=409,
                        )

                Reservation.objects.filter(
                    master_reservation=master,
                    status=Reservation.STATUS_CHOICES.PENDING,
                ).update(
                    status=Reservation.STATUS_CHOICES.CONFIRMED,
                )

            master.payment_id = payment_id
            master.status = "success"
            master.save(
                update_fields=["payment_id", "status"],
            )

        # Send the receipt after the database transaction succeeds.
        try:
            send_booking_receipt(master)
        except Exception:
            logger.exception(
                "Receipt email failed for booking %s",
                master.pk,
            )

        messages.success(
            request,
            "Payment successful! Your seats have been confirmed.",
        )
        return redirect("home")

    except MasterReservation.DoesNotExist:
        return HttpResponse(
            "Booking not found for this checkout session.",
            status=404,
        )

    except Exception:
        logger.exception("Payment verification failed")

        messages.error(
            request,
            "We could not verify your payment. Please contact support.",
        )
        return redirect("home")


# =========================================================
# BOOKING CONFIRMATION EMAIL
# =========================================================

def send_booking_receipt(master):
    reservations = list(
        master.reservation.select_related(
            "customer",
            "show",
            "show__movie",
            "show__cinemahallauditorium",
            "show__cinemahallauditorium__cinemahall",
            "show__cinemahallauditorium__cinemahall__cinema",
            "seat",
        ).order_by(
            "show__showtime",
            "seat__name",
        )
    )

    if not reservations:
        logger.error(
            "No reservations found for master booking %s",
            master.pk,
        )
        return

    first = reservations[0]

    user = first.customer
    show = first.show
    movie = show.movie
    auditorium = show.cinemahallauditorium
    hall = auditorium.cinemahall
    cinema = hall.cinema

    seats = [
        reservation.seat.name
        for reservation in reservations
    ]

    ticket_count = len(reservations)
    total_price = sum(
        reservation.show.price
        for reservation in reservations
    )

    showtime = timezone.localtime(
        show.showtime,
    ).strftime("%A, %d %B %Y, %I:%M %p")

    subject = f"CineMS Booking Confirmation - {movie.name}"

    email_body = f"""
Hello {user.get_full_name() or user.get_username()},

Your payment has been verified successfully, and your
CineMS booking is confirmed.

============================================================
                  CineMS BOOKING RECEIPT
============================================================

BOOKING INFORMATION
------------------------------------------------------------
Booking Reference : {master.pk}
Booking Status    : CONFIRMED

MOVIE INFORMATION
------------------------------------------------------------
Movie             : {movie.name}
Genre             : {movie.genre}

CINEMA INFORMATION
------------------------------------------------------------
Cinema Brand      : {cinema.name if cinema else 'N/A'}
Cinema Hall       : {hall.name}
Location          : {hall.location or 'N/A'}
Auditorium        : {auditorium.name}

SHOW INFORMATION
------------------------------------------------------------
Show Date & Time  : {showtime}

TICKET INFORMATION
------------------------------------------------------------
Selected Seats    : {", ".join(seats)}
Number of Tickets : {ticket_count}
Price per Ticket  : NPR {show.price:,.2f}
Total Ticket Cost : NPR {total_price:,.2f}

PAYMENT INFORMATION
------------------------------------------------------------
Payment Reference : {master.payment_id}
Payment Status    : SUCCESS
Currency          : NPR

============================================================

Please arrive before your scheduled showtime.
Keep this email for your records.

Thank you for choosing CineMS!

CineMS Team
""".strip()

    qr_bytes = build_booking_qr(master)

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <body style="background:#f4f4f4;padding:20px;font-family:Arial,sans-serif;">
        <div style="background:white;max-width:650px;margin:auto;padding:20px;">
            <pre style="white-space:pre-wrap;font-family:monospace;">{email_body}</pre>
            <div style="text-align:center;padding:15px;border:1px dashed #ccc;">
                <strong>Your Entry Ticket QR Code</strong>
                <p>Show this QR code at the cinema entrance.</p>
                <img src="cid:qr_ticket" alt="Booking QR Code"
                     style="width:160px;height:160px;">
            </div>
        </div>
    </body>
    </html>
    """

    # Send to the booking customer's registered email.
    # Replace with a fixed address only if intentionally testing.
    recipient = user.email

    if not recipient:
        logger.warning(
            "No customer email for booking %s",
            master.pk,
        )
        return

    email = EmailMultiAlternatives(
        subject=subject,
        body=email_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
    )
    email.attach_alternative(
        html_content,
        "text/html",
    )

    qr_image = MIMEImage(qr_bytes, _subtype="png")
    qr_image.add_header(
        "Content-ID",
        "<qr_ticket>",
    )
    qr_image.add_header(
        "Content-Disposition",
        "inline",
        filename="qrcode.png",
    )
    email.attach(qr_image)

    email.send(fail_silently=False)


# =========================================================
# PAYMENT CANCELLATION
# =========================================================

def payment_cancel(request):
    session_id = request.GET.get("session_id")

    if not session_id:
        messages.info(request, "Payment was cancelled.")
        return redirect("home")

    master = MasterReservation.objects.filter(
        session_id=session_id,
    ).first()

    if master:
        with transaction.atomic():
            master = MasterReservation.objects.select_for_update().get(
                pk=master.pk,
            )

            # Never cancel an already successful booking.
            if master.status != "success":
                Reservation.objects.filter(
                    master_reservation=master,
                    status=Reservation.STATUS_CHOICES.PENDING,
                ).update(
                    status=Reservation.STATUS_CHOICES.CANCELLED,
                )

                master.status = "cancelled"
                master.save(update_fields=["status"])

    messages.info(request, "Payment was cancelled.")
    return redirect("home")


# =========================================================
# CUSTOMER BOOKING HISTORY
# =========================================================

@login_required
def mybookings(request):
    reservations = (
        Reservation.objects
        .filter(customer=request.user)
        .select_related(
            "show",
            "show__movie",
            "show__cinemahallauditorium",
            "show__cinemahallauditorium__cinemahall",
            "show__cinemahallauditorium__cinemahall__cinema",
            "seat",
            "seat__cinemahallauditorium",
            "master_reservation",
        )
        .order_by("-created_at")
    )

    grouped_bookings = {}
    bookings = []

    for reservation in reservations:
        master = reservation.master_reservation

        group_key = (
            f"master_{master.pk}"
            if master
            else f"reservation_{reservation.pk}"
        )

        if group_key not in grouped_bookings:
            booking = {
                "master": master,
                "show": reservation.show,
                "reservations": [],
                "seats": [],
                "total_price": 0,
                "created_at": reservation.created_at,
                "status": reservation.get_status_display(),
                "status_code": reservation.status,
            }

            grouped_bookings[group_key] = booking
            bookings.append(booking)

        booking = grouped_bookings[group_key]
        booking["reservations"].append(reservation)
        booking["seats"].append(reservation.seat.name)
        booking["total_price"] += reservation.show.price

        # A booking is confirmed only when all its seats are confirmed.
        statuses = {
            item.status
            for item in booking["reservations"]
        }

        if statuses == {Reservation.STATUS_CHOICES.CONFIRMED}:
            booking["status"] = "Confirmed"
            booking["status_code"] = "cm"
        elif Reservation.STATUS_CHOICES.PENDING in statuses:
            booking["status"] = "Pending"
            booking["status_code"] = "pd"
        elif Reservation.STATUS_CHOICES.EXPIRED in statuses:
            booking["status"] = "Expired"
            booking["status_code"] = "ex"
        elif Reservation.STATUS_CHOICES.CANCELLED in statuses:
            booking["status"] = "Cancelled"
            booking["status_code"] = "cl"

    return render(
        request,
        "core/mybookings.html",
        {"bookings": bookings},
    )


# =========================================================
# PDF BOOKING RECEIPT
# =========================================================

@login_required
def download_receipt_pdf(request, master_id):
    master = (
        MasterReservation.objects
        .filter(
            pk=master_id,
            reservation__customer=request.user,
        )
        .first()
    )

    if master is None:
        raise Http404("Booking receipt not found.")

    reservations = list(
        master.reservation.select_related(
            "customer",
            "show",
            "show__movie",
            "show__cinemahallauditorium",
            "show__cinemahallauditorium__cinemahall",
            "show__cinemahallauditorium__cinemahall__cinema",
            "seat",
        ).order_by(
            "show__showtime",
            "seat__name",
        )
    )

    if not reservations:
        raise Http404("No seat reservations found.")

    first = reservations[0]

    user = first.customer
    show = first.show
    movie = show.movie
    auditorium = show.cinemahallauditorium
    hall = auditorium.cinemahall
    cinema = hall.cinema

    seats = [
        reservation.seat.name
        for reservation in reservations
    ]

    showtime = timezone.localtime(
        show.showtime,
    ).strftime("%A, %d %B %Y, %I:%M %p")

    total_price = sum(
        reservation.show.price
        for reservation in reservations
    )

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        textColor=colors.HexColor("#E50914"),
        alignment=1,
        spaceAfter=15,
    )

    header_style = ParagraphStyle(
        "HeaderStyle",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor=colors.HexColor("#1E293B"),
        spaceBefore=10,
        spaceAfter=6,
    )

    text_style = ParagraphStyle(
        "TextStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        textColor=colors.HexColor("#334155"),
    )

    story.append(
        Paragraph("CineMS BOOKING RECEIPT", title_style)
    )
    story.append(Spacer(1, 10))

    data = [
        [
            Paragraph("<b>Booking Reference:</b>", text_style),
            Paragraph(str(master.pk), text_style),
        ],
        [
            Paragraph("<b>Customer:</b>", text_style),
            Paragraph(
                user.get_full_name() or user.get_username(),
                text_style,
            ),
        ],
        [
            Paragraph("<b>Movie:</b>", text_style),
            Paragraph(
                f"<b>{movie.name}</b> ({movie.genre})",
                text_style,
            ),
        ],
        [
            Paragraph("<b>Cinema Brand:</b>", text_style),
            Paragraph(
                cinema.name if cinema else "N/A",
                text_style,
            ),
        ],
        [
            Paragraph("<b>Cinema Hall:</b>", text_style),
            Paragraph(hall.name, text_style),
        ],
        [
            Paragraph("<b>Location:</b>", text_style),
            Paragraph(hall.location or "N/A", text_style),
        ],
        [
            Paragraph("<b>Auditorium:</b>", text_style),
            Paragraph(auditorium.name, text_style),
        ],
        [
            Paragraph("<b>Showtime:</b>", text_style),
            Paragraph(showtime, text_style),
        ],
        [
            Paragraph("<b>Seats:</b>", text_style),
            Paragraph(", ".join(seats), text_style),
        ],
        [
            Paragraph("<b>Ticket Count:</b>", text_style),
            Paragraph(str(len(seats)), text_style),
        ],
        [
            Paragraph("<b>Booking Status:</b>", text_style),
            Paragraph(master.status.upper(), text_style),
        ],
        [
            Paragraph("<b>Payment ID:</b>", text_style),
            Paragraph(master.payment_id or "N/A", text_style),
        ],
        [
            Paragraph("<b>Total Amount:</b>", text_style),
            Paragraph(
                f"<b>NPR {total_price:,.2f}</b>",
                text_style,
            ),
        ],
    ]

    table = Table(
        data,
        colWidths=[2.0 * inch, 4.5 * inch],
    )

    table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, -1),
                colors.HexColor("#F8FAFC"),
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor("#E2E8F0"),
            ),
            ("PADDING", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )

    story.append(table)
    story.append(Spacer(1, 20))

    qr_bytes = build_booking_qr(master)
    qr_buffer = io.BytesIO(qr_bytes)

    story.append(
        Paragraph("<b>Entry QR Code</b>", header_style)
    )
    story.append(
        Paragraph(
            "Show this QR code at the entrance gate.",
            text_style,
        )
    )
    story.append(Spacer(1, 8))
    story.append(
        PDFImage(
            qr_buffer,
            width=1.8 * inch,
            height=1.8 * inch,
        )
    )

    doc.build(story)
    buffer.seek(0)

    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/pdf",
    )
    response["Content-Disposition"] = (
        f'attachment; filename="CineMS_Ticket_{master.pk}.pdf"'
    )

    return response



from django.contrib.auth import views as auth_views
from django.core.mail import send_mail as django_send_mail
from django.urls import reverse, reverse_lazy


class CineMSPasswordResetView(auth_views.PasswordResetView):
    template_name = "core/password_reset.html"
    extra_context = {"page": "request"}

    def send_mail(
        self,
        subject_template_name,
        email_template_name,
        context,
        from_email,
        to_email,
        html_email_template_name=None,
    ):
        subject = "Reset Your CineMS Password"

        reset_path = reverse(
            "password_reset_confirm",
            kwargs={
                "uidb64": context["uid"],
                "token": context["token"],
            },
        )

        reset_url = (
            f"{context['protocol']}://{context['domain']}{reset_path}"
        )

        body = f"""CineMS
Your Movie Experience Starts Here
----------------------------------------

Hello {context['user'].get_username()},

We received a request to reset the password for your CineMS account.

RESET YOUR PASSWORD

Use the link below to securely create a new password:

{reset_url}

For your security:
- This link is intended only for your account.
- If you did not request this reset, you can safely ignore this email.
- Your password will not change unless you complete the reset process.

----------------------------------------
CineMS Team
Your next movie experience awaits.
"""

        django_send_mail(
            subject=subject,
            message=body,
            from_email=from_email,
            recipient_list=[to_email],
            fail_silently=False,
        )


password_reset_view = CineMSPasswordResetView.as_view(
    success_url=reverse_lazy("password_reset_done"),
)

password_reset_done_view = auth_views.PasswordResetDoneView.as_view(
    template_name="core/password_reset.html",
    extra_context={"page": "done"},
)

password_reset_confirm_view = auth_views.PasswordResetConfirmView.as_view(
    template_name="core/password_reset.html",
    extra_context={"page": "confirm"},
    success_url=reverse_lazy("password_reset_complete"),
)

password_reset_complete_view = auth_views.PasswordResetCompleteView.as_view(
    template_name="core/password_reset.html",
    extra_context={"page": "complete"},
)
