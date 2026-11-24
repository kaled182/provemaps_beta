"""EV-0096: limiares ópticos e capacidade da PON passam a ser guardados na base."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("setup_app", "0030_cronjob"),
    ]

    operations = [
        migrations.AddField(
            model_name="firsttimesetup",
            name="optical_rx_warning_threshold",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="firsttimesetup",
            name="optical_rx_critical_threshold",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="firsttimesetup",
            name="optical_thresholds_by_distance",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="firsttimesetup",
            name="gpon_pon_capacity",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="firsttimesetup",
            name="epon_pon_capacity",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
    ]
