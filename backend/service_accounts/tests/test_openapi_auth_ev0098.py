"""EV-0098 — o esquema OpenAPI descreve o token de conta de serviço e não avisa por view."""

from __future__ import annotations

import io

import pytest
import yaml
from django.core.management import call_command


@pytest.mark.django_db
def test_schema_documents_bearer_token_without_warnings():
    out, err = io.StringIO(), io.StringIO()
    call_command("spectacular", "--format", "openapi", stdout=out, stderr=err)
    assert "ServiceAccountTokenAuthentication" not in err.getvalue()
    schema = yaml.safe_load(out.getvalue())
    scheme = schema["components"]["securitySchemes"]["bearerAuth"]
    assert (scheme["type"], scheme["scheme"]) == ("http", "bearer")
    securities = [
        op.get("security", [])
        for path in schema["paths"].values()
        for op in path.values()
        if isinstance(op, dict)
    ]
    assert any({"bearerAuth": []} in sec for sec in securities)
