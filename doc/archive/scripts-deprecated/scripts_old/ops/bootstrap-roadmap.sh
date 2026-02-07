#!/usr/bin/env bash
# scripts/ops/bootstrap-roadmap.sh
#
# Bootstrap do roadmap do MapsProve (labels, milestones e issues) a partir de scripts/ops/roadmap.yml
# Requisitos:
#   - gh (GitHub CLI) autenticado:    gh auth status
#   - yq (YAML parser):                https://github.com/mikefarah/yq/
# Uso:
#   chmod +x scripts/ops/bootstrap-roadmap.sh
#   scripts/ops/bootstrap-roadmap.sh <owner/repo>
#
# Variáveis de ambiente:
#   ROADMAP_FILE  -> caminho do YAML (default: scripts/ops/roadmap.yml)
#   DRY_RUN=true  -> apenas imprime ações (não executa gh)
#   START_DATE=YYYY-MM-DD -> data-base para calcular due_on dos milestones (default: hoje)
#
set -euo pipefail

# ------------------------------ Utils ------------------------------

log() { printf '%b\n' "$*"; }
info() { log "ℹ️  $*"; }
ok()   { log "✅ $*"; }
warn() { log "⚠️  $*"; }
err()  { log "❌ $*" >&2; }

is_gnu_date() {
  date --version >/dev/null 2>&1
}

DATE_CMD="date"
if command -v gdate >/dev/null 2>&1; then
  DATE_CMD="gdate"
fi

require_tools() {
  if ! command -v gh >/dev/null 2>&1; then
    err "GitHub CLI (gh) não encontrado. Instale em https://cli.github.com/"
    exit 1
  fi
  if ! gh auth status >/dev/null 2>&1; then
    err "gh não está autenticado. Execute: gh auth login"
    exit 1
  fi
  if ! command -v yq >/dev/null 2>&1; then
    err "yq (YAML parser) não encontrado. Instale em https://github.com/mikefarah/yq/"
    exit 1
  fi
}

resolve_repo() {
  local repo_arg="${1:-}"
  if [[ -n "$repo_arg" ]]; then
    echo "$repo_arg"
    return
  fi
  # tenta detectar repo atual
  local detected
  detected="$(gh repo view --json nameWithOwner --jq .nameWithOwner 2>/dev/null || true)"
  if [[ -z "$detected" ]]; then
    err "Não foi possível detectar o repositório. Use: $0 <owner/repo>"
    exit 1
  fi
  echo "$detected"
}

# Calcula due_on (ISO 8601 UTC) adicionando N semanas à data-base (ou hoje)
compute_due_date() {
  local week="$1"                # inteiro >= 1
  local base="${START_DATE:-}"   # YYYY-MM-DD (opcional)
  local iso

  if [[ "$DATE_CMD" = "gdate" ]] || is_gnu_date; then
    if [[ -n "$base" ]]; then
      iso="$($DATE_CMD -u -d "${base} +${week} week" --iso-8601=seconds)"
    else
      iso="$($DATE_CMD -u -d "+${week} week" --iso-8601=seconds)"
    fi
  else
    # BSD date (macOS). Requer -v+<n>w para adicionar semanas.
    if [[ -n "$base" ]]; then
      # tenta parsear base como YYYY-MM-DD
      iso="$(date -u -j -f "%Y-%m-%d" "$base" -v+${week}w -Iseconds 2>/dev/null || true)"
      if [[ -z "$iso" ]]; then
        warn "START_DATE inválida para BSD date. Usando hoje."
        iso="$(date -u -v+${week}w -Iseconds)"
      fi
    else
      iso="$(date -u -v+${week}w -Iseconds)"
    fi
  fi
  echo "$iso"
}

# Execução condicional (respeita DRY_RUN)
gh_run() {
  if [[ "${DRY_RUN:-}" = "true" ]]; then
    echo "[DRY_RUN] gh $*"
    return 0
  fi
  gh "$@"
}

gh_api() {
  if [[ "${DRY_RUN:-}" = "true" ]]; then
    echo "[DRY_RUN] gh api $*"
    return 0
  fi
  gh api "$@"
}

# ------------------------------ Processadores ------------------------------

process_labels() {
  local repo="$1" file="$2"
  info "==> Criando/atualizando labels…"
  local total
  total="$(yq '.labels | length' "$file")"
  [[ "$total" -gt 0 ]] || { warn "Nenhuma label definida em $file"; return; }

  for i in $(seq 0 $((total - 1))); do
    local name color desc
    name="$(yq -r ".labels[$i].name" "$file")"
    color="$(yq -r ".labels[$i].color" "$file")"
    desc="$(yq -r ".labels[$i].description" "$file")"

    if gh label list -R "$repo" --limit 300 | awk '{print $1}' | grep -Fxq "$name"; then
      gh_run label edit "$name" -R "$repo" --color "$color" --description "$desc" >/dev/null
      log "🔁 label atualizado: $name"
    else
      gh_run label create "$name" -R "$repo" --color "$color" --description "$desc" >/dev/null
      log "🏷️  label criado: $name"
    fi
  done
  ok "Labels processadas"
}

process_milestones() {
  local repo="$1" file="$2"
  info "==> Criando/atualizando milestones…"
  local total
  total="$(yq '.milestones | length' "$file")"
  [[ "$total" -gt 0 ]] || { warn "Nenhum milestone definido em $file"; return; }

  for i in $(seq 0 $((total - 1))); do
    local title desc week due
    title="$(yq -r ".milestones[$i].title" "$file")"
    desc="$(yq -r ".milestones[$i].description" "$file")"
    week="$(yq -r ".milestones[$i].week" "$file")"

    # calcula due_on
    due="$(compute_due_date "$week")"

    # busca id existente
    local id
    id="$(gh_api "repos/$repo/milestones" --jq ".[] | select(.title==\"$title\") | .number" 2>/dev/null || true)"

    if [[ -z "$id" ]]; then
      gh_api "repos/$repo/milestones" -f title="$title" -f description="$desc" -f due_on="$due" >/dev/null
      log "🏁 milestone criado: $title (due_on: ${due%T*})"
    else
      gh_api -X PATCH "repos/$repo/milestones/$id" -f title="$title" -f description="$desc" -f due_on="$due" >/dev/null
      log "🔁 milestone atualizado: $title (due_on: ${due%T*})"
    fi
  done
  ok "Milestones processados"
}

process_issues() {
  local repo="$1" file="$2"
  info "==> Criando/atualizando issues…"
  local total
  total="$(yq '.issues | length' "$file")"
  [[ "$total" -gt 0 ]] || { warn "Nenhuma issue definida em $file"; return; }

  for i in $(seq 0 $((total - 1))); do
    local title body milestone labels_csv
    title="$(yq -r ".issues[$i].title" "$file")"
    body="$(yq -r ".issues[$i].body" "$file")"
    milestone="$(yq -r ".issues[$i].milestone" "$file")"
    labels_csv="$(yq -r ".issues[$i].labels | join(\",\")" "$file")"

    # checa existência por título (qualquer estado)
    local existing
    existing="$(gh issue list -R "$repo" --state all --search "in:title \"$title\"" --json number,title --jq '.[0].number' 2>/dev/null || true)"

    if [[ -n "$existing" ]]; then
      log "🔎 issue já existe (#$existing): $title"
      continue
    fi

    # cria
    if [[ -n "$labels_csv" && "$labels_csv" != "null" ]]; then
      gh_run issue create -R "$repo" --title "$title" --body "$body" --milestone "$milestone" --label "$labels_csv" >/dev/null
    else
      gh_run issue create -R "$repo" --title "$title" --body "$body" --milestone "$milestone" >/dev/null
    fi
    log "🆕 issue criado: $title"
  done
  ok "Issues processadas"
}

# ------------------------------ Main ------------------------------

main() {
  require_tools

  local REPO
  REPO="$(resolve_repo "${1:-}")"
  info "📦 Repositório alvo: $REPO"

  local SCRIPT_DIR ROADMAP_FILE
  SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
  ROADMAP_FILE="${ROADMAP_FILE:-$SCRIPT_DIR/roadmap.yml}"

  if [[ ! -f "$ROADMAP_FILE" ]]; then
    err "Arquivo de dados não encontrado: $ROADMAP_FILE"
    exit 1
  fi

  info "🗂  Usando roadmap: $ROADMAP_FILE"
  if [[ "${DRY_RUN:-}" = "true" ]]; then
    warn "DRY_RUN habilitado — nenhuma alteração será aplicada."
  fi
  if [[ -n "${START_DATE:-}" ]]; then
    info "🗓  START_DATE definido: ${START_DATE}"
  fi

  process_labels     "$REPO" "$ROADMAP_FILE"
  process_milestones "$REPO" "$ROADMAP_FILE"
  process_issues     "$REPO" "$ROADMAP_FILE"

  ok "Roadmap bootstrap concluído!"
}

main "$@"
