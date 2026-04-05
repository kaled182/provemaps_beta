"""
Unified configuration package for mapsprovefiber.

Provides helpers to import environment modules like ``settings.dev`` or
``settings.prod`` automatically.
"""

import os
import sys
from typing import TYPE_CHECKING, Any, Dict


def _resolve_settings_module() -> str:
    """
    Determine and ensure DJANGO_SETTINGS_MODULE is set in the environment.

    Priority:
    1. DJANGO_SETTINGS_MODULE env var (e.g. set by docker-compose) — respected as-is
    2. DEBUG=true  → settings.dev
    3. PRODUCTION=true → settings.prod
    4. pytest in argv → settings.test
    5. runserver/shell in argv → settings.dev
    6. Fallback → settings.dev
    """
    module = os.environ.get("DJANGO_SETTINGS_MODULE", "").strip()

    if not module:
        # Determine from environment context when not explicitly set
        if os.getenv("DEBUG", "").lower() == "true":
            module = "settings.dev"
        elif os.getenv("PRODUCTION", "").lower() == "true":
            module = "settings.prod"
        else:
            argv = " ".join(sys.argv)
            if "pytest" in argv:
                module = "settings.test"
            elif "runserver" in argv or "shell" in argv:
                module = "settings.dev"
            else:
                module = "settings.dev"

        # Normalize: accept bare names like "dev" → "settings.dev"
        if not module.startswith("settings."):
            module = f"settings.{module}"

        # Write resolved module back so Django (and sub-processes) pick it up
        os.environ["DJANGO_SETTINGS_MODULE"] = module

    return module


# Resolve once at package import time — does NOT import the settings module
# itself (Django's LazySettings handles that via DJANGO_SETTINGS_MODULE).
current_settings: str = _resolve_settings_module()


def get_settings_info() -> Dict[str, Any]:
    """Return metadata about the current settings for debugging purposes."""
    env = (
        "production"
        if current_settings.endswith(".prod")
        else ("test" if current_settings.endswith(".test") else "development")
    )
    return {
        "module": current_settings,
        "debug": os.getenv("DEBUG", "Not set"),
        "environment": env,
        "python_path": sys.path,
    }


if TYPE_CHECKING:  # pragma: no cover — assists type checkers only
    from .base import *  # noqa: F401,F403
    from .dev import *   # noqa: F401,F403
    from .prod import *  # noqa: F401,F403
