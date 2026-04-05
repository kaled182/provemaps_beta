from __future__ import annotations

import logging
import os
import signal
import subprocess
import threading
from typing import Iterable, List

logger = logging.getLogger(__name__)


def restart_via_sigterm(delay: float = 3.0) -> None:
    """
    Reinicia o container enviando SIGTERM ao PID 1.

    Como o entrypoint usa ``exec "$@"``, o gunicorn roda como PID 1.
    SIGTERM causa seu encerramento gracioso; o Docker reinicia o
    container automaticamente (restart: unless-stopped) e o entrypoint
    recarrega o runtime.env com as novas credenciais antes de iniciar
    o gunicorn.

    O sinal é enviado em background após ``delay`` segundos para
    garantir que a resposta HTTP já chegou ao navegador do usuário.
    """
    def _send_sigterm() -> None:
        try:
            os.kill(1, signal.SIGTERM)
            logger.info(
                "SIGTERM enviado ao PID 1 — "
                "container será reiniciado pelo Docker"
            )
        except Exception as exc:
            logger.error("Falha ao enviar SIGTERM ao PID 1: %s", exc)

    timer = threading.Timer(delay, _send_sigterm)
    timer.daemon = True
    timer.start()
    logger.info("Restart via SIGTERM agendado em %.1fs", delay)


def _collect_base_commands() -> list[str]:
    """
    Gather restart commands from environment (preferred) or settings fallback.

    Expected format: "cmd1; cmd2; cmd3".
    Commands execute with shell=True to support composed statements.
    """
    raw = os.getenv("SERVICE_RESTART_COMMANDS", "")
    if not raw:
        from django.conf import settings

        raw = getattr(settings, "SERVICE_RESTART_COMMANDS", "")

    commands = [snippet.strip() for snippet in raw.split(";") if snippet.strip()]
    return commands


def _run_commands(commands: Iterable[str]) -> None:
    for command in commands:
        try:
            logger.info("Restarting services via command: %s", command)
            subprocess.run(command, shell=True, check=True)
        except subprocess.CalledProcessError as exc:
            logger.error("Restart command failed (%s): %s", exc.returncode, command, exc_info=True)
        except Exception:
            logger.exception("Unexpected error executing restart command: %s", command)


def trigger_restart(additional_commands: Iterable[str] | None = None, *, async_mode: bool = True) -> bool:
    """
    Execute configured restart commands.

    Returns True if at least one command is scheduled/executed.
    """
    commands: List[str] = _collect_base_commands()
    if additional_commands:
        commands.extend(cmd for cmd in additional_commands if cmd)

    if not commands:
        logger.info("No service restart commands configured; skipping restart.")
        return False

    if async_mode:
        thread = threading.Thread(target=_run_commands, args=(commands,), daemon=True)
        thread.start()
    else:
        _run_commands(commands)
    return True


__all__ = ["trigger_restart"]
