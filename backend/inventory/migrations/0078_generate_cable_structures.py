"""EV-0133: gera a estrutura física (tubos loose e fibras, cores ABNT) dos cabos existentes.

Os 17 cabos tinham 0 tubos e 0 fibras (sem perfil): a estrutura dava erro/ficava vazia e a
Ocupação do inventário dizia «sem dados». O perfil escolhe-se pelo nº de fibras do grupo do
cabo; cabos sem grupo (nem perfil) ficam para o modal pedir. Não mexe em cabos que já têm tubos.
"""

from django.db import migrations

from inventory.utils_fiber import get_color_for_index


def generate(apps, schema_editor):
    FiberCable = apps.get_model("inventory", "FiberCable")
    FiberProfile = apps.get_model("inventory", "FiberProfile")
    BufferTube = apps.get_model("inventory", "BufferTube")
    FiberStrand = apps.get_model("inventory", "FiberStrand")
    for cable in FiberCable.objects.select_related("profile", "cable_group"):
        if BufferTube.objects.filter(cable=cable).exists():
            continue
        profile = cable.profile
        if profile is None:
            fibers = (
                getattr(cable.cable_group, "fiber_count", None) if cable.cable_group_id else None
            )
            if not fibers:
                continue
            profile = FiberProfile.objects.filter(total_fibers=fibers).order_by("id").first()
            if profile is None:
                continue
            cable.profile = profile
            cable.save(update_fields=["profile"])
        strands = []
        for tube_num in range(1, profile.tube_count + 1):
            tc = get_color_for_index(tube_num)
            tube = BufferTube.objects.create(
                cable=cable, number=tube_num, color=tc["name"], color_hex=tc["hex"]
            )
            for fiber_num in range(1, profile.fibers_per_tube + 1):
                fc = get_color_for_index(fiber_num)
                strands.append(
                    FiberStrand(
                        tube=tube,
                        number=fiber_num,
                        absolute_number=(tube_num - 1) * profile.fibers_per_tube + fiber_num,
                        color=fc["name"],
                        color_hex=fc["hex"],
                        status="dark",
                    )
                )
        FiberStrand.objects.bulk_create(strands)


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0077_otdr_alert_status"),
    ]

    operations = [
        migrations.RunPython(generate, migrations.RunPython.noop),
    ]
