#!/usr/bin/env bash
# =============================================================================
# Repõe as skills de agente declaradas em skills-lock.json.
# -----------------------------------------------------------------------------
# Porquê um script e não `skills experimental_install`: esse comando escreve
# SEMPRE em `.agents/skills/` (por desenho do CLI), e o Claude Code lê
# `.claude/skills/`. Este script re-corre os `skills add` com `-a claude-code`,
# derivando as fontes do próprio lockfile (uma invocação por repositório).
#
# Uso:  ./scripts/skills-install.sh  (ou `make skills`)
# Pré-requisito: `npm install -g skills` (CLI de vercel-labs/skills).
# Mesmo mecanismo do CRM Simples Internet — ver doc/ferramentas-agente.md.
# =============================================================================
set -euo pipefail

cd "$(dirname "$0")/.."

command -v skills >/dev/null 2>&1 || {
  echo "CLI 'skills' não encontrada. Instala com: npm install -g skills" >&2
  exit 1
}
[ -f skills-lock.json ] || { echo "skills-lock.json não existe." >&2; exit 1; }

# Agrupa por fonte: "<source>\t<skill> <skill> ..." (uma invocação por repo).
node -e '
const lock = require("./skills-lock.json");
const bySource = new Map();
for (const [name, meta] of Object.entries(lock.skills ?? {})) {
  if (!bySource.has(meta.source)) bySource.set(meta.source, []);
  bySource.get(meta.source).push(name);
}
for (const [source, names] of bySource) console.log([source, ...names].join("\t"));
' | while IFS=$'\t' read -r source names; do
  # shellcheck disable=SC2086
  read -r -a skill_names <<< "$names"
  args=()
  for n in "${skill_names[@]}"; do args+=(--skill "$n"); done
  echo "→ $source: ${skill_names[*]}"
  # `</dev/null`: sem isto o CLI consome o stdin do pipe e o loop só corre 1x.
  skills add "$source" "${args[@]}" -a claude-code -y </dev/null >/dev/null
done

echo "✓ Skills repostas em .claude/skills/ (as novas só entram na sessão seguinte)."
