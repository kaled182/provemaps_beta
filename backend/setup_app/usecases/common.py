"""Conversões partilhadas pelos usecases do setup_app."""

from __future__ import annotations


def to_bool(value: object) -> bool:
    """Interpreta flags vindas do .env/JSON ("true", "1", "yes", "on" → True)."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        return False
    return bool(value)
