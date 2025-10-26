#!/usr/bin/env bash
# Simple Celery status check with fallback awareness
set -euo pipefail
URL="${CELERY_STATUS_URL:-http://localhost:8000/celery/status}"
TIMEOUT="${CELERY_STATUS_TIMEOUT:-8}"
RAW=$(curl -s -m "$TIMEOUT" -w "\n%{http_code}" "$URL" || true)
HTTP_CODE=$(echo "$RAW" | tail -n1)
BODY=$(echo "$RAW" | sed '$d')
if [[ -z "$HTTP_CODE" ]]; then
  echo "✗ Falha ao obter status (timeout ou erro de rede)"; exit 3
fi
STATUS=$(echo "$BODY" | python - <<'PY'
import sys, json
try:
  data=json.load(sys.stdin)
  print(data.get('status','unknown'), str(data.get('worker',{}).get('available')))
except Exception:
  print('parse_error','False')
PY
)
APP_STATUS=$(echo "$STATUS" | awk '{print $1}')
WORKER_AVAILABLE=$(echo "$STATUS" | awk '{print $2}')
if [[ "$HTTP_CODE" == "200" && "$APP_STATUS" == "ok" ]]; then
  echo "✓ Celery OK"
  exit 0
elif [[ "$WORKER_AVAILABLE" == "True" ]]; then
  echo "⚠ Celery degradado (worker ativo, estatísticas indisponíveis)"
  exit 1
else
  echo "✗ Celery indisponível (sem worker)"
  exit 2
fi
