import os
import sqlite3


def drop_tables(db_path: str, tables_to_drop: list[str]) -> None:
    if not os.path.exists(db_path):
        print(f"[INFO] Banco não encontrado: {db_path}")
        return
    print(f"[INFO] Conectando em {db_path}")
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        # Descobrir tabelas existentes
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing = {row[0] for row in cur.fetchall()}

        # Adicionar candidatos dinâmicos contendo 'snapshot' e termos relacionados
        dynamic_candidates = [t for t in existing if (
            "snapshot" in t.lower() and (
                "optical" in t.lower() or "traffic" in t.lower() or "zabbix" in t.lower()
            )
        )]

        candidates = list(set(tables_to_drop) & existing) + dynamic_candidates
        if not candidates:
            print("[OK] Nenhuma tabela de snapshot/gráfico encontrada para remover.")
            return

        print(f"[INFO] Tabelas a remover: {', '.join(sorted(candidates))}")
        for t in candidates:
            cur.execute(f'DROP TABLE IF EXISTS "{t}"')
            print(f"[WARN] Removida: {t}")
        conn.commit()
        print("[OK] Limpeza concluída.")
    finally:
        conn.close()


def main() -> None:
    # Caminhos padrão de bancos SQLite neste projeto
    candidates_dbs = [
        os.path.join("database", "db.sqlite3"),
        os.path.join("test_db.sqlite3"),
    ]
    tables = [
        "inventory_optical_power_snapshot",
        "zabbix_api_optical_power_snapshot",
        "optical_power_snapshot",
    ]
    for db in candidates_dbs:
        drop_tables(db, tables)


if __name__ == "__main__":
    main()
