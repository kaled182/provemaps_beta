from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0050_add_custom_maps"),
    ]

    operations = [
        migrations.AddField(
            model_name="device",
            name="memory_usage_item_key",
            field=models.CharField(
                max_length=255,
                blank=True,
                help_text=(
                    "Zabbix item key for Memory usage "
                    "(e.g. vm.memory.size[percent] or mem.util)"
                ),
            ),
        ),
        migrations.AddField(
            model_name="device",
            name="cpu_usage_manual_percent",
            field=models.DecimalField(
                max_digits=5,
                decimal_places=2,
                null=True,
                blank=True,
                help_text="Manual CPU usage percent when Zabbix data is unavailable",
            ),
        ),
        migrations.AddField(
            model_name="device",
            name="memory_usage_manual_percent",
            field=models.DecimalField(
                max_digits=5,
                decimal_places=2,
                null=True,
                blank=True,
                help_text="Manual Memory usage percent when Zabbix data is unavailable",
            ),
        ),
    ]
