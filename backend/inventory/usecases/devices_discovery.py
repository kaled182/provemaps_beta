# ruff: noqa: E501
"""Descoberta e criação de dispositivos a partir do Zabbix; listagens de dispositivos e sites.

Saiu de `inventory/usecases/devices.py` em EV-0017f. O scoring e a descoberta de portas vivem em
`devices_ports.py`; aqui fica o fluxo «host do Zabbix → Device/Site/Port no inventário».
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from decimal import Decimal, InvalidOperation
from typing import Any, cast

from django.db.models import Prefetch
from django.utils.text import slugify

from inventory.domain.optical import fetch_ports_optical_snapshots
from inventory.models import Device, FiberCable, Port, Site
from inventory.services.device_groups import sync_device_groups_for_device
from setup_app.models import MessagingGateway

from . import devices_common as common
from .devices_common import (
    DeviceLike,
    HostItemList,
    InventoryNotFound,
    InventoryValidationError,
    PortLike,
    PortRecord,
    SiteLike,
    _apply_port_updates,
    _coerce_dict_list,
    _coerce_host_items,
    _extract_key_tokens,
    _identify_item_role,
    _normalize_identifier,
    _port_map_key,
    _PortEntry,
    _resolve_host_inventory,
)
from .devices_ports import _preload_optical_discovery_cache, _score_port_match

logger = logging.getLogger(__name__)


def add_device_from_zabbix(payload: Mapping[str, Any]) -> dict[str, Any]:
    hostid = payload.get("hostid") or payload.get("device_name")
    if not hostid:
        raise InventoryValidationError("hostid is required")

    update_identity = bool(payload.get("update_identity", True))
    apply_auto_rules = bool(payload.get("apply_auto_rules", True))
    sync_groups = bool(payload.get("sync_groups", True))
    update_site = bool(payload.get("update_site", True))
    import_interfaces = bool(payload.get("import_interfaces", True))

    logger.info(
        "[ZBX_SYNC_FLAGS] hostid=%s update_identity=%s apply_auto_rules=%s sync_groups=%s update_site=%s import_interfaces=%s",
        hostid,
        update_identity,
        apply_auto_rules,
        sync_groups,
        update_site,
        import_interfaces,
    )

    zabbix_data = common.ZABBIX_REQUEST(
        "host.get",
        {
            "output": ["hostid", "name", "host"],
            "hostids": hostid,
            "selectInterfaces": ["interfaceid", "ip", "dns", "port", "type"],
            "selectInventory": "extend",
        },
    )
    if not zabbix_data:
        raise InventoryNotFound("Host not found in Zabbix")

    host = zabbix_data[0]
    inventory = _resolve_host_inventory(host)

    def _clean(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        return str(value).strip()

    def _to_decimal(value: str) -> Decimal | None:
        if not value:
            return None
        try:
            return Decimal(value)
        except (InvalidOperation, ValueError):
            return None

    site_display_name = (
        _clean(inventory.get("location"))
        or _clean(inventory.get("site_location"))
        or _clean(inventory.get("site_city"))
        or _clean(host.get("name"))
        or _clean(host.get("host"))
        or f"Zabbix Host {hostid}"
    )
    site_state = _clean(inventory.get("site_state"))
    site_country = _clean(inventory.get("site_country"))

    slug_source = "-".join(part for part in [site_display_name, site_state, site_country] if part)
    slug_candidate = slugify(slug_source) or slugify(site_display_name) or f"site-{hostid}"

    host_primary_name = _clean(host.get("host"))
    fallback_host_name = _clean(host.get("name"))
    desired_device_name = (
        host_primary_name or fallback_host_name or site_display_name or f"Zabbix Host {hostid}"
    )

    hostid_str = str(hostid)
    existing_device = Device.objects.select_related("site").filter(zabbix_hostid=hostid_str).first()
    original_site_id = existing_device.site_id if existing_device else None

    address_payload = {
        "display_name": site_display_name,
        "address_line1": _clean(inventory.get("site_address_a")),
        "address_line2": _clean(inventory.get("site_address_b")),
        "address_line3": _clean(inventory.get("site_address_c")),
        "city": _clean(inventory.get("site_city")),
        "state": site_state,
        "postal_code": _clean(inventory.get("site_zip")),
        "country": site_country,
        "rack_location": _clean(inventory.get("site_location")),
    }

    lat_decimal = _to_decimal(_clean(inventory.get("location_lat")))
    lon_decimal = _to_decimal(_clean(inventory.get("location_lon")))

    # Find existing site based on what Zabbix returns
    site = None
    logger.info(f"Searching for site: '{site_display_name}'")

    if not update_site:
        if existing_device:
            site = existing_device.site
            logger.info(
                "[ZBX_SYNC_FLAGS] update_site disabled; keeping existing site_id=%s for device %s",
                site.id if site else None,
                existing_device.id,
            )
        else:
            logger.info(
                "[ZBX_SYNC_FLAGS] update_site disabled and device does not exist; skipping site resolution"
            )
    else:
        # Strategy 1: Exact match (case-insensitive)
        site = Site.objects.filter(display_name__iexact=site_display_name).first()
        if site:
            logger.info(f"Found site by exact match: {site.display_name}")

        if site is None:
            # Strategy 2: Match by slug
            site = Site.objects.filter(slug=slug_candidate).first()
            if site:
                logger.info(f"Found site by slug '{slug_candidate}': {site.display_name}")

        if site is None:
            # Strategy 3: Normalize both sides and compare (remove accents)
            from unicodedata import normalize

            # Remove accents from search term
            normalized_search = (
                normalize("NFKD", site_display_name)
                .encode("ASCII", "ignore")
                .decode("ASCII")
                .strip()
                .lower()
            )
            logger.info(f"Trying normalized search: '{normalized_search}'")

            # Check all sites with normalized comparison
            for existing_site in Site.objects.all():
                normalized_existing = (
                    normalize("NFKD", existing_site.display_name)
                    .encode("ASCII", "ignore")
                    .decode("ASCII")
                    .strip()
                    .lower()
                )
                if normalized_existing == normalized_search:
                    site = existing_site
                    logger.info(f"Found site by normalized match: {site.display_name}")
                    break

        if site is None and existing_device and existing_device.site:
            # Strategy 4: Reuse existing device's site (update its display_name)
            # This handles cases where the site name changed in Zabbix
            site = existing_device.site
            logger.info(
                f"Reusing existing device's site (id={site.id}, old name='{site.display_name}')"
            )

            # Update site display_name to match Zabbix
            if site.display_name != site_display_name:
                logger.info(
                    f"Updating site display_name from '{site.display_name}' to '{site_display_name}'"
                )
                site.display_name = site_display_name
                site.slug = slug_candidate
                site.save(update_fields=["display_name", "slug"])

    site_created = False
    if site is None and update_site:
        logger.warning(f"Site '{site_display_name}' not found in database. Creating new site.")

        # Last resort: Use get_or_create to avoid duplicate key violations
        # This ensures thread-safety when multiple devices are added simultaneously
        site_defaults = {**address_payload}
        site_defaults["slug"] = slug_candidate
        if lat_decimal is not None:
            site_defaults["latitude"] = lat_decimal
        if lon_decimal is not None:
            site_defaults["longitude"] = lon_decimal

        try:
            site, site_created = Site.objects.get_or_create(
                display_name=site_display_name, defaults=site_defaults
            )
            if site_created:
                logger.info(f"Created new site: {site.display_name}")
            else:
                logger.info(f"Site already exists (race condition avoided): {site.display_name}")
        except Exception as e:
            # If still fails due to unique constraint, try to find it one more time
            logger.error(f"Failed to create site '{site_display_name}': {e}")

            # Try exact match again (another process might have created it)
            site = Site.objects.filter(display_name__iexact=site_display_name).first()

            if site is None:
                # Try normalized match as last resort
                from unicodedata import normalize

                normalized_search = (
                    normalize("NFKD", site_display_name)
                    .encode("ASCII", "ignore")
                    .decode("ASCII")
                    .strip()
                    .lower()
                )

                for existing_site in Site.objects.all():
                    normalized_existing = (
                        normalize("NFKD", existing_site.display_name)
                        .encode("ASCII", "ignore")
                        .decode("ASCII")
                        .strip()
                        .lower()
                    )
                    if normalized_existing == normalized_search:
                        site = existing_site
                        logger.info(
                            f"Found site after error by normalized match: {site.display_name}"
                        )
                        break

            if site is None:
                # Absolute last resort: use normalized name
                logger.error(
                    f"Could not find or create site '{site_display_name}'. Re-raising exception."
                )
                raise
    elif site is not None and update_site:
        logger.info(f"Using existing site: {site.display_name}")

        # Update site fields if needed (but NEVER update display_name or slug - these are immutable)
        update_fields: list[str] = []
        for field, value in address_payload.items():
            # Skip immutable fields
            if field in ("display_name", "slug"):
                continue
            if value and getattr(site, field) != value:
                setattr(site, field, value)
                update_fields.append(field)
        if lat_decimal is not None and site.latitude != lat_decimal:
            site.latitude = lat_decimal
            update_fields.append("latitude")
        if lon_decimal is not None and site.longitude != lon_decimal:
            site.longitude = lon_decimal
            update_fields.append("longitude")
        if update_fields:
            site.save(update_fields=update_fields)

    # Extrair IP primário das interfaces do Zabbix
    primary_ip = None
    interfaces = host.get("interfaces", [])
    if interfaces:
        # Preferir interface do tipo 1 (agent) ou 2 (SNMP), depois qualquer uma com IP
        for iface in interfaces:
            if iface.get("ip"):
                primary_ip = iface["ip"].strip()
                # Preferir interface do tipo 1 ou 2
                if iface.get("type") in ["1", "2", 1, 2]:
                    break

    # Buscar items do Zabbix primeiro para detectar uptime e CPU keys
    raw_host_items = common.ZABBIX_REQUEST(
        "item.get",
        {
            "output": ["itemid", "key_", "name", "interfaceid", "lastvalue", "units", "snmpindex"],
            "hostids": hostid,
            "filter": {"status": "0"},
            "limit": 2000,
        },
    )
    host_items: HostItemList = _coerce_host_items(raw_host_items)

    # Buscar item keys para uptime, CPU e Memory usage
    uptime_key = None
    cpu_key = None
    memory_key = None

    for item in host_items:
        key = item.get("key_") or ""
        key_lower = key.lower()
        name_lower = (item.get("name") or "").lower()

        # Identificar item key de uptime - aceita: sysUpTime, system.uptime
        # NÃO aceita: InterfaceUptime, ifLastChange, lastdowntime, etc
        if not uptime_key:
            # Verificar se é realmente uptime do SISTEMA (não interface, lastchange, etc)
            if "sysuptime" in key_lower:
                uptime_key = key
            elif "system.uptime" in key_lower:
                uptime_key = key
            elif "uptime" in key_lower:
                # Excluir falsos positivos: interface, lastchange, lastdown, iflast
                if not any(
                    exclude in key_lower
                    for exclude in ["interface", "lastchange", "lastdown", "iflast"]
                ):
                    uptime_key = key
            elif "uptime" in name_lower and "system" in name_lower:
                uptime_key = key

        # Identificar item key de CPU usage - aceita: hwCpuDevDuty, cpu.util, system.cpu, etc
        if not cpu_key:
            if any(
                pattern in key_lower
                for pattern in ["hwcpudevduty", "cpu.util", "cpu.usage", "system.cpu"]
            ):
                cpu_key = key
            elif "cpu" in key_lower and any(
                pattern in key_lower for pattern in ["duty", "load", "util", "usage"]
            ):
                cpu_key = key
            elif "cpu" in name_lower and any(
                pattern in name_lower for pattern in ["uso", "usage", "util", "duty", "utiliza"]
            ):
                cpu_key = key

        # Identificar item key de Memory usage - aceita: vm.memory.size[percent], mem.util, memory.usage
        if not memory_key:
            if any(
                pattern in key_lower
                for pattern in ["vm.memory", "mem.util", "memory.util", "memory.usage", "mem.usage"]
            ):
                memory_key = key
            elif "memory" in key_lower and any(
                pattern in key_lower for pattern in ["percent", "util", "usage", "used"]
            ):
                memory_key = key
            elif "mem" in key_lower and any(
                pattern in key_lower for pattern in ["percent", "util", "usage", "used"]
            ):
                memory_key = key

    device_created = False
    if existing_device:
        device = existing_device
        update_fields: list[str] = []
        # Auto-apply import rules for devices that existed before rules were created
        # Only if device still has default category and/or no monitoring group assigned
        if apply_auto_rules and (not device.monitoring_group_id or device.category == "backbone"):
            try:
                from inventory.services.import_rules import (
                    apply_import_rules,  # local import to avoid circulars
                )

                rule_result_existing = apply_import_rules(desired_device_name)
                if rule_result_existing:
                    # Update category if still default
                    if (
                        device.category == "backbone"
                        and rule_result_existing.get("category")
                        and rule_result_existing["category"] != device.category
                    ):
                        device.category = rule_result_existing["category"]
                        update_fields.append("category")
                    # Assign monitoring_group if missing and rule has group
                    if (not device.monitoring_group_id) and rule_result_existing.get("group_id"):
                        device.monitoring_group_id = rule_result_existing["group_id"]
                        update_fields.append("monitoring_group")
                    logger.info(
                        f"Applied import rule #{rule_result_existing.get('rule_id')} (existing device sync) to {desired_device_name}: "
                        f"category={rule_result_existing.get('category')}, group_id={rule_result_existing.get('group_id')}"
                    )
            except Exception as e:  # pragma: no cover - defensive
                logger.warning(
                    f"Failed applying import rules to existing device {desired_device_name}: {e}"
                )
        if update_site and device.site_id != getattr(site, "pk", None):
            device.site = site
            update_fields.append("site")
        if update_identity and desired_device_name and device.name != desired_device_name:
            device.name = desired_device_name
            update_fields.append("name")
        if not device.zabbix_hostid or str(device.zabbix_hostid) != hostid_str:
            device.zabbix_hostid = hostid_str
            update_fields.append("zabbix_hostid")
        # Atualizar IP se mudou
        if update_identity and primary_ip and device.primary_ip != primary_ip:
            device.primary_ip = primary_ip
            update_fields.append("primary_ip")
        # Atualizar uptime_item_key se mudou
        if update_identity and uptime_key and device.uptime_item_key != uptime_key:
            device.uptime_item_key = uptime_key
            update_fields.append("uptime_item_key")
        # Atualizar cpu_usage_item_key se mudou
        if update_identity and cpu_key and device.cpu_usage_item_key != cpu_key:
            device.cpu_usage_item_key = cpu_key
            update_fields.append("cpu_usage_item_key")
        # Atualizar memory_usage_item_key se mudou
        if (
            update_identity
            and memory_key
            and getattr(device, "memory_usage_item_key", "") != memory_key
        ):
            device.memory_usage_item_key = memory_key
            update_fields.append("memory_usage_item_key")
        if update_fields:
            device.save(update_fields=update_fields)
    else:
        # Apply import rules for auto-categorization
        from inventory.services.import_rules import apply_import_rules

        rule_result = apply_import_rules(desired_device_name) if apply_auto_rules else None

        device_defaults = {
            "vendor": "",
            "model": "",
            "zabbix_hostid": hostid_str,
            "primary_ip": primary_ip,
            "uptime_item_key": uptime_key or "",
            "cpu_usage_item_key": cpu_key or "",
            "memory_usage_item_key": memory_key or "",
        }

        # Apply rule if matched
        if rule_result:
            device_defaults["category"] = rule_result["category"]
            if rule_result["group_id"]:
                device_defaults["monitoring_group_id"] = rule_result["group_id"]
            logger.info(
                f"Applied import rule #{rule_result['rule_id']} "
                f"({rule_result['rule_description']}) to {desired_device_name}: "
                f"category={rule_result['category']}"
            )

        if not update_site and site is None:
            raise InventoryValidationError(
                "Site inexistente e update_site desativado; não é possível criar novo site automaticamente."
            )

        device, device_created = Device.objects.get_or_create(
            site=site,
            name=desired_device_name,
            defaults=device_defaults,
        )
        if not device_created and (
            not device.zabbix_hostid or str(device.zabbix_hostid) != hostid_str
        ):
            update_fields_list = ["zabbix_hostid"]
            device.zabbix_hostid = hostid_str
            if update_identity and primary_ip and device.primary_ip != primary_ip:
                device.primary_ip = primary_ip
                update_fields_list.append("primary_ip")
            if update_identity and uptime_key and device.uptime_item_key != uptime_key:
                device.uptime_item_key = uptime_key
                update_fields_list.append("uptime_item_key")
            if update_identity and cpu_key and device.cpu_usage_item_key != cpu_key:
                device.cpu_usage_item_key = cpu_key
                update_fields_list.append("cpu_usage_item_key")
            if (
                update_identity
                and memory_key
                and getattr(device, "memory_usage_item_key", "") != memory_key
            ):
                device.memory_usage_item_key = memory_key
                update_fields_list.append("memory_usage_item_key")
            device.save(update_fields=update_fields_list)

    # Sync device groups from Zabbix automatically
    if sync_groups:
        try:
            sync_device_groups_for_device(device)
            logger.info(f"Auto-synced device groups for {device.name}")
        except Exception as e:
            logger.warning(f"Failed to auto-sync device groups for {device.name}: {e}")

    port_records: list[PortRecord] = []
    primary_items: HostItemList = []
    legacy_primary_items: HostItemList = []

    for item in host_items:
        key = item.get("key_") or ""
        key_lower = key.lower()
        name_lower = (item.get("name") or "").lower()
        role = _identify_item_role(key_lower, name_lower)
        item["_role"] = role
        if role == "primary_oper":
            primary_items.append(item)
        elif role == "legacy_lastdown":
            legacy_primary_items.append(item)

    creation_candidates: HostItemList = primary_items if primary_items else legacy_primary_items
    if not creation_candidates:
        creation_candidates = [
            item
            for item in host_items
            if (item.get("key_") or "").lower().startswith(("ifoperstatus[", "lastdowntime["))
        ]

    port_record_map: dict[tuple[int, str], PortRecord] = {}

    if not import_interfaces:
        device_like = cast(DeviceLike, device)
        return {
            "created": {
                "sites": int(site_created),
                "devices": int(device_created),
                "ports": 0,
            },
            "device": {
                "id": device_like.id,
                "name": device_like.name,
                "site": getattr(device_like.site, "display_name", None),
                "zabbix_hostid": device_like.zabbix_hostid,
            },
            "ports_created": [],
            "ports_updated": [],
            "total_ports_detected": 0,
            "optical_snapshots": [],
        }

    for item in creation_candidates:
        key = item.get("key_") or ""
        tokens = _extract_key_tokens(key)
        if not tokens:
            continue
        port_name = tokens[0].strip()
        if not port_name:
            continue

        defaults = {
            "zabbix_item_key": key,
            "zabbix_interfaceid": str(item.get("interfaceid") or ""),
            "zabbix_itemid": str(item.get("itemid") or ""),
            "notes": item.get("name", ""),
        }

        port, port_created = Port.objects.get_or_create(
            device=device,
            name=port_name,
            defaults=defaults,
        )

        record = PortRecord(port=port, created=port_created, defaults=defaults)
        port_records.append(record)
        port_record_map[_port_map_key(port)] = record
        key = item.get("key_") or ""
        tokens = _extract_key_tokens(key)
        if not tokens:
            continue
        port_name = tokens[0].strip()
        if not port_name:
            continue

        defaults = {
            "zabbix_item_key": key,
            "zabbix_interfaceid": str(item.get("interfaceid") or ""),
            "zabbix_itemid": str(item.get("itemid") or ""),
            "notes": item.get("name", ""),
        }

        port, port_created = Port.objects.get_or_create(
            device=device,
            name=port_name,
            defaults=defaults,
        )

        record = PortRecord(port=port, created=port_created, defaults=defaults)
        port_records.append(record)
        port_record_map[_port_map_key(port)] = record

    if import_interfaces and not port_records:
        for item in host_items:
            key = item.get("key_") or ""
            tokens = _extract_key_tokens(key)
            if not tokens:
                continue
            port_name = tokens[0].strip()
            if not port_name:
                continue
            port, _ = Port.objects.get_or_create(
                device=device,
                name=port_name,
                defaults={
                    "zabbix_item_key": key,
                    "zabbix_interfaceid": str(item.get("interfaceid") or ""),
                    "notes": item.get("name", ""),
                },
            )
            record = PortRecord(port=port, created=False, defaults={})
            port_records.append(record)
            port_record_map[_port_map_key(port)] = record

    created_summary = {
        "sites": int(site_created),
        "devices": int(device_created),
        "ports": 0,
    }

    port_entries: list[_PortEntry] = []
    for record in port_records:
        port = record.port
        lower = port.name.lower()
        normalized = _normalize_identifier(lower)
        trimmed = lower[1:] if lower.startswith("x") else lower
        normalized_trimmed = normalized[1:] if normalized.startswith("x") else normalized
        port_entries.append(
            _PortEntry(
                port=port,
                record=record,
                lower=lower,
                normalized=normalized,
                trimmed=trimmed,
                normalized_trimmed=normalized_trimmed,
            )
        )

    for item in host_items:
        key = item.get("key_") or ""
        key_lower = key.lower()
        name_lower = (item.get("name") or "").lower()
        role = item.get("_role") or _identify_item_role(key_lower, name_lower)
        if not role:
            continue

        tokens = _extract_key_tokens(key)
        combined_text = f"{key_lower} {name_lower}"
        combined_normalized = _normalize_identifier(combined_text)

        best_entry: _PortEntry | None = None
        best_score = 0
        for entry in port_entries:
            score = _score_port_match(entry, tokens, combined_text, combined_normalized)
            if score > best_score:
                best_score = score
                best_entry = entry
        if not best_entry or best_score < 45:
            continue

        port = best_entry.port
        record = best_entry.record
        updates: dict[str, Any] = {}
        iface_id = str(item.get("interfaceid") or "")
        if iface_id and iface_id not in ("0", port.zabbix_interfaceid):
            updates["zabbix_interfaceid"] = iface_id

        item_id = str(item.get("itemid") or "")
        if role in ("primary_oper", "legacy_lastdown"):
            should_override = role == "primary_oper" or not port.zabbix_item_key
            if key and should_override and port.zabbix_item_key != key:
                updates["zabbix_item_key"] = key
            if item_id:
                if should_override and port.zabbix_itemid != item_id:
                    updates["zabbix_itemid"] = item_id
                elif role == "legacy_lastdown" and not port.zabbix_itemid:
                    updates["zabbix_itemid"] = item_id
            note = item.get("name", "")
            if note and should_override and port.notes != note:
                updates["notes"] = note
        elif role == "traffic_in":
            if item_id and not port.zabbix_item_id_traffic_in:
                updates["zabbix_item_id_traffic_in"] = item_id
        elif role == "traffic_out":
            if item_id and not port.zabbix_item_id_traffic_out:
                updates["zabbix_item_id_traffic_out"] = item_id
        elif role == "optical_rx":
            if key and port.rx_power_item_key != key:
                updates["rx_power_item_key"] = key
        elif role == "optical_tx":
            if key and port.tx_power_item_key != key:
                updates["tx_power_item_key"] = key

        _apply_port_updates(port, updates, record.updated_fields)

    discovery_cache = _preload_optical_discovery_cache(
        str(device.zabbix_hostid or ""),
        [record.port for record in port_records],
    )
    bulk_snapshots = fetch_ports_optical_snapshots(
        [record.port for record in port_records],
        discovery_cache=discovery_cache,
        persist_keys=True,
        include_status_meta=False,
    )

    optical_snapshots: list[dict[str, Any]] = []
    for record in port_records:
        port_like = cast(PortLike, record.port)
        snapshot = bulk_snapshots.get(
            port_like.id,
            {
                "rx_key": None,
                "tx_key": None,
                "rx_dbm": None,
                "tx_dbm": None,
            },
        )
        record.optical_snapshot = snapshot
        optical_snapshots.append(
            {
                "port_id": port_like.id,
                "rx_key": snapshot.get("rx_key"),
                "tx_key": snapshot.get("tx_key"),
                "rx_dbm": snapshot.get("rx_dbm"),
                "tx_dbm": snapshot.get("tx_dbm"),
            }
        )

    ports_created_payload: list[dict[str, Any]] = []
    ports_updated_payload: list[dict[str, Any]] = []
    for record in port_records:
        port = record.port
        port_like = cast(PortLike, port)
        port.refresh_from_db()
        summary: dict[str, Any] = {
            "id": port_like.id,
            "name": port_like.name,
            "zabbix_item_key": port_like.zabbix_item_key,
            "zabbix_itemid": port_like.zabbix_itemid,
            "zabbix_interfaceid": port_like.zabbix_interfaceid,
            "zabbix_item_id_traffic_in": port_like.zabbix_item_id_traffic_in,
            "zabbix_item_id_traffic_out": port_like.zabbix_item_id_traffic_out,
            "rx_power_item_key": port_like.rx_power_item_key,
            "tx_power_item_key": port_like.tx_power_item_key,
            "updated_fields": sorted(record.updated_fields) if record.updated_fields else [],
            "optical_snapshot": record.optical_snapshot,
        }
        if record.created:
            ports_created_payload.append(summary)
        elif summary["updated_fields"]:
            ports_updated_payload.append(summary)

    created_summary["ports"] = len(ports_created_payload)

    device_like = cast(DeviceLike, device)

    # Garante que, se update_site for false, não alteramos o site
    if not update_site and device_like.site_id != original_site_id:
        device_like.site_id = original_site_id
        device_like.save(update_fields=["site"])
        device_like.refresh_from_db()

    return {
        "created": created_summary,
        "device": {
            "id": device_like.id,
            "name": device_like.name,
            "site": getattr(device_like.site, "display_name", None),
            "zabbix_hostid": device_like.zabbix_hostid,
        },
        "ports_created": ports_created_payload,
        "ports_updated": ports_updated_payload,
        "total_ports_detected": len(port_records),
        "optical_snapshots": optical_snapshots,
    }


def discover_zabbix_hosts() -> dict[str, Any]:
    raw_hosts = common.ZABBIX_REQUEST(
        "host.get",
        {
            "output": ["hostid", "host", "name"],
            "selectInterfaces": ["interfaceid", "ip", "dns", "port", "type"],
        },
    )
    hosts = _coerce_dict_list(raw_hosts)
    results: list[dict[str, Any]] = []
    for host in hosts:
        interfaces = host.get("interfaces", [])
        results.append(
            {
                "hostid": host.get("hostid"),
                "name": host.get("name") or host.get("host"),
                "interfaces": interfaces,
            }
        )
    return {"hosts": results}


def bulk_create_inventory(payload: Mapping[str, Any]) -> dict[str, Any]:
    sites_payload = payload.get("sites", [])
    devices_payload = payload.get("devices", [])
    ports_payload = payload.get("ports", [])
    fibers_payload = payload.get("fibers", [])

    created = {"sites": 0, "devices": 0, "ports": 0, "fibers": 0}
    site_map: dict[str, Site] = {}
    device_map: dict[tuple[str, str], Device] = {}

    def _register_site(site_obj: Site) -> None:
        keys = {site_obj.display_name, site_obj.slug}
        for key in keys:
            if key:
                site_map[str(key).strip()] = site_obj

    for existing_site in Site.objects.all():
        _register_site(existing_site)

    for site_data in sites_payload:
        raw_name = site_data.get("display_name") or site_data.get("name")
        if not raw_name:
            continue
        display_name = str(raw_name).strip()
        state_value = str(site_data.get("state") or "").strip()
        country_value = str(site_data.get("country") or "").strip()
        slug_source = "-".join(part for part in [display_name, state_value, country_value] if part)
        slug_candidate = slugify(slug_source) or slugify(display_name) or None

        site = Site.objects.filter(display_name__iexact=display_name).first()
        was_created = False
        if site is None:
            site = Site(
                display_name=display_name,
                address_line1=str(
                    site_data.get("address_line1") or site_data.get("address") or ""
                ).strip(),
                address_line2=str(site_data.get("address_line2") or "").strip(),
                address_line3=str(site_data.get("address_line3") or "").strip(),
                city=str(site_data.get("city") or "").strip(),
                state=state_value,
                postal_code=str(site_data.get("postal_code") or site_data.get("zip") or "").strip(),
                country=country_value,
                rack_location=str(site_data.get("rack_location") or "").strip(),
                description=str(site_data.get("description") or "").strip(),
            )
            if slug_candidate:
                site.slug = slug_candidate

            lat_value = site_data.get("lat")
            lon_value = site_data.get("lng")
            try:
                if lat_value is not None:
                    site.latitude = Decimal(str(lat_value))
            except (InvalidOperation, ValueError):  # pragma: no cover - defensive
                pass
            try:
                if lon_value is not None:
                    site.longitude = Decimal(str(lon_value))
            except (InvalidOperation, ValueError):  # pragma: no cover
                pass
            site.save()
            was_created = True
        else:
            update_fields: list[str] = []
            field_mapping: dict[str, Any] = {
                "address_line1": site_data.get("address_line1") or site_data.get("address") or "",
                "address_line2": site_data.get("address_line2") or "",
                "address_line3": site_data.get("address_line3") or "",
                "city": site_data.get("city") or "",
                "state": state_value,
                "postal_code": site_data.get("postal_code") or site_data.get("zip") or "",
                "country": country_value,
                "rack_location": site_data.get("rack_location") or "",
                "description": site_data.get("description") or site.description,
            }
            for field, raw in field_mapping.items():
                value = str(raw).strip()
                if value and getattr(site, field) != value:
                    setattr(site, field, value)
                    update_fields.append(field)
            if slug_candidate and site.slug != slug_candidate:
                site.slug = slug_candidate
                update_fields.append("slug")
            if update_fields:
                site.save(update_fields=update_fields)
        if was_created:
            created["sites"] += 1
        _register_site(site)

    for device_data in devices_payload:
        site_name = str(device_data.get("site") or "").strip()
        site = site_map.get(site_name)
        if not site:
            site = (
                Site.objects.filter(display_name__iexact=site_name).first()
                or Site.objects.filter(slug=slugify(site_name)).first()
            )
            if site:
                _register_site(site)
        if not site:
            continue
        device, was_created = Device.objects.get_or_create(
            site=site,
            name=device_data.get("name"),
            defaults={
                "vendor": device_data.get("vendor", ""),
                "model": device_data.get("model", ""),
                "zabbix_hostid": device_data.get("zabbix_hostid", ""),
            },
        )
        if was_created:
            created["devices"] += 1
        for key in (site.display_name, site.slug):
            if key:
                device_map[(str(key).strip(), device.name)] = device

    port_map: dict[tuple[int, str], Port] = {}
    for port_data in ports_payload:
        site_name = str(port_data.get("site") or "").strip()
        device_name = port_data.get("device")
        device = device_map.get((site_name, device_name))
        if not device:
            continue
        device_like = cast(DeviceLike, device)
        port, was_created = Port.objects.get_or_create(
            device=device,
            name=port_data.get("name"),
            defaults={
                "zabbix_item_key": port_data.get("zabbix_item_key", ""),
                "zabbix_interfaceid": port_data.get("zabbix_interfaceid", ""),
                "notes": port_data.get("notes", ""),
            },
        )
        if was_created:
            created["ports"] += 1
        port_like = cast(PortLike, port)
        port_map[(device_like.id, port_like.name)] = port

    for fiber_data in fibers_payload:
        origin_device_raw = device_map.get(
            (str(fiber_data.get("origin_site") or "").strip(), fiber_data.get("origin_device"))
        )
        dest_device_raw = device_map.get(
            (str(fiber_data.get("dest_site") or "").strip(), fiber_data.get("dest_device"))
        )

        origin_device = cast(DeviceLike | None, origin_device_raw) if origin_device_raw else None
        dest_device = cast(DeviceLike | None, dest_device_raw) if dest_device_raw else None

        origin_port_name = fiber_data.get("origin_port")
        dest_port_name = fiber_data.get("dest_port")

        origin_port = (
            port_map.get((origin_device.id, origin_port_name))
            if origin_device and isinstance(origin_port_name, str)
            else None
        )
        dest_port = (
            port_map.get((dest_device.id, dest_port_name))
            if dest_device and isinstance(dest_port_name, str)
            else None
        )
        if not origin_port or not dest_port:
            continue
        _, was_created = FiberCable.objects.get_or_create(
            name=fiber_data.get("name"),
            defaults={
                "origin_port": origin_port,
                "destination_port": dest_port,
                "length_km": fiber_data.get("length_km"),
                # path PostGIS field will be populated by signal if needed
                "status": FiberCable.STATUS_UNKNOWN,
            },
        )
        if was_created:
            created["fibers"] += 1

    return {"created": created}


def list_sites() -> dict[str, Any]:
    sites_qs = Site.objects.prefetch_related(
        Prefetch(
            "devices",
            queryset=Device.objects.only("id", "name", "zabbix_hostid", "site", "device_icon"),
        )
    )

    # Buscar contagem de câmeras por site
    cameras_by_site = {}
    try:
        video_gateways = (
            MessagingGateway.objects.filter(gateway_type="video", site_name__isnull=False)
            .values("site_name")
            .distinct()
        )

        for gateway in video_gateways:
            site_name = gateway["site_name"]
            count = MessagingGateway.objects.filter(
                gateway_type="video", site_name=site_name
            ).count()
            cameras_by_site[site_name] = count
    except Exception as exc:
        logger.warning("Failed to count cameras by site: %s", exc)
        cameras_by_site = {}

    data: list[dict[str, Any]] = []
    for site_obj in sites_qs:
        site_like = cast(SiteLike, site_obj)
        devices_payload: list[dict[str, Any]] = []
        device_iterable = cast(Iterable[Device], site_like.devices.all())
        for device_obj in device_iterable:
            device_like = cast(DeviceLike, device_obj)
            icon_url: str | None
            try:
                icon_url = (
                    cast(str | None, getattr(device_like.device_icon, "url", None))
                    if device_like.device_icon
                    else None
                )
            except Exception:
                icon_url = None

            devices_payload.append(
                {
                    "id": device_like.id,
                    "name": device_like.name,
                    "zabbix_hostid": device_like.zabbix_hostid,
                    "lat": float(site_like.latitude) if site_like.latitude else None,
                    "lng": float(site_like.longitude) if site_like.longitude else None,
                    "icon_url": icon_url,
                }
            )

        # Buscar contagem de câmeras para este site
        # Tenta primeiro pelo display_name, depois pelo name
        camera_count = (
            cameras_by_site.get(site_like.display_name, 0)
            if site_like.display_name
            else cameras_by_site.get(site_like.name, 0)
        )
        # Se não encontrou, tenta pelo name também
        if camera_count == 0 and site_like.display_name != site_like.name:
            camera_count = cameras_by_site.get(site_like.name, 0)

        data.append(
            {
                "id": site_like.id,
                "display_name": site_like.display_name,
                "name": site_like.name,  # Backward compat
                "city": site_like.city,
                "lat": float(site_like.latitude) if site_like.latitude else None,
                "lng": float(site_like.longitude) if site_like.longitude else None,
                "devices": devices_payload,
                "camera_count": camera_count,
            }
        )
    return {"sites": data}


def list_device_select_options() -> list[dict[str, Any]]:
    """Return device options suitable for select inputs in the UI."""

    device_rows = (
        Device.objects.select_related("site")
        .order_by("name")
        .values(
            "id",
            "name",
            "site_id",
            "site__display_name",
        )
    )

    options: list[dict[str, Any]] = []

    for entry in device_rows:
        site_label = entry.get("site__display_name") or ""
        site_id = entry.get("site_id")

        option: dict[str, Any] = {
            "id": int(entry["id"]),
            "name": entry["name"],
        }

        if site_label:
            option["site"] = site_label

        if site_id:
            option["site_id"] = int(site_id)

        options.append(option)

    return options


def list_devices_autocomplete() -> list[dict[str, Any]]:
    """
    Return devices with enriched data for autocomplete component.
    Includes coordinates, Zabbix hostid, IP, and site information.
    """
    device_rows = (
        Device.objects.select_related("site")
        .order_by("name")
        .values(
            "id",
            "name",
            "vendor",
            "model",
            "primary_ip",
            "zabbix_hostid",
            "site_id",
            "site__display_name",
            "site__latitude",
            "site__longitude",
            "site__city",
            "site__state",
        )
    )

    options: list[dict[str, Any]] = []

    for entry in device_rows:
        site_label = entry.get("site__display_name") or ""
        lat = entry.get("site__latitude")
        lng = entry.get("site__longitude")

        option: dict[str, Any] = {
            "id": int(entry["id"]),
            "name": entry["name"],
            "ip": entry.get("primary_ip") or "",
            "vendor": entry.get("vendor") or "",
            "model": entry.get("model") or "",
            "zabbix_hostid": entry.get("zabbix_hostid") or "",
        }

        if site_label:
            option["site"] = site_label

        if entry.get("site_id"):
            option["site_id"] = int(entry["site_id"])

        # Add coordinates if available
        if lat is not None and lng is not None:
            option["lat"] = float(lat)
            option["lng"] = float(lng)

        # Add city/state for better search
        city = entry.get("site__city")
        state = entry.get("site__state")
        if city or state:
            location_parts = []
            if city:
                location_parts.append(city)
            if state:
                location_parts.append(state)
            option["location"] = ", ".join(location_parts)

        options.append(option)

    return options
