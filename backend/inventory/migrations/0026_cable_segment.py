# Generated migration for CableSegment model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0025_spliceboxtemplate_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='CableSegment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('segment_number', models.IntegerField(help_text='Número sequencial do segmento (1, 2, 3...)')),
                ('name', models.CharField(max_length=200, help_text='Ex: Cabo-Principal-Seg1')),
                ('cable', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='segments',
                    to='inventory.fibercable',
                    help_text='Cabo físico ao qual este segmento pertence'
                )),
                ('start_infrastructure', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='segments_starting_here',
                    to='inventory.fiberinfrastructure',
                    null=True,
                    blank=True,
                    help_text='Infraestrutura de origem (CEO, Site, etc.)'
                )),
                ('end_infrastructure', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='segments_ending_here',
                    to='inventory.fiberinfrastructure',
                    null=True,
                    blank=True,
                    help_text='Infraestrutura de destino'
                )),
                ('length_meters', models.FloatField(
                    default=0,
                    help_text='Comprimento deste segmento em metros'
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'inventory_cable_segment',
                'ordering': ['cable', 'segment_number'],
                'unique_together': [['cable', 'segment_number']],
                'verbose_name': 'Segmento de Cabo',
                'verbose_name_plural': 'Segmentos de Cabo',
            },
        ),
        
        # Adicionar campo segment ao FiberStrand
        migrations.AddField(
            model_name='fiberstrand',
            name='segment',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='strands',
                to='inventory.cablesegment',
                help_text='Segmento ao qual esta fibra pertence (para rastreabilidade)'
            ),
        ),
        
        # Índices para performance
        migrations.AddIndex(
            model_name='cablesegment',
            index=models.Index(fields=['cable', 'segment_number'], name='idx_cable_segment_num'),
        ),
        migrations.AddIndex(
            model_name='cablesegment',
            index=models.Index(fields=['start_infrastructure'], name='idx_segment_start'),
        ),
        migrations.AddIndex(
            model_name='cablesegment',
            index=models.Index(fields=['end_infrastructure'], name='idx_segment_end'),
        ),
    ]
