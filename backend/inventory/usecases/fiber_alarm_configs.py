"""Use cases for managing fiber cable alarm configurations."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.db import transaction
from django.utils import timezone

from inventory.models import FiberCable, FiberCableAlarmConfig
try:
    from core.models import Department
except Exception:  # pragma: no cover
    Department = None  # type: ignore

try:  # Optional dependency: contacts app might be disabled in some deployments
    from setup_app.models_contacts import Contact, ContactGroup
except Exception:  # pragma: no cover - fallback when setup_app not available
    Contact = None  # type: ignore
    ContactGroup = None  # type: ignore

try:  # Optional dependency: alert templates may be disabled
    from setup_app.models import AlertTemplate
except Exception:  # pragma: no cover - fallback when setup_app not available
    AlertTemplate = None  # type: ignore

UserModel = get_user_model()

ALLOWED_CHANNELS = {"email", "whatsapp", "sms", "telegram"}
DEFAULT_CHANNEL_ORDER = ("email", "whatsapp", "sms", "telegram")
ALLOWED_TARGETS = {
    FiberCableAlarmConfig.TARGET_DEPARTMENT_GROUP,
    FiberCableAlarmConfig.TARGET_SYSTEM_USER,
    FiberCableAlarmConfig.TARGET_CONTACT,
    FiberCableAlarmConfig.TARGET_DEPARTMENT,
}
ALLOWED_TRIGGERS = {
    FiberCableAlarmConfig.TRIGGER_WARNING,
    FiberCableAlarmConfig.TRIGGER_CRITICAL,
}
ALLOWED_ALERT_TYPES = {
    FiberCableAlarmConfig.ALERT_BREAK,
    FiberCableAlarmConfig.ALERT_ATTENUATION,
    FiberCableAlarmConfig.ALERT_NORMALIZATION,
}

# Map alert_type → AlertTemplate category
ALERT_TYPE_TO_CATEGORY = {
    FiberCableAlarmConfig.ALERT_BREAK: 'cable_break',
    FiberCableAlarmConfig.ALERT_ATTENUATION: 'cable_attenuation',
    FiberCableAlarmConfig.ALERT_NORMALIZATION: 'cable_normalization',
}

DEFAULT_TEMPLATE_CATEGORY = 'cable_break'


class FiberCableAlarmError(Exception):
    """Base error for alarm configuration operations."""


class FiberCableAlarmValidationError(FiberCableAlarmError):
    """Raised when input data fails validation."""


@dataclass
class TargetContext:
    target_type: str
    target_id: int | None
    display: str
    snapshot: dict[str, object]
    model_object: object | None


def _template_snapshot(template: 'AlertTemplate') -> dict[str, object]:  # type: ignore[name-defined]
    updated_at = getattr(template, 'updated_at', None)
    try:
        updated_at_iso = timezone.localtime(updated_at).isoformat() if updated_at else None
    except Exception:  # pragma: no cover - timezone edge cases
        updated_at_iso = updated_at.isoformat() if updated_at else None
    return {
        'id': template.pk,
        'name': template.name,
        'description': template.description,
        'subject': template.subject,
        'content': template.content,
        'placeholders': list(template.placeholders or []),
        'channel': template.channel,
        'category': template.category,
        'is_default': template.is_default,
        'updated_at': updated_at_iso,
    }


def _category_for_alert_type(alert_type: str) -> str:
    """Return the AlertTemplate category that corresponds to an alert_type."""
    return ALERT_TYPE_TO_CATEGORY.get(alert_type, DEFAULT_TEMPLATE_CATEGORY)


def _normalize_template_category(raw_category: object, alert_type: str = '') -> str:
    if AlertTemplate is None:
        return _category_for_alert_type(alert_type)
    # Prefer the category derived from alert_type when no explicit category given
    category = str(raw_category or '').strip() or _category_for_alert_type(alert_type)
    valid_categories = {choice[0] for choice in getattr(AlertTemplate, 'CATEGORY_CHOICES', [])}
    if category not in valid_categories:
        return _category_for_alert_type(alert_type)
    return category


def _build_template_metadata(
    category: str,
    channels: Sequence[str],
    requested_map: object,
) -> dict[str, object]:
    metadata: dict[str, object] = {
        'category': category,
        'bindings': {},
        'snapshots': {},
    }

    if not channels:
        return metadata
    if AlertTemplate is None:
        return metadata

    channels_list = [str(channel).strip().lower() for channel in channels if channel]
    channels_set = set(channels_list)
    resolved: dict[str, int] = {}
    snapshots: dict[str, dict[str, object]] = {}

    if isinstance(requested_map, dict):
        for raw_channel, template_id in requested_map.items():
            channel = str(raw_channel).strip().lower()
            if channel not in channels_set:
                continue
            try:
                template_pk = int(template_id)
            except (TypeError, ValueError):
                raise FiberCableAlarmValidationError('Modelo de aviso inválido.') from None
            try:
                template = AlertTemplate.objects.get(pk=template_pk, is_active=True)
            except AlertTemplate.DoesNotExist:
                raise FiberCableAlarmValidationError('Modelo de aviso selecionado não encontrado.') from None
            if template.channel != channel:
                raise FiberCableAlarmValidationError('Canal do modelo não corresponde ao canal selecionado.')
            if template.category != category:
                raise FiberCableAlarmValidationError('Modelo de aviso incompatível com esta categoria de alerta.')
            resolved[channel] = template.pk
            snapshots[channel] = _template_snapshot(template)

    missing_channels = [channel for channel in channels_list if channel not in resolved]
    if missing_channels:
        defaults = (
            AlertTemplate.objects.filter(
                category=category,
                channel__in=missing_channels,
                is_active=True,
            )
            .order_by('-is_default', '-updated_at', 'name')
        )
        for template in defaults:
            channel = template.channel
            if channel not in resolved:
                resolved[channel] = template.pk
                snapshots[channel] = _template_snapshot(template)

    metadata['bindings'] = resolved
    metadata['snapshots'] = snapshots
    metadata['resolved_at'] = timezone.now().isoformat()
    return metadata


def _normalize_channels(raw_channels: Sequence[object] | object | None) -> list[str]:
    channels: list[str] = []
    if raw_channels is None:
        return channels
    if isinstance(raw_channels, (str, bytes)):
        candidates: Iterable[str] = str(raw_channels).split(",")
    elif isinstance(raw_channels, Sequence):
        candidates = (str(item) for item in raw_channels)
    else:
        return channels

    seen = set()
    for candidate in candidates:
        key = candidate.strip().lower()
        if key in ALLOWED_CHANNELS and key not in seen:
            seen.add(key)
            channels.append(key)

    # Preserve canonical order for stable diffs/UI
    channels.sort(key=lambda value: DEFAULT_CHANNEL_ORDER.index(value) if value in DEFAULT_CHANNEL_ORDER else len(DEFAULT_CHANNEL_ORDER))
    return channels


def _resolve_user(user_id: int | str | None) -> AbstractBaseUser | None:
    if not user_id:
        return None
    try:
        return UserModel.objects.get(pk=user_id)
    except (UserModel.DoesNotExist, ValueError, TypeError):
        raise FiberCableAlarmValidationError("Usuário do sistema não encontrado") from None


def _resolve_department(dept_id: int | str | None):
    if dept_id in (None, ""):
        return None
    if Department is None:
        raise FiberCableAlarmValidationError("Módulo de departamentos não disponível")
    try:
        return Department.objects.get(pk=dept_id)
    except (Department.DoesNotExist, ValueError, TypeError):
        raise FiberCableAlarmValidationError("Departamento não encontrado") from None


def _resolve_contact(contact_id: int | str | None):
    if contact_id in (None, ""):
        return None
    if Contact is None:
        raise FiberCableAlarmValidationError("Módulo de contatos não disponível")
    try:
        return Contact.objects.get(pk=contact_id)
    except (Contact.DoesNotExist, ValueError, TypeError):
        raise FiberCableAlarmValidationError("Contato não encontrado") from None


def _resolve_group(group_id: int | str | None):
    if group_id in (None, ""):
        return None
    if ContactGroup is None:
        raise FiberCableAlarmValidationError("Módulo de grupos de contato não disponível")
    try:
        return ContactGroup.objects.get(pk=group_id)
    except (ContactGroup.DoesNotExist, ValueError, TypeError):
        raise FiberCableAlarmValidationError("Grupo de contatos não encontrado") from None


def _extract_target_context(payload: dict[str, object]) -> TargetContext:
    raw_target = str(payload.get("target") or payload.get("target_type") or "").strip().lower()
    if raw_target not in ALLOWED_TARGETS:
        raise FiberCableAlarmValidationError("Tipo de destino inválido")

    if raw_target == FiberCableAlarmConfig.TARGET_DEPARTMENT_GROUP:
        group = _resolve_group(payload.get("department_group") or payload.get("target_id"))
        if group is None:
            raise FiberCableAlarmValidationError("Grupo de departamento obrigatório")
        contact_count = group.contacts.count() if hasattr(group, "contacts") else None
        display = group.name
        if contact_count is not None:
            display = f"{group.name} ({contact_count} contatos)"
        snapshot = {
            "name": group.name,
            "display": display,
            "contact_count": contact_count,
        }
        return TargetContext(raw_target, int(group.pk), display, snapshot, group)

    if raw_target == FiberCableAlarmConfig.TARGET_SYSTEM_USER:
        system_user = _resolve_user(payload.get("system_user") or payload.get("target_id"))
        if system_user is None:
            raise FiberCableAlarmValidationError("Usuário do sistema obrigatório")
        display = system_user.get_full_name() or system_user.username or system_user.email or str(system_user.pk)
        snapshot = {
            "name": display,
            "display": display,
            "username": system_user.username,
            "email": getattr(system_user, "email", ""),
        }
        return TargetContext(raw_target, int(system_user.pk), display, snapshot, system_user)

    if raw_target == FiberCableAlarmConfig.TARGET_DEPARTMENT:
        dept = _resolve_department(payload.get("department") or payload.get("target_id"))
        if dept is None:
            raise FiberCableAlarmValidationError("Departamento obrigatório")
        member_count = dept.user_profiles.count() if hasattr(dept, "user_profiles") else None
        display = dept.name
        if member_count is not None:
            display = f"{dept.name} ({member_count} membros)"
        snapshot = {"name": dept.name, "display": display, "member_count": member_count}
        return TargetContext(raw_target, int(dept.pk), display, snapshot, dept)

    contact = _resolve_contact(payload.get("contact") or payload.get("target_id"))
    if contact is None:
        raise FiberCableAlarmValidationError("Contato obrigatório")
    display = contact.name or contact.phone or str(contact.pk)
    snapshot = {
        "name": contact.name,
        "display": display,
        "phone": getattr(contact, "phone", ""),
        "email": getattr(contact, "email", ""),
        "company": getattr(contact, "company", ""),
    }
    return TargetContext(raw_target, int(contact.pk), display, snapshot, contact)


def alarm_config_to_payload(config: FiberCableAlarmConfig) -> dict[str, object]:
    """Serialize a FiberCableAlarmConfig into a DTO expected by the frontend."""

    target_id: int | None
    if config.target_type == FiberCableAlarmConfig.TARGET_DEPARTMENT_GROUP:
        target_id = config.contact_group_id
    elif config.target_type == FiberCableAlarmConfig.TARGET_SYSTEM_USER:
        target_id = config.system_user_id
    elif config.target_type == FiberCableAlarmConfig.TARGET_DEPARTMENT:
        target_id = config.department_id
    else:
        target_id = config.contact_id

    created_by_snapshot: dict[str, object] | None = None
    if config.created_by_id:
        user = config.created_by
        if user:
            created_by_snapshot = {
                "id": user.pk,
                "name": user.get_full_name() or user.username,
                "email": getattr(user, "email", ""),
            }
        else:  # pragma: no cover - rare case when user deleted
            created_by_snapshot = {"id": config.created_by_id}

    metadata = config.metadata or {}

    payload: dict[str, object] = {
        "id": config.pk,
        "fiber_cable_id": config.fiber_cable_id,
        "target_type": config.target_type,
        "target_id": target_id,
        "target_display": config.target_display,
        "channels": list(config.channels or []),
        "trigger_level": config.trigger_level,
        "alert_type": config.alert_type or "",
        "persist_minutes": config.persist_minutes,
        "description": config.description or "",
        "target_snapshot": config.target_snapshot or {},
        "metadata": metadata,
        "created_at": timezone.localtime(config.created_at).isoformat(),
        "updated_at": timezone.localtime(config.updated_at).isoformat(),
    }
    if created_by_snapshot:
        payload["created_by"] = created_by_snapshot
    templates_meta = metadata.get('templates') if isinstance(metadata, dict) else None
    if isinstance(templates_meta, dict):
        payload['templates'] = templates_meta
        payload['template_category'] = templates_meta.get('category')
    return payload


def list_alarm_configs(cable: FiberCable) -> list[dict[str, object]]:
    """Return alarm configurations for a cable ordered by newest first."""

    configs = (
        FiberCableAlarmConfig.objects.filter(fiber_cable=cable)
        .select_related("contact_group", "contact", "system_user", "department", "created_by")
        .order_by("-created_at", "id")
    )
    return [alarm_config_to_payload(config) for config in configs]


@transaction.atomic
def create_alarm_config(
    cable: FiberCable,
    payload: dict[str, object],
    requested_by: AbstractBaseUser | None = None,
) -> dict[str, object]:
    """Create a new alarm configuration for a cable and return its payload."""

    target = _extract_target_context(payload)
    channels = _normalize_channels(payload.get("channels"))
    if not channels:
        raise FiberCableAlarmValidationError("Selecione pelo menos um canal de notificação")

    trigger_level = str(payload.get("trigger_level") or payload.get("triggerLevel") or FiberCableAlarmConfig.TRIGGER_WARNING).strip().lower()
    if trigger_level not in ALLOWED_TRIGGERS:
        trigger_level = FiberCableAlarmConfig.TRIGGER_WARNING

    alert_type = str(payload.get("alert_type") or payload.get("alertType") or "").strip().lower()
    if alert_type not in ALLOWED_ALERT_TYPES:
        alert_type = ""

    persist_raw = payload.get("persist_minutes") or payload.get("persistMinutes") or 0
    try:
        persist_minutes = max(int(persist_raw), 0)
    except (TypeError, ValueError):
        persist_minutes = 0

    description = str(payload.get("description") or payload.get("notes") or "").strip()
    metadata_raw = payload.get("metadata")
    metadata = metadata_raw if isinstance(metadata_raw, dict) else {}

    template_category = _normalize_template_category(payload.get('template_category'), alert_type)
    templates_meta = _build_template_metadata(template_category, channels, payload.get('templates'))
    if templates_meta:
        metadata = dict(metadata)
        metadata['templates'] = templates_meta

    created_by = requested_by if getattr(requested_by, "is_authenticated", False) else None

    config = FiberCableAlarmConfig(
        fiber_cable=cable,
        target_type=target.target_type,
        channels=channels,
        trigger_level=trigger_level,
        alert_type=alert_type,
        persist_minutes=persist_minutes,
        description=description,
        metadata=metadata,
        target_snapshot=target.snapshot,
        created_by=created_by,
    )

    if target.target_type == FiberCableAlarmConfig.TARGET_DEPARTMENT_GROUP:
        config.contact_group_id = target.target_id
    elif target.target_type == FiberCableAlarmConfig.TARGET_SYSTEM_USER:
        config.system_user_id = target.target_id
    elif target.target_type == FiberCableAlarmConfig.TARGET_DEPARTMENT:
        config.department_id = target.target_id
    else:
        config.contact_id = target.target_id

    config.save()
    return alarm_config_to_payload(config)


# ── Envio de teste manual ──────────────────────────────────────────────────

def _resolve_recipients(config: FiberCableAlarmConfig) -> list[dict[str, str]]:
    """Resolve a lista de destinatários ({name, phone, email}) para uma config.

    Encapsula a regra por target_type — DEPARTMENT_GROUP itera contatos do
    grupo, SYSTEM_USER usa UserProfile, DEPARTMENT itera UserProfiles do
    departamento, CONTACT é um único.
    """
    out: list[dict[str, str]] = []
    target_type = config.target_type

    if target_type == FiberCableAlarmConfig.TARGET_DEPARTMENT_GROUP and config.contact_group_id:
        group = config.contact_group
        if group is None:
            return out
        for c in group.contacts.filter(is_active=True):
            phone = c.formatted_phone if c.phone else ""
            out.append({"name": c.name or c.phone or "Contato", "phone": phone, "email": c.email or ""})
        return out

    if target_type == FiberCableAlarmConfig.TARGET_CONTACT and config.contact_id:
        c = config.contact
        if c is None:
            return out
        phone = c.formatted_phone if c.phone else ""
        return [{"name": c.name or c.phone or "Contato", "phone": phone, "email": c.email or ""}]

    if target_type == FiberCableAlarmConfig.TARGET_SYSTEM_USER and config.system_user_id:
        u = config.system_user
        if u is None:
            return out
        profile = getattr(u, "profile", None)
        phone = (getattr(profile, "phone_number", "") or "").strip()
        return [{
            "name": u.get_full_name() or u.username or u.email or f"User {u.pk}",
            "phone": phone,
            "email": (u.email or "").strip(),
        }]

    if target_type == FiberCableAlarmConfig.TARGET_DEPARTMENT and config.department_id:
        dept = config.department
        if dept is None or not hasattr(dept, "user_profiles"):
            return out
        for p in dept.user_profiles.select_related("user").all():
            phone = (p.phone_number or "").strip()
            user = p.user
            out.append({
                "name": (user.get_full_name() if user else "") or (user.username if user else "") or "Usuário",
                "phone": phone,
                "email": (user.email if user else "").strip(),
            })
        return out

    return out


def _format_test_message(config: FiberCableAlarmConfig) -> str:
    """Compõe a mensagem de teste — texto pronto para WhatsApp/SMS."""
    cable_name = config.fiber_cable.name or f"Cabo #{config.fiber_cable_id}"
    alert_label = {
        FiberCableAlarmConfig.ALERT_BREAK: "Rompimento",
        FiberCableAlarmConfig.ALERT_ATTENUATION: "Atenuação",
        FiberCableAlarmConfig.ALERT_NORMALIZATION: "Normalização",
    }.get(config.alert_type, config.alert_type or "—")

    trigger_label = {
        FiberCableAlarmConfig.TRIGGER_WARNING: "Atenção",
        FiberCableAlarmConfig.TRIGGER_CRITICAL: "Crítico",
    }.get(config.trigger_level, config.trigger_level or "—")

    return (
        f"🧪 *[TESTE] ProveMaps — Configuração de Alarme*\n\n"
        f"Cabo: *{cable_name}*\n"
        f"Tipo de evento: *{alert_label}*\n"
        f"Nível de disparo: *{trigger_label}*\n"
        f"Persistência mínima: *{config.persist_minutes} min*\n\n"
        f"Esta é uma mensagem de _teste manual_ para validar a configuração "
        f"de alarme. *Nenhum incidente real ocorreu.*"
    )


def _format_event_endpoints_block(cable) -> str:
    """Linha multi-line com Origem/Destino do cabo (Device + Porta + Site).
    Vazio se ambos endpoints não tiverem porta cadastrada."""
    from inventory.api.maintenance_alert import _format_endpoint
    lines = []
    origin = _format_endpoint(cable.origin_port, getattr(cable, "site_a", None))
    dest = _format_endpoint(cable.destination_port, getattr(cable, "site_b", None))
    if origin and origin != "—":
        lines.append(f"   ◦ Origem: {origin}")
    if dest and dest != "—":
        lines.append(f"   ◦ Destino: {dest}")
    return "\n".join(lines)


def _format_event_message(config: FiberCableAlarmConfig, alert_type: str, event=None) -> str:
    """Mensagem REAL (sem prefixo TESTE) para um evento detectado pelo dispatcher.

    Formato segue o mesmo padrão de manutenção (familiar pro técnico):
      ⚠️ *Alerta — ProveMaps*
      <descrição do evento>
      *Cabos afetados (1):*
      • *NOME*
         ◦ Origem: ...
         ◦ Destino: ...
    """
    cable = config.fiber_cable
    cable_name = cable.name or f"Cabo #{cable.pk}"

    headline = {
        FiberCableAlarmConfig.ALERT_BREAK: "⚠️ *Alerta — Cabo OFFLINE*",
        FiberCableAlarmConfig.ALERT_ATTENUATION: "⚠️ *Alerta — Sinal Degradado*",
        FiberCableAlarmConfig.ALERT_NORMALIZATION: "✅ *Cabo NORMALIZADO*",
    }.get(alert_type, "⚠️ *Alerta — ProveMaps*")

    description = {
        FiberCableAlarmConfig.ALERT_BREAK: "ENLACE OFF — possível rompimento ou queda de equipamento.",
        FiberCableAlarmConfig.ALERT_ATTENUATION: "Atenuação detectada no sinal óptico.",
        FiberCableAlarmConfig.ALERT_NORMALIZATION: "Serviço restabelecido — operação normal.",
    }.get(alert_type, "Mudança de estado detectada.")

    lines = [headline, "", description, "", f"*Cabos afetados (1):*", f"• *{cable_name}*"]
    endpoints = _format_event_endpoints_block(cable)
    if endpoints:
        lines.append(endpoints)

    if event is not None and getattr(event, "detected_reason", ""):
        lines.append("")
        lines.append(f"_Motivo: {event.detected_reason}_")

    return "\n".join(lines)


def _dispatch_message(
    config: FiberCableAlarmConfig,
    message: str,
    *,
    event=None,
    alert_type: str = "",
    is_test: bool = False,
    log: bool = True,
) -> list[dict[str, object]]:
    """Despacha `message` para todos os destinatários da config nos canais habilitados.

    Núcleo compartilhado entre `send_test_alarm` (manual) e `dispatch_pending_alarms`
    (automático). Quando `log=True`, persiste cada tentativa em FiberAlarmNotificationLog
    para auditoria e dedupe.
    """
    from inventory.api.maintenance_alert import _get_whatsapp_gateway, _send_whatsapp
    from inventory.models import FiberAlarmNotificationLog

    channels = list(config.channels or [])
    recipients = _resolve_recipients(config)
    results: list[dict[str, object]] = []

    if not recipients:
        return results

    def _log(channel: str, recipient: dict, success: bool, error: str = ""):
        if not log:
            return
        try:
            FiberAlarmNotificationLog.objects.create(
                config=config,
                event=event,
                alert_type=alert_type or config.alert_type or "",
                channel=channel,
                recipient_label=str(recipient.get("name") or "")[:200],
                recipient_phone=str(recipient.get("phone") or "")[:32],
                recipient_email=str(recipient.get("email") or "")[:200],
                success=success,
                error=error[:1000] if error else "",
                is_test=is_test,
            )
        except Exception as exc:  # pragma: no cover - logging falha não deve quebrar envio
            import logging as _logging
            _logging.getLogger(__name__).warning("Failed to log notification: %s", exc)

    if "whatsapp" in channels:
        gw, service_url = _get_whatsapp_gateway()
        if not gw:
            err = "Gateway WhatsApp não configurado/habilitado"
            results.append({"channel": "whatsapp", "recipient": "—", "success": False, "error": err})
            _log("whatsapp", {"name": "—"}, False, err)
        else:
            for r in recipients:
                phone = r.get("phone", "")
                if not phone:
                    err = "Sem telefone cadastrado"
                    results.append({"channel": "whatsapp", "recipient": r.get("name") or "—",
                                    "phone": "", "success": False, "error": err})
                    _log("whatsapp", r, False, err)
                    continue
                ok = _send_whatsapp(service_url, gw.id, phone, message)
                err = "" if ok else "Falha no envio (ver logs)"
                results.append({
                    "channel": "whatsapp",
                    "recipient": r.get("name") or phone,
                    "phone": phone,
                    "success": bool(ok),
                    **({"error": err} if err else {}),
                })
                _log("whatsapp", r, bool(ok), err)

    return results


def send_test_alarm(config: FiberCableAlarmConfig) -> dict[str, object]:
    """Envia uma mensagem de TESTE para os destinatários da config.

    Retorna { ok, sent, total, results, message } — usado pelo botão
    "Enviar Teste" no UI.
    """
    message = _format_test_message(config)
    recipients = _resolve_recipients(config)
    if not recipients:
        return {
            "ok": False, "sent": 0, "total": 0, "results": [], "message": message,
            "error": "Nenhum destinatário com dados de contato encontrado",
        }

    results = _dispatch_message(config, message, is_test=True)
    sent_ok = sum(1 for r in results if r.get("success"))
    return {
        "ok": sent_ok > 0,
        "sent": sent_ok,
        "total": len(results),
        "results": results,
        "message": message,
    }


# ── Dispatcher automático (Fase A) ─────────────────────────────────────────

# Mapa transição (previous_status, new_status) → alert_type da config
def _classify_transition(previous_status: str, new_status: str) -> str | None:
    """Decide qual alert_type da config se aplica a uma transição de status.

    Regras (status no banco usa: up, down, degraded, unknown):
      → down       : ALERT_BREAK (rompimento confirmado)
      → degraded   : ALERT_ATTENUATION (sinal degradado)
      → up         : ALERT_NORMALIZATION (volta ao normal)
                     desde que viesse de um estado adverso
      qualquer outra: None (não dispara — transições para/de unknown são ruidosas)
    """
    prev = (previous_status or "").lower().strip()
    new = (new_status or "").lower().strip()
    if new == "down":
        return FiberCableAlarmConfig.ALERT_BREAK
    if new == "degraded":
        return FiberCableAlarmConfig.ALERT_ATTENUATION
    if new == "up" and prev in ("down", "degraded"):
        return FiberCableAlarmConfig.ALERT_NORMALIZATION
    return None


def dispatch_pending_alarms(window_minutes: int = 10) -> dict[str, object]:
    """Lê `FiberEvent` recentes, faz match com configs e envia notificações.

    - `window_minutes`: olha eventos das últimas N minutes (default 10).
      Janela maior que o intervalo da Celery beat (1 min) = tolerância caso
      uma execução perca a janela; o dedupe via FiberAlarmNotificationLog
      garante que ninguém recebe a mesma notificação 2x.
    - Aplica `persist_minutes` da config: só dispara se o evento já dura ≥ N min
      (skipa eventos muito recentes que podem reverter sozinhos).
    """
    import logging as _logging
    from inventory.models import FiberEvent, FiberAlarmNotificationLog
    log = _logging.getLogger(__name__)

    cutoff = timezone.now() - timezone.timedelta(minutes=window_minutes) \
        if hasattr(timezone, "timedelta") else None
    if cutoff is None:
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(minutes=window_minutes)

    events_qs = (
        FiberEvent.objects
        .select_related("fiber")
        .filter(timestamp__gte=cutoff)
        .order_by("timestamp")
    )

    summary = {"events_scanned": 0, "events_matched": 0, "configs_evaluated": 0,
               "sent": 0, "failed": 0, "skipped_persist": 0, "skipped_dedupe": 0}

    now = timezone.now()
    for event in events_qs:
        summary["events_scanned"] += 1
        alert_type = _classify_transition(event.previous_status, event.new_status)
        if not alert_type:
            continue
        summary["events_matched"] += 1

        configs = (
            FiberCableAlarmConfig.objects
            .filter(fiber_cable=event.fiber, alert_type=alert_type)
            .select_related("contact_group", "contact", "system_user", "department")
        )

        for config in configs:
            summary["configs_evaluated"] += 1

            # Persistência mínima: o evento precisa ter pelo menos N min de idade
            if config.persist_minutes and config.persist_minutes > 0:
                age_min = (now - event.timestamp).total_seconds() / 60.0
                if age_min < config.persist_minutes:
                    summary["skipped_persist"] += 1
                    continue

            # Dedupe: não notificar 2x o mesmo (config, event, sucesso)
            already = FiberAlarmNotificationLog.objects.filter(
                config=config, event=event, success=True,
            ).exists()
            if already:
                summary["skipped_dedupe"] += 1
                continue

            message = _format_event_message(config, alert_type, event=event)
            try:
                results = _dispatch_message(
                    config, message,
                    event=event, alert_type=alert_type, is_test=False,
                )
                summary["sent"] += sum(1 for r in results if r.get("success"))
                summary["failed"] += sum(1 for r in results if not r.get("success"))
            except Exception as exc:  # pragma: no cover - safety
                log.exception("dispatch_pending_alarms: failed for config=%s event=%s", config.pk, event.pk)
                summary["failed"] += 1

    return summary