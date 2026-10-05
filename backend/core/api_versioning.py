"""Versionamento único da API: o prefixo ``/api/v<N>/`` do caminho (EV-0030).

O URLconf monta a API sob um prefixo literal ``api/v1/`` (sem ``<version>`` nos
padrões), por isso ``URLPathVersioning`` não serve; ``NamespaceVersioning``
leria os namespaces (``inventory-api``…) como versões. Esta classe lê a versão
do caminho e trata as rotas legadas sem prefixo (``/api/users/``,
``/api/config/``) como ``v1`` — é a única versão que existe.
"""

from __future__ import annotations

import re

from rest_framework import exceptions
from rest_framework.versioning import BaseVersioning

_VERSION_IN_PATH = re.compile(r"^/api/(v\d+)/")


class PathPrefixVersioning(BaseVersioning):
    default_version = "v1"
    allowed_versions = ["v1"]
    version_param = "version"
    invalid_version_message = "Invalid version in URL path."

    def determine_version(self, request, *args, **kwargs):  # type: ignore[override]
        match = _VERSION_IN_PATH.match(request.path or "")
        version = match.group(1) if match else self.default_version
        if not self.is_allowed_version(version):
            raise exceptions.NotFound(self.invalid_version_message)
        return version
