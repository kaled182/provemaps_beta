from unittest.mock import patch

from django.test import TestCase

from inventory.models import Device, Site
from inventory.usecases import devices as device_uc


class DeviceSyncFlagsTest(TestCase):
    def setUp(self) -> None:
        self.site = Site.objects.create(display_name="CDT")
        self.device = Device.objects.create(
            name="Huawei - Switch CDT",
            primary_ip="10.1.0.6",
            zabbix_hostid="10667",
            site=self.site,
        )

    def test_sync_does_not_move_site_when_update_site_disabled(self):
        """Garantir que update_site=False não cria/muda o site."""

        def fake_zabbix_request(method: str, params):
            if method == "host.get":
                return [
                    {
                        "hostid": "10667",
                        "name": "Huawei - Switch CDT",
                        "host": "huawei-switch-cdt",
                        "interfaces": [
                            {"ip": "10.1.0.6", "type": "1", "dns": "", "port": "161"}
                        ],
                        "inventory": {
                            # Valor que criaria/mudaria site se update_site estivesse true
                            "location": "SITE QUE NAO DEVE SER CRIADO",
                            "site_location": "SITE QUE NAO DEVE SER CRIADO",
                        },
                    }
                ]
            if method == "item.get":
                # Sem itens relevantes para não alterar keys
                return []
            return []

        with patch.object(device_uc, "ZABBIX_REQUEST", side_effect=fake_zabbix_request), patch.object(
            device_uc, "sync_device_groups_for_device", return_value=None
        ), patch("inventory.services.import_rules.apply_import_rules", return_value=None):
            payload = device_uc.add_device_from_zabbix(
                {
                    "hostid": "10667",
                    "update_site": False,
                    "import_interfaces": False,
                    "sync_groups": False,
                    "apply_auto_rules": False,
                }
            )

        self.device.refresh_from_db()

        # Site deve permanecer o original
        self.assertEqual(self.device.site_id, self.site.id)
        self.assertEqual(Site.objects.count(), 1, "Não deve criar site novo")

        # Payload de retorno também não deve apontar para site novo
        self.assertEqual(payload["device"]["site"], self.site.display_name)
