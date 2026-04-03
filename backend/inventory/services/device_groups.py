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
    
    Note:
        Uses reverse lookup (searching hosts by group) as a workaround 
        because selectGroups parameter in host.get doesn't return groups 
        in some Zabbix versions/configurations.
    """
    if not device.zabbix_hostid:
        logger.debug(f"Device {device.name} has no zabbix_hostid, skipping group sync")
        return False

    try:
        # Workaround: Instead of using selectGroups (which doesn't work),
        # we fetch all groups and check which ones contain this host
        all_groups = zabbix_request(
            "hostgroup.get",
            {
                "output": ["groupid", "name"],
            },
        )

        if not all_groups:
            logger.warning("No groups found in Zabbix")
            device.groups.clear()
            return True

        device_group_ids = []
        
        # For each group, check if our device is in it
        for group_data in all_groups:
            group_id = group_data.get("groupid")
            if not group_id:
                continue
            
            # Check if this device is in this group
            hosts_in_group = zabbix_request(
                "host.get",
                {
                    "output": ["hostid"],
                    "groupids": [group_id],
                    "hostids": [device.zabbix_hostid],
                },
            )
            
            # If the device is in this group, add it to our list
            if hosts_in_group:
                device_group_ids.append({
                    "groupid": group_id,
                    "name": group_data.get("name")
                })

        if not device_group_ids:
            logger.debug(f"No groups found for device {device.name}")
            device.groups.clear()
            return True

        zabbix_group_ids = [g["groupid"] for g in device_group_ids]

        # Ensure all groups exist in our database
        existing_groups = DeviceGroup.objects.filter(
            zabbix_groupid__in=zabbix_group_ids
        )
        existing_group_ids = set(existing_groups.values_list('zabbix_groupid', flat=True))
        
        # Create missing groups
        missing_groups = [g for g in device_group_ids if g["groupid"] not in existing_group_ids]
        if missing_groups:
            with transaction.atomic():
                for group_data in missing_groups:
                    groupid = group_data["groupid"]
                    name = group_data["name"]
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
    
    Uses optimized reverse lookup: fetches hosts by group instead of groups by host.
    This is much more efficient than individual sync and works around 
    the selectGroups parameter not working in some Zabbix versions.
    
    Returns:
        dict with 'synced' and 'failed' counts
    """
    logger.info("Starting optimized group sync for all devices...")
    
    try:
        # Fetch all groups from Zabbix
        all_groups = zabbix_request(
            "hostgroup.get",
            {
                "output": ["groupid", "name"],
            },
        )

        if not all_groups:
            logger.warning("No groups found in Zabbix")
            return {"synced": 0, "failed": 0}

        synced_count = 0
        devices_updated = set()

        # For each group, fetch all hosts in it
        for group_data in all_groups:
            group_id = group_data.get("groupid")
            group_name = group_data.get("name")

            if not group_id:
                continue

            # Get or create the DeviceGroup
            device_group, created = DeviceGroup.objects.get_or_create(
                zabbix_groupid=group_id,
                defaults={"name": group_name}
            )

            if created:
                logger.info(f"Auto-created group: {group_name} ({group_id})")

            # Fetch all hosts in this group
            hosts = zabbix_request(
                "host.get",
                {
                    "output": ["hostid", "name"],
                    "groupids": [group_id],
                },
            )

            if not hosts:
                continue

            # Associate each host with this group
            for host in hosts:
                host_id = host.get("hostid")
                
                try:
                    # Find device in our database
                    device = Device.objects.get(zabbix_hostid=host_id)
                    
                    # Add to group if not already there
                    if not device.groups.filter(id=device_group.id).exists():
                        device.groups.add(device_group)
                        devices_updated.add(device.id)
                        logger.debug(f"Associated {device.name} with {group_name}")
                    
                    synced_count += 1
                    
                except Device.DoesNotExist:
                    # Device not in our database yet
                    continue

        logger.info(
            f"Synced device groups: {len(devices_updated)} devices updated, "
            f"{synced_count} associations processed"
        )
        
        return {"synced": synced_count, "failed": 0}

    except Exception as e:
        logger.exception(f"Error syncing all device groups: {e}")
        return {"synced": 0, "failed": 1}
