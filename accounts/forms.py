
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm

from .avatar_validation import validate_avatar


class RegisterForm(UserCreationForm):
    email = forms.EmailField(label="Email", max_length=150)
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    avatar = forms.ImageField(required=False, validators=[validate_avatar])

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        if User.objects.filter(username__iexact=email).exists() or User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Этот email уже зарегистрирован.")

        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["email"]
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"].strip()
        user.last_name = self.cleaned_data["last_name"].strip()

        if commit:
            user.save()

        return user


class EmailLoginForm(AuthenticationForm):
    username = forms.EmailField(label="Email")

    def clean(self):
        if "username" in self.cleaned_data:
            self.cleaned_data["username"] = self.cleaned_data["username"].strip().lower()

        return super().clean()
