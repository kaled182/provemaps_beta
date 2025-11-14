"""
Service layer for device group operations.
"""
import logging

from django.db import transaction

from integrations.zabbix.zabbix_service import zabbix_request
from inventory.models import Device, DeviceGroup

logger = logging.getLogger(__name__)


def import_device_groups_from_zabbix() -> dict[str, int]:
    """
    Import all device groups from Zabbix.
    
    Returns:
        dict with 'created' and 'updated' counts
    """
    try:
        groups = zabbix_request(
            "hostgroup.get",
            {
                "output": ["groupid", "name"],
            },
        )

        if not groups:
            logger.warning("No groups found in Zabbix")
            return {"created": 0, "updated": 0}

        created_count = 0
        updated_count = 0

        with transaction.atomic():
            for group_data in groups:
                groupid = group_data.get("groupid")
                name = group_data.get("name")

                if not groupid or not name:
                    continue

                group, created = DeviceGroup.objects.update_or_create(
                    zabbix_groupid=groupid,
                    defaults={"name": name},
                )

                if created:
                    created_count += 1
                    logger.info(f"Created device group: {name} ({groupid})")
                else:
                    updated_count += 1
                    logger.debug(f"Updated device group: {name} ({groupid})")

        logger.info(
            f"Imported device groups: {created_count} created, {updated_count} updated"
        )
        return {"created": created_count, "updated": updated_count}

    except Exception as e:
        logger.exception(f"Error importing device groups from Zabbix: {e}")
        raise


def sync_device_groups_for_device(device: Device) -> bool:
    """
    Sync group relationships for a specific device from Zabbix.
    
    Args:
        device: Device instance with zabbix_hostid
        
    Returns:
        bool indicating if sync was successful
    """
    if not device.zabbix_hostid:
        logger.debug(f"Device {device.name} has no zabbix_hostid, skipping group sync")
        return False

    try:
        # Fetch host with groups from Zabbix
        hosts = zabbix_request(
            "host.get",
            {
                "output": ["hostid"],
                "hostids": [device.zabbix_hostid],
                "selectGroups": ["groupid", "name"],
            },
        )

        if not hosts:
            logger.warning(f"Device {device.name} not found in Zabbix")
            return False

        host_data = hosts[0]
        zabbix_groups = host_data.get("groups", [])
        
        if not zabbix_groups:
            logger.debug(f"No groups found for device {device.name}")
            device.groups.clear()
            return True

        zabbix_group_ids = [
            g.get("groupid") for g in zabbix_groups
            if g.get("groupid")
        ]

        if not zabbix_group_ids:
            device.groups.clear()
            return True

        # Ensure all groups exist in our database
        # Import any missing groups first
        missing_group_ids = []
        existing_groups = DeviceGroup.objects.filter(
            zabbix_groupid__in=zabbix_group_ids
        )
        existing_group_ids = set(existing_groups.values_list('zabbix_groupid', flat=True))
        
        for group_data in zabbix_groups:
            groupid = group_data.get("groupid")
            if groupid and groupid not in existing_group_ids:
                missing_group_ids.append(group_data)

        # Create missing groups
        if missing_group_ids:
            with transaction.atomic():
                for group_data in missing_group_ids:
                    groupid = group_data.get("groupid")
                    name = group_data.get("name")
                    if groupid and name:
                        DeviceGroup.objects.get_or_create(
                            zabbix_groupid=groupid,
                            defaults={"name": name}
                        )
                        logger.info(f"Auto-created missing group: {name} ({groupid})")

        # Now get all device groups for this device
        device_groups = DeviceGroup.objects.filter(
            zabbix_groupid__in=zabbix_group_ids
        )

        # Sync the relationship
        device.groups.set(device_groups)
        
        group_names = ", ".join([g.name for g in device_groups])
        logger.info(f"Synced groups for device {device.name}: {group_names}")
        
        return True

    except Exception as e:
        logger.exception(f"Error syncing groups for device {device.name}: {e}")
        return False


def sync_all_device_groups() -> dict[str, int]:
    """
    Sync group relationships for all devices with zabbix_hostid.
    
    Returns:
        dict with 'synced' and 'failed' counts
    """
    devices_with_zabbix = Device.objects.exclude(zabbix_hostid="")
    synced_count = 0
    failed_count = 0

    for device in devices_with_zabbix:
        if sync_device_groups_for_device(device):
            synced_count += 1
        else:
            failed_count += 1

    logger.info(
        f"Synced device groups: {synced_count} successful, {failed_count} failed"
    )
    return {"synced": synced_count, "failed": failed_count}
