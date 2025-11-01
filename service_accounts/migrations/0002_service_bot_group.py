from typing import Any

from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps


def create_service_bot_group(
    apps: StateApps,
    schema_editor: BaseDatabaseSchemaEditor,
) -> None:
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    service_account_ct, _ = ContentType.objects.get_or_create(
        app_label="service_accounts",
        model="serviceaccount",
    )
    audit_log_ct, _ = ContentType.objects.get_or_create(
        app_label="service_accounts",
        model="serviceaccountauditlog",
    )
    token_ct, _ = ContentType.objects.get_or_create(
        app_label="service_accounts",
        model="serviceaccounttoken",
    )

    permissions_codenames = [
        (service_account_ct, "view_serviceaccount"),
        (service_account_ct, "add_serviceaccount"),
        (service_account_ct, "change_serviceaccount"),
        (service_account_ct, "manage_tokens"),
        (token_ct, "view_serviceaccounttoken"),
        (audit_log_ct, "view_serviceaccountauditlog"),
    ]

    perms: list[Any] = []
    for ct, codename in permissions_codenames:
        perm, _ = Permission.objects.get_or_create(
            content_type=ct,
            codename=codename,
            defaults={
                "name": codename.replace("_", " ").title(),
            },
        )
        perms.append(perm)

    group, _created = Group.objects.get_or_create(name="Service Bots")
    group.permissions.set(perms)  # type: ignore[attr-defined]
    group.save()


def remove_service_bot_group(
    apps: StateApps,
    schema_editor: BaseDatabaseSchemaEditor,
) -> None:
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name="Service Bots").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("service_accounts", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(
            create_service_bot_group,
            remove_service_bot_group,
        ),
    ]
