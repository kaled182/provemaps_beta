from django.db import migrations, models

import setup_app.fields


class Migration(migrations.Migration):
    dependencies = [
        ("setup_app", "0014_messaginggateway"),
    ]

    operations = [
        migrations.CreateModel(
            name="CompanyProfile",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("company_legal_name", models.CharField(blank=True, max_length=255)),
                ("company_trade_name", models.CharField(blank=True, max_length=255)),
                ("company_doc", models.CharField(blank=True, max_length=32)),
                ("company_owner_name", models.CharField(blank=True, max_length=255)),
                ("company_owner_doc", models.CharField(blank=True, max_length=32)),
                ("company_owner_birth", models.CharField(blank=True, max_length=32)),
                ("company_state_reg", models.CharField(blank=True, max_length=64)),
                ("company_city_reg", models.CharField(blank=True, max_length=64)),
                ("company_fistel", models.CharField(blank=True, max_length=64)),
                ("company_created_date", models.CharField(blank=True, max_length=32)),
                ("company_active", models.BooleanField(default=True)),
                ("company_reports_active", models.BooleanField(default=True)),
                ("address_zip", models.CharField(blank=True, max_length=16)),
                ("address_street", models.CharField(blank=True, max_length=255)),
                ("address_number", models.CharField(blank=True, max_length=32)),
                ("address_district", models.CharField(blank=True, max_length=128)),
                ("address_city", models.CharField(blank=True, max_length=128)),
                ("address_state", models.CharField(blank=True, max_length=8)),
                ("address_country", models.CharField(blank=True, default="Brasil", max_length=64)),
                ("address_extra", models.CharField(blank=True, max_length=255)),
                ("address_reference", models.CharField(blank=True, max_length=255)),
                ("address_coords", models.CharField(blank=True, max_length=64)),
                ("address_complex", models.CharField(blank=True, max_length=128)),
                ("address_ibge", models.CharField(blank=True, max_length=32)),
                ("assets_logo", models.FileField(blank=True, null=True, upload_to="setup_app/company/logo/")),
                ("assets_central_logo", models.FileField(blank=True, null=True, upload_to="setup_app/company/central_logo/")),
                ("assets_background", models.FileField(blank=True, null=True, upload_to="setup_app/company/background/")),
                ("assets_domain", models.CharField(blank=True, max_length=255)),
                ("assets_cert_file", models.FileField(blank=True, null=True, upload_to="setup_app/company/cert/")),
                ("assets_cert_password", setup_app.fields.EncryptedCharField(blank=True, max_length=255, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
