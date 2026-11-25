#!/usr/bin/env bash
# Central de Evolução (ADR 0006) — sincroniza o quadro do CLAUDE.md com a produção.
#
#   1. fecha na Central os itens cujo commit `fecha EV-NNNN` já está no ar
#      (o git corre aqui, no host; o Django no container web);
#   2. pede ao container o bloco gerado (`evolucao_quadro --imprimir`);
#   3. troca o bloco <!-- EVOLUCAO:INICIO … --> … <!-- EVOLUCAO:FIM --> do CLAUDE.md DO HOST.
#
# Porquê um script: dentro do container o `evolucao_quadro` escreveria na cópia do CLAUDE.md
# que está na imagem (efémera), não no repositório; e o alvo antigo do makefile apontava para
# o porto 8000 e o manage.py local. Recusa escrever se o bloco vier vazio ou sem marcadores.
#
# Variáveis: EVOLUCAO_HEALTH_URL (http://127.0.0.1:8100/healthz),
#            EVOLUCAO_MANAGE ("docker exec -i docker-web-1 python manage.py").
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HEALTH="${EVOLUCAO_HEALTH_URL:-http://127.0.0.1:8100/healthz}"
read -r -a MANAGE <<< "${EVOLUCAO_MANAGE:-docker exec -i docker-web-1 python manage.py}"

EVOLUCAO_HEALTH_URL="$HEALTH" "$REPO/scripts/evolucao_fechados.sh" | "${MANAGE[@]}" evolucao_fechar

bloco="$("${MANAGE[@]}" evolucao_quadro --imprimir 2>/dev/null \
  | sed -n '/<!-- EVOLUCAO:INICIO/,/<!-- EVOLUCAO:FIM/p')"
case "$bloco" in
  "<!-- EVOLUCAO:INICIO"*"<!-- EVOLUCAO:FIM -->") ;;
  *) echo "evolucao_sync: bloco gerado vazio ou sem marcadores — CLAUDE.md não foi tocado" >&2; exit 1 ;;
esac

BLOCO="$bloco" python3 - "$REPO/CLAUDE.md" <<'PY'
import os, sys
caminho = sys.argv[1]
texto = open(caminho, encoding="utf-8").read()
ini = texto.find("<!-- EVOLUCAO:INICIO")
fim_marca = "<!-- EVOLUCAO:FIM -->"
fim = texto.find(fim_marca, ini)
if ini < 0 or fim < 0:
    sys.exit("evolucao_sync: marcadores EVOLUCAO não encontrados no CLAUDE.md")
novo = texto[:ini] + os.environ["BLOCO"] + texto[fim + len(fim_marca):]
if novo == texto:
    print("evolucao_sync: quadro já estava em dia")
else:
    open(caminho, "w", encoding="utf-8").write(novo)
    print("evolucao_sync: quadro atualizado")
PY
