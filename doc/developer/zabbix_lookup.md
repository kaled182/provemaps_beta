# Zabbix Lookup Page

## Overview

The lookup page (`/zabbix/lookup/`) now consumes the inventory API directly via `inventory/api/zabbix_lookup.py`. Key endpoints:

- `GET /api/v1/inventory/zabbix/lookup/host-groups/` – lists host groups ordered by name. The optional `exclude_empty=1` flag filters out groups without hosts and includes a `host_count` field for UI badges.
- `GET /api/v1/inventory/zabbix/lookup/hosts/` – fetches hosts for the selected group (or search term) and returns normalized availability metadata so the UI can render status pills.
- `POST /api/v1/inventory/devices/add-from-zabbix/` – imports the selected host into the inventory and synchronizes its ports.

## UI Notes

- The group input is now a dropdown that auto loads values via the `/api/v1/inventory/zabbix/lookup/host-groups/` endpoint and automatically triggers a search when a group is selected.
- Availability badges derive their label from the returned availability value (`1` = Online, `2` = Offline, otherwise Unknown) so missing labels from Zabbix no longer break the color coding.
- Failed import attempts now surface the backend error detail, which helps operators understand why a device could not be added.

## Import Requirements

Device import (`add_device_from_zabbix`) now validates the Zabbix inventory payload up front:

- `hostid` remains mandatory. If the host is not found, a 404 is returned.
- Host inventory **must be enabled** in Zabbix. The API expects a dictionary in the host `inventory` field (either directly or via `selectInventory`).
- When the inventory feature is disabled or empty, the API returns HTTP 400 with the message:
  `"Host inventory data is missing in Zabbix. Enable host inventory and populate the fields before importing."`

Recommended operator steps before importing a device:

1. Enable *Host inventory* for the host inside Zabbix (Configuration → Hosts → host → Inventory tab).
2. Populate key location fields such as *Site address*, *Location*, and optional latitude/longitude.
3. Retry the import from `/zabbix/lookup/`.

These checks prevent internal exceptions caused by Zabbix returning an empty list for the inventory payload and provide actionable guidance to the user.
