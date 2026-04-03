from __future__ import annotations

import os
import uuid
import logging
import platform
import sys

from celery import shared_task

logger = logging.getLogger(__name__)

# Path where the installation UUID is persisted between restarts
_BASE_DIR = os.path.dirname(  # project root
    os.path.dirname(           # backend/
        os.path.dirname(       # telemetry/
            os.path.abspath(__file__)
        )
    )
)
_INSTALLATION_ID_FILE = os.path.join(_BASE_DIR, "data", "installation.id")


def get_or_create_installation_id() -> uuid.UUID:
    """
    Returns the stable anonymous installation UUID.
    Creates and persists a new one if it doesn't exist yet.
    """
    os.makedirs(os.path.dirname(_INSTALLATION_ID_FILE), exist_ok=True)
    try:
        with open(_INSTALLATION_ID_FILE) as f:
            return uuid.UUID(f.read().strip())
    except (FileNotFoundError, ValueError):
        new_id = uuid.uuid4()
        with open(_INSTALLATION_ID_FILE, "w") as f:
            f.write(str(new_id))
        logger.info("Telemetry: new installation ID generated: %s", new_id)
        return new_id


def _read_version() -> str:
    version_file = os.path.join(_BASE_DIR, "VERSION")
    try:
        with open(version_file) as f:
            return f.read().strip()
    except FileNotFoundError:
        return "unknown"


@shared_task(
    name="telemetry.tasks.send_ping",
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 min between retries
    ignore_result=True,
)
def send_ping(self):
    """
    Daily telemetry ping — sends anonymous installation data to the
    configured TELEMETRY_ENDPOINT. Silently skipped if
    TELEMETRY_ENABLED=false or endpoint is not set.
    """
    from django.conf import settings

    enabled = os.environ.get("TELEMETRY_ENABLED", "true").lower()
    if enabled in ("false", "0", "no"):
        logger.debug("Telemetry disabled — skipping ping.")
        return

    endpoint = getattr(settings, "TELEMETRY_ENDPOINT", None) or os.environ.get(
        "TELEMETRY_ENDPOINT", ""
    )
    if not endpoint:
        logger.debug("Telemetry: TELEMETRY_ENDPOINT not set — skipping ping.")
        return

    installation_id = get_or_create_installation_id()
    version = _read_version()

    payload = {
        "id": str(installation_id),
        "version": version,
        "os": platform.system(),
    }

    try:
        import urllib.request, json as _json

        data = _json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": f"ProVemaps/{version}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            logger.info(
                "Telemetry ping sent: id=%s version=%s status=%s",
                installation_id,
                version,
                resp.status,
            )
    except Exception as exc:
        logger.warning("Telemetry ping failed: %s", exc)
        try:
            self.retry(exc=exc)
        except Exception:
            pass  # max retries reached — fail silently
