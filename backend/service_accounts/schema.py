"""Descrição OpenAPI da autenticação por token de conta de serviço (EV-0098, ADR 0008).

Sem esta extensão o drf-spectacular não sabe descrever o ``ServiceAccountTokenAuthentication``:
avisava «could not resolve authenticator» em cada view DRF e o esquema não dizia que a API
aceita ``Authorization: Bearer <token>``. Registada ao importar (``apps.ready``).
"""

from __future__ import annotations

from drf_spectacular.extensions import OpenApiAuthenticationExtension


class ServiceAccountTokenScheme(OpenApiAuthenticationExtension):
    target_class = "service_accounts.authentication.ServiceAccountTokenAuthentication"
    name = "serviceAccountToken"

    def get_security_definition(self, auto_schema):  # type: ignore[override]
        return {
            "type": "http",
            "scheme": "bearer",
            "description": "Token de conta de serviço (ADR 0008): `Authorization: Bearer <token>`.",
        }
