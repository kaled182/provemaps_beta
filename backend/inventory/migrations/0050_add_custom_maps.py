# Generated manually for custom maps feature

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import inventory.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('inventory', '0034_add_device_dashboard_config'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomMap',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Nome do mapa personalizado', max_length=200)),
                ('description', models.TextField(blank=True, help_text='Descrição do propósito deste mapa')),
                ('category', models.CharField(
                    choices=[
                        ('backbone', 'Backbone'),
                        ('gpon', 'GPON'),
                        ('dwdm', 'DWDM'),
                        ('custom', 'Personalizado')
                    ],
                    default='backbone',
                    help_text='Categoria do mapa',
                    max_length=50
                )),
                ('is_public', models.BooleanField(default=True, help_text='Se True, mapa visível para todos os usuários')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('selected_devices', inventory.fields.LenientJSONField(
                    blank=True,
                    default=list,
                    help_text='IDs dos dispositivos incluídos neste mapa'
                )),
                ('selected_cables', inventory.fields.LenientJSONField(
                    blank=True,
                    default=list,
                    help_text='IDs dos cabos incluídos neste mapa'
                )),
                ('selected_cameras', inventory.fields.LenientJSONField(
                    blank=True,
                    default=list,
                    help_text='IDs das câmeras incluídas neste mapa'
                )),
                ('selected_racks', inventory.fields.LenientJSONField(
                    blank=True,
                    default=list,
                    help_text='IDs dos racks incluídos neste mapa'
                )),
                ('created_by', models.ForeignKey(
                    help_text='Usuário que criou o mapa',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='custom_maps',
                    to=settings.AUTH_USER_MODEL
                )),
            ],
            options={
                'verbose_name': 'Mapa Personalizado',
                'verbose_name_plural': 'Mapas Personalizados',
                'db_table': 'custom_maps',
                'ordering': ['-created_at'],
            },
        ),
    ]
