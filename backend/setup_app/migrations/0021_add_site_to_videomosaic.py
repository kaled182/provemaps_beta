from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('inventory', '0054_remove_optical_snapshot_model'),
        ('setup_app', '0020_add_departments_to_cameras'),
    ]

    operations = [
        migrations.AddField(
            model_name='videomosaic',
            name='site',
            field=models.ForeignKey(
                to='inventory.site',
                on_delete=models.SET_NULL,
                null=True,
                blank=True,
                related_name='video_mosaics',
                help_text='Site associado a este mosaico (filtra câmeras por local)'
            ),
        ),
    ]
