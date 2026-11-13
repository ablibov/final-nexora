
import secrets
from datetime import timedelta
from smtplib import SMTPException

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.sessions.models import Session
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from core.models import NexoraAvatar
from .models import AccountPreferences, PendingEmailChange
from .settings_forms import ProfileForm, ThemeForm, EmailChangeRequestForm, VerificationCodeForm

User = get_user_model()
CODE_LIFETIME = timedelta(minutes=10)
RESEND_COOLDOWN = timedelta(minutes=1)
MAX_ATTEMPTS = 5


def _code():
    return f"{secrets.randbelow(1_000_000):06d}"


def _send_code(address, code):
    sent = send_mail(
        "Nexora — подтверждение нового email",
        f"Код подтверждения нового email: {code}. Он действует 10 минут. Если ты не запрашивал смену адреса, проигнорируй письмо.",
        settings.DEFAULT_FROM_EMAIL,
        [address],
        fail_silently=False,
    )

    if sent != 1:
        raise SMTPException("Почтовый сервер не принял сообщение.")


@login_required
@require_http_methods(["GET", "POST"])
def account_settings(request):
    preferences, _ = AccountPreferences.objects.get_or_create(user=request.user)

    profile_form = ProfileForm(instance=request.user, prefix="profile")
    password_form = PasswordChangeForm(user=request.user, prefix="password")
    email_form = EmailChangeRequestForm(user=request.user, prefix="email")
    theme_form = ThemeForm(initial={"theme": preferences.theme})

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "profile":
            profile_form = ProfileForm(
                request.POST,
                request.FILES,
                instance=request.user,
                prefix="profile"
            )

            if profile_form.is_valid():
                profile_form.save()

                avatar = profile_form.cleaned_data.get("avatar")
                if avatar:
                    NexoraAvatar.objects.update_or_create(
                        user=request.user,
                        defaults={"image": avatar}
                    )

                messages.success(request, "Данные профиля обновлены.")
                return redirect("account_settings")

        elif action == "password":
            password_form = PasswordChangeForm(
                user=request.user,
                data=request.POST,
                prefix="password"
            )

            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)

                messages.success(
                    request,
                    "Пароль обновлён. Другие сеансы с прежним паролем станут недействительными."
                )
                return redirect("account_settings")

        elif action == "theme":
            theme_form = ThemeForm(request.POST)

            if theme_form.is_valid():
                preferences.theme = theme_form.cleaned_data["theme"]
                preferences.save(update_fields=["theme"])

                messages.success(request, "Тема оформления сохранена.")
                return redirect("account_settings")

        elif action == "email":
            email_form = EmailChangeRequestForm(
                request.POST,
                user=request.user,
                prefix="email"
            )

            if email_form.is_valid():
                pending = PendingEmailChange.objects.filter(user=request.user).first()

                if pending and pending.sent_at > timezone.now() - RESEND_COOLDOWN:
                    email_form.add_error(None, "Подожди минуту перед следующим запросом.")

                else:
                    code = _code()

                    try:
                        with transaction.atomic():
                            PendingEmailChange.objects.update_or_create(
                                user=request.user,
                                defaults={
                                    "new_email": email_form.cleaned_data["new_email"],
                                    "code_hash": make_password(code),
                                    "expires_at": timezone.now() + CODE_LIFETIME,
                                    "sent_at": timezone.now(),
                                    "attempts": 0,
                                },
                            )

                            _send_code(email_form.cleaned_data["new_email"], code)

                    except (OSError, SMTPException):
                        email_form.add_error(
                            None,
                            "Не удалось отправить письмо. Проверь почтовые настройки."
                        )
                    else:
                        messages.success(
                            request,
                            "Код отправлен на новый адрес электронной почты."
                        )
                        return redirect("verify_new_email")

        else:
            messages.error(request, "Неизвестное действие.")
            return redirect("account_settings")

    pending = PendingEmailChange.objects.filter(user=request.user).first()

    return render(request, "account_settings.html", {
        "profile_form": profile_form,
        "password_form": password_form,
        "email_form": email_form,
        "theme_form": theme_form,
        "pending_email": pending.new_email if pending else "",
        "preferences": preferences,
    })


@login_required
@require_http_methods(["GET", "POST"])
def verify_new_email(request):
    pending = PendingEmailChange.objects.filter(user=request.user).first()

    if pending is None:
        messages.info(request, "Нет ожидающей подтверждения смены email.")
        return redirect("account_settings")

    form = VerificationCodeForm(request.POST or None)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "resend":
            if pending.sent_at > timezone.now() - RESEND_COOLDOWN:
                messages.error(request, "Новый код можно запросить через минуту.")

            else:
                code = _code()

                try:
                    with transaction.atomic():
                        pending.code_hash = make_password(code)
                        pending.expires_at = timezone.now() + CODE_LIFETIME
                        pending.sent_at = timezone.now()
                        pending.attempts = 0

                        pending.save(
                            update_fields=["code_hash", "expires_at", "sent_at", "attempts"]
                        )

                        _send_code(pending.new_email, code)

                except (OSError, SMTPException):
                    messages.error(request, "Письмо не отправлено. Попробуй позже.")
                else:
                    messages.success(request, "Новый код отправлен.")

            return redirect("verify_new_email")

        if action == "cancel":
            pending.delete()
            messages.info(request, "Смена email отменена.")
            return redirect("account_settings")

        if form.is_valid():
            if pending.expires_at <= timezone.now():
                form.add_error(None, "Срок действия кода истёк. Запроси новый.")

            elif pending.attempts >= MAX_ATTEMPTS:
                form.add_error(None, "Слишком много попыток. Запроси новый код.")

            elif not check_password(form.cleaned_data["code"], pending.code_hash):
                pending.attempts += 1
                pending.save(update_fields=["attempts"])
                form.add_error(None, "Неверный код подтверждения.")

            else:
                with transaction.atomic():
                    pending = PendingEmailChange.objects.select_for_update().get(pk=pending.pk)
                    user = User.objects.select_for_update().get(pk=request.user.pk)

                    email_taken = (
                        User.objects.filter(email__iexact=pending.new_email)
                        .exclude(pk=user.pk)
                        .exists()
                        or User.objects.filter(username__iexact=pending.new_email)
                        .exclude(pk=user.pk)
                        .exists()
                    )

                    if email_taken:
                        form.add_error(None, "Этот email уже занят другим аккаунтом.")

                    else:
                        user.email = pending.new_email
                        user.username = pending.new_email
                        user.save(update_fields=["email", "username"])

                        pending.delete()

                        messages.success(
                            request,
                            "Email подтверждён и изменён. Теперь входи с новым адресом."
                        )
                        return redirect("account_settings")

    return render(
        request,
        "verify_new_email.html",
        {"form": form, "pending": pending}
    )


@require_POST
@login_required
def logout_other_sessions(request):
    password = request.POST.get("current_password", "")

    if not request.user.check_password(password):
        messages.error(request, "Неверный пароль. Другие сеансы не изменены.")
        return redirect("account_settings")

    current_key = request.session.session_key

    other_sessions = (
        Session.objects.filter(expire_date__gte=timezone.now())
        .exclude(session_key=current_key)
    )

    deleted_count = 0

    for session in other_sessions.iterator():
        try:
            if session.get_decoded().get("_auth_user_id") == str(request.user.pk):
                session.delete()
                deleted_count += 1
        except Exception:
            continue

    messages.success(request, f"Завершено других сеансов: {deleted_count}.")
    return redirect("account_settings")
