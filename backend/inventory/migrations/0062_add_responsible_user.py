import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0061_add_cable_folder'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='fibercable',
            name='responsible_user',
            field=models.ForeignKey(
                blank=True,
                help_text='System user responsible for this cable',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='cable_responsibles',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
