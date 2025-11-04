"""Contract tests for the routes_builder.services public API."""

from __future__ import annotations

import inspect
from typing import Any

import pytest

from routes_builder import services


def _callable_signature(obj: Any) -> inspect.Signature:
    return inspect.signature(obj)


def test_rebuild_route_signature_and_placeholder() -> None:
    sig = _callable_signature(services.rebuild_route)
    assert list(sig.parameters) == ["context"], (
        "rebuild_route expects a context parameter"
    )
    context = services.RouteBuildContext(route_id=1, force=True, options={})
    with pytest.raises(services.RouteServiceError):
        services.rebuild_route(context)


def test_rebuild_routes_batch_signature_and_placeholder() -> None:
    sig = _callable_signature(services.rebuild_routes_batch)
    assert list(sig.parameters) == ["contexts"], (
        "rebuild_routes_batch expects an iterable of contexts"
    )
    context = services.RouteBuildContext(route_id=1)
    result = services.rebuild_routes_batch([context])
    assert result.processed == ()
    assert result.failures == (1,)


def test_import_route_from_payload_signature_and_placeholder() -> None:
    sig = _callable_signature(services.import_route_from_payload)
    params = list(sig.parameters)
    assert params == ["payload", "created_by"], (
        "import_route_from_payload exposes payload and created_by parameters"
    )
    with pytest.raises(services.RouteServiceError):
        services.import_route_from_payload({}, created_by="tests")


def test_invalidate_route_cache_placeholder() -> None:
    assert services.invalidate_route_cache(1) is None


@pytest.mark.django_db
def test_health_summary_returns_expected_structure() -> None:
    summary: dict[str, Any] = services.health_summary()
    assert summary["routes"] >= 0
    assert summary["segments"] >= 0
    assert summary["events"] >= 0
    assert "recent_events" in summary
    assert "generated_at" in summary
