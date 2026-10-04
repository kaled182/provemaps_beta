"""
EV-0016 — `UserProfile.totp_secret` passa a ser cifrado em repouso (Fernet).

Os segredos existentes (base32 em texto puro) são cifrados pela migração.
Reverter devolve o texto puro (para poder voltar ao CharField).

O passo de dados lê e escreve a coluna com SQL cru: depois do `AlterField`, o
modelo histórico já usa `EncryptedCharField`, que decifra ao ler e cifra ao
gravar — pelo ORM não se consegue saber o que está de facto na coluna.
"""

from django.db import migrations

import setup_app.fields

TABLE = "core_userprofile"
SELECT_SQL = (
    "SELECT id, totp_secret FROM {table} WHERE totp_secret IS NOT NULL AND totp_secret <> ''"
)
UPDATE_SQL = "UPDATE {table} SET totp_secret = %s WHERE id = %s"


def _is_encrypted(value: str) -> bool:
    from cryptography.fernet import InvalidToken

    from setup_app.fields import _get_fernets

    for fernet in _get_fernets():
        try:
            fernet.decrypt(value.encode())
        except InvalidToken:
            continue
        return True
    return False


def _rewrite_column(schema_editor, should_rewrite, transform):
    table = schema_editor.quote_name(TABLE)
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(SELECT_SQL.format(table=table))
        rows = cursor.fetchall()
        for pk, raw in rows:
            if isinstance(raw, str) and should_rewrite(raw):
                cursor.execute(UPDATE_SQL.format(table=table), [transform(raw), pk])


def encrypt_existing(apps, schema_editor):
    from setup_app.fields import encrypt_string

    _rewrite_column(schema_editor, lambda raw: not _is_encrypted(raw), encrypt_string)


def decrypt_existing(apps, schema_editor):
    from setup_app.fields import decrypt_string

    _rewrite_column(schema_editor, _is_encrypted, decrypt_string)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0005_userprofile_departments"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userprofile",
            name="totp_secret",
            field=setup_app.fields.EncryptedCharField(
                "TOTP Secret", blank=True, max_plain_length=64, null=True
            ),
        ),
        migrations.RunPython(encrypt_existing, decrypt_existing),
    ]
