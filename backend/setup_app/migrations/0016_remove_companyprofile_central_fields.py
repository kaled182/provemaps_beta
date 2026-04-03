from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("setup_app", "0015_companyprofile"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="companyprofile",
            name="assets_central_logo",
        ),
        migrations.RemoveField(
            model_name="companyprofile",
            name="assets_background",
        ),
        migrations.RemoveField(
            model_name="companyprofile",
            name="assets_domain",
        ),
    ]
