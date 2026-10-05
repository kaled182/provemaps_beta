"""Views do perfil da empresa: `/setup_app/api/company-profile/[update/]`.

Finas de propósito (EV-0017e): a lógica está em `setup_app.usecases.company`.
"""

from __future__ import annotations

import json

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from ..usecases import company as usecase
from ._auth import staff_required


@require_GET
@staff_required
def get_company_profile(request):
    try:
        profile = usecase.get_or_create_company_profile()
        return JsonResponse(
            {
                "success": True,
                "profile": usecase.serialize_company_profile(profile, request=request),
            }
        )
    except Exception as exc:
        return JsonResponse({"success": False, "message": f"Server error: {exc}"}, status=500)


@require_POST
@staff_required
def update_company_profile(request):
    """Aceita JSON ou `multipart/form-data` (logo e certificado vêm como ficheiros)."""
    try:
        profile = usecase.get_or_create_company_profile()
        if (request.content_type or "").startswith("multipart/form-data"):
            data = request.POST
        else:
            data = json.loads(request.body or "{}")
        usecase.update_company_profile(profile, data, request.FILES)
        return JsonResponse(
            {
                "success": True,
                "message": "Cadastro atualizado.",
                "profile": usecase.serialize_company_profile(profile, request=request),
            }
        )
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "message": "JSON inválido."}, status=400)
    except Exception as exc:
        return JsonResponse({"success": False, "message": f"Server error: {exc}"}, status=500)
