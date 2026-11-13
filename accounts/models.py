from django.db import models
from django.conf import settings


class EmailVerification(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_verification",
    )
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    sent_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)


class AccountPreferences(models.Model):
    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"
    THEME_CHOICES = [
        (SYSTEM, "Как в системе"),
        (LIGHT, "Светлая"),
        (DARK, "Тёмная"),
    ]
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="account_preferences",
    )
    theme = models.CharField(max_length=6, choices=THEME_CHOICES, default=SYSTEM)
    reader_mode = models.BooleanField(default=False)


class PendingEmailChange(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pending_email_change",
    )
    new_email = models.EmailField(max_length=150)
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    sent_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
