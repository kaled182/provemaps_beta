"""EV-0095 — regras puras: sinal, queda coletiva, severidade, ocupação."""

from datetime import UTC, datetime, timedelta

from gpon.domain import rules

T0 = datetime(2026, 11, 24, 1, 0, tzinfo=UTC)


def test_signal_classification_boundaries():
    assert rules.classify_signal(None, -24, -27) is None
    assert rules.classify_signal(-23.9, -24, -27) == "normal"
    assert rules.classify_signal(-24.0, -24, -27) == "warning"
    assert rules.classify_signal(-27.0, -24, -27) == "warning"
    assert rules.classify_signal(-27.1, -24, -27) == "critical"


def test_signal_uses_onu_rx_then_olt_rx():
    assert rules.signal_dbm(-20.0, -26.0) == -20.0
    assert rules.signal_dbm(None, -26.0) == -26.0
    assert rules.signal_dbm(None, None) is None


def test_collective_drop_three_los_within_nine_minutes():
    times = [T0, T0 + timedelta(minutes=4), T0 + timedelta(minutes=9)]
    assert rules.is_collective_drop(times) is True


def test_collective_drop_spread_over_twenty_minutes_is_false():
    times = [T0, T0 + timedelta(minutes=10, seconds=1), T0 + timedelta(minutes=20)]
    assert rules.is_collective_drop(times) is False


def test_collective_drop_needs_three():
    assert rules.is_collective_drop([T0, T0]) is False
    # janela deslizante: as três últimas caem em 10 min
    times = [
        T0,
        T0 + timedelta(hours=1),
        T0 + timedelta(hours=1, minutes=5),
        T0 + timedelta(hours=1, minutes=10),
    ]
    assert rules.is_collective_drop(times) is True


def test_pon_severity():
    base = {
        "collective_drop": False,
        "los": 0,
        "status": "up",
        "signal_warning": 0,
        "signal_critical": 0,
        "occupancy": 10.0,
    }
    assert rules.pon_severity(**base) == "normal"
    assert rules.pon_severity(**{**base, "collective_drop": True}) == "critical"
    assert rules.pon_severity(**{**base, "los": 3}) == "critical"
    assert rules.pon_severity(**{**base, "los": 2}) == "normal"
    assert rules.pon_severity(**{**base, "status": "down"}) == "critical"
    assert rules.pon_severity(**{**base, "signal_warning": 1}) == "warning"
    assert rules.pon_severity(**{**base, "signal_critical": 1}) == "warning"
    assert rules.pon_severity(**{**base, "occupancy": 85.0}) == "normal"
    assert rules.pon_severity(**{**base, "occupancy": 85.1}) == "warning"


def test_onu_severity_rank():
    assert rules.onu_severity_rank("offline", "los", None) == 0
    assert rules.onu_severity_rank("online", None, "critical") == 1
    assert rules.onu_severity_rank("online", None, "warning") == 2
    assert rules.onu_severity_rank("offline", "dying_gasp", None) == 3
    assert rules.onu_severity_rank("offline", "other", None) == 4
    assert rules.onu_severity_rank("offline", None, None) == 4
    assert rules.onu_severity_rank("unknown", None, None) == 5
    assert rules.onu_severity_rank("online", None, "normal") == 6
    assert rules.onu_severity_rank("online", None, None) == 6


def test_occupancy():
    assert rules.occupancy_pct(12, 128) == 9.4
    assert rules.occupancy_pct(64, 64) == 100.0
    assert rules.occupancy_pct(1, 0) is None
