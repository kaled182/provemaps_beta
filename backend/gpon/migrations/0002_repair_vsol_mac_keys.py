"""EV-0099: o template VSOL do Zabbix apaga «:0» do MAC (``…:35:0a:32`` → ``…:35a:32``).
A coleta passa a reparar o MAC (``parsers.repair_vsol_mac``) e a chave da ONU VSOL usa o MAC
reparado — esta migração reescreve as linhas já guardadas para a próxima coleta as encontrar
(senão nasciam linhas novas e as antigas ficavam a apodrecer como «desconhecidas»).
Chave VSOL: ``<pon>:<n>|<mac ou serial>``. Reversível: o reverso é um no-op (a coleta antiga
voltaria a criar as suas chaves)."""

from django.db import migrations


def _repair(apps, schema_editor):
    from gpon.domain.parsers import repair_vsol_mac

    OnuState = apps.get_model("gpon", "OnuState")
    for state in OnuState.objects.filter(vendor="vsol").exclude(mac=""):
        mac = repair_vsol_mac(state.mac)
        if mac == state.mac:
            continue
        base, _, ident = state.onu_key.partition("|")
        new_key = f"{base}|{mac}" if ident else state.onu_key
        if OnuState.objects.filter(device_id=state.device_id, onu_key=new_key).exists():
            continue  # a coleta já criou a linha nova; a antiga fica (passa a «desconhecida»)
        state.mac = mac
        state.onu_key = new_key
        state.save(update_fields=["mac", "onu_key"])


class Migration(migrations.Migration):

    dependencies = [
        ("gpon", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(_repair, migrations.RunPython.noop),
    ]
