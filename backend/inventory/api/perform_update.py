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


def _run(cmd: list[str], cwd: str, timeout: int = 120) -> dict:
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd
        )
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except FileNotFoundError:
        return {"ok": False, "stdout": "", "stderr": f"Comando não encontrado: {cmd[0]}"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "stdout": "", "stderr": "Timeout"}
    except Exception as e:
        return {"ok": False, "stdout": "", "stderr": str(e)}


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _stream_update():
    yield _sse({"step": "start", "msg": "Iniciando atualização…"})

    # Step 1 — git pull
    yield _sse({"step": "git", "msg": "Obtendo código mais recente (git pull)…", "running": True})
    res = _run(["git", "pull", "origin", "main"], cwd=APP_DIR, timeout=60)
    yield _sse({
        "step": "git",
        "ok": res["ok"],
        "msg": res["stdout"] or res["stderr"] or "git pull concluído",
        "running": False,
    })

    # Step 2 — migrate
    yield _sse({"step": "migrate", "msg": "Aplicando migrações do banco (migrate)…", "running": True})
    res = _run(
        ["python", "manage.py", "migrate", "--noinput", "--skip-checks"],
        cwd=BACKEND_DIR, timeout=120,
    )
    yield _sse({
        "step": "migrate",
        "ok": res["ok"],
        "msg": res["stdout"][-500:] if res["stdout"] else (res["stderr"] or "migrate concluído"),
        "running": False,
    })

    # Step 3 — collectstatic
    yield _sse({"step": "static", "msg": "Coletando arquivos estáticos (collectstatic)…", "running": True})
    res = _run(
        ["python", "manage.py", "collectstatic", "--noinput", "--skip-checks"],
        cwd=BACKEND_DIR, timeout=120,
    )
    yield _sse({
        "step": "static",
        "ok": res["ok"],
        "msg": res["stdout"][-300:] if res["stdout"] else (res["stderr"] or "collectstatic concluído"),
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
