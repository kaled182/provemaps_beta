from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "__first__"),
        ("inventory", "0067_alter_cabletype_id_alter_fibercablephoto_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="fibercablealarmconfig",
            name="department",
            field=models.ForeignKey(
                blank=True,
                help_text="Departamento alvo quando target_type=department.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="fiber_alarm_configs",
                to="core.department",
            ),
        ),
        migrations.AlterField(
            model_name="fibercablealarmconfig",
            name="target_type",
            field=models.CharField(
                choices=[
                    ("department_group", "Department group"),
                    ("system_user", "System user"),
                    ("contact", "Contact"),
                    ("department", "Departamento"),
                ],
                help_text="Tipo de destino (grupo, usuário ou contato).",
                max_length=32,
            ),
        ),
    ]
