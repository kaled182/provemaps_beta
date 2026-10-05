#!/usr/bin/env bash
# Diz que itens da Central de Evolução foram resolvidos por commits que JÁ ESTÃO no ar
# (ADR 0006 §4.4). Porte do script homónimo do CRM.
#
# Corre onde o Git existe (host ou CI); a outra metade — `manage.py evolucao_fechar` — corre
# onde a base é alcançável. As duas falam por este JSON em stdout:
#   [{"codigo","commit","mensagem","deploy_em"}]   (ou `[]`)
#
# ⚠️ Fecha por VERBO, não por menção: `fecha EV-0042` (também `fecham`, `resolve`, `closes`,
# `fixes`, com «o/os» opcional). Um commit menciona um código por muitas razões — abrir o
# item, referir-se a ele — e só uma delas é «resolvi isto».
#
# ⚠️ Fail-closed e silencioso: sem `git_sha` no /healthz (imagem construída sem GIT_SHA), ou
# com um SHA que este repositório não conhece, devolve `[]` e explica em stderr. NUNCA rebenta:
# é chamado por hook/make, e um hook que rebenta é desligado ao terceiro dia.
set -uo pipefail

SAUDE="${EVOLUCAO_HEALTH_URL:-http://127.0.0.1:8000/healthz}"
JANELA="${EVOLUCAO_JANELA_DIAS:-90}"
REPO="${EVOLUCAO_REPO_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

resposta="$(curl -s --max-time 5 "$SAUDE" 2>/dev/null || true)"
sha="$(printf '%s' "$resposta" | sed -n 's/.*"git_sha" *: *"\([^"]*\)".*/\1/p')"
iniciado="$(printf '%s' "$resposta" | sed -n 's/.*"iniciado_em" *: *"\([^"]*\)".*/\1/p')"

if [ -z "$sha" ]; then
  echo "evolucao: sem git_sha em $SAUDE — nada é fechado (imagem construída sem GIT_SHA?)" >&2
  echo "[]"
  exit 0
fi
if ! git -C "$REPO" cat-file -e "${sha}^{commit}" 2>/dev/null; then
  echo "evolucao: o commit implantado ($sha) não existe em $REPO — nada é fechado (git fetch?)" >&2
  echo "[]"
  exit 0
fi

primeiro=1
printf '['
# `git log "$sha"` e não `git log`: só o que é ALCANÇÁVEL a partir do que está implantado.
# A janela de dias evita reler a história toda a cada sessão.
while IFS=$'\t' read -r commit assunto; do
  [ -n "$commit" ] || continue
  for codigo in $(printf '%s' "$assunto" \
      | grep -oiE '(fecha|fecham|resolve|resolvem|closes|fixes) +(o +|os +)?EV-[0-9]{4}' \
      | grep -oE 'EV-[0-9]{4}' | sort -u); do
    [ $primeiro -eq 1 ] || printf ','
    primeiro=0
    esc="$(printf '%s' "$assunto" | sed 's/\\/\\\\/g; s/"/\\"/g')"
    printf '{"codigo":"%s","commit":"%s","mensagem":"%s","deploy_em":"%s"}' \
      "$codigo" "$commit" "$esc" "$iniciado"
  done
done < <(git -C "$REPO" log "$sha" --since="${JANELA} days ago" --format='%h%x09%s' 2>/dev/null)
printf ']\n'
