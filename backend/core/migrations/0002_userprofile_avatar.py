from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_userprofile"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="avatar",
            field=models.ImageField(blank=True, null=True, upload_to="avatars/", verbose_name="Foto de Perfil"),
        ),
    ]
