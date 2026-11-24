"""EV-0095 — parsers ZTE/VSOL e classificação do motivo (módulo puro).

Os itens são cópias de linhas reais do ``item.get`` de produção (2026-11-24, só leitura).
"""

from gpon.domain import parsers
from inventory.domain.optical import validate_optical_reading

CLOCK = "1795484312"

# valuemap 1406 «Motivo Offline ONU» tal como está no Zabbix de produção.
VALUEMAP_1406 = [
    {"type": "0", "value": "1", "newvalue": "Desconhecido"},
    {"type": "0", "value": "2", "newvalue": "LOS"},
    {"type": "0", "value": "3", "newvalue": "LOSi"},
    {"type": "0", "value": "4", "newvalue": "LOFi"},
    {"type": "0", "value": "5", "newvalue": "SFi"},
    {"type": "0", "value": "6", "newvalue": "LOAi"},
    {"type": "0", "value": "7", "newvalue": "LOAMi"},
    {"type": "0", "value": "8", "newvalue": "AuthFail"},
    {"type": "0", "value": "9", "newvalue": "PowerOff"},
    {"type": "0", "value": "10", "newvalue": "DeactivateSucc"},
    {"type": "0", "value": "11", "newvalue": "DeactivateFail"},
    {"type": "0", "value": "12", "newvalue": "Reboot"},
    {"type": "0", "value": "13", "newvalue": "Shutdown"},
]


def item(key, lastvalue, *, value_type="0", lastclock=CLOCK, state="0", **extra):
    return {
        "key_": key,
        "value_type": value_type,
        "lastvalue": lastvalue,
        "lastclock": lastclock,
        "state": state,
        **extra,
    }


def zte_onu(serial, slot, pon, onu, *, status, reason, rx, dist):
    params = f"{serial},{slot},{pon},{onu}"
    return [
        item(f"onu.status[{params}]", status, value_type="1"),
        item(f"onu.offreason[{params}]", reason, value_type="3", valuemapid="1406"),
        item(f"onu.rx[{params}]", rx),
        item(f"onu.dist[{params}]", dist, value_type="3"),
    ]


def parse_zte(items):
    return parsers.parse_zte(items, validate_rx=validate_optical_reading)


def parse_vsol(items):
    return parsers.parse_vsol(items, validate_rx=validate_optical_reading)


# --- ZTE ------------------------------------------------------------------------------------


def test_zte_onu_online_with_rx_and_distance():
    olt = parse_zte(
        zte_onu(
            "SHLN3C3C2609",
            9,
            13,
            2,
            status="online",
            reason="9",
            rx="-25.086000000000002",
            dist="1854",
        )
    )
    assert olt.vendor == "zte" and olt.technology == "gpon"
    [onu] = olt.onus
    assert onu.onu_key == "SHLN3C3C2609"
    assert onu.serial == "SHLN3C3C2609"
    assert onu.pon_id == "9/13" and onu.onu_index == 2
    assert onu.status == "online" and onu.raw_status == "online"
    assert onu.raw_reason == "9" and onu.reason_valuemapid == "1406"
    assert onu.rx_olt_dbm == -25.086000000000002
    assert onu.rx_onu_dbm is None  # ZTE não tem RX na ONU
    assert onu.distance_m == 1854
    assert onu.rx_item_key == "onu.rx[SHLN3C3C2609,9,13,2]"


def test_zte_sentinels_and_zero_distance_are_null():
    offline = zte_onu("2008350141B7", 9, 12, 13, status="offline", reason="9", rx="-80", dist="0")
    online_no_reading = zte_onu(
        "ZYXE8CAEECCE", 9, 14, 1, status="online", reason="2", rx="0", dist="0"
    )
    olt = parse_zte(offline + online_no_reading)
    by_key = {o.onu_key: o for o in olt.onus}
    assert by_key["2008350141B7"].rx_olt_dbm is None
    assert by_key["2008350141B7"].distance_m is None
    assert by_key["ZYXE8CAEECCE"].rx_olt_dbm is None
    assert by_key["ZYXE8CAEECCE"].status == "online"
    # o item de RX existe e é numérico: há histórico mesmo sem leitura agora
    assert by_key["ZYXE8CAEECCE"].rx_item_key


def test_zte_unsupported_or_never_collected_status_is_unknown():
    items = [
        item("onu.status[AAAA00000001,9,1,1]", "online", value_type="1", state="1"),
        item("onu.status[AAAA00000002,9,1,2]", "online", value_type="1", lastclock="0"),
        item("onu.status[AAAA00000003,9,1,3]", "logging", value_type="1"),
    ]
    olt = parse_zte(items)
    assert [o.status for o in olt.onus] == ["unknown", "unknown", "unknown"]
    assert olt.has_known_onu is False


def test_zte_olt_fields_ping_cpu_model_and_pon_status():
    items = [
        item("icmpping", "1", value_type="3", lastclock="1795484582"),
        item("cpu", "0", value_type="3", lastclock="0", state="1"),  # unsupported em produção
        item("cardcpu[1.1.0]", "12", value_type="3"),
        item("cardcpu[1.2.0]", "17", value_type="3"),
        item("TempGeral", "0", value_type="3", lastclock="0", state="1"),
        item(
            "sysDescr",
            "C300 Version V2.1.0 Software, Copyright (c) by ZTE Corporation Compiled",
            value_type="1",
        ),
        item("ifOperStatus[285280526]", "1", value_type="1"),  # 0x1101090E = gpon 9/14
        item("ifOperStatus[285280515]", "2", value_type="1"),  # 0x11010903 = gpon 9/3
        item("ifOperStatus[654311425]", "2", value_type="1"),  # 0x27000001 — não é PON
    ]
    olt = parse_zte(items)
    assert olt.ping == 1
    assert olt.cpu_pct == 17.0  # sem `cpu` agregado: a placa mais carregada
    assert olt.temperature_c is None
    assert olt.model == "C300"
    assert olt.pon_status == {"9/14": "up", "9/3": "down"}


def test_zte_pon_from_ifindex():
    assert parsers.zte_pon_from_ifindex(285280513) == "9/1"
    assert parsers.zte_pon_from_ifindex(285283332) == "20/4"
    assert parsers.zte_pon_from_ifindex(654311425) is None


# --- VSOL -----------------------------------------------------------------------------------


def test_vsol_mac_keyed_items_with_description():
    items = [
        item(
            "OnlineStateS0P1[00:19:46:49:4b:7d - 10]",
            "1",
            value_type="3",
            name="Status da ONU 0/1/10 - 00:19:46:49:4b:7d - INTRANET-CAMERAS-DVR",
        ),
        item(
            "SinalRXS0P1[00:19:46:49:4b:7d - 10]",
            "-26.99",
            name="Sinal RX da ONU 0/1/10 - 00:19:46:49:4b:7d - INTRANET-CAMERAS-DVR",
        ),
    ]
    olt = parse_vsol(items)
    assert olt.vendor == "vsol" and olt.technology == "epon"
    [onu] = olt.onus
    assert onu.onu_key == "1:10|00:19:46:49:4b:7d"
    assert onu.pon_id == "0/1" and onu.onu_index == 10
    assert onu.mac == "00:19:46:49:4b:7d" and onu.serial == ""
    assert onu.description == "INTRANET-CAMERAS-DVR"
    assert onu.status == "online"
    assert onu.rx_onu_dbm == -26.99 and onu.rx_olt_dbm is None
    assert onu.rx_item_key == "SinalRXS0P1[00:19:46:49:4b:7d - 10]"


def test_vsol_gpon_style_keys_serial_and_interface_description():
    items = [
        item(
            "OnlineStateS0P1[GPON0/1:10 - 10]",
            "2",
            value_type="3",
            name="Status da ONU 0/1/10 - DACM91889c5c - GPON0/1:10",
        ),
        item(
            "SinalRXS0P1[GPON0/1:10 - 10]",
            "0",
            name="Sinal RX da ONU 0/1/10 - DACM91889c5c - GPON0/1:10",
        ),
        item("ifOperStatus[GPON0/1]", "1", value_type="3"),
    ]
    olt = parse_vsol(items)
    [onu] = olt.onus
    assert onu.onu_key == "1:10|dacm91889c5c"
    assert onu.serial == "DACM91889c5c" and onu.mac == ""
    assert onu.description == ""  # «GPON0/1:10» é a interface, não descrição
    assert onu.status == "offline"
    assert onu.rx_onu_dbm is None  # 0 = sentinela
    assert olt.pon_status == {"0/1": "up"}


def test_vsol_never_collected_is_unknown_and_null_description():
    # Nova Barreira: 196 ONUs todas assim (lastclock 0, lastvalue 0).
    items = [
        item(
            "OnlineStateS0P1[a8:bf:3c:355:3a - 124]",
            "0",
            value_type="3",
            lastclock="0",
            name="Status da ONU 0/1/124 - a8:bf:3c:355:3a - NULL",
        ),
        item(
            "SinalRXS0P1[a8:bf:3c:355:3a - 124]",
            "0",
            lastclock="0",
            name="Sinal RX da ONU 0/1/124 - a8:bf:3c:355:3a - NULL",
        ),
        item("icmpping", "1", value_type="3"),
        item("cpuLoad", "0", value_type="3", lastclock="0"),
        item("sysTemperature", "0", value_type="3", lastclock="0"),
    ]
    olt = parse_vsol(items)
    [onu] = olt.onus
    assert onu.status == "unknown" and onu.raw_status == ""
    assert onu.description == ""
    assert onu.mac == "a8:bf:3c:355:3a"
    assert onu.rx_onu_dbm is None
    assert olt.ping == 1 and olt.cpu_pct is None and olt.temperature_c is None
    assert olt.has_known_onu is False


def test_vsol_status_values():
    def status_of(value):
        olt = parse_vsol(
            [
                item(
                    "OnlineStateS0P2[a8:bf:3c:4d:92:3e - 44]",
                    value,
                    value_type="3",
                    name="Status da ONU 0/2/44 - a8:bf:3c:4d:92:3e - NULL",
                )
            ]
        )
        return olt.onus[0].status

    assert status_of("1") == "online"
    assert status_of("2") == "offline"
    assert status_of("0") == "unknown"
    assert status_of("5") == "unknown"


def test_vsol_without_name_falls_back_to_key():
    olt = parse_vsol([item("OnlineStateS0P4[d8:38d:66:e2:b0 - 16]", "1", value_type="3")])
    [onu] = olt.onus
    assert onu.pon_id == "0/4" and onu.onu_index == 16
    assert onu.onu_key == "4:16"


def test_parse_olt_items_dispatches_by_vendor():
    assert parsers.parse_olt_items("zte", [], validate_rx=validate_optical_reading).vendor == "zte"
    assert (
        parsers.parse_olt_items("vsol", [], validate_rx=validate_optical_reading).vendor == "vsol"
    )


def test_detect_vendor():
    assert parsers.detect_vendor("ZTE - OLT BRV C300", "") == "zte"
    assert parsers.detect_vendor("VSOL - OLT EPON PLANURA", None) == "vsol"
    assert parsers.detect_vendor("OLT Bairro", "V-SOL") == "vsol"
    assert parsers.detect_vendor("Huawei OLT", "") is None


# --- Motivo (valuemap) ----------------------------------------------------------------------


def test_valuemap_1406_classification():
    expected = {
        "1": "other",
        "2": "los",
        "3": "los",
        "4": "los",
        "5": "other",
        "6": "other",
        "7": "other",
        "8": "other",
        "9": "dying_gasp",
        "10": "other",
        "11": "other",
        "12": "other",
        "13": "other",
    }
    got = {
        code: parsers.classify_reason_text(parsers.valuemap_text(VALUEMAP_1406, code))
        for code in expected
    }
    assert got == expected


def test_reason_without_valuemap_or_unknown_code_is_null():
    assert parsers.valuemap_text(None, "2") is None
    assert parsers.valuemap_text([], "2") is None
    assert parsers.valuemap_text(VALUEMAP_1406, "99") is None
    assert parsers.classify_reason_text(None) is None
    # só correspondência exata (type 0); intervalos/regex não se interpretam
    assert parsers.valuemap_text([{"type": "1", "value": "2", "newvalue": "LOS"}], "2") is None


def test_classify_reason_text_variants():
    assert parsers.classify_reason_text("Loss of signal") == "los"
    assert parsers.classify_reason_text("DyingGasp") == "dying_gasp"
    assert parsers.classify_reason_text("Closed") == "other"  # «los» dentro de palavra não conta
