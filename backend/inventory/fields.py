"""Custom field utilities for the inventory app."""
from __future__ import annotations

from typing import Any, Tuple, cast

from django.db import models


class LenientJSONField(models.JSONField):  # type: ignore[misc]
    """JSONField that tolerates already-deserialized values from the DB."""

    def from_db_value(
        self,
        value: object,
        expression: Any,
        connection: Any,
    ) -> Any:  # noqa: ANN401 - Django contract
        if value is None:
            return value
        # psycopg2 may already deserialize JSON columns into Python types.
        if isinstance(value, (dict, list)):
            return cast(Any, value)
        try:
            return super().from_db_value(value, expression, connection)
        except TypeError:
            # Some drivers raise TypeError instead of JSONDecodeError on lists.
            return cast(Any, value)

    def deconstruct(self) -> Tuple[str, str, Tuple[Any, ...], dict[str, Any]]:
        name, path, args, kwargs = super().deconstruct()
        path = "inventory.fields.LenientJSONField"
        return name, path, args, kwargs
