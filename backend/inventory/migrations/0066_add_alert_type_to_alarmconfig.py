from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0065_add_cable_photo"),
    ]

    operations = [
        migrations.AddField(
            model_name="fibercablealarmconfig",
            name="alert_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("break", "Rompimento"),
                    ("attenuation", "Atenuação"),
                    ("normalization", "Normalização"),
                ],
                default="",
                help_text="Tipo de evento: rompimento, atenuação ou normalização.",
                max_length=16,
            ),
        ),
    ]
