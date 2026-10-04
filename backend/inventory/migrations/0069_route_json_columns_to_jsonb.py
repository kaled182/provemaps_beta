"""
EV-0008 — colunas JSON das rotas passam a jsonb no PostgreSQL.

As migrações 0003 e 0007 criaram `inventory_route`, `inventory_routesegment` e
`inventory_routeevent` com SQL cru e colunas do tipo ``JSON`` (não ``jsonb``).
Com psycopg 3 o driver devolve colunas ``json`` já desserializadas (dict/list),
e o ``JSONField`` do Django só regista o loader de passagem para ``jsonb``:
qualquer leitura de uma rota com ``metadata``/``details`` preenchido rebentava
com ``TypeError: the JSON object must be str, bytes or bytearray, not dict``.
Os 46 testes de ``inventory/routes/tests`` nunca eram coletados, por isso o
defeito ficou escondido.

Só actua no PostgreSQL; noutros backends é no-op. Reversível.
"""

from django.db import migrations

COLUMNS = (
    ("inventory_route", "metadata"),
    ("inventory_routesegment", "metadata"),
    ("inventory_routeevent", "details"),
)


def _alter(apps, schema_editor, target_type):
    connection = schema_editor.connection
    if connection.vendor != "postgresql":
        return
    with connection.cursor() as cursor:
        for table, column in COLUMNS:
            cursor.execute(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_schema = current_schema() AND table_name = %s AND column_name = %s",
                [table, column],
            )
            row = cursor.fetchone()
            if row is None or row[0] == target_type:
                continue
            cursor.execute(
                f'ALTER TABLE "{table}" ALTER COLUMN "{column}" '
                f'TYPE {target_type} USING "{column}"::{target_type}'
            )


def forwards(apps, schema_editor):
    _alter(apps, schema_editor, "jsonb")


def backwards(apps, schema_editor):
    _alter(apps, schema_editor, "json")


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0068_add_department_to_alarmconfig"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
