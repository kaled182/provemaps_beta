"""EV-0081 — comando `corrigir_chaves_opticas` e usecase `optical_keys` (Zabbix mockado)."""

from __future__ import annotations

import json
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.core.management import CommandError, call_command
from django.test import TestCase

from inventory.models import Device, Port, Site
from inventory.usecases import devices_common, optical_keys

ZTE_NAME = "ZTE - OLT BRV C300"
IFINDEX_9_1 = 0x10090100  # 269025536 → slot 9, PON 1
IFINDEX_9_13 = 0x10090D00  # 269028608 → slot 9, PON 13


def _onu_item(serial, slot, pon, onu, value="-23.5", lost=False, status="0"):
    return {
        "itemid": f"{slot}{pon}{onu}{serial}",
        "key_": f"onu.rx[{serial},{slot},{pon},{onu}]",
        "status": status,
        "lastvalue": value,
        "units": "dBm",
        "itemDiscovery": {
            "status": "1" if lost else "0",
            "ts_delete": "1796911277" if lost else "0",
        },
    }


class FakeZabbix:
    """Responde a host.get / item.get como o Zabbix de produção descrito no relatório."""

    def __init__(self, *, new_host_name=ZTE_NAME, new_host_exists=True, old_host_exists=False):
        self.new_host_name = new_host_name
        self.new_host_exists = new_host_exists
        self.old_host_exists = old_host_exists
        self.onu_items = [
            _onu_item("GPON00A87658", 9, 1, 1, "-23.24"),
            # 9/13/2: ONU trocada — o item antigo ficou «perdido» no LLD; só o ativo conta.
            _onu_item("SHLN3C4D936E", 9, 13, 2, "-25.14", lost=True),
            _onu_item("SHLN3C3C2609", 9, 13, 2, "-25.14"),
        ]
        self.huawei_items = [
            {
                "hostid": "10675",
                "key_": "hwEntityOpticalLaneTxPower[67469646]",
                "lastvalue": "32.2471",
                "lastclock": "1795476812",
                "state": "0",
            },
            {
                "hostid": "10675",
                "key_": "hwEntityOpticalLaneRxPower[67469646]",
                "lastvalue": "0",
                "lastclock": "0",
                "state": "1",
            },
            {
                "hostid": "10675",
                "key_": "hwEntityOpticalLaneTxPower[1]",
                "lastvalue": "-2.1",
                "lastclock": "1795476812",
                "state": "0",
            },
            {
                "hostid": "10675",
                "key_": "hwEntityOpticalLaneRxPower[1]",
                "lastvalue": "-5.3",
                "lastclock": "1795476812",
                "state": "0",
            },
        ]
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, method, params):
        self.calls.append((method, params))
        if method == "host.get":
            hosts = []
            if self.old_host_exists:
                hosts.append({"hostid": "10694", "host": ZTE_NAME, "name": ZTE_NAME})
            if self.new_host_exists:
                hosts.append(
                    {"hostid": "10744", "host": self.new_host_name, "name": self.new_host_name}
                )
            return hosts
        if method == "item.get" and params.get("search", {}).get("key_") == "onu.rx[":
            assert params["hostids"] == ["10744"]
            return list(self.onu_items)
        if method == "item.get" and "filter" in params:
            keys = set(params["filter"]["key_"])
            return [i for i in self.huawei_items if i["key_"] in keys]
        raise AssertionError(f"chamada inesperada {method} {params}")


class CorrigirChavesOpticasTest(TestCase):
    def setUp(self) -> None:
        site = Site.objects.create(display_name="BRV")
        # Sem `id=22` explícito: as sequências do Postgres não recuam no rollback entre testes
        # e, ao fim de uns dez testes, o próximo Device da sequência colidia com o 22. O
        # usecase procura o ZTE por `ZTE_DEVICE_ID`; aqui aponta-se para o pk real.
        self.zte = Device.objects.create(name=ZTE_NAME, zabbix_hostid="10694", site=site)
        patcher = patch.object(optical_keys, "ZTE_DEVICE_ID", self.zte.pk)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.vsol = Device.objects.create(
            name="VSOL - OLT EPON GRANADA", zabbix_hostid="10702", site=site
        )
        self.huawei = Device.objects.create(
            name="Huawei - Switch Faz. Cristo Rei", zabbix_hostid="10675", site=site
        )
        mk = Port.objects.create
        self.onu_ok = mk(
            device=self.zte,
            name=f"{IFINDEX_9_1}.1",
            rx_power_item_key=f"zxoltrxsignal.[{IFINDEX_9_1}.1]",
            tx_power_item_key=f"zxolttxsignal.[{IFINDEX_9_1}.1]",
        )
        self.onu_lost_dup = mk(
            device=self.zte,
            name=f"{IFINDEX_9_13}.2",
            rx_power_item_key=f"zxoltrxsignal.[{IFINDEX_9_13}.2]",
            tx_power_item_key=f"zxolttxsignal.[{IFINDEX_9_13}.2]",
        )
        self.onu_sem_item = mk(
            device=self.zte,
            name=f"{IFINDEX_9_1}.12",
            rx_power_item_key=f"zxoltrxsignal.[{IFINDEX_9_1}.12]",
            tx_power_item_key=f"zxolttxsignal.[{IFINDEX_9_1}.12]",
        )
        self.cartao = mk(
            device=self.zte,
            name="9",
            zabbix_item_key="Card[9]",
            rx_power_item_key=f"zxoltrxsignal.[{IFINDEX_9_1}.1]",
            tx_power_item_key=f"zxolttxsignal.[{IFINDEX_9_1}.1]",
        )
        self.trafego = mk(
            device=self.zte,
            name="ifHCInOctets.285280769",
            rx_power_item_key="net.if.in[ifHCInOctets.285280769]",
            tx_power_item_key="",
        )
        self.fonte = mk(
            device=self.zte,
            name="power0",
            rx_power_item_key="olt[power0]",
            tx_power_item_key="olt[power0]",
        )
        self.zte_intocada = mk(device=self.zte, name="gpon_1/9/1", zabbix_item_key="x")
        self.vsol_macro = mk(
            device=self.vsol,
            name="GPON0/1:6",
            rx_power_item_key="SinalRXS0P1[{#USERNAME} - 4]",
            tx_power_item_key="SinalRXS0P1[GPON0/1:6 - 6]",
        )
        self.vsol_igual = mk(
            device=self.vsol,
            name="GPON0/1:2",
            rx_power_item_key="SinalRXS0P1[GPON0/1:2 - 2]",
            tx_power_item_key="SinalRXS0P1[GPON0/1:2 - 2]",
        )
        self.huawei_sem_ddm = mk(
            device=self.huawei,
            name="XGigabitEthernet0/0/5",
            rx_power_item_key="hwEntityOpticalLaneRxPower[67469646]",
            tx_power_item_key="hwEntityOpticalLaneTxPower[67469646]",
        )
        self.huawei_ok = mk(
            device=self.huawei,
            name="XGigabitEthernet0/0/1",
            rx_power_item_key="hwEntityOpticalLaneRxPower[1]",
            tx_power_item_key="hwEntityOpticalLaneTxPower[1]",
        )
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.backup_dir = Path(self.tmp.name)

    # -- auxiliares ---------------------------------------------------------------------------
    def _snapshot(self):
        ports = {
            p.id: (p.rx_power_item_key, p.tx_power_item_key) for p in Port.objects.order_by("id")
        }
        return Device.objects.get(pk=self.zte.pk).zabbix_hostid, ports

    def _run(self, fake, *args):
        out = StringIO()
        with (
            patch.object(devices_common, "ZABBIX_REQUEST", side_effect=fake),
            patch.object(optical_keys, "invalidate_fiber_cache") as inv_fiber,
            patch.object(optical_keys, "invalidate_dashboard_cache") as inv_dash,
        ):
            call_command(
                "corrigir_chaves_opticas", *args, "--backup-dir", str(self.backup_dir), stdout=out
            )
        return out.getvalue(), inv_fiber, inv_dash

    def _keys(self, port):
        port.refresh_from_db()
        return port.rx_power_item_key, port.tx_power_item_key

    # -- testes --------------------------------------------------------------------------------
    def test_ensaio_nao_escreve(self):
        before = self._snapshot()
        out, inv_fiber, inv_dash = self._run(FakeZabbix())
        self.assertEqual(self._snapshot(), before)
        self.assertEqual(list(self.backup_dir.iterdir()), [])
        inv_fiber.assert_not_called()
        inv_dash.assert_not_called()
        self.assertIn("ENSAIO", out)
        self.assertIn("'10694' → '10744'", out)
        self.assertIn("onu.rx[GPON00A87658,9,1,1]", out)

    def test_aplicar_escreve_grava_backup_e_invalida_caches(self):
        out, inv_fiber, inv_dash = self._run(FakeZabbix(), "--aplicar")

        self.assertEqual(Device.objects.get(pk=self.zte.pk).zabbix_hostid, "10744")
        self.assertEqual(self._keys(self.onu_ok), ("onu.rx[GPON00A87658,9,1,1]", ""))
        # Item LLD perdido ignorado: fica o da ONU atual.
        self.assertEqual(self._keys(self.onu_lost_dup), ("onu.rx[SHLN3C3C2609,9,13,2]", ""))
        for port in (self.onu_sem_item, self.cartao, self.trafego, self.fonte):
            self.assertEqual(self._keys(port), ("", ""), port.name)
        self.assertEqual(self._keys(self.zte_intocada), ("", ""))
        self.assertEqual(self._keys(self.vsol_macro), ("", ""))
        self.assertEqual(self._keys(self.vsol_igual), ("SinalRXS0P1[GPON0/1:2 - 2]", ""))
        self.assertEqual(self._keys(self.huawei_sem_ddm), ("", ""))
        self.assertEqual(
            self._keys(self.huawei_ok),
            ("hwEntityOpticalLaneRxPower[1]", "hwEntityOpticalLaneTxPower[1]"),
        )

        inv_fiber.assert_called_once()
        inv_dash.assert_called_once()

        files = list(self.backup_dir.glob("ev0081-chaves-opticas-*.json"))
        self.assertEqual(len(files), 1)
        self.assertIn(str(files[0]), out)
        backup = json.loads(files[0].read_text(encoding="utf-8"))
        self.assertEqual(backup["devices"], [{"id": self.zte.pk, "zabbix_hostid": "10694"}])
        by_id = {p["id"]: p for p in backup["ports"]}
        self.assertEqual(len(by_id), 9)
        self.assertEqual(
            by_id[self.onu_ok.id]["rx_power_item_key"], f"zxoltrxsignal.[{IFINDEX_9_1}.1]"
        )
        self.assertNotIn(self.huawei_ok.id, by_id)
        self.assertNotIn(self.zte_intocada.id, by_id)

    def test_idempotente(self):
        self._run(FakeZabbix(), "--aplicar")
        after_first = self._snapshot()
        out, inv_fiber, _ = self._run(FakeZabbix(), "--aplicar")
        self.assertEqual(self._snapshot(), after_first)
        self.assertEqual(len(list(self.backup_dir.iterdir())), 1)
        inv_fiber.assert_not_called()
        self.assertIn("Nada a mudar", out)
        self.assertIn("portas a mudar: 0", out)

    def test_porta_sem_correspondencia_unica_nao_muda(self):
        fake = FakeZabbix()
        # Dois itens ATIVOS na mesma posição 9/1/1: não se adivinha.
        fake.onu_items.append(_onu_item("OUTRA0000001", 9, 1, 1, "-20"))
        self._run(fake, "--aplicar")
        self.assertEqual(
            self._keys(self.onu_ok),
            (f"zxoltrxsignal.[{IFINDEX_9_1}.1]", f"zxolttxsignal.[{IFINDEX_9_1}.1]"),
        )
        # As outras regras continuam a aplicar.
        self.assertEqual(self._keys(self.onu_lost_dup), ("onu.rx[SHLN3C3C2609,9,13,2]", ""))

    def test_sem_correspondencia_listada_no_ensaio(self):
        fake = FakeZabbix()
        fake.onu_items.append(_onu_item("OUTRA0000001", 9, 1, 1, "-20"))
        with patch.object(devices_common, "ZABBIX_REQUEST", side_effect=fake):
            plan = optical_keys.build_optical_key_plan()
        self.assertEqual([u["port_id"] for u in plan["unmatched"]], [self.onu_ok.id])
        self.assertNotIn(self.onu_ok.id, [c["port_id"] for c in plan["ports"]])

    def test_so_item_perdido_na_posicao_nao_muda(self):
        fake = FakeZabbix()
        fake.onu_items = [i for i in fake.onu_items if i["key_"] != "onu.rx[SHLN3C3C2609,9,13,2]"]
        self._run(fake, "--aplicar")
        self.assertEqual(
            self._keys(self.onu_lost_dup),
            (f"zxoltrxsignal.[{IFINDEX_9_13}.2]", f"zxolttxsignal.[{IFINDEX_9_13}.2]"),
        )

    def test_device_nao_muda_se_host_novo_tem_outro_nome(self):
        self._run(FakeZabbix(new_host_name="ZTE - OLT OUTRA"), "--aplicar")
        self.assertEqual(Device.objects.get(pk=self.zte.pk).zabbix_hostid, "10694")
        # Sem host confirmado, as portas ZTE também não mudam.
        self.assertEqual(
            self._keys(self.onu_ok),
            (f"zxoltrxsignal.[{IFINDEX_9_1}.1]", f"zxolttxsignal.[{IFINDEX_9_1}.1]"),
        )
        self.assertEqual(self._keys(self.fonte), ("olt[power0]", "olt[power0]"))
        # As regras VSOL/Huawei não dependem do host do ZTE.
        self.assertEqual(self._keys(self.vsol_macro), ("", ""))

    def test_device_nao_muda_se_host_novo_nao_existe(self):
        self._run(FakeZabbix(new_host_exists=False), "--aplicar")
        self.assertEqual(Device.objects.get(pk=self.zte.pk).zabbix_hostid, "10694")
        self.assertEqual(self._keys(self.cartao)[0], f"zxoltrxsignal.[{IFINDEX_9_1}.1]")

    def test_device_nao_muda_se_host_antigo_ainda_existe(self):
        self._run(FakeZabbix(old_host_exists=True), "--aplicar")
        self.assertEqual(Device.objects.get(pk=self.zte.pk).zabbix_hostid, "10694")

    def test_falha_do_zabbix_impede_aplicar(self):
        def broken(method, params):
            raise RuntimeError("Zabbix fora")

        before = self._snapshot()
        with self.assertRaises(CommandError):
            self._run(broken, "--aplicar")
        self.assertEqual(self._snapshot(), before)
        self.assertEqual(list(self.backup_dir.iterdir()), [])

    def test_decode_zte_old_ifindex(self):
        self.assertEqual(optical_keys.decode_zte_old_ifindex(269025536), (9, 1))
        self.assertEqual(optical_keys.decode_zte_old_ifindex(269028608), (9, 13))
        self.assertIsNone(optical_keys.decode_zte_old_ifindex(285280769))  # 0x1101SSPP
