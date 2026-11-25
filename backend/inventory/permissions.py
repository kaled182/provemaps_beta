"""Permissões DRF do inventário."""

from rest_framework.permissions import SAFE_METHODS, BasePermission


class StaffWritePermission(BasePermission):
    """Leitura para qualquer utilizador autenticado; escrita só para staff (EV-0138).

    É a mesma regra das rotas de cabos (`integrations.zabbix.guards.staff_guard`): quem
    altera a topologia física é a engenharia, não a operação.
    """

    message = "Permissão insuficiente: só a engenharia (staff) altera a topologia física."

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        return request.method in SAFE_METHODS or bool(user.is_staff)
