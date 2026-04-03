from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0062_add_responsible_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='fibercable',
            name='cable_type',
            field=models.CharField(
                blank=True,
                choices=[
                    ('backbone', 'Backbone'),
                    ('distribuicao', 'Distribuição'),
                    ('drop', 'Drop'),
                    ('acesso', 'Acesso'),
                ],
                default='',
                help_text='Categoria operacional do cabo (Backbone, Distribuição, Drop, Acesso)',
                max_length=20,
            ),
        ),
    ]
