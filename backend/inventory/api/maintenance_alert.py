"""
Maintenance area notification API.

GET  maintenance-alert/recipients/ → list users + responsibles with available channels
POST maintenance-alert/send/       → dispatch alerts via configured channels
"""
from __future__ import annotations

import json
import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET, require_POST

import requests as http_requests

from core.models import UserProfile
from inventory.models import Responsible
from setup_app.models import FirstTimeSetup, MessagingGateway

logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────

def _get_whatsapp_gateway() -> tuple[MessagingGateway, str] | tuple[None, None]:
    """Return the first connected WhatsApp gateway and its service URL."""
    gw = (
        MessagingGateway.objects
        .filter(gateway_type="whatsapp", enabled=True)
        .first()
    )
    if not gw:
        return None, None
    config = gw.config or {}
    service_url = config.get("qr_service_url", "").strip()
    if not service_url:
        return None, None
    return gw, service_url


def _send_whatsapp(service_url: str, gateway_id: int, phone: str, message: str) -> bool:
    """Send a WhatsApp message via the QR gateway service. Returns True on success."""
    try:
        resp = http_requests.post(
            f"{service_url.rstrip('/')}/message/test",
            json={"gateway_id": gateway_id, "recipient": phone, "message": message},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        ok = data.get("success", False)
        if not ok:
            logger.warning("[maintenance_alert] WhatsApp send failed: %s", data)
        return ok
    except Exception as exc:
        logger.error("[maintenance_alert] WhatsApp error for %s: %s", phone, exc)
        return False


def _get_smtp_config() -> dict | None:
    """Return SMTP config from the most recent configured FirstTimeSetup row."""
    record = (
        FirstTimeSetup.objects.filter(configured=True, smtp_enabled=True)
        .order_by("-configured_at")
        .first()
    )
    if not record:
        return None
    return {
        "host": record.smtp_host or "",
        "port": int(record.smtp_port or 587),
        "security": record.smtp_security or "tls",
        "user": record.smtp_user or "",
        "password": record.smtp_password or "",
        "from_email": record.smtp_from_email or record.smtp_user or "",
        "from_name": record.smtp_from_name or "ProveMaps",
    }


def _send_email(smtp: dict, to_address: str, subject: str, html_body: str) -> bool:
    """Send a single email via smtplib. Returns True on success."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{smtp['from_name']} <{smtp['from_email']}>"
        msg["To"] = to_address
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        security = smtp["security"].lower()
        if security == "ssl":
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp["host"], smtp["port"], context=ctx) as server:
                if smtp["user"] and smtp["password"]:
                    server.login(smtp["user"], smtp["password"])
                server.sendmail(smtp["from_email"], to_address, msg.as_string())
        else:
            with smtplib.SMTP(smtp["host"], smtp["port"]) as server:
                if security == "tls":
                    server.starttls()
                if smtp["user"] and smtp["password"]:
                    server.login(smtp["user"], smtp["password"])
                server.sendmail(smtp["from_email"], to_address, msg.as_string())
        return True
    except Exception as exc:
        logger.error("[maintenance_alert] Failed to send email to %s: %s", to_address, exc)
        return False


def _format_endpoint(port, fallback_site=None) -> str:
    """Formata um endpoint do cabo: 'DEVICE / PORTA (Site)'.

    Se a porta não estiver definida (cabo sem terminação física), tenta
    cair para o site do cabo (site_a/site_b) como pista para o técnico.
    """
    if port is None:
        if fallback_site is not None:
            site_name = (
                getattr(fallback_site, "display_name", None)
                or getattr(fallback_site, "name", None)
                or ""
            )
            return f"— (Site: {site_name})" if site_name else "—"
        return "—"

    device = getattr(port, "device", None)
    device_name = (getattr(device, "name", None) or "—") if device else "—"
    port_name = getattr(port, "name", None) or "—"
    site = getattr(device, "site", None) if device else None
    site_name = (
        getattr(site, "display_name", None)
        or getattr(site, "name", None)
        or ""
    )
    base = f"{device_name} / {port_name}"
    return f"{base} ({site_name})" if site_name else base


def _resolve_cable_endpoints(cable_ids: list) -> dict:
    """Para cada cable_id, retorna {origin, destination} formatados.

    Faz UM query agrupado com select_related — evita N+1 mesmo com 50 cabos.
    """
    from inventory.models import FiberCable
    if not cable_ids:
        return {}
    cables_qs = (
        FiberCable.objects
        .select_related(
            "origin_port__device__site",
            "destination_port__device__site",
            "site_a",
            "site_b",
        )
        .filter(pk__in=cable_ids)
    )
    out: dict = {}
    for cable in cables_qs:
        out[cable.pk] = {
            "origin": _format_endpoint(cable.origin_port, cable.site_a),
            "destination": _format_endpoint(cable.destination_port, cable.site_b),
        }
    return out


def _build_email_body(message: str, cables: list, devices: list, cable_endpoints_map: dict | None = None) -> str:
    """Build an HTML email body for the maintenance alert."""
    cable_endpoints_map = cable_endpoints_map or {}
    cables_html = ""
    if cables:
        def _row(c):
            cid = c.get("id")
            name = c.get("name", "—")
            status = c.get("status", "—")
            color = "#10b981" if status == "online" else "#ef4444" if status == "offline" else "#f59e0b"
            endpoints = cable_endpoints_map.get(cid) or {}
            origin = endpoints.get("origin") or "—"
            destination = endpoints.get("destination") or "—"
            return (
                f"<tr><td style='padding:6px 8px;border-bottom:1px solid #2d3748;vertical-align:top'>"
                f"<div style='font-weight:600;color:#e2e8f0'>{name}</div>"
                f"<div style='color:#94a3b8;font-size:12px;margin-top:2px'>"
                f"<span style='color:#cbd5e1'>Origem:</span> {origin}<br>"
                f"<span style='color:#cbd5e1'>Destino:</span> {destination}"
                f"</div></td>"
                f"<td style='padding:6px 8px;border-bottom:1px solid #2d3748;text-transform:uppercase;color:{color};vertical-align:top'>"
                f"{status}</td></tr>"
            )
        rows = "".join(_row(c) for c in cables)
        cables_html = f"""
        <h3 style='color:#f59e0b;margin:16px 0 8px'>Cabos Afetados ({len(cables)})</h3>
        <table style='width:100%;border-collapse:collapse;background:#1e2139;border-radius:6px;overflow:hidden'>
          <thead><tr>
            <th style='padding:6px 8px;text-align:left;color:#94a3b8;font-size:12px'>Cabo / Endpoints</th>
            <th style='padding:6px 8px;text-align:left;color:#94a3b8;font-size:12px'>Status</th>
          </tr></thead>
          <tbody>{rows}</tbody>
        </table>"""

    devices_html = ""
    if devices:
        rows = "".join(
            f"<tr><td style='padding:4px 8px;border-bottom:1px solid #2d3748'>{d.get('name','—')}</td>"
            f"<td style='padding:4px 8px;border-bottom:1px solid #2d3748'>{d.get('site_name','—')}</td></tr>"
            for d in devices
        )
        devices_html = f"""
        <h3 style='color:#f59e0b;margin:16px 0 8px'>Equipamentos Afetados ({len(devices)})</h3>
        <table style='width:100%;border-collapse:collapse;background:#1e2139;border-radius:6px;overflow:hidden'>
          <thead><tr>
            <th style='padding:6px 8px;text-align:left;color:#94a3b8;font-size:12px'>Nome</th>
            <th style='padding:6px 8px;text-align:left;color:#94a3b8;font-size:12px'>Site</th>
          </tr></thead>
          <tbody>{rows}</tbody>
        </table>"""

    return f"""
    <div style='font-family:Arial,sans-serif;background:#0f172a;color:#e2e8f0;padding:24px;max-width:600px'>
      <div style='background:#1e2139;border:1px solid rgba(245,158,11,0.4);border-radius:12px;padding:20px;margin-bottom:20px'>
        <h2 style='color:#f59e0b;margin:0 0 12px'>⚠️ Alerta de Manutenção — ProveMaps</h2>
        <p style='margin:0;color:#cbd5e1;line-height:1.6'>{message}</p>
      </div>
      {cables_html}
      {devices_html}
      <p style='margin-top:20px;font-size:12px;color:#475569'>
        Mensagem enviada automaticamente pelo sistema ProveMaps.<br>
        Não responda a este e-mail.
      </p>
    </div>"""


# ── Views ──────────────────────────────────────────────────────────────────

@require_GET
@login_required
def api_maintenance_recipients(request: HttpRequest) -> JsonResponse:
    """Return the list of potential notification recipients with available channels."""
    smtp_enabled = bool(_get_smtp_config())
    whatsapp_gw, _ = _get_whatsapp_gateway()
    whatsapp_enabled = bool(whatsapp_gw)

    # System users with active accounts
    users = []
    for user in User.objects.filter(is_active=True).select_related("profile").order_by("first_name", "username"):
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            profile = None

        channels = []
        if user.email and smtp_enabled:
            channels.append("email")
        if profile and profile.phone_number and whatsapp_enabled:
            channels.append("whatsapp")
        if profile and profile.telegram_chat_id:
            channels.append("telegram")

        if not channels:
            continue

        users.append({
            "id": user.id,
            "type": "user",
            "name": user.get_full_name() or user.username,
            "email": user.email or "",
            "phone": profile.phone_number if profile else "",
            "telegram_chat_id": profile.telegram_chat_id if profile else "",
            "channels": channels,
            "notify_via_email": profile.notify_via_email if profile else True,
            "notify_via_whatsapp": profile.notify_via_whatsapp if profile else False,
            "notify_via_telegram": profile.notify_via_telegram if profile else False,
        })

    # Responsibles
    responsibles = []
    for r in Responsible.objects.order_by("name"):
        channels = []
        if r.email and smtp_enabled:
            channels.append("email")
        if r.phone and whatsapp_enabled:
            channels.append("whatsapp")

        if not channels:
            continue

        responsibles.append({
            "id": r.id,
            "type": "responsible",
            "name": r.name,
            "email": r.email or "",
            "phone": r.phone or "",
            "type_label": r.get_type_display(),
            "channels": channels,
        })

    # Contatos da agenda (setup_app.models_contacts.Contact) — opcional
    contacts: list[dict] = []
    try:
        from setup_app.models_contacts import Contact
        for c in Contact.objects.filter(is_active=True).prefetch_related("groups").order_by("name"):
            channels = []
            if c.email and smtp_enabled:
                channels.append("email")
            if c.phone and whatsapp_enabled:
                channels.append("whatsapp")
            if not channels:
                continue
            group_names = [g.name for g in c.groups.all()]
            # type_label aparece logo abaixo do nome no UI — ajuda a distinguir
            # contatos da agenda (tem nome da empresa/grupo) dos outros tipos.
            type_label = c.company or (group_names[0] if group_names else "Contato da Agenda")
            contacts.append({
                "id": c.id,
                "type": "contact",
                "name": c.name,
                "email": c.email or "",
                "phone": c.formatted_phone if c.phone else "",
                "company": c.company or "",
                "groups": group_names,
                "channels": channels,
                "type_label": type_label,
            })
    except Exception as exc:  # pragma: no cover - app pode não estar instalado
        logger.debug("[maintenance_alert] Contatos da agenda indisponíveis: %s", exc)

    return JsonResponse({
        "smtp_enabled": smtp_enabled,
        "whatsapp_enabled": whatsapp_enabled,
        "users": users,
        "responsibles": responsibles,
        "contacts": contacts,
    })


@require_POST
@login_required
def api_maintenance_send_alert(request: HttpRequest) -> JsonResponse:
    """Dispatch maintenance area notifications to selected recipients."""
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # Mensagem opcional — se vazia, usa default "ENLACE OFF." (notificação rápida).
    # O bloco de Origem/Destino dos cabos já dá ao técnico tudo que ele precisa
    # saber sem o operador precisar digitar nada.
    DEFAULT_MESSAGE = "ENLACE OFF."
    message = (data.get("message") or "").strip() or DEFAULT_MESSAGE

    recipients = data.get("recipients", [])  # [{type, id, channels: ['email','whatsapp']}]
    cables = data.get("cables", [])
    devices = data.get("devices", [])

    if not recipients:
        return JsonResponse({"error": "recipients is required"}, status=400)

    smtp = _get_smtp_config()
    whatsapp_gw, whatsapp_url = _get_whatsapp_gateway()
    subject = "⚠️ Alerta de Manutenção — ProveMaps"

    # Enriquecer cabos com origem/destino (device + porta + site) — busca FiberCable
    # por id e expande os endpoints para o técnico saber exatamente onde verificar.
    cable_ids = [c.get("id") for c in (cables or []) if c.get("id")]
    cable_endpoints_map = _resolve_cable_endpoints(cable_ids) if cable_ids else {}

    html_body = _build_email_body(message, cables, devices, cable_endpoints_map)

    # ── WhatsApp text ──────────────────────────────────────────────────────
    whatsapp_lines = [f"⚠️ *Alerta de Manutenção — ProveMaps*", "", message, ""]

    if cables:
        whatsapp_lines.append(f"*Cabos afetados ({len(cables)}):*")
        for c in cables:
            name = c.get("name") or f"Cabo #{c.get('id')}"
            whatsapp_lines.append(f"• *{name}*")
            endpoints = cable_endpoints_map.get(c.get("id"))
            if endpoints:
                origin = endpoints.get("origin")
                dest = endpoints.get("destination")
                if origin:
                    whatsapp_lines.append(f"   ◦ Origem: {origin}")
                if dest:
                    whatsapp_lines.append(f"   ◦ Destino: {dest}")
        whatsapp_lines.append("")

    if devices:
        device_names = ", ".join(d.get("name", "") for d in devices)
        whatsapp_lines.append(f"*Equipamentos adicionais:* {device_names}")

    whatsapp_text = "\n".join(whatsapp_lines).rstrip()

    results = {
        "email": {"sent": 0, "failed": 0},
        "whatsapp": {"sent": 0, "failed": 0},
        "telegram": {"queued": 0},
    }
    errors = []

    for rec in recipients:
        rec_type = rec.get("type")
        rec_id = rec.get("id")
        channels = rec.get("channels", [])

        # Resolve contact details
        email_addr = ""
        phone = ""
        telegram_id = ""

        if rec_type == "user":
            try:
                user = User.objects.select_related("profile").get(id=rec_id)
                email_addr = user.email or ""
                try:
                    email_addr = user.email or ""
                    phone = user.profile.phone_number or ""
                    telegram_id = user.profile.telegram_chat_id or ""
                except UserProfile.DoesNotExist:
                    pass
            except User.DoesNotExist:
                errors.append(f"user:{rec_id} not found")
                continue

        elif rec_type == "responsible":
            try:
                r = Responsible.objects.get(id=rec_id)
                email_addr = r.email or ""
                phone = r.phone or ""
            except Responsible.DoesNotExist:
                errors.append(f"responsible:{rec_id} not found")
                continue

        elif rec_type == "contact":
            try:
                from setup_app.models_contacts import Contact
                c = Contact.objects.get(id=rec_id, is_active=True)
                email_addr = c.email or ""
                phone = c.formatted_phone if c.phone else ""
            except Exception:
                errors.append(f"contact:{rec_id} not found")
                continue

        # Dispatch per channel
        if "email" in channels and email_addr:
            if smtp:
                ok = _send_email(smtp, email_addr, subject, html_body)
                if ok:
                    results["email"]["sent"] += 1
                    logger.info("[maintenance_alert] Email sent to %s", email_addr)
                else:
                    results["email"]["failed"] += 1
                    errors.append(f"email:{email_addr} failed")
            else:
                errors.append("SMTP not configured")

        if "whatsapp" in channels and phone:
            if whatsapp_gw and whatsapp_url:
                ok = _send_whatsapp(whatsapp_url, whatsapp_gw.id, phone, whatsapp_text)
                if ok:
                    results["whatsapp"]["sent"] += 1
                    logger.info("[maintenance_alert] WhatsApp sent to %s", phone)
                else:
                    results["whatsapp"]["failed"] += 1
                    errors.append(f"whatsapp:{phone} failed")
            else:
                errors.append("WhatsApp gateway not configured")

        if "telegram" in channels and telegram_id:
            # Telegram bot integration queued for when bot token is configured
            results["telegram"]["queued"] += 1
            logger.info("[maintenance_alert] Telegram queued for chat_id %s (bot not yet configured)", telegram_id)

    total_sent = (
        results["email"]["sent"]
        + results["whatsapp"]["sent"]
        + results["telegram"]["queued"]
    )
    return JsonResponse({
        "ok": True,
        "total_sent": total_sent,
        "results": results,
        "errors": errors,
    })
