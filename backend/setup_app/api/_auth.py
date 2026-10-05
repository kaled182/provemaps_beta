"""Guardas de acesso partilhadas pelas views do setup_app."""

from __future__ import annotations

from django.contrib.auth.decorators import login_required, user_passes_test


def staff_check(user) -> bool:
    """Só utilizadores ativos e staff mexem na configuração do sistema."""
    return bool(user.is_active and user.is_staff)


def staff_required(view):
    """`login_required` + staff; o mesmo par de decoradores das views legadas."""
    return login_required(user_passes_test(staff_check)(view))
