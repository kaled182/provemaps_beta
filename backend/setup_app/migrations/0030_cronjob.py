from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('setup_app', '0029_alter_alerttemplate_category'),
    ]

    operations = [
        migrations.CreateModel(
            name='CronJob',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True, default='')),
                ('schedule', models.CharField(max_length=100)),
                ('command', models.TextField()),
                ('enabled', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Cron Job',
                'verbose_name_plural': 'Cron Jobs',
                'ordering': ['name'],
            },
        ),
    ]
