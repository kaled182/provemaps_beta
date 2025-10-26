# Generated manually

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('zabbix_api', '0011_unmanage_inventory_models'),
    ]

    operations = [
        # Delete all inventory models from zabbix_api schema
        migrations.DeleteModel(name='FiberEvent'),
        migrations.DeleteModel(name='FiberCable'),
        migrations.DeleteModel(name='Port'),
        migrations.DeleteModel(name='Device'),
        migrations.DeleteModel(name='Site'),
    ]
