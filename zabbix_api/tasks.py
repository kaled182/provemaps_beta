from celery import shared_task

from inventory.models import Port
from .domain.optical import _fetch_port_optical_snapshot


@shared_task(queue="mapspro_default")
def warm_port_optical_cache(port_id: int):
    port = (
        Port.objects.select_related("device")
        .only("id", "device_id", "device__zabbix_hostid", "rx_power_item_key", "tx_power_item_key")
        .filter(id=port_id)
        .first()
    )
    if not port:
        return
    _fetch_port_optical_snapshot(port, discovery_cache={}, persist_keys=False)


@shared_task(queue="mapspro_default")
def warm_device_ports(device_id: int):
    ports = (
        Port.objects.select_related("device")
        .only("id", "device_id", "device__zabbix_hostid", "rx_power_item_key", "tx_power_item_key")
        .filter(device_id=device_id)
    )
    for port in ports:
        _fetch_port_optical_snapshot(port, discovery_cache={}, persist_keys=False)


@shared_task(queue="mapspro_default")
def warm_all_optical_snapshots():
    device_port_ids = list(
        Port.objects.values_list("id", flat=True)
    )
    for port_id in device_port_ids:
        warm_port_optical_cache.delay(port_id)
