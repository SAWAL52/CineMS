
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

from core.models import (
    CinemaHall,
    CinemaHallAuditorium,
    Movie,
    Show,
)

User = get_user_model()

FORM_CONTROL = (
    "w-full rounded-lg border border-gray-600 bg-gray-800 "
    "px-4 py-3 text-white focus:border-red-500 focus:outline-none"
)


# =========================================================
# VENUE FORM
# =========================================================

class VenueForm(forms.ModelForm):
    class Meta:
        model = CinemaHall
        fields = ["cinema", "name", "location"]
        widgets = {
            "cinema": forms.Select(attrs={
                "class": FORM_CONTROL,
            }),
            "name": forms.TextInput(attrs={
                "class": FORM_CONTROL,
                "placeholder": "e.g. QFX Civil Mall",
            }),
            "location": forms.TextInput(attrs={
                "class": FORM_CONTROL,
                "placeholder": "e.g. Sundhara, Kathmandu",
            }),
        }

    def clean_name(self):
        return self.cleaned_data["name"].strip()


# =========================================================
# AUDITORIUM FORM
# =========================================================

class AuditoriumForm(forms.ModelForm):
    class Meta:
        model = CinemaHallAuditorium
        fields = ["cinemahall", "name"]
        widgets = {
            "cinemahall": forms.Select(attrs={
                "class": FORM_CONTROL,
            }),
            "name": forms.TextInput(attrs={
                "class": FORM_CONTROL,
                "placeholder": "e.g. Auditorium 1",
            }),
        }

    def clean(self):
        cleaned_data = super().clean()

        venue = cleaned_data.get("cinemahall")
        name = cleaned_data.get("name")

        if venue and name:
            duplicates = CinemaHallAuditorium.objects.filter(
                cinemahall=venue,
                name__iexact=name.strip(),
            )

            if self.instance.pk:
                duplicates = duplicates.exclude(
                    pk=self.instance.pk
                )

            if duplicates.exists():
                self.add_error(
                    "name",
                    "An auditorium with this name already exists "
                    "at this venue.",
                )

        return cleaned_data


# =========================================================
# SHOW FORM
# =========================================================

class ShowForm(forms.ModelForm):
    class Meta:
        model = Show
        fields = [
            "movie",
            "cinemahallauditorium",
            "showtime",
            "price",
        ]
        widgets = {
            "movie": forms.Select(attrs={
                "class": FORM_CONTROL,
            }),
            "cinemahallauditorium": forms.Select(attrs={
                "class": FORM_CONTROL,
            }),
            "showtime": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={
                    "type": "datetime-local",
                    "class": FORM_CONTROL,
                },
            ),
            "price": forms.NumberInput(attrs={
                "class": FORM_CONTROL,
                "min": "1",
                "step": "1",
                "placeholder": "Enter ticket price in NPR",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["movie"].queryset = Movie.objects.order_by(
            "name"
        )

        self.fields[
            "cinemahallauditorium"
        ].queryset = (
            CinemaHallAuditorium.objects.select_related(
                "cinemahall",
                "cinemahall__cinema",
            ).order_by(
                "cinemahall__name",
                "name",
            )
        )

        self.fields["showtime"].input_formats = [
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d %H:%M:%S",
        ]

    def clean_price(self):
        price = self.cleaned_data["price"]

        if price <= 0:
            raise ValidationError(
                "The ticket price must be greater than zero."
            )

        return price

    def clean(self):
        cleaned_data = super().clean()

        auditorium = cleaned_data.get(
            "cinemahallauditorium"
        )
        showtime = cleaned_data.get("showtime")

        if auditorium and showtime:
            conflicts = Show.objects.filter(
                cinemahallauditorium=auditorium,
                showtime=showtime,
            )

            if self.instance.pk:
                conflicts = conflicts.exclude(
                    pk=self.instance.pk
                )

            if conflicts.exists():
                raise ValidationError(
                    "A show is already scheduled in this "
                    "auditorium at this exact date and time."
                )

        return cleaned_data


# =========================================================
# MOVIE FORM
# =========================================================

class MovieForm(forms.ModelForm):
    class Meta:
        model = Movie
        fields = ["name", "genre", "poster"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": FORM_CONTROL,
                "placeholder": "Enter movie name",
            }),
            "genre": forms.TextInput(attrs={
                "class": FORM_CONTROL,
                "placeholder": "e.g. Action, Drama, Comedy",
            }),
            "poster": forms.ClearableFileInput(attrs={
                "class": FORM_CONTROL,
                "accept": "image/*",
            }),
        }

    def clean_name(self):
        return self.cleaned_data["name"].strip()


# =========================================================
# SUPPORT STAFF CREATION FORM
# =========================================================

class SupportStaffCreationForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            "class": FORM_CONTROL,
            "placeholder": "First name",
        }),
    )

    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            "class": FORM_CONTROL,
            "placeholder": "Last name",
        }),
    )

    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            "class": FORM_CONTROL,
            "placeholder": "staff@example.com",
        }),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
        )
        widgets = {
            "username": forms.TextInput(attrs={
                "class": FORM_CONTROL,
                "placeholder": "Choose a username",
            }),
        }

    def save(self, commit=True):
        user = super().save(commit=False)

        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]

        user.is_staff = True
        user.is_superuser = False

        if commit:
            user.save()

        return user
