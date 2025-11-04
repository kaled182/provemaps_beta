"""
Unified configuration package for mapsprovefiber.

Provides helpers to import environment modules like ``settings.dev`` or
``settings.prod`` automatically.
"""

import os
import sys
from typing import TYPE_CHECKING, Any, Dict

# -----------------------------------------------------
# Environment configuration with validation
# -----------------------------------------------------


def setup_environment() -> str:
    """Configure Django with safe fallbacks and return the settings module."""
    env_settings = os.getenv("DJANGO_SETTINGS_MODULE", "").strip()

    # If not specified, determine from context
    if not env_settings:
        if os.getenv("DEBUG", "").lower() == "true":
            env_settings = "settings.dev"
        elif os.getenv("PRODUCTION", "").lower() == "true":
            env_settings = "settings.prod"
        else:
            # Fallback based on common conventions
            argv = " ".join(sys.argv)
            if "pytest" in argv:
                env_settings = "settings.test"
            elif "runserver" in argv or "shell" in argv:
                env_settings = "settings.dev"
            else:
                env_settings = "settings.dev"  # Safe default

    # Normalize module format
    if env_settings and not env_settings.startswith("settings."):
        env_settings = f"settings.{env_settings}"

    # Validate that the module exists (except base)
    if env_settings and env_settings != "settings.base":
        try:
            __import__(env_settings)
        except ImportError as e:
            print(f"⚠️  Warning: failed to import {env_settings}: {e}")
            print("📁 Falling back to settings.dev")
            env_settings = "settings.dev"

    # Update environment variable
    if env_settings:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", env_settings)

    return env_settings


# Execute setup
current_settings = setup_environment()

# -----------------------------------------------------
# Debug helpers
# -----------------------------------------------------


def get_settings_info() -> Dict[str, Any]:
    """Return metadata about the current settings for debugging purposes."""
    env = "production" if current_settings.endswith(".prod") else (
        "test" if current_settings.endswith(".test") else "development"
    )
    return {
        "module": current_settings,
        "debug": os.getenv("DEBUG", "Not set"),
        "environment": env,
        "python_path": sys.path,
    }


# -----------------------------------------------------
# Conditional imports for IDEs and type checkers (never run at runtime)
# -----------------------------------------------------
if TYPE_CHECKING:  # pragma: no cover
    from .base import *  # noqa: F401,F403
    from .dev import *  # noqa: F401,F403
    from .prod import *  # noqa: F401,F403
