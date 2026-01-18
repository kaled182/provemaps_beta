from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Iterable

from django.conf import settings


_DEFAULT_ENV_PATH = Path(settings.BASE_DIR) / ".env"
ENV_PATH = Path(os.environ.get("ENV_FILE_PATH", _DEFAULT_ENV_PATH))
_RAW_JSON_KEYS = {"GDRIVE_CREDENTIALS_JSON"}


def _normalize_value(value: str | None) -> str:
    if value is None:
        return ""
    return value.replace("\n", "").strip()


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def _quote(value: str, use_single: bool = False) -> str:
    if use_single and "'" not in value:
        return f"'{value}'"
    escaped = value.replace('"', '\\"')
    return f'"{escaped}"'


def _maybe_unescape_json(value: str) -> str:
    if '\\"' in value:
        return value.replace('\\"', '"')
    return value


def read_env() -> Dict[str, str]:
    """
    Read the .env file and return a dict mapping keys to values.
    Comments and empty lines are ignored.
    """
    data: Dict[str, str] = {}
    if not ENV_PATH.exists():
        return data

    with ENV_PATH.open("r", encoding="utf-8") as handler:
        for raw_line in handler:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            data[key.strip()] = _strip_quotes(value.strip())
    return data


def read_values(keys: Iterable[str]) -> Dict[str, str]:
    env_map = read_env()
    values: Dict[str, str] = {}
    for key in keys:
        raw_value = env_map.get(key, "")
        if not raw_value:
            raw_value = os.environ.get(key, "")
        value = _normalize_value(raw_value)
        if key in _RAW_JSON_KEYS:
            value = _maybe_unescape_json(value)
        values[key] = value
    return values


def write_values(values: Dict[str, str]) -> None:
    """
    Update the specified keys while preserving the rest of the file.
    Missing keys are appended to the end.
    """
    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    normalized_values = {}
    for key, val in values.items():
        normalized = _normalize_value(val)
        use_single = key in _RAW_JSON_KEYS
        normalized_values[key] = _quote(normalized, use_single=use_single)
    lines: list[str] = []
    seen = set()

    if ENV_PATH.exists():
        with ENV_PATH.open("r", encoding="utf-8") as handler:
            for raw_line in handler:
                if "=" not in raw_line:
                    lines.append(raw_line)
                    continue

                key, _ = raw_line.split("=", 1)
                key = key.strip()
                if key in normalized_values:
                    lines.append(f"{key}={normalized_values[key]}\n")
                    seen.add(key)
                else:
                    lines.append(raw_line)
    else:
        ENV_PATH.touch()

    for key, value in normalized_values.items():
        if key not in seen:
            lines.append(f"{key}={value}\n")

    with ENV_PATH.open("w", encoding="utf-8") as handler:
        handler.writelines(lines)
