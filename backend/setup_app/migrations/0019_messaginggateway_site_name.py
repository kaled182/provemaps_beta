# Generated manually for adding site_name to MessagingGateway

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('setup_app', '0018_add_departments_to_videomosaic'),
    ]

    operations = [
        migrations.AddField(
            model_name='messaginggateway',
            name='site_name',
            field=models.CharField(blank=True, help_text='Nome do site onde o dispositivo está localizado (apenas para gateways de vídeo)', max_length=255, null=True),
        ),
    ]
