from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_department"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="departments",
            field=models.ManyToManyField(blank=True, related_name="user_profiles", to="core.department"),
        ),
    ]
