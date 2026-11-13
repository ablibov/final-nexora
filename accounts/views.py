
import secrets
from datetime import timedelta
from smtplib import SMTPException

from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import EmailLoginForm, RegisterForm
from .models import EmailVerification
from core.models import NexoraAvatar


def register_view(request):
    if request.user.is_authenticated:
        return redirect("index")

    form = RegisterForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        code = f"{secrets.randbelow(1_000_000):06d}"

        try:
            with transaction.atomic():
                user = form.save(commit=False)
                user.is_active = False
                user.save()

                avatar = form.cleaned_data.get("avatar")
                if avatar:
                    NexoraAvatar.objects.create(user=user, image=avatar)

                EmailVerification.objects.create(
                    user=user,
                    code_hash=make_password(code),
                    expires_at=timezone.now() + timedelta(minutes=10),
                    sent_at=timezone.now(),
                )

                sent_count = send_mail(
                    "Your Nexora verification code",
                    f"Your verification code is {code}. It expires in 10 minutes.",
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                )

                if sent_count != 1:
                    raise SMTPException("The verification email was not accepted.")

        except (OSError, SMTPException):
            form.add_error(
                None,
                "Не удалось отправить письмо. Проверь email и попробуй ещё раз."
            )
        else:
            request.session["registration_email"] = user.email
            return redirect("verify_email")

    return render(request, "register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("index")

    form = EmailLoginForm(request, data=request.POST or None)

    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())

        next_url = request.POST.get("next", "")

        if url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(next_url)

        return redirect("index")

    return render(
        request,
        "login.html",
        {
            "form": form,
            "next": request.GET.get("next", request.POST.get("next", ""))
        }
    )


def verify_email_view(request):
    if request.user.is_authenticated:
        return redirect("index")

    error = None
    message = None

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()

        verification = (
            EmailVerification.objects.select_related("user")
            .filter(user__email__iexact=email, user__is_active=False)
            .first()
        )

        if request.POST.get("action") == "resend":
            if verification is None:
                error = "Email не найден или уже подтверждён."

            elif verification.sent_at > timezone.now() - timedelta(minutes=1):
                error = "Подожди минуту перед отправкой нового кода."

            else:
                code = f"{secrets.randbelow(1_000_000):06d}"

                try:
                    with transaction.atomic():
                        verification.code_hash = make_password(code)
                        verification.expires_at = timezone.now() + timedelta(minutes=10)
                        verification.sent_at = timezone.now()
                        verification.attempts = 0

                        verification.save(
                            update_fields=("code_hash", "expires_at", "sent_at", "attempts")
                        )

                        sent_count = send_mail(
                            "Your Nexora verification code",
                            f"Your verification code is {code}. It expires in 10 minutes.",
                            settings.DEFAULT_FROM_EMAIL,
                            [verification.user.email],
                        )

                        if sent_count != 1:
                            raise SMTPException("The verification email was not accepted.")

                except (OSError, SMTPException):
                    error = "Не удалось отправить письмо. Попробуй ещё раз."
                else:
                    message = "Новый код отправлен на почту."

        elif verification is None:
            error = "Неверный email или код подтверждения."

        elif verification.expires_at <= timezone.now():
            error = "Срок действия кода истёк. Запроси новый."

        elif verification.attempts >= 5:
            error = "Слишком много попыток. Запроси новый код."

        else:
            code = request.POST.get("code", "").strip()

            if not check_password(code, verification.code_hash):
                verification.attempts += 1
                verification.save(update_fields=("attempts",))
                error = "Неверный email или код подтверждения."

            else:
                user = verification.user
                user.is_active = True
                user.save(update_fields=("is_active",))

                verification.delete()
                login(request, user)
                request.session.pop("registration_email", None)

                return redirect("index")

    return render(
        request,
        "verify_email.html",
        {
            "error": error,
            "message": message,
            "email": request.POST.get("email", request.session.get("registration_email", ""))
        }
    )


@require_POST
@login_required
def logout_view(request):
    logout(request)
    return redirect("login")
