from typing import List

import pytest
from django.db import connection


@pytest.mark.api
def test_no_zabbix_snapshot_tables_present(db) -> None:
    """
    Garante a política: não persistir histórico do Zabbix.

    Falha caso qualquer tabela de snapshot/gráfico relacionada ao Zabbix/óptico/tráfego
    exista no banco atual (SQLite/PostgreSQL).
    """
    introspection = connection.introspection
    tables: List[str] = introspection.table_names()

    forbidden_exact = {
        "inventory_optical_power_snapshot",
        "zabbix_api_optical_power_snapshot",
        "optical_power_snapshot",
    }

    # Qualquer tabela que contenha 'snapshot' e termos de domínio
    suspicious: List[str] = []
    for t in tables:
        tl = t.lower()
        if "snapshot" in tl and (
            "zabbix" in tl or "optical" in tl or "traffic" in tl or "interface" in tl
        ):
            suspicious.append(t)
        if t in forbidden_exact:
            suspicious.append(t)

    assert not suspicious, (
        "Tabelas de snapshot/gráfico do Zabbix não devem existir no banco: "
        + ", ".join(sorted(set(suspicious)))
    )
