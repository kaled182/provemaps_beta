"""EV-0115: limiares de RX das portas de switch (backbone), guardados na base como os do GPON."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("setup_app", "0031_firsttimesetup_optical_and_pon"),
    ]

    operations = [
        migrations.AddField(
            model_name="firsttimesetup",
            name="backbone_rx_warning_threshold",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="firsttimesetup",
            name="backbone_rx_critical_threshold",
            field=models.FloatField(blank=True, null=True),
        ),
    ]
