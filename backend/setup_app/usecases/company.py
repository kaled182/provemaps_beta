"""Perfil da empresa (`CompanyProfile`, registo único). Saiu de `setup_app/api_views.py` em EV-0017e."""

from __future__ import annotations

from typing import Any

from ..models import CompanyProfile
from .common import to_bool

COMPANY_TEXT_FIELDS = [
    "company_legal_name",
    "company_trade_name",
    "company_doc",
    "company_owner_name",
    "company_owner_doc",
    "company_owner_birth",
    "company_state_reg",
    "company_city_reg",
    "company_fistel",
    "company_created_date",
    "address_zip",
    "address_street",
    "address_number",
    "address_district",
    "address_city",
    "address_state",
    "address_country",
    "address_extra",
    "address_reference",
    "address_coords",
    "address_complex",
    "address_ibge",
]
COMPANY_BOOL_FIELDS = ["company_active", "company_reports_active"]


def get_or_create_company_profile() -> CompanyProfile:
    profile = CompanyProfile.objects.first()
    if not profile:
        profile = CompanyProfile.objects.create()
    return profile


def file_info(field, request=None) -> dict[str, str]:
    """`{name, url}` de um FileField; a URL fica absoluta quando há `request`."""
    if not field or not getattr(field, "name", ""):
        return {"name": "", "url": ""}
    try:
        url = field.url
    except Exception:
        url = ""
    if url and request is not None:
        url = request.build_absolute_uri(url)
    return {"name": field.name, "url": url}


def serialize_company_profile(profile: CompanyProfile, request=None) -> dict[str, Any]:
    data: dict[str, Any] = {field: getattr(profile, field) for field in COMPANY_TEXT_FIELDS[:10]}
    data["company_active"] = profile.company_active
    data["company_reports_active"] = profile.company_reports_active
    data.update({field: getattr(profile, field) for field in COMPANY_TEXT_FIELDS[10:]})
    data["assets_logo"] = file_info(profile.assets_logo, request)
    data["assets_cert_file"] = file_info(profile.assets_cert_file, request)
    data["updated_at"] = profile.updated_at.isoformat() if profile.updated_at else ""
    return data


def update_company_profile(profile: CompanyProfile, data, files=None) -> CompanyProfile:
    """Atualização parcial: só as chaves presentes; ficheiros por `files`; a senha do
    certificado só muda quando vem preenchida."""
    files = files or {}
    for field in COMPANY_TEXT_FIELDS:
        if field in data:
            setattr(profile, field, (data.get(field) or "").strip())
    for field in COMPANY_BOOL_FIELDS:
        if field in data:
            setattr(profile, field, to_bool(data.get(field)))
    if "assets_logo" in files:
        profile.assets_logo = files["assets_logo"]
    if "assets_cert_file" in files:
        profile.assets_cert_file = files["assets_cert_file"]
    if data.get("assets_cert_password"):
        profile.assets_cert_password = data.get("assets_cert_password") or ""
    profile.save()
    return profile
