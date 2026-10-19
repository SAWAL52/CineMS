
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

User = get_user_model()


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label="Email address",
    )

    phone_number = forms.CharField(
        required=True,
        label="Phone number",
        max_length=20,
        widget=forms.TextInput(attrs={
            "placeholder": "e.g. 98XXXXXXXX",
            "type": "tel",
            "autocomplete": "tel",
        }),
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password1",
            "password2",
        ]

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email already exists."
            )

        return email

    def clean_phone_number(self):
        phone = self.cleaned_data["phone_number"].strip()

        # Allow digits, spaces, +, hyphens and parentheses.
        allowed = set("0123456789+ -()")
        if not phone or any(char not in allowed for char in phone):
            raise forms.ValidationError(
                "Enter a valid phone number."
            )

        digits = "".join(char for char in phone if char.isdigit())
        if not 7 <= len(digits) <= 15:
            raise forms.ValidationError(
                "Phone number must contain 7–15 digits."
            )

        return phone

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].strip().lower()

        if commit:
            user.save()

            from .models import UserProfile
            UserProfile.objects.create(
                user=user,
                phone_number=self.cleaned_data["phone_number"],
            )

        return user
