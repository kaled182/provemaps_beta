"""EV-0003 — `history.get` com o value_type real do item, não `3` fixo."""

from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from inventory.domain import zabbix_history
from inventory.models import Device, FiberCable, Port, Site


def _fake_zabbix(items_meta, histories):
    """Simula item.get/history.get e regista o `history` pedido por item."""
    calls: dict[str, int] = {}

    def _request(method, params=None, **kwargs):
        params = params or {}
        if method == "item.get":
            ids = [str(i) for i in params.get("itemids", [])]
            return [
                {"itemid": i, "value_type": items_meta[i][0], "units": items_meta[i][1]}
                for i in ids
                if i in items_meta
            ]
        if method == "history.get":
            itemid = str(params["itemids"][0])
            calls[itemid] = params["history"]
            # Como o Zabbix real: tipo errado devolve lista vazia.
            if int(params["history"]) != int(items_meta.get(itemid, ("3", ""))[0]):
                return []
            return histories.get(itemid, [])
        return []

    return _request, calls


class ZabbixHistoryHelperTests(TestCase):
    def test_get_items_meta_resolves_type_and_units(self):
        fake, _ = _fake_zabbix({"111": ("0", "bps"), "222": ("3", "Bps")}, {})
        with patch.object(zabbix_history.zabbix_service, "zabbix_request", side_effect=fake):
            meta = zabbix_history.get_items_meta(["111", 222, None, ""])
        self.assertEqual(meta["111"], {"itemid": "111", "value_type": 0, "units": "bps"})
        self.assertEqual(meta["222"]["value_type"], 3)
        self.assertEqual(meta["222"]["units"], "Bps")

    def test_fetch_history_uses_float_type_for_float_item(self):
        fake, calls = _fake_zabbix(
            {"111": ("0", "bps")},
            {"111": [{"clock": "1690000000", "value": "12.5"}]},
        )
        with patch.object(zabbix_history.zabbix_service, "zabbix_request", side_effect=fake):
            history = zabbix_history.fetch_history("111", 1689990000, 1690000001)
        self.assertEqual(calls["111"], 0)
        self.assertEqual(history, [{"clock": "1690000000", "value": "12.5"}])

    def test_fetch_history_defaults_to_unsigned_when_meta_missing(self):
        fake, calls = _fake_zabbix({}, {"999": [{"clock": "1", "value": "1"}]})
        with patch.object(zabbix_history.zabbix_service, "zabbix_request", side_effect=fake):
            zabbix_history.fetch_history("999", 0, 10)
        self.assertEqual(calls["999"], zabbix_history.DEFAULT_VALUE_TYPE)

    def test_fetch_history_skips_non_numeric_items(self):
        fake, calls = _fake_zabbix({"555": ("4", "")}, {})
        with patch.object(zabbix_history.zabbix_service, "zabbix_request", side_effect=fake):
            self.assertEqual(zabbix_history.fetch_history("555", 0, 10), [])
        self.assertNotIn("555", calls)

    def test_item_get_failure_falls_back_without_raising(self):
        def boom(method, params=None, **kwargs):
            if method == "item.get":
                raise RuntimeError("zabbix down")
            return []

        with patch.object(zabbix_history.zabbix_service, "zabbix_request", side_effect=boom):
            self.assertEqual(zabbix_history.get_items_meta(["1"]), {})
            self.assertEqual(zabbix_history.fetch_history("1", 0, 10), [])

    def test_limit_is_forwarded(self):
        seen = {}

        def _request(method, params=None, **kwargs):
            if method == "item.get":
                return [{"itemid": "7", "value_type": "3", "units": ""}]
            seen.update(params)
            return []

        with patch.object(zabbix_history.zabbix_service, "zabbix_request", side_effect=_request):
            zabbix_history.fetch_history("7", 0, 10, limit=500)
        self.assertEqual(seen["limit"], 500)


class TrafficHistoryEndpointsTests(TestCase):
    """Os endpoints DRF deixam de devolver vazio para itens float."""

    def setUp(self):
        user = get_user_model().objects.create_user(username="ops", password="x")
        self.client.force_login(user)
        site = Site.objects.create(display_name="POP-GYN", city="Goiania")
        self.device = Device.objects.create(
            site=site, name="SW-01", vendor="Huawei", model="S6730", zabbix_hostid="10101"
        )
        self.port_a = Port.objects.create(
            device=self.device,
            name="GE0/0/1",
            zabbix_item_id_traffic_in="111",
            zabbix_item_id_traffic_out="222",
        )
        self.port_b = Port.objects.create(
            device=self.device,
            name="GE0/0/2",
            zabbix_item_id_traffic_in="333",
            zabbix_item_id_traffic_out="444",
        )
        # 111/333 são float (0) — era aqui que `history: 3` devolvia vazio.
        self.meta = {
            "111": ("0", "bps"),
            "222": ("3", "bps"),
            "333": ("0", "Bps"),
            "444": ("3", "Bps"),
        }
        self.histories = {
            "111": [{"clock": "1690000000", "value": "1000.5"}],
            "222": [{"clock": "1690000000", "value": "2000"}],
            "333": [{"clock": "1690000000", "value": "30"}],
            "444": [{"clock": "1690000060", "value": "40"}],
        }

    def test_port_traffic_history_uses_real_value_type(self):
        fake, calls = _fake_zabbix(self.meta, self.histories)
        url = reverse("port-traffic-history", args=[self.port_a.pk])
        with patch("integrations.zabbix.zabbix_service.zabbix_request", side_effect=fake):
            response = self.client.get(url, {"hours": 24})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(calls, {"111": 0, "222": 3})
        payload = response.json()
        self.assertEqual(len(payload["history"]), 1)
        self.assertEqual(payload["history"][0]["traffic_in"], 1000.5)
        self.assertEqual(payload["history"][0]["traffic_out"], 2000.0)
        self.assertEqual(payload["statistics"]["unit_in"], "bps")
        self.assertEqual(payload["statistics"]["unit_out"], "bps")

    def test_cable_traffic_history_uses_real_value_type_for_both_ports(self):
        cable = FiberCable.objects.create(
            name="CABO-01", origin_port=self.port_a, destination_port=self.port_b
        )
        fake, calls = _fake_zabbix(self.meta, self.histories)
        url = reverse("fibercable-traffic-history", args=[cable.pk])
        with patch("integrations.zabbix.zabbix_service.zabbix_request", side_effect=fake):
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(calls, {"111": 0, "222": 3, "333": 0, "444": 3})
        payload = response.json()
        self.assertEqual(payload["origin"]["history"][0]["traffic_in"], 1000.5)
        self.assertEqual(payload["destination"]["statistics"]["unit_in"], "Bps")
        self.assertEqual(len(payload["destination"]["history"]), 2)

    def test_port_traffic_history_aligns_in_and_out_by_bucket(self):
        """EV-0010: IN aos +7 s e OUT aos +43 s caem na mesma linha; 0 bps é valor."""
        histories = {
            "111": [{"clock": "1690000027", "value": "0"}, {"clock": "1690000147", "value": "900"}],
            "222": [{"clock": "1690000063", "value": "50"}],
        }
        fake, _ = _fake_zabbix(self.meta, histories)
        url = reverse("port-traffic-history", args=[self.port_a.pk])
        with patch("integrations.zabbix.zabbix_service.zabbix_request", side_effect=fake):
            payload = self.client.get(url, {"hours": 24}).json()
        rows = payload["history"]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["traffic_in"], 0.0)
        self.assertEqual(rows[0]["traffic_out"], 50.0)
        self.assertEqual(rows[1]["traffic_in"], 900.0)
        self.assertIsNone(rows[1]["traffic_out"])  # buraco real, não forward-fill
        self.assertEqual(rows[0]["timestamp"], "2023-07-22T04:27:00+00:00")  # início do bucket de 60 s

    def test_cable_traffic_history_unknown_cable_is_404_not_500(self):
        url = reverse("fibercable-traffic-history", args=[999999])
        with patch("integrations.zabbix.zabbix_service.zabbix_request", return_value=[]):
            response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class MergeSeriesTests(TestCase):
    """EV-0010 — alinhamento por bucket com `None` real nos buracos."""

    def test_samples_in_different_seconds_land_in_the_same_bucket(self):
        # 1_000_000_020 é início de bucket (múltiplo de 60); RX aos +7 s, TX aos +43 s.
        rows = zabbix_history.merge_series(
            {"rx": [(1_000_000_027, -21.0)], "tx": [(1_000_000_063, -3.0)]},
            bucket_seconds=60,
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["rx"], -21.0)
        self.assertEqual(rows[0]["tx"], -3.0)
        self.assertEqual(rows[0]["timestamp"], "2001-09-09T01:47:00+00:00")

    def test_gap_is_none_not_previous_value(self):
        rows = zabbix_history.merge_series(
            {"in": [(0, 100.0), (120, 300.0)], "out": [(0, 50.0), (60, 70.0), (120, 90.0)]},
            bucket_seconds=60,
        )
        self.assertEqual([r["in"] for r in rows], [100.0, None, 300.0])
        self.assertEqual([r["out"] for r in rows], [50.0, 70.0, 90.0])

    def test_zero_is_a_value(self):
        rows = zabbix_history.merge_series({"in": [(0, 0.0)]}, bucket_seconds=60)
        self.assertEqual(rows[0]["in"], 0.0)

    def test_bucket_averages_multiple_samples(self):
        rows = zabbix_history.merge_series(
            {"in": [(0, 10.0), (20, 20.0), (40, 30.0)]}, bucket_seconds=60
        )
        self.assertEqual(rows[0]["in"], 20.0)

    def test_choose_bucket_keeps_point_count_bounded(self):
        self.assertEqual(zabbix_history.choose_bucket_seconds(24 * 3600), 60)
        self.assertEqual(zabbix_history.choose_bucket_seconds(7 * 24 * 3600), 600)
        self.assertEqual(zabbix_history.choose_bucket_seconds(30 * 24 * 3600, max_points=100), 7200 * 4)

    def test_history_to_samples_skips_garbage(self):
        samples = zabbix_history.history_to_samples(
            [{"clock": "10", "value": "1.5"}, {"clock": "x"}, {"value": "2"}, {"clock": "20", "value": None}]
        )
        self.assertEqual(samples, [(10, 1.5)])
