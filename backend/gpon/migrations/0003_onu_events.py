# EV-0108: eventos de ONU (transições observadas) e o último estado conhecido de cada ONU.

import django.db.models.deletion
from django.db import migrations, models
from django.db.models import F


def fill_last_known(apps, schema_editor):
    """O estado atual de quem não está em «unknown» passa a ser o último conhecido."""
    OnuState = apps.get_model("gpon", "OnuState")
    OnuState.objects.exclude(status="unknown").update(
        last_known_status=F("status"), last_known_reason=F("reason")
    )


class Migration(migrations.Migration):

    dependencies = [
        ("gpon", "0002_repair_vsol_mac_keys"),
        ("inventory", "0073_port_optical_problem"),
    ]

    operations = [
        migrations.AddField(
            model_name="onustate",
            name="last_known_reason",
            field=models.CharField(blank=True, max_length=16),
        ),
        migrations.AddField(
            model_name="onustate",
            name="last_known_status",
            field=models.CharField(blank=True, max_length=8),
        ),
        migrations.CreateModel(
            name="OnuEvent",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("pon_id", models.CharField(max_length=32)),
                ("at", models.DateTimeField()),
                ("previous_status", models.CharField(blank=True, max_length=8)),
                ("previous_reason", models.CharField(blank=True, max_length=16)),
                ("status", models.CharField(max_length=8)),
                ("reason", models.CharField(blank=True, max_length=16)),
                ("reason_label", models.CharField(blank=True, max_length=64)),
                (
                    "device",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="inventory.device",
                    ),
                ),
                (
                    "onu",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="events",
                        to="gpon.onustate",
                    ),
                ),
            ],
            options={
                "verbose_name": "Evento de ONU",
                "verbose_name_plural": "Eventos de ONU",
                "indexes": [
                    models.Index(
                        fields=["device", "pon_id", "at"], name="gpon_evt_device_pon_at_idx"
                    ),
                    models.Index(fields=["at"], name="gpon_evt_at_idx"),
                ],
            },
        ),
        migrations.RunPython(fill_last_known, migrations.RunPython.noop),
    ]
