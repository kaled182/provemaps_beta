from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("service_accounts", "0002_service_bot_group"),
    ]

    operations = [
        migrations.AddField(
            model_name="serviceaccount",
            name="auto_rotate_days",
            field=models.PositiveIntegerField(
                blank=True,
                help_text=(
                    "Número de dias para rotacionar tokens automaticamente."
                ),
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="serviceaccount",
            name="notification_webhook_url",
            field=models.URLField(
                blank=True,
                help_text=(
                    "Webhook opcional (ex.: Slack) para alertas automáticos."
                ),
            ),
        ),
        migrations.AddField(
            model_name="serviceaccount",
            name="notify_before_days",
            field=models.PositiveIntegerField(
                blank=True,
                help_text=(
                    "Quantos dias antes da expiração avisar responsáveis "
                    "sobre o token ativo."
                ),
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="serviceaccounttoken",
            name="last_notified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="serviceaccountauditlog",
            name="action",
            field=models.CharField(
                choices=[
                    ("created", "Account Created"),
                    ("updated", "Account Updated"),
                    ("token_created", "Token Created"),
                    ("token_revoked", "Token Revoked"),
                    ("token_rotated", "Token Rotated"),
                    ("token_expired", "Token Expired"),
                    ("rotation_notice", "Rotation Notice Sent"),
                ],
                max_length=32,
            ),
        ),
    ]
