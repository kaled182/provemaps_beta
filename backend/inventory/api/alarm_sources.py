"""
Alarm configuration sources API.

GET /api/v1/inventory/alarm-config-sources/
Returns the available targets (users, contact groups, contacts) for alarm
configurations, accessible to any authenticated user.
"""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET

from core.models import UserProfile, Department

try:
    from setup_app.models_contacts import Contact, ContactGroup
except Exception:
    Contact = None
    ContactGroup = None

User = get_user_model()


@require_GET
@login_required
def api_alarm_config_sources(request: HttpRequest) -> JsonResponse:
    """
    Return all target sources available for alarm configuration:
      - system_users  → auth.User active accounts
      - contact_groups → ContactGroup objects
      - contacts       → Contact objects (active)
    """

    # ── System users (auth.User) ────────────────────────────────────────────
    system_users = []
    for user in (
        User.objects
        .filter(is_active=True)
        .select_related("profile")
        .order_by("first_name", "username")
    ):
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            profile = None

        system_users.append({
            "id": user.id,
            "name": user.get_full_name() or user.username,
            "username": user.username,
            "email": user.email or "",
            "phone": profile.phone_number if profile else "",
        })

    # ── Departments ─────────────────────────────────────────────────────────
    departments = []
    for dept in Department.objects.filter(is_active=True).order_by("name"):
        member_count = dept.user_profiles.count()
        departments.append({
            "id": dept.id,
            "name": dept.name,
            "member_count": member_count,
        })

    # ── Contact groups ──────────────────────────────────────────────────────
    contact_groups = []
    if ContactGroup is not None:
        for group in ContactGroup.objects.order_by("name"):
            cnt = group.contacts.count() if hasattr(group, "contacts") else 0
            contact_groups.append({
                "id": group.id,
                "name": group.name,
                "contact_count": cnt,
            })

    # ── Contacts ────────────────────────────────────────────────────────────
    contacts = []
    if Contact is not None:
        for contact in Contact.objects.filter(is_active=True).order_by("name"):
            parts = []
            if contact.phone:
                parts.append(contact.phone)
            if contact.email:
                parts.append(contact.email)
            if contact.company:
                parts.append(contact.company)
            contacts.append({
                "id": contact.id,
                "name": contact.name or "",
                "phone": contact.phone or "",
                "email": contact.email or "",
                "company": contact.company or "",
                "summary": " • ".join(parts) if parts else "Sem detalhes",
            })

    return JsonResponse({
        "system_users": system_users,
        "departments": departments,
        "contact_groups": contact_groups,
        "contacts": contacts,
    })
