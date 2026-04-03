#!/usr/bin/env bash
# mapsprove/scripts/infra/apply-config.sh
set -euo pipefail

# Ajuste estes nomes conforme seu compose/serviços
BACKEND_PORT="${BACKEND_PORT:-3000}"       # onde o backend expõe /api/settings (interno)
BACKEND_HOST="${BACKEND_HOST:-localhost}"  # se rodar dentro do mesmo container, use 127.0.0.1
APPLY_TOKEN="${APPLY_TOKEN:-}"             # se quiser proteger o endpoint interno (futuro)

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TEMPLATES_DIR="${ROOT_DIR}/config/templates"
OUT_DIR="${ROOT_DIR}/config/generated"
mkdir -p "$OUT_DIR"

echo "[apply-config] Buscando configurações do backend…"
# Exemplo minimalista: pegar só algumas chaves usando psql OU endpoint interno.
# (A forma mais simples aqui: psql. Se preferir endpoint HTTP, ajuste.)
# Exemplo com psql (esperando DATABASE_URL configurado no container/shell):
# psql "$DATABASE_URL" -Atc "SELECT key, encode(value_enc,'base64'), encode(nonce,'base64') FROM app_settings"

# Para MVP, vamos assumir que backend já aplica ZABBIX_* diretamente do DB em runtime.
# Aqui só vamos gerar um arquivo para um hipotético exporter:

ZBX_URL="${ZABBIX_URL:-}"
ZBX_USER="${ZABBIX_USER:-}"
ZBX_PASS="${ZABBIX_PASSWORD:-}"

# Se quiser ler via psql, descomente e adapte:
# readarray -t rows < <(psql "$DATABASE_URL" -Atc "SELECT key FROM app_settings")
# echo "Chaves salvas: ${rows[*]}"

# Renderização simples com envsubst (instale 'gettext-base' se faltar):
export ZABBIX_URL ZABBIX_USER ZABBIX_PASSWORD
mkdir -p "$TEMPLATES_DIR"
cat > "${TEMPLATES_DIR}/snmp_exporter.yml.tmpl" <<'EOF'
# Template de exemplo (snmp_exporter.yml)
auth:
  zabbix_url: "${ZABBIX_URL}"
  zabbix_user: "${ZABBIX_USER}"
  zabbix_pass: "${ZABBIX_PASSWORD}"
EOF

echo "[apply-config] Gerando config do snmp_exporter…"
envsubst < "${TEMPLATES_DIR}/snmp_exporter.yml.tmpl" > "${OUT_DIR}/snmp_exporter.yml"

# Recarregar/recriar serviço (ajuste o nome do serviço no compose)
if command -v docker >/dev/null 2>&1; then
  echo "[apply-config] Recriando serviço 'snmp-exporter' via docker compose…"
  (cd "$ROOT_DIR" && docker compose up -d --force-recreate snmp-exporter) || true
else
  echo "[apply-config] docker não disponível aqui — pulei recriação. (ok em DEV)"
fi

echo "[apply-config] OK."
