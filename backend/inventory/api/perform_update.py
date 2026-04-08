from __future__ import annotations

import json
import logging
import os
import subprocess

from django.contrib.auth.decorators import login_required
from django.http import StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)

APP_DIR = os.environ.get("APP_DIR", "/app")
BACKEND_DIR = os.path.join(APP_DIR, "backend")

# Aviso do collectstatic sobre arquivos duplicados — não é um erro real
_COLLECTSTATIC_DUPE_WARNING = "another file with the destination path"


def _run(cmd: list[str], cwd: str, timeout: int = 120) -> dict:
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd
        )
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode,
        }
    except FileNotFoundError:
        return {"ok": False, "stdout": "", "stderr": f"Comando não encontrado: {cmd[0]}", "returncode": -1}
    except subprocess.TimeoutExpired:
        return {"ok": False, "stdout": "", "stderr": "Timeout ao executar comando", "returncode": -1}
    except Exception as e:
        return {"ok": False, "stdout": "", "stderr": str(e), "returncode": -1}


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _msg_for(res: dict, fallback: str = "Concluído") -> str:
    """Retorna a mensagem mais útil do resultado do comando."""
    combined = "\n".join(filter(None, [res.get("stdout", ""), res.get("stderr", "")])).strip()
    return combined[-400:] if combined else fallback


def _stream_update():
    yield _sse({"step": "start", "msg": "Iniciando atualização…"})

    # ── Step 1: git pull (opcional — pode falhar no container sem repo remoto) ──
    yield _sse({"step": "git", "msg": "Verificando código (git pull)…", "running": True})
    res = _run(["git", "pull", "origin", "main"], cwd=APP_DIR, timeout=60)

    if res["ok"]:
        git_msg = res["stdout"] or "Código já atualizado."
    else:
        # No container, o código é baked na imagem — git pull não funciona.
        # Reportar como aviso (warning), não como erro crítico.
        git_msg = (
            "ℹ️  git pull não disponível no container (código baked na imagem).\n"
            "Para atualizar o código, execute scripts/update.sh no servidor."
        )

    yield _sse({
        "step": "git",
        "ok": True,          # sempre ok — não é um passo crítico
        "warning": not res["ok"],   # sinaliza aviso visual sem bloquear
        "msg": git_msg,
        "running": False,
    })

    # ── Step 2: migrate ──────────────────────────────────────────────────────
    yield _sse({"step": "migrate", "msg": "Aplicando migrações do banco…", "running": True})
    res = _run(
        ["python", "manage.py", "migrate", "--noinput", "--skip-checks"],
        cwd=BACKEND_DIR, timeout=120,
    )
    yield _sse({
        "step": "migrate",
        "ok": res["ok"],
        "msg": _msg_for(res, "Migrações aplicadas com sucesso."),
        "running": False,
    })

    if not res["ok"]:
        yield _sse({"step": "done", "msg": "Atualização interrompida: falha nas migrações."})
        return

    # ── Step 3: collectstatic ────────────────────────────────────────────────
    yield _sse({"step": "static", "msg": "Coletando arquivos estáticos…", "running": True})
    res = _run(
        ["python", "manage.py", "collectstatic", "--noinput", "--skip-checks"],
        cwd=BACKEND_DIR, timeout=120,
    )

    # Warnings de arquivo duplicado (legacy JS) são normais — não são erros
    is_real_error = not res["ok"] and _COLLECTSTATIC_DUPE_WARNING not in res.get("stdout", "")

    # Mensagem limpa: pegar só a última linha relevante (evita o aviso de duplicata)
    lines = [l for l in (res.get("stdout") or "").splitlines()
             if l.strip() and _COLLECTSTATIC_DUPE_WARNING not in l]
    clean_msg = lines[-1].strip() if lines else (_msg_for(res, "Arquivos estáticos coletados."))

    yield _sse({
        "step": "static",
        "ok": not is_real_error,
        "msg": clean_msg,
        "running": False,
    })

    yield _sse({"step": "done", "msg": "Atualização concluída! Recarregue a página para ver as novidades."})


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def api_perform_update(request):
    response = StreamingHttpResponse(
        _stream_update(),
        content_type="text/event-stream; charset=utf-8",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    response["Connection"] = "keep-alive"
    return response
