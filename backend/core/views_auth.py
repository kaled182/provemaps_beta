from __future__ import annotations

import logging

from django import forms
from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView, PasswordResetView
from django.core.cache import cache
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic.edit import FormView

from core.api_users import _verify_totp
from setup_app.utils.env_manager import read_values

logger = logging.getLogger(__name__)


def _apply_runtime_email_settings() -> None:
    values = read_values(
        [
            "SMTP_ENABLED",
            "SMTP_HOST",
            "SMTP_PORT",
            "SMTP_SECURITY",
            "SMTP_USER",
            "SMTP_PASSWORD",
            "SMTP_FROM_EMAIL",
            "EMAIL_BACKEND",
            "EMAIL_HOST",
            "EMAIL_PORT",
            "EMAIL_HOST_USER",
            "EMAIL_HOST_PASSWORD",
            "EMAIL_USE_TLS",
            "EMAIL_USE_SSL",
            "DEFAULT_FROM_EMAIL",
            "SERVER_EMAIL",
        ]
    )

    smtp_enabled = values.get("SMTP_ENABLED", "").lower() == "true"
    email_host = values.get("EMAIL_HOST", "")
    smtp_host = values.get("SMTP_HOST", "")

    if not email_host and smtp_enabled and smtp_host:
        from_email = values.get("SMTP_FROM_EMAIL") or values.get("SMTP_USER") or ""
        settings.EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
        settings.EMAIL_HOST = smtp_host
        settings.EMAIL_PORT = int(values.get("SMTP_PORT") or "587")
        settings.EMAIL_HOST_USER = values.get("SMTP_USER", "")
        settings.EMAIL_HOST_PASSWORD = values.get("SMTP_PASSWORD", "")
        security = (values.get("SMTP_SECURITY") or "").lower()
        settings.EMAIL_USE_TLS = security == "tls"
        settings.EMAIL_USE_SSL = security == "ssl"
        if from_email:
            settings.DEFAULT_FROM_EMAIL = from_email
            settings.SERVER_EMAIL = from_email
        return

    if email_host:
        settings.EMAIL_BACKEND = values.get(
            "EMAIL_BACKEND", settings.EMAIL_BACKEND
        )
        settings.EMAIL_HOST = email_host
        settings.EMAIL_PORT = int(values.get("EMAIL_PORT") or "587")
        settings.EMAIL_HOST_USER = values.get("EMAIL_HOST_USER", "")
        settings.EMAIL_HOST_PASSWORD = values.get("EMAIL_HOST_PASSWORD", "")
        settings.EMAIL_USE_TLS = values.get("EMAIL_USE_TLS", "False").lower() == "true"
        settings.EMAIL_USE_SSL = values.get("EMAIL_USE_SSL", "False").lower() == "true"
        default_from = values.get("DEFAULT_FROM_EMAIL", "")
        server_email = values.get("SERVER_EMAIL", "")
        if default_from:
            settings.DEFAULT_FROM_EMAIL = default_from
        if server_email:
            settings.SERVER_EMAIL = server_email


class RuntimeEmailPasswordResetView(PasswordResetView):
    def form_valid(self, form):
        _apply_runtime_email_settings()
        return super().form_valid(form)


class TotpCodeForm(forms.Form):
    otp = forms.CharField(
        label="Codigo de verificacao",
        required=True,
        widget=forms.TextInput(attrs={"autocomplete": "one-time-code"}),
    )


class TwoStepLoginView(LoginView):
    authentication_form = AuthenticationForm
    template_name = "registration/login.html"

    def form_valid(self, form):
        user = form.get_user()
        profile = getattr(user, "profile", None)
        if profile and profile.totp_enabled:
            self.request.session["pending_2fa_user_id"] = user.id
            self.request.session["pending_2fa_next"] = self.get_success_url()
            return redirect(reverse("login_otp"))
        return super().form_valid(form)


OTP_FAIL_WINDOW_SECONDS = 300  # janela em que as falhas contam
OTP_LOCKOUT_SECONDS = 300  # bloqueio após max_attempts falhas


def _otp_fail_key(user_id) -> str:
    return f"otp:fail:{user_id}"


def _otp_lock_key(user_id) -> str:
    return f"otp:lock:{user_id}"


def otp_is_locked(user_id) -> bool:
    return bool(cache.get(_otp_lock_key(user_id)))


def otp_register_failure(user_id, max_attempts: int) -> int:
    """Conta a falha no servidor (não na sessão) e bloqueia ao atingir o máximo.

    EV-0016: o contador vivia em ``request.session`` — bastava limpar o cookie
    para zerar as tentativas. Agora é por utilizador, na cache, com TTL.
    """
    key = _otp_fail_key(user_id)
    if cache.add(key, 1, OTP_FAIL_WINDOW_SECONDS):
        attempts = 1
    else:
        try:
            attempts = cache.incr(key)
        except ValueError:  # chave expirou entre o add e o incr
            cache.set(key, 1, OTP_FAIL_WINDOW_SECONDS)
            attempts = 1
    if attempts >= max_attempts:
        cache.set(_otp_lock_key(user_id), True, OTP_LOCKOUT_SECONDS)
        cache.delete(key)
        logger.warning("otp.locked", extra={"user_id": user_id, "attempts": attempts})
    return attempts


def otp_clear_failures(user_id) -> None:
    cache.delete(_otp_fail_key(user_id))
    cache.delete(_otp_lock_key(user_id))


class RuntimeOtpView(FormView):
    form_class = TotpCodeForm
    template_name = "registration/otp.html"
    max_attempts = 3

    def dispatch(self, request, *args, **kwargs):
        if not request.session.get("pending_2fa_user_id"):
            return redirect(settings.LOGIN_URL)
        return super().dispatch(request, *args, **kwargs)

    @staticmethod
    def _pending_user(user_id):
        """Return the user awaiting 2FA, or None when the session is stale."""
        if not user_id:
            return None
        user = User.objects.filter(id=user_id).first()
        profile = getattr(user, "profile", None) if user else None
        if not profile or not profile.totp_enabled or not profile.totp_secret:
            return None
        return user

    def form_valid(self, form):
        user = self._pending_user(self.request.session.get("pending_2fa_user_id"))
        if user is None:
            return redirect(settings.LOGIN_URL)
        profile = user.profile

        if otp_is_locked(user.id):
            self.request.session.pop("pending_2fa_user_id", None)
            self.request.session.pop("pending_2fa_next", None)
            return redirect(f"{settings.LOGIN_URL}?otp=locked")

        otp = form.cleaned_data.get("otp", "").strip()
        if not _verify_totp(profile.totp_secret, otp):
            attempts = otp_register_failure(user.id, self.max_attempts)
            if attempts >= self.max_attempts:
                self.request.session.pop("pending_2fa_user_id", None)
                self.request.session.pop("pending_2fa_next", None)
                return redirect(f"{settings.LOGIN_URL}?otp=locked")
            form.add_error("otp", "Codigo de verificacao invalido.")
            return self.form_invalid(form)

        otp_clear_failures(user.id)

        backend = settings.AUTHENTICATION_BACKENDS[0]
        user.backend = backend
        login(self.request, user)
        next_url = self.request.session.pop(
            "pending_2fa_next",
            settings.LOGIN_REDIRECT_URL
        )
        self.request.session.pop("pending_2fa_user_id", None)
        return redirect(next_url)
