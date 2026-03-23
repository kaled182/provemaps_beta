# Generated migration for adding MAP_* configuration fields

from django.db import migrations, models
import setup_app.fields


class Migration(migrations.Migration):

    dependencies = [
        ('setup_app', '0022_add_contacts_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='firsttimesetup',
            name='map_default_zoom',
            field=models.IntegerField(default=12),
        ),
        migrations.AddField(
            model_name='firsttimesetup',
            name='map_default_lat',
            field=models.DecimalField(max_digits=10, decimal_places=7, default=-15.7801),
        ),
        migrations.AddField(
            model_name='firsttimesetup',
            name='map_default_lng',
            field=models.DecimalField(max_digits=10, decimal_places=7, default=-47.9292),
        ),
        migrations.AddField(
            model_name='firsttimesetup',
            name='map_type',
            field=models.CharField(max_length=20, default='roadmap'),
        ),
        migrations.AddField(
            model_name='firsttimesetup',
            name='map_styles',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='firsttimesetup',
            name='enable_street_view',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='firsttimesetup',
            name='enable_traffic',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='firsttimesetup',
            name='mapbox_style',
            field=models.CharField(max_length=255, default='mapbox://styles/mapbox/streets-v12'),
        ),
        migrations.AddField(
            model_name='firsttimesetup',
            name='mapbox_custom_style',
            field=models.CharField(max_length=255, blank=True, null=True),
        ),
        migrations.AddField(
            model_name='firsttimesetup',
            name='mapbox_enable_3d',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='firsttimesetup',
            name='esri_api_key',
            field=setup_app.fields.EncryptedCharField(max_length=512, blank=True, null=True),
        ),
        migrations.AddField(
            model_name='firsttimesetup',
            name='esri_basemap',
            field=models.CharField(max_length=50, default='streets'),
        ),
        migrations.AddField(
            model_name='firsttimesetup',
            name='map_language',
            field=models.CharField(max_length=10, default='pt-BR'),
        ),
        migrations.AddField(
            model_name='firsttimesetup',
            name='enable_map_clustering',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='firsttimesetup',
            name='enable_drawing_tools',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='firsttimesetup',
            name='enable_fullscreen',
            field=models.BooleanField(default=True),
        ),
    ]
