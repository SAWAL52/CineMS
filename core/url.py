from django.urls import path
from . import views



urlpatterns=[ path("logout/", views.logout_view, name="logout"), path("login/", views.login_view, name="login"),
             path(
    "verify-registration-otp/",
    views.verify_registration_otp,
    name="verify_registration_otp",
),
 path("mybookings/", views.mybookings, name="mybookings"), path("booking/<uuid:master_id>/pdf/", views.download_receipt_pdf, name="download_receipt_pdf"), path('', views.home, name="home"), path('movies/<pk>/', views.movie_detail, name="movie_detail"), path("register/", views.register, name="register"), path(
        "payment/return/",
        views.payment_return,
        name="payment_return",
    ),
    path("profile/", views.user_profile, name="user_profile"),
    path(
        "payment/cancel/",
        views.payment_cancel,
        name="payment_cancel",
    ), path("show/<show_id>", views.hall_seats_view, name="hall_seats"),



        path("password-reset/", views.password_reset_view, name="password_reset"),
        path("password-reset/done/", views.password_reset_done_view, name="password_reset_done"),
        path("reset/<uidb64>/<token>/", views.password_reset_confirm_view, name="password_reset_confirm"),
        path("reset/complete/", views.password_reset_complete_view, name="password_reset_complete"),

]
