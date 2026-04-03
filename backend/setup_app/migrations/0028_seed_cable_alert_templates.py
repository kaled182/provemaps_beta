"""
Data migration: seed default AlertTemplate records for the 3 cable alarm types.

Creates one default template per (category, channel) combination for:
  - cable_break   × whatsapp, smtp
  - cable_attenuation × whatsapp, smtp
  - cable_normalization × whatsapp, smtp
"""
from django.db import migrations


TEMPLATES = [
    # ── Rompimento de cabo ──────────────────────────────────────────────────
    {
        "name": "Rompimento de Cabo — WhatsApp",
        "category": "cable_break",
        "channel": "whatsapp",
        "subject": "",
        "content": (
            "⚠️ *ALERTA: Rompimento de Cabo — ProveMaps*\n\n"
            "Olá {{contact_name}},\n\n"
            "Foi detectado um rompimento no enlace de fibra *{{cable_name}}*.\n\n"
            "📍 *Trecho:* {{site_a_name}} → {{site_b_name}}\n"
            "🕐 *Detectado em:* {{incident_time}}\n"
            "🔴 *Status:* {{cable_status}}\n\n"
            "Por favor, tome as providências necessárias.\n"
            "— ProveMaps"
        ),
        "is_default": True,
    },
    {
        "name": "Rompimento de Cabo — E-mail",
        "category": "cable_break",
        "channel": "smtp",
        "subject": "⚠️ Alerta: Rompimento de Cabo — {{cable_name}}",
        "content": (
            "Olá {{contact_name}},\n\n"
            "Foi detectado um rompimento no enlace de fibra {{cable_name}}.\n\n"
            "Trecho: {{site_a_name}} → {{site_b_name}}\n"
            "Detectado em: {{incident_time}}\n"
            "Status: {{cable_status}}\n\n"
            "Por favor, acesse o ProveMaps para mais detalhes e acione a equipe responsável.\n\n"
            "— ProveMaps (mensagem automática)"
        ),
        "is_default": True,
    },
    # ── Atenuação de cabo ───────────────────────────────────────────────────
    {
        "name": "Atenuação de Cabo — WhatsApp",
        "category": "cable_attenuation",
        "channel": "whatsapp",
        "subject": "",
        "content": (
            "📡 *ALERTA: Atenuação Elevada — ProveMaps*\n\n"
            "Olá {{contact_name}},\n\n"
            "O enlace *{{cable_name}}* apresenta nível óptico acima do padrão.\n\n"
            "📍 *Trecho:* {{site_a_name}} → {{site_b_name}}\n"
            "📶 *Nível óptico:* {{signal_level}} dBm  (limite: {{signal_threshold}} dBm)\n"
            "⚠️ *Classificação:* {{alarm_level}}\n"
            "🕐 *Horário:* {{incident_time}}\n\n"
            "Verifique o estado do enlace no ProveMaps.\n"
            "— ProveMaps"
        ),
        "is_default": True,
    },
    {
        "name": "Atenuação de Cabo — E-mail",
        "category": "cable_attenuation",
        "channel": "smtp",
        "subject": "📡 Alerta de Atenuação — {{cable_name}}",
        "content": (
            "Olá {{contact_name}},\n\n"
            "O enlace {{cable_name}} apresenta nível óptico acima do limite configurado.\n\n"
            "Trecho: {{site_a_name}} → {{site_b_name}}\n"
            "Nível óptico medido: {{signal_level}} dBm\n"
            "Limite configurado: {{signal_threshold}} dBm\n"
            "Classificação: {{alarm_level}}\n"
            "Horário: {{incident_time}}\n\n"
            "Acesse o ProveMaps para verificar o histórico óptico do enlace.\n\n"
            "— ProveMaps (mensagem automática)"
        ),
        "is_default": True,
    },
    # ── Normalização de serviço ─────────────────────────────────────────────
    {
        "name": "Normalização de Serviço — WhatsApp",
        "category": "cable_normalization",
        "channel": "whatsapp",
        "subject": "",
        "content": (
            "✅ *SERVIÇO NORMALIZADO — ProveMaps*\n\n"
            "Olá {{contact_name}},\n\n"
            "O enlace *{{cable_name}}* foi restabelecido com sucesso.\n\n"
            "📍 *Trecho:* {{site_a_name}} → {{site_b_name}}\n"
            "🕐 *Normalizado em:* {{incident_time}}\n"
            "⏱️ *Tempo indisponível:* {{downtime_minutes}} minutos\n\n"
            "Nenhuma ação é necessária neste momento.\n"
            "— ProveMaps"
        ),
        "is_default": True,
    },
    {
        "name": "Normalização de Serviço — E-mail",
        "category": "cable_normalization",
        "channel": "smtp",
        "subject": "✅ Serviço Normalizado — {{cable_name}}",
        "content": (
            "Olá {{contact_name}},\n\n"
            "O enlace {{cable_name}} foi restabelecido com sucesso.\n\n"
            "Trecho: {{site_a_name}} → {{site_b_name}}\n"
            "Normalizado em: {{incident_time}}\n"
            "Tempo indisponível: {{downtime_minutes}} minutos\n\n"
            "Nenhuma ação é necessária neste momento.\n\n"
            "— ProveMaps (mensagem automática)"
        ),
        "is_default": True,
    },
]


def seed_templates(apps, schema_editor):
    AlertTemplate = apps.get_model("setup_app", "AlertTemplate")
    for tpl in TEMPLATES:
        if AlertTemplate.objects.filter(
            category=tpl["category"], channel=tpl["channel"], name=tpl["name"]
        ).exists():
            continue
        AlertTemplate.objects.create(
            name=tpl["name"],
            category=tpl["category"],
            channel=tpl["channel"],
            subject=tpl.get("subject", ""),
            content=tpl["content"],
            is_default=tpl.get("is_default", False),
            is_active=True,
        )


def unseed_templates(apps, schema_editor):
    AlertTemplate = apps.get_model("setup_app", "AlertTemplate")
    names = [tpl["name"] for tpl in TEMPLATES]
    AlertTemplate.objects.filter(name__in=names).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("setup_app", "0027_alter_alerttemplate_category_alter_alerttemplate_id_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_templates, reverse_code=unseed_templates),
    ]
