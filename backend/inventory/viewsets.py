"""DRF ViewSets for Inventory API."""

import logging

from django.db.models import Count, Q
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from inventory.cache.fibers import invalidate_fiber_cache
from inventory.metrics import (
    track_viewset_action,
    track_model_operation,
    track_endpoint_usage,
)
from inventory.models import (
    Device,
    DeviceGroup,
    FiberCable,
    FiberProfile,
    Port,
    Site,
    ImportRule,
)
from inventory.usecases import fiber_alarm_configs
from maps_view.cache_swr import invalidate_dashboard_cache

from .serializers import (
    DeviceGroupSerializer,
    DeviceSerializer,
    FiberCableSerializer,
    FiberCableStructureSerializer,
    FiberProfileSerializer,
    PortSerializer,
    SiteSerializer,
    ImportRuleSerializer,
)

logger = logging.getLogger(__name__)


class SiteViewSet(viewsets.ModelViewSet):  # type: ignore[misc]
    """ViewSet for Site CRUD operations."""

    queryset = (
        Site.objects.annotate(device_count=Count("devices", distinct=True))
        .order_by("display_name")
    )
    serializer_class = SiteSerializer
    permission_classes = [IsAuthenticated]  # 🔒 Sprint 1, Week 1: Fixed security vulnerability (was AllowAny)

    @track_viewset_action("SiteViewSet")
    def list(self, request, *args, **kwargs):
        """List all sites with device count."""
        return super().list(request, *args, **kwargs)

    @track_viewset_action("SiteViewSet")
    def retrieve(self, request, *args, **kwargs):
        """Retrieve a single site."""
        return super().retrieve(request, *args, **kwargs)

    @track_viewset_action("SiteViewSet")
    def create(self, request, *args, **kwargs):
        """Create a new site."""
        return super().create(request, *args, **kwargs)

    @track_viewset_action("SiteViewSet")
    def update(self, request, *args, **kwargs):
        """Update a site."""
        return super().update(request, *args, **kwargs)

    @track_viewset_action("SiteViewSet")
    def destroy(self, request, *args, **kwargs):
        """Delete a site."""
        return super().destroy(request, *args, **kwargs)

    @track_model_operation("Site", "create")
    def perform_create(self, serializer):
        """Perform site creation with metrics."""
        super().perform_create(serializer)

    @track_model_operation("Site", "update")
    def perform_update(self, serializer):
        """Perform site update with metrics."""
        super().perform_update(serializer)

    @track_model_operation("Site", "delete")
    def perform_destroy(self, instance):
        """Perform site deletion with metrics."""
        super().perform_destroy(instance)

    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated])
    @track_endpoint_usage("/api/v1/inventory/sites/{id}/devices/")
    @track_viewset_action("SiteViewSet")
    def devices(self, request, pk=None):
        """Return devices associated with a site."""

        site = self.get_object()
        devices_qs = site.devices.select_related("site").order_by("name")
        serializer = DeviceSerializer(devices_qs, many=True)

        payload = {
            "site_id": site.id,
            "site_name": site.display_name,
            "site_city": site.city,
            "latitude": float(site.latitude)
            if site.latitude is not None
            else None,
            "longitude": float(site.longitude)
            if site.longitude is not None
            else None,
            "device_count": devices_qs.count(),
            "devices": serializer.data,
        }

        return Response(payload)

    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated])
    @track_endpoint_usage("/api/v1/inventory/sites/{id}/fiber_cables/")
    @track_viewset_action("SiteViewSet")
    def fiber_cables(self, request, pk=None):
        """Return fiber cables connected to this site (as site_a or site_b)."""
        from django.db.models import Q

        site = self.get_object()
        
        # Buscar cabos onde o site é origem (site_a) ou destino (site_b)
        cables_qs = (
            FiberCable.objects.filter(
                Q(site_a=site) | Q(site_b=site),
                parent_cable__isnull=True  # Only parent cables (exclude segments)
            )
            .select_related(
                "site_a",
                "site_b",
                "origin_port__device__site",
                "destination_port__device__site",
                "profile"
            )
            .order_by("name")
        )
        
        serializer = FiberCableSerializer(cables_qs, many=True)

        payload = {
            "site_id": site.id,
            "site_name": site.display_name,
            "fiber_count": cables_qs.count(),
            "fibers": serializer.data,
        }

        return Response(payload)


class DeviceViewSet(viewsets.ModelViewSet):  # type: ignore[misc]
    """ViewSet for Device CRUD operations"""

    queryset = Device.objects.select_related("site").order_by(
        "site__display_name", "name"
    )
    serializer_class = DeviceSerializer
    permission_classes = [IsAuthenticated]  # 🔒 Sprint 1, Week 1: Fixed security vulnerability (was AllowAny)

    @track_viewset_action("DeviceViewSet")
    def list(self, request, *args, **kwargs):
        """List all devices."""
        return super().list(request, *args, **kwargs)

    @track_viewset_action("DeviceViewSet")
    def retrieve(self, request, *args, **kwargs):
        """Retrieve a single device."""
        return super().retrieve(request, *args, **kwargs)

    @track_viewset_action("DeviceViewSet")
    def create(self, request, *args, **kwargs):
        """Create a new device."""
        return super().create(request, *args, **kwargs)

    @track_viewset_action("DeviceViewSet")
    def update(self, request, *args, **kwargs):
        """Update a device."""
        return super().update(request, *args, **kwargs)

    @track_viewset_action("DeviceViewSet")
    def destroy(self, request, *args, **kwargs):
        """Delete a device."""
        return super().destroy(request, *args, **kwargs)

    @track_model_operation("Device", "create")
    def perform_create(self, serializer):
        """Perform device creation with metrics."""
        super().perform_create(serializer)

    @track_model_operation("Device", "update")
    def perform_update(self, serializer):
        """Perform device update with metrics."""
        super().perform_update(serializer)

    @track_model_operation("Device", "delete")
    def perform_destroy(self, instance):
        """Perform device deletion with metrics."""
        super().perform_destroy(instance)

    @action(
        detail=False,
        methods=["get"],
        url_path="by-zabbix/(?P<zabbix_id>[^/.]+)",
    )
    @track_endpoint_usage("/api/v1/inventory/devices/by-zabbix/{zabbix_id}/")
    @track_viewset_action("DeviceViewSet")
    def by_zabbix_id(self, request, zabbix_id=None):
        """Get device by Zabbix host ID"""
        try:
            device = Device.objects.select_related("site").get(
                zabbix_hostid=zabbix_id
            )
            serializer = self.get_serializer(device)
            return Response(serializer.data)
        except Device.DoesNotExist:
            return Response(
                {
                    "error": (
                        f"Device with zabbix_hostid '{zabbix_id}' not found"
                    )
                },
                status=404,
            )

    @action(detail=False, methods=["get"], url_path="available-for-group")
    def available_for_group(self, request):
        """
        Retorna devices sem monitoring_group OU pertencentes ao grupo informado.
        Útil para montar o picker de grupos sem baixar todos os devices.
        """
        group_id = request.query_params.get("group_id")
        filters = Q(monitoring_group__isnull=True)
        if group_id and group_id != "null":
            filters |= Q(monitoring_group_id=group_id)

        devices_qs = (
            self.get_queryset()
            .filter(filters)
            .select_related("site")
            .order_by("site__display_name", "name")
        )
        serializer = self.get_serializer(devices_qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="sync")
    def sync_from_zabbix(self, request, pk=None):
        """Synchronize a device with current data from Zabbix.

        Steps:
        1. Fetch host + inventory (use case)
        2. Re-apply import rules if default category / missing group
        3. Sync host group relationships (ManyToMany)
        4. Set monitoring_group if still empty (first group)
        Returns updated serialized device payload.
        """
        try:
            device = self.get_object()
        except Device.DoesNotExist:
            return Response({"error": "Device not found"}, status=404)

        if not device.zabbix_hostid:
            return Response(
                {"error": "Device missing zabbix_hostid; cannot sync"},
                status=400,
            )

        def _as_bool(value, default=True):
            if value is None:
                return default
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                return value != 0
            return str(value).lower() in ("1", "true", "yes", "on")

        # Aceita snake_case e camelCase no payload
        update_site_raw = request.data.get("update_site")
        if update_site_raw is None:
            update_site_raw = request.data.get("updateSite")

        sync_options = {
            "update_identity": _as_bool(request.data.get("update_identity"), True),
            "apply_auto_rules": _as_bool(request.data.get("apply_auto_rules"), True),
            "sync_groups": _as_bool(request.data.get("sync_groups"), True),
            "update_site": _as_bool(update_site_raw, True),
            "import_interfaces": _as_bool(request.data.get("import_interfaces"), True),
        }

        logger.info(
            "[SYNC_FLAGS] update_identity=%s apply_auto_rules=%s sync_groups=%s update_site=%s import_interfaces=%s",
            sync_options["update_identity"],
            sync_options["apply_auto_rules"],
            sync_options["sync_groups"],
            sync_options["update_site"],
            sync_options["import_interfaces"],
        )

        # Use existing use case to pull fresh data and apply rules/site logic
        from inventory.usecases.devices import add_device_from_zabbix
        from inventory.services.device_groups import (
            sync_device_groups_for_device,
        )
        from inventory.services.import_rules import apply_import_rules

        original_site_id = device.site_id

        try:
            try:
                add_device_from_zabbix(
                    {
                        "hostid": device.zabbix_hostid,
                        **sync_options,
                    }
                )
            except Exception as e:  # pragma: no cover
                logger.exception("Failed fetching from Zabbix during sync")
                return Response(
                    {"error": f"Failed fetching from Zabbix: {e}"},
                    status=502,
                )

            # Refresh device after use case execution
            device.refresh_from_db()

            # If usuário desativou atualização de site, garante que não foi alterado
            if not sync_options["update_site"] and device.site_id != original_site_id:
                device.site_id = original_site_id
                device.save(update_fields=["site"])

            # Re-apply rules for existing devices still lacking classification
            if sync_options["apply_auto_rules"] and (
                (not device.monitoring_group_id) or device.category == "backbone"
            ):
                try:
                    rule_result = apply_import_rules(device.name)
                    if rule_result:
                        update_fields: list[str] = []
                        if (
                            device.category == "backbone"
                            and rule_result.get("category")
                            and rule_result["category"] != device.category
                        ):
                            device.category = rule_result["category"]
                            update_fields.append("category")
                        if (
                            not device.monitoring_group_id
                            and rule_result.get("group_id")
                        ):
                            device.monitoring_group_id = rule_result["group_id"]
                            update_fields.append("monitoring_group")
                        if update_fields:
                            device.save(update_fields=update_fields)
                except Exception:
                    pass
            # Sync host groups and assign monitoring_group if still missing
            if sync_options["sync_groups"]:
                sync_device_groups_for_device(device)
                device.refresh_from_db()
                if not device.monitoring_group_id and device.groups.exists():
                    first_group = device.groups.first()
                    if first_group:
                        device.monitoring_group = first_group
                        device.save(update_fields=["monitoring_group"])

            serializer = self.get_serializer(device)
            return Response({"status": "synced", "device": serializer.data})
        except Exception as exc:  # pragma: no cover
            logger.exception("Unexpected error during sync_from_zabbix")
            return Response(
                {"error": f"Unexpected error during sync: {exc}"},
                status=500,
            )

    @action(detail=True, methods=["get"], url_path="metrics")
    def metrics(self, request, pk=None):
        """
        Return basic metrics for a device (CPU %, Memory %, Uptime).
        Falls back to manual overrides when Zabbix data is unavailable.
        """
        try:
            device = self.get_object()
        except Device.DoesNotExist:
            return Response({"error": "Device not found"}, status=404)

        cpu_val = None
        mem_val = None
        uptime_sec = None
        uptime_human = None

        try:
            from integrations.zabbix.zabbix_service import zabbix_request
            hostid = device.zabbix_hostid
            items = []
            if device.uptime_item_key:
                items.append(device.uptime_item_key)
            if device.cpu_usage_item_key:
                items.append(device.cpu_usage_item_key)
            if getattr(device, "memory_usage_item_key", ""):
                items.append(device.memory_usage_item_key)

            if hostid and items:
                raw = zabbix_request(
                    "item.get",
                    {
                        "output": ["key_", "lastvalue", "units"],
                        "hostids": [hostid],
                        "filter": {"key_": items},
                    },
                )
                # Proteger contra None - zabbix_request pode retornar None em caso de erro
                if raw is not None:
                    for it in raw:
                        key = it.get("key_", "")
                        last = it.get("lastvalue", "")
                        units = it.get("units", "")
                        if key == device.uptime_item_key and last:
                            try:
                                uptime_sec = int(float(last))
                                days = uptime_sec // 86400
                                hours = (uptime_sec % 86400) // 3600
                                minutes = (uptime_sec % 3600) // 60
                                parts = []
                                if days > 0:
                                    parts.append(f"{days}d")
                                if hours > 0:
                                    parts.append(f"{hours}h")
                                if minutes > 0:
                                    parts.append(f"{minutes}m")
                                uptime_human = " ".join(parts) if parts else "< 1m"
                            except Exception:
                                uptime_human = str(last)
                        elif key == device.cpu_usage_item_key and last:
                            try:
                                cpu_val = float(last)
                            except Exception:
                                try:
                                    cpu_val = float(str(last).replace("%", ""))
                                except Exception:
                                    cpu_val = None
                        elif key == getattr(device, "memory_usage_item_key", "") and last:
                            try:
                                mem_val = float(last)
                            except Exception:
                                try:
                                    mem_val = float(str(last).replace("%", ""))
                                except Exception:
                                    mem_val = None
                # Fallback: quando uptime não veio mas o host está disponível no Zabbix
                if uptime_sec is None and hostid:
                    try:
                        host_info = zabbix_request(
                            "host.get",
                            {"hostids": [hostid], "output": ["available"]},
                        )
                        if isinstance(host_info, list) and host_info:
                            available = host_info[0].get("available")
                            if str(available) == "1":
                                uptime_sec = 1
                                uptime_human = "unknown"
                    except Exception:
                        logger.warning(
                            "Zabbix availability fallback failed for device %s",
                            device.pk,
                            exc_info=True,
                        )
                # Fallback via icmpping (ping) quando uptime não está disponível
                if uptime_sec is None and hostid:
                    try:
                        ping_items = zabbix_request(
                            "item.get",
                            {
                                "hostids": [hostid],
                                "filter": {"key_": "icmpping"},
                                "output": ["key_", "lastvalue"],
                            },
                        )
                        if isinstance(ping_items, list):
                            for it in ping_items:
                                if it.get("key_") == "icmpping" and str(it.get("lastvalue")) == "1":
                                    uptime_sec = 1
                                    uptime_human = "unknown"
                                    break
                    except Exception:
                        logger.warning(
                            "Zabbix icmpping fallback failed for device %s",
                            device.pk,
                            exc_info=True,
                        )
        except Exception as exc:
            logger.warning(
                "Metrics fetch failed for device %s: %s",
                device.pk,
                exc,
                exc_info=True,
            )

        # Fallbacks to manual overrides
        if cpu_val is None and device.cpu_usage_manual_percent is not None:
            cpu_val = float(device.cpu_usage_manual_percent)
        if mem_val is None and device.memory_usage_manual_percent is not None:
            mem_val = float(device.memory_usage_manual_percent)

        return Response({
            "cpu": cpu_val,
            "memory": mem_val,
            "uptime_seconds": uptime_sec,
            "uptime_human": uptime_human,
        })


class PortViewSet(viewsets.ModelViewSet):  # type: ignore[misc]
    """ViewSet for Port CRUD operations with device filtering"""

    queryset = Port.objects.select_related("device__site").order_by("name")
    serializer_class = PortSerializer
    permission_classes = [IsAuthenticated]  # 🔒 Sprint 1, Week 1: Fixed security vulnerability (was AllowAny)

    @track_viewset_action("PortViewSet")
    def list(self, request, *args, **kwargs):
        """List all ports."""
        return super().list(request, *args, **kwargs)

    @track_viewset_action("PortViewSet")
    def retrieve(self, request, *args, **kwargs):
        """Retrieve a single port."""
        return super().retrieve(request, *args, **kwargs)

    @track_viewset_action("PortViewSet")
    def create(self, request, *args, **kwargs):
        """Create a new port."""
        return super().create(request, *args, **kwargs)

    @track_viewset_action("PortViewSet")
    def update(self, request, *args, **kwargs):
        """Update a port."""
        return super().update(request, *args, **kwargs)

    @track_viewset_action("PortViewSet")
    def destroy(self, request, *args, **kwargs):
        """Delete a port."""
        return super().destroy(request, *args, **kwargs)

    @track_model_operation("Port", "create")
    def perform_create(self, serializer):
        """Perform port creation with metrics."""
        super().perform_create(serializer)

    @track_model_operation("Port", "update")
    def perform_update(self, serializer):
        """Perform port update with metrics."""
        super().perform_update(serializer)

    @track_model_operation("Port", "delete")
    def perform_destroy(self, instance):
        """Perform port deletion with metrics."""
        super().perform_destroy(instance)

    def get_queryset(self):
        """Filter ports by device if device query param is provided"""
        queryset = super().get_queryset()
        device_id = self.request.query_params.get('device')
        
        if device_id:
            queryset = queryset.filter(device_id=device_id)
        
        return queryset

    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated])
    def optical_history(self, request, pk=None):
        """
        Return historical optical power data from Zabbix history.get API.
        
        Busca últimas 24 horas de dados RX/TX diretamente do Zabbix
        sem persistir no banco local.
        
        Query params:
            hours: número de horas de histórico (default=24, max=168)
        """
        from datetime import datetime, timedelta, timezone as dt_timezone
        from django.utils import timezone
        from integrations.zabbix.zabbix_service import zabbix_request
        from inventory.domain.optical import _discover_optical_keys_by_portname
        
        port = self.get_object()
        
        # Buscar chaves ópticas do item no Zabbix
        hostid = port.device.zabbix_hostid if port.device else None
        if not hostid:
            return Response({"error": "Device não possui hostid configurado"}, status=400)
        
        # Usar chaves configuradas na porta ou descobrir dinamicamente
        rx_key = port.rx_power_item_key or None
        tx_key = port.tx_power_item_key or None
        
        # Se não tiver chaves configuradas, tentar descobrir
        if not rx_key and not tx_key:
            optical_keys = _discover_optical_keys_by_portname(
                hostid=hostid,
                port_name=port.name,
            )
            rx_key = optical_keys.get("rx")
            tx_key = optical_keys.get("tx")
        
        if not rx_key and not tx_key:
            return Response({"error": "Nenhum item óptico encontrado no Zabbix para esta porta"}, status=404)
        
        # Obter período de consulta
        hours = int(request.query_params.get("hours", 24))
        hours = min(hours, 168)  # Máximo 7 dias
        
        time_from = int((timezone.now() - timedelta(hours=hours)).timestamp())
        time_till = int(timezone.now().timestamp())
        
        history_data = []
        
        # Buscar RX history
        if rx_key:
            rx_items = zabbix_request("item.get", {
                "hostids": [str(hostid)],
                "filter": {"key_": rx_key},
                "output": ["itemid", "value_type"]
            })
            if rx_items:
                rx_item = rx_items[0]
                rx_history = zabbix_request("history.get", {
                    "itemids": [rx_item["itemid"]],
                    "history": int(rx_item.get("value_type", 0)),
                    "time_from": time_from,
                    "time_till": time_till,
                    "sortfield": "clock",
                    "sortorder": "ASC",
                })
                if rx_history:
                    for entry in rx_history:
                        timestamp = datetime.fromtimestamp(int(entry["clock"]), tz=dt_timezone.utc)
                        history_data.append({
                            "timestamp": timestamp.isoformat(),
                            "rx_power": float(entry.get("value", 0)),
                            "tx_power": None,
                        })
        
        # Buscar TX history
        if tx_key:
            tx_items = zabbix_request("item.get", {
                "hostids": [str(hostid)],
                "filter": {"key_": tx_key},
                "output": ["itemid", "value_type"]
            })
            if tx_items:
                tx_item = tx_items[0]
                tx_history = zabbix_request("history.get", {
                    "itemids": [tx_item["itemid"]],
                    "history": int(tx_item.get("value_type", 0)),
                    "time_from": time_from,
                    "time_till": time_till,
                    "sortfield": "clock",
                    "sortorder": "ASC",
                })
                if tx_history:
                    # Mesclar com RX history baseado em timestamp
                    tx_by_time = {int(e["clock"]): float(e.get("value", 0)) for e in tx_history}
                    
                    # Atualizar registros existentes ou criar novos
                    existing_times = {datetime.fromisoformat(d["timestamp"]).timestamp() for d in history_data}
                    
                    for entry in history_data:
                        ts = datetime.fromisoformat(entry["timestamp"]).timestamp()
                        if int(ts) in tx_by_time:
                            entry["tx_power"] = tx_by_time[int(ts)]
                    
                    # Adicionar TX-only entries
                    for clock, tx_value in tx_by_time.items():
                        if clock not in existing_times:
                            timestamp = datetime.fromtimestamp(clock, tz=dt_timezone.utc)
                            history_data.append({
                                "timestamp": timestamp.isoformat(),
                                "rx_power": None,
                                "tx_power": tx_value,
                            })
        
        # Ordenar por timestamp
        history_data.sort(key=lambda x: x["timestamp"])
        
        return Response(history_data)

    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated])
    def traffic_history(self, request, pk=None):
        """
        Return traffic history with 95th percentile calculation.
        
        Query params:
            hours: número de horas de histórico (default=24, max=168)
        """
        from datetime import datetime, timedelta, timezone as dt_timezone
        from django.utils import timezone
        from integrations.zabbix.zabbix_service import zabbix_request
        import statistics
        
        port = self.get_object()
        
        hostid = port.device.zabbix_hostid if port.device else None
        if not hostid:
            return Response({"error": "Device não possui hostid configurado"}, status=400)
        
        # Item IDs de tráfego
        traffic_in_id = port.zabbix_item_id_traffic_in
        traffic_out_id = port.zabbix_item_id_traffic_out
        
        if not traffic_in_id and not traffic_out_id:
            return Response({"error": "Porta não possui items de tráfego configurados"}, status=404)
        
        # Período de consulta
        hours = int(request.query_params.get("hours", 24))
        hours = min(hours, 168)  # Máximo 7 dias
        
        time_from = int((timezone.now() - timedelta(hours=hours)).timestamp())
        time_till = int(timezone.now().timestamp())
        
        traffic_data = []
        in_values = []
        out_values = []
        
        # Buscar tráfego IN
        if traffic_in_id:
            in_history = zabbix_request("history.get", {
                "itemids": [traffic_in_id],
                "history": 3,  # Numeric (unsigned) - típico para contadores de tráfego
                "time_from": time_from,
                "time_till": time_till,
                "sortfield": "clock",
                "sortorder": "ASC",
            })
            if in_history:
                for entry in in_history:
                    timestamp = datetime.fromtimestamp(int(entry["clock"]), tz=dt_timezone.utc)
                    value_bps = float(entry.get("value", 0))
                    in_values.append(value_bps)
                    traffic_data.append({
                        "timestamp": timestamp.isoformat(),
                        "traffic_in": value_bps,
                        "traffic_out": None,
                    })
        
        # Buscar tráfego OUT
        if traffic_out_id:
            out_history = zabbix_request("history.get", {
                "itemids": [traffic_out_id],
                "history": 3,
                "time_from": time_from,
                "time_till": time_till,
                "sortfield": "clock",
                "sortorder": "ASC",
            })
            if out_history:
                out_by_time = {int(e["clock"]): float(e.get("value", 0)) for e in out_history}
                out_values = list(out_by_time.values())
                
                # Mesclar com IN data
                existing_times = {datetime.fromisoformat(d["timestamp"]).timestamp() for d in traffic_data}
                
                for entry in traffic_data:
                    ts = datetime.fromisoformat(entry["timestamp"]).timestamp()
                    if int(ts) in out_by_time:
                        entry["traffic_out"] = out_by_time[int(ts)]
                
                # Adicionar OUT-only entries
                for clock, out_value in out_by_time.items():
                    if clock not in existing_times:
                        timestamp = datetime.fromtimestamp(clock, tz=dt_timezone.utc)
                        traffic_data.append({
                            "timestamp": timestamp.isoformat(),
                            "traffic_in": None,
                            "traffic_out": out_value,
                        })
        
        # Ordenar por timestamp
        traffic_data.sort(key=lambda x: x["timestamp"])
        
        # Calcular 95º percentil
        percentile_95_in = None
        percentile_95_out = None
        
        if in_values:
            in_values_sorted = sorted(in_values)
            idx_95 = int(len(in_values_sorted) * 0.95)
            percentile_95_in = in_values_sorted[idx_95] if idx_95 < len(in_values_sorted) else in_values_sorted[-1]
        
        if out_values:
            out_values_sorted = sorted(out_values)
            idx_95 = int(len(out_values_sorted) * 0.95)
            percentile_95_out = out_values_sorted[idx_95] if idx_95 < len(out_values_sorted) else out_values_sorted[-1]
        
        return Response({
            "history": traffic_data,
            "statistics": {
                "percentile_95_in": percentile_95_in,
                "percentile_95_out": percentile_95_out,
                "avg_in": statistics.mean(in_values) if in_values else None,
                "avg_out": statistics.mean(out_values) if out_values else None,
                "max_in": max(in_values) if in_values else None,
                "max_out": max(out_values) if out_values else None,
                "period_hours": hours,
            }
        })


class FiberCableViewSet(viewsets.ModelViewSet):  # type: ignore[misc]
    """ViewSet for FiberCable CRUD operations"""

    # Exclude child segments (only show parent cables in main list)
    queryset = FiberCable.objects.filter(
        parent_cable__isnull=True  # Only cables without parent (main cables)
    ).select_related(
        "origin_port__device__site", "destination_port__device__site"
    ).prefetch_related(
        "segments__start_infrastructure",
        "segments__end_infrastructure"
    ).order_by("name")
    serializer_class = FiberCableSerializer
    permission_classes = [IsAuthenticated]  # 🔒 Sprint 1, Week 1: Fixed security vulnerability (was AllowAny)

    @track_viewset_action("FiberCableViewSet")
    def list(self, request, *args, **kwargs):
        """
        List all fiber cables with ETag caching support.
        
        Performance optimization (Sprint 4 Week 2):
        - Generates ETag from queryset hash + last modified timestamp
        - Returns 304 Not Modified if client ETag matches
        - Reduces bandwidth by ~90% for unchanged data
        """
        from django.utils.http import http_date, parse_http_date
        from django.utils.cache import get_conditional_response
        import hashlib
        
        # Get queryset and calculate ETag
        queryset = self.filter_queryset(self.get_queryset())
        
        # Initialize variables outside try block
        last_modified = None
        etag = None
        
        # Generate ETag from count + last update time
        try:
            count = queryset.count()
            last_modified = queryset.latest('updated_at').updated_at if count > 0 else None
            
            if last_modified:
                etag_source = f"{count}:{last_modified.isoformat()}"
                etag = hashlib.md5(etag_source.encode()).hexdigest()
                
                # Check If-None-Match header
                client_etag = request.META.get('HTTP_IF_NONE_MATCH', '').strip('"')
                
                if client_etag == etag:
                    # Client has current version - return 304
                    from rest_framework.response import Response
                    response = Response(status=304)
                    response['ETag'] = f'"{etag}"'
                    response['Last-Modified'] = http_date(last_modified.timestamp())
                    response['Cache-Control'] = 'private, max-age=30'
                    return response
        except Exception:
            # If ETag generation fails, proceed normally
            pass
        
        # Standard list response
        response = super().list(request, *args, **kwargs)
        
        # Add caching headers
        if last_modified and etag:
            response['ETag'] = f'"{etag}"'
            response['Last-Modified'] = http_date(last_modified.timestamp())
            response['Cache-Control'] = 'private, max-age=30'
        
        return response

    @track_viewset_action("FiberCableViewSet")
    def retrieve(self, request, *args, **kwargs):
        """Retrieve a single fiber cable."""
        return super().retrieve(request, *args, **kwargs)

    @track_viewset_action("FiberCableViewSet")
    def create(self, request, *args, **kwargs):
        """Create a new fiber cable."""
        return super().create(request, *args, **kwargs)

    @track_viewset_action("FiberCableViewSet")
    def update(self, request, *args, **kwargs):
        """Update a fiber cable."""
        return super().update(request, *args, **kwargs)

    @track_viewset_action("FiberCableViewSet")
    def destroy(self, request, *args, **kwargs):
        """Delete a fiber cable."""
        return super().destroy(request, *args, **kwargs)

    @track_model_operation("FiberCable", "create")
    def perform_create(self, serializer):
        """Perform fiber cable creation with metrics."""
        cable = super().perform_create(serializer)
        invalidate_fiber_cache()
        invalidate_dashboard_cache()
        return cable

    @track_model_operation("FiberCable", "update")
    def perform_update(self, serializer):
        """Perform fiber cable update with metrics."""
        cable = super().perform_update(serializer)
        invalidate_fiber_cache()
        invalidate_dashboard_cache()
        return cable

    @track_model_operation("FiberCable", "delete")
    def perform_destroy(self, instance):
        """Perform fiber cable deletion with metrics."""
        super().perform_destroy(instance)
        invalidate_fiber_cache()
        invalidate_dashboard_cache()

    @action(detail=True, methods=["get"])
    @track_endpoint_usage("/api/v1/inventory/fibers/{id}/structure/")
    @track_viewset_action("FiberCableViewSet")
    def structure(self, request, pk=None):
        """
        Return complete physical structure (Tubes and Strands) of the cable.
        Auto-generates structure on-the-fly if it doesn't exist (lazy creation).
        
        Returns nested hierarchy: Cable -> Tubes -> Strands with ABNT colors.
        """
        cable = self.get_object()
        
        # Auto-generation (Lazy Creation) for legacy cables
        if not cable.tubes.exists() and cable.profile:
            logger.info(
                "Auto-generating structure for cable %s (profile: %s)",
                cable.id,
                cable.profile.name,
            )
            cable.create_structure()
            # Reload to get newly created relationships
            cable.refresh_from_db()

        cable = (
            FiberCable.objects.select_related(
                "origin_port__device__site",
                "destination_port__device__site",
            )
            .prefetch_related(
                "tubes__strands__fusions_as_a__infrastructure",
                "tubes__strands__fusions_as_a__fiber_b__tube__cable",
                "tubes__strands__fusions_as_b__infrastructure",
                "tubes__strands__fusions_as_b__fiber_a__tube__cable",
            )
            .get(pk=cable.pk)
        )

        serializer = FiberCableStructureSerializer(cable)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="metrics")
    def metrics(self, request, pk=None):
        """
        Return basic metrics for a device (CPU %, Memory %, Uptime).
        Falls back to manual overrides when Zabbix data is unavailable.
        """
        try:
            device = Device.objects.get(pk=pk)
        except Device.DoesNotExist:
            return Response({"error": "Device not found"}, status=404)

        cpu_val = None
        mem_val = None
        uptime_sec = None
        uptime_human = None

        try:
            from integrations.zabbix.zabbix_service import zabbix_request
            hostid = device.zabbix_hostid
            items = []
            if device.uptime_item_key:
                items.append(device.uptime_item_key)
            if device.cpu_usage_item_key:
                items.append(device.cpu_usage_item_key)
            if getattr(device, "memory_usage_item_key", ""):
                items.append(device.memory_usage_item_key)

            if hostid and items:
                raw = zabbix_request(
                    "item.get",
                    {
                        "output": ["key_", "lastvalue", "units"],
                        "hostids": [hostid],
                        "filter": {"key_": items},
                    },
                )
                # Proteger contra None - zabbix_request pode retornar None em caso de erro
                if raw is not None:
                    for it in raw:
                        key = it.get("key_", "")
                        last = it.get("lastvalue", "")
                        units = it.get("units", "")
                        if key == device.uptime_item_key and last:
                            try:
                                uptime_sec = int(float(last))
                                days = uptime_sec // 86400
                                hours = (uptime_sec % 86400) // 3600
                                minutes = (uptime_sec % 3600) // 60
                                parts = []
                                if days > 0:
                                    parts.append(f"{days}d")
                                if hours > 0:
                                    parts.append(f"{hours}h")
                                if minutes > 0:
                                    parts.append(f"{minutes}m")
                                uptime_human = " ".join(parts) if parts else "< 1m"
                            except Exception:
                                uptime_human = str(last)
                        elif key == device.cpu_usage_item_key and last:
                            try:
                                cpu_val = float(last)
                            except Exception:
                                try:
                                    cpu_val = float(str(last).replace("%", ""))
                                except Exception:
                                    cpu_val = None
                        elif key == getattr(device, "memory_usage_item_key", "") and last:
                            try:
                                mem_val = float(last)
                            except Exception:
                                try:
                                    mem_val = float(str(last).replace("%", ""))
                                except Exception:
                                    mem_val = None
                # Fallback: quando uptime não veio mas o host está disponível no Zabbix
                if uptime_sec is None and hostid:
                    try:
                        host_info = zabbix_request(
                            "host.get",
                            {"hostids": [hostid], "output": ["available"]},
                        )
                        if isinstance(host_info, list) and host_info:
                            available = host_info[0].get("available")
                            if str(available) == "1":
                                uptime_sec = 1
                                uptime_human = "unknown"
                    except Exception:
                        logger.warning(
                            "Zabbix availability fallback failed for device %s",
                            device.pk,
                            exc_info=True,
                        )
                # Fallback via icmpping (ping) quando uptime não está disponível
                if uptime_sec is None and hostid:
                    try:
                        ping_items = zabbix_request(
                            "item.get",
                            {
                                "hostids": [hostid],
                                "filter": {"key_": "icmpping"},
                                "output": ["key_", "lastvalue"],
                            },
                        )
                        if isinstance(ping_items, list):
                            for it in ping_items:
                                if it.get("key_") == "icmpping" and str(it.get("lastvalue")) == "1":
                                    uptime_sec = 1
                                    uptime_human = "unknown"
                                    break
                    except Exception:
                        logger.warning(
                            "Zabbix icmpping fallback failed for device %s",
                            device.pk,
                            exc_info=True,
                        )
        except Exception as exc:
            logger.warning(
                "Metrics fetch failed for device %s: %s",
                device.pk,
                exc,
                exc_info=True,
            )

        # Fallbacks to manual overrides
        if cpu_val is None and device.cpu_usage_manual_percent is not None:
            cpu_val = float(device.cpu_usage_manual_percent)
        if mem_val is None and device.memory_usage_manual_percent is not None:
            mem_val = float(device.memory_usage_manual_percent)

        return Response({
            "cpu": cpu_val,
            "memory": mem_val,
            "uptime_seconds": uptime_sec,
            "uptime_human": uptime_human,
        })

    @action(detail=False, methods=["get"])
    def profiles(self, request):
        """List available fiber profiles for cable creation dropdown."""
        profiles = FiberProfile.objects.all().order_by("total_fibers")
        serializer = FiberProfileSerializer(profiles, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="update-path")
    def update_path(self, request, pk=None):
        """
        Update cable path coordinates and length.

        Expects JSON body with "path": [{"lat": <float>, "lng": <float>}, ...]
        Returns {status, length_km, points}.
        """
        from inventory.usecases.fibers import update_fiber_path

        cable = self.get_object()
        raw_path = request.data.get("path") or []
        try:
            result = update_fiber_path(cable, raw_path)
            return Response(result)
        except Exception as exc:  # pragma: no cover
            logger.exception(
                "Failed to update fiber path for cable %s",
                cable.id,
            )
            return Response({"error": str(exc)}, status=400)

    @action(
        detail=True,
        methods=["post"],
        url_path="import-kml",
        parser_classes=[MultiPartParser, FormParser],
    )
    def import_kml(self, request, pk=None):
        """
        Import KML and set path for existing cable.

        Accepts multipart/form-data with file field named "kml".
        Parses KML LineString coordinates and updates path/length.
        """
        from inventory.usecases.fibers import (
            parse_kml_coordinates,
            update_fiber_path,
        )

        cable = self.get_object()
        kml_file = request.FILES.get("kml")
        if not kml_file:
            return Response({"error": "Missing 'kml' file"}, status=400)
        try:
            coords = parse_kml_coordinates(kml_file)
            result = update_fiber_path(cable, coords)
            return Response({"status": "ok", **result})
        except Exception as exc:  # pragma: no cover
            logger.exception("Failed to import KML for cable %s", cable.id)
            return Response({"error": str(exc)}, status=400)
    
    @action(detail=True, methods=["post"])
    def connect(self, request, pk=None):
        """
        Connect a floating cable to sites (Logical Connection).
        
        Implements "Inventory First, Routing Later" pattern:
        - Cables can be created without sites/ports (floating inventory)
        - Later connected via this endpoint (logical routing)
        - Physical termination (ports) added separately
        
        Payload:
            {
                "site_a": <site_id>,
                "site_b": <site_id>
            }
        """
        cable = self.get_object()
        
        site_a_id = request.data.get("site_a")
        site_b_id = request.data.get("site_b")
        
        if not site_a_id or not site_b_id:
            return Response(
                {"error": "Both site_a and site_b are required"},
                status=400
            )
        
        if site_a_id == site_b_id:
            return Response(
                {"error": "Origin and destination sites cannot be the same"},
                status=400
            )
        
        # Validate sites exist
        try:
            site_a = Site.objects.get(id=site_a_id)
            site_b = Site.objects.get(id=site_b_id)
        except Site.DoesNotExist as e:
            return Response(
                {"error": f"Site not found: {e}"},
                status=404
            )
        
        # Update cable connection
        cable.site_a = site_a
        cable.site_b = site_b
        cable.save(update_fields=["site_a", "site_b"])
        
        logger.info(
            "Cable %s connected: %s -> %s",
            cable.id,
            site_a.display_name,
            site_b.display_name,
        )
        
        # Return updated cable
        serializer = self.get_serializer(cable)
        return Response(serializer.data)

    @action(detail=True, methods=["get", "post"], url_path="alarms")
    def alarms(self, request, pk=None):
        """List or create alarm configurations for the selected cable."""

        cable = self.get_object()

        if request.method.lower() == "get":
            payload = fiber_alarm_configs.list_alarm_configs(cable)
            return Response({"results": payload})

        try:
            result = fiber_alarm_configs.create_alarm_config(
                cable,
                request.data,
                request.user,
            )
        except fiber_alarm_configs.FiberCableAlarmValidationError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except fiber_alarm_configs.FiberCableAlarmError as exc:  # pragma: no cover - unexpected domain errors
            logger.exception("Failed to create fiber alarm config", exc_info=True)
            return Response(
                {"error": "Falha ao criar configuração de alarme"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            invalidate_fiber_cache()
        except Exception:  # pragma: no cover - cache backend offline
            logger.debug("Unable to invalidate fiber cache after alarm creation", exc_info=True)

        try:
            invalidate_dashboard_cache()
        except Exception:  # pragma: no cover - cache backend offline
            logger.debug("Unable to invalidate dashboard cache after alarm creation", exc_info=True)

        return Response(result, status=status.HTTP_201_CREATED)


class DeviceGroupViewSet(  # type: ignore[misc]
    mixins.DestroyModelMixin, viewsets.ReadOnlyModelViewSet
):
    """ViewSet for DeviceGroup operations
    (list/retrieve + destroy when empty)
    """

    queryset = (
        DeviceGroup.objects.annotate(
            device_count=Count("primary_devices", distinct=True)
        ).order_by("name")
    )
    serializer_class = DeviceGroupSerializer
    permission_classes = [IsAuthenticated]  # 🔒 Sprint 1, Week 1: Fixed security vulnerability (was AllowAny)

    def destroy(self, request, *args, **kwargs):
        """Block deletion when group still has devices linked."""

        instance = self.get_object()
        if instance.primary_devices.exists():
            return Response(
                {
                    "error": (
                        "Não é possível remover um grupo que ainda possui devices. "
                        + "Migre ou remova os devices antes de continuar."
                    )
                },
                status=400,
            )
        return super().destroy(request, *args, **kwargs)


class ImportRuleViewSet(viewsets.ModelViewSet):  # type: ignore[misc]
    """ViewSet for ImportRule CRUD operations with reordering support."""

    queryset = ImportRule.objects.all().order_by("priority", "id")
    serializer_class = ImportRuleSerializer
    permission_classes = [IsAuthenticated]  # 🔒 Sprint 1, Week 1: Fixed security vulnerability (was AllowAny)

    @action(detail=False, methods=["post"])
    def reorder(self, request):
        """
        Bulk update priorities for drag-and-drop reordering.
        
        Expects:
            {"rules": [{"id": 1, "priority": 0}, {"id": 2, "priority": 10}]}
        """
        rules_data = request.data.get("rules", [])
        
        if not isinstance(rules_data, list):
            return Response(
                {"error": "Expected 'rules' array"},
                status=400,
            )
        
        # Bulk update priorities
        for item in rules_data:
            rule_id = item.get("id")
            priority = item.get("priority")
            
            if rule_id is None or priority is None:
                continue
            
            ImportRule.objects.filter(id=rule_id).update(priority=priority)
        
        return Response({"status": "ok", "updated": len(rules_data)})
    
    @action(detail=False, methods=["post"])
    def test_pattern(self, request):
        """
        Test regex pattern against sample device names.
        
        Expects: {"pattern": "^OLT.*", "samples": ["OLT-01", "SWITCH-02", ...]}
        Returns: {"matches": ["OLT-01"], "non_matches": ["SWITCH-02"]}
        """
        import re
        
        pattern = request.data.get("pattern", "")
        samples = request.data.get("samples", [])
        
        if not pattern:
            return Response({"error": "Pattern required"}, status=400)
        
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            return Response(
                {"error": f"Invalid regex: {e}"},
                status=400,
            )
        
        matches = []
        non_matches = []
        
        for sample in samples:
            if regex.match(str(sample)):
                matches.append(sample)
            else:
                non_matches.append(sample)
        
        return Response({
            "matches": matches,
            "non_matches": non_matches,
        })
