import django.db.models.deletion
from django.db import migrations, models


PREDEFINED_TYPES = ["Backbone", "Distribuição", "Drop", "Acesso"]


def seed_cable_types(apps, schema_editor):
    CableType = apps.get_model("inventory", "CableType")
    for i, name in enumerate(PREDEFINED_TYPES):
        CableType.objects.get_or_create(name=name, defaults={"order": i})


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0063_add_cable_type"),
    ]

    operations = [
        # 1. Create the CableType lookup table
        migrations.CreateModel(
            name="CableType",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=50, unique=True)),
                ("order", models.PositiveSmallIntegerField(default=0, help_text="Display order in lists")),
            ],
            options={
                "db_table": "inventory_cable_type",
                "ordering": ["order", "name"],
            },
        ),
        # 2. Seed predefined types
        migrations.RunPython(seed_cable_types, migrations.RunPython.noop),
        # 3. Remove the old CharField (no cables have it set yet — added this session)
        migrations.RemoveField(
            model_name="fibercable",
            name="cable_type",
        ),
        # 4. Add the FK field
        migrations.AddField(
            model_name="fibercable",
            name="cable_type",
            field=models.ForeignKey(
                blank=True,
                help_text="Categoria operacional do cabo (Backbone, Distribuição, Drop, Acesso)",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="cables",
                to="inventory.cabletype",
            ),
        ),
    ]
