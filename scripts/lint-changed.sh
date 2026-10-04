#!/usr/bin/env bash
# Lint só dos ficheiros Python alterados face a uma base (EV-0022).
#
# O lint da árvore inteira nunca passou (2.985 achados ruff, 283 ficheiros por
# formatar em 2026-10-04) e uma formatação global tocaria tudo. A regra do
# projeto é «lint limpo nos ficheiros tocados» (CLAUDE.md §9); este script é a
# versão mecânica dela: black, isort e ruff correm sobre os .py que mudaram.
#
# Uso: scripts/lint-changed.sh [BASE_REF]   (default: origin/inicial)
#      No CI, BASE_REF vem do evento (base do PR ou commit anterior do push).
set -euo pipefail
cd "$(dirname "$0")/.."
BASE="${1:-origin/inicial}"

if ! git rev-parse --verify --quiet "$BASE" >/dev/null; then
  echo "lint-changed: base '$BASE' não existe localmente (git fetch origin inicial)" >&2
  exit 2
fi

# Ficheiros alterados ou novos face à base, mais os já no índice/working tree.
mapfile -t FILES < <(
  {
    git diff --name-only --diff-filter=AMR "$BASE"...HEAD -- '*.py'
    git diff --name-only --diff-filter=AMR -- '*.py'
    git diff --name-only --cached --diff-filter=AMR -- '*.py'
  } | grep -v '/migrations/' | sort -u | while read -r f; do [ -f "$f" ] && echo "$f"; done
)

if [ "${#FILES[@]}" -eq 0 ]; then
  echo "lint-changed: nenhum .py alterado face a $BASE"
  exit 0
fi

echo "lint-changed: ${#FILES[@]} ficheiro(s) face a $BASE"
printf '  %s\n' "${FILES[@]}"

# A configuração (line-length, profile, regras) vem de backend/pyproject.toml.
status=0
( cd backend && black --check --config pyproject.toml "${FILES[@]/#backend\//}" ) || status=1
( cd backend && isort --check-only --settings-path pyproject.toml "${FILES[@]/#backend\//}" ) || status=1
( cd backend && ruff check "${FILES[@]/#backend\//}" ) || status=1
exit $status
