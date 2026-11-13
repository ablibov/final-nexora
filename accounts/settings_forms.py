
from django import forms
from django.contrib.auth import get_user_model

from .avatar_validation import validate_avatar
from .models import AccountPreferences

User = get_user_model()


class ProfileForm(forms.ModelForm):
    avatar = forms.ImageField(
        required=False,
        validators=[validate_avatar],
        widget=forms.ClearableFileInput(attrs={
            "id": "profile-avatar",
            "accept": "image/png,image/jpeg,image/webp"
        })
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name")
        labels = {"first_name": "Имя", "last_name": "Фамилия"}
        widgets = {
            "first_name": forms.TextInput(attrs={"autocomplete": "given-name", "maxlength": "150"}),
            "last_name": forms.TextInput(attrs={"autocomplete": "family-name", "maxlength": "150"}),
        }


class ThemeForm(forms.Form):
    theme = forms.ChoiceField(choices=AccountPreferences.THEME_CHOICES)


class EmailChangeRequestForm(forms.Form):
    new_email = forms.EmailField(max_length=150, label="Новый email")
    current_password = forms.CharField(widget=forms.PasswordInput, label="Текущий пароль")

    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_new_email(self):
        email = self.cleaned_data["new_email"].strip().lower()

        if email == self.user.email.lower():
            raise forms.ValidationError("Это уже твой текущий email.")

        if User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists() or User.objects.filter(username__iexact=email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError("Этот адрес уже используется.")

        return email

    def clean_current_password(self):
        password = self.cleaned_data["current_password"]

        if not self.user.check_password(password):
            raise forms.ValidationError("Неверный текущий пароль.")

        return password


class VerificationCodeForm(forms.Form):
    code = forms.RegexField(
        regex=r"^[0-9]{6}$",
        max_length=6,
        label="Код подтверждения",
        error_messages={"invalid": "Введи шестизначный код."}
    )
