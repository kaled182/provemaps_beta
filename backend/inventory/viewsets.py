"""DRF ViewSets for Inventory API."""

from django.db.models import Count, Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from inventory.models import (
    Device,
    DeviceGroup,
    FiberCable,
    Port,
    Site,
    ImportRule,
)

from .serializers import (
    DeviceGroupSerializer,
    DeviceSerializer,
    FiberCableSerializer,
    PortSerializer,
    SiteSerializer,
    ImportRuleSerializer,
)


class SiteViewSet(viewsets.ModelViewSet):  # type: ignore[misc]
    """ViewSet for Site CRUD operations."""

    queryset = (
        Site.objects.annotate(device_count=Count("devices", distinct=True))
        .order_by("display_name")
    )
    serializer_class = SiteSerializer
    permission_classes = [AllowAny]  # Allow public access for dashboard

    @action(detail=True, methods=["get"], permission_classes=[AllowAny])
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


class DeviceViewSet(viewsets.ModelViewSet):  # type: ignore[misc]
    """ViewSet for Device CRUD operations"""

    queryset = Device.objects.select_related("site").order_by(
        "site__display_name", "name"
    )
    serializer_class = DeviceSerializer
    permission_classes = [AllowAny]  # Allow public access for dashboard

    @action(
        detail=False,
        methods=["get"],
        url_path="by-zabbix/(?P<zabbix_id>[^/.]+)",
    )
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

        # Use existing use case to pull fresh data and apply rules/site logic
        from inventory.usecases.devices import add_device_from_zabbix
        from inventory.services.device_groups import (
            sync_device_groups_for_device,
        )
        from inventory.services.import_rules import apply_import_rules

        try:
            add_device_from_zabbix({"hostid": device.zabbix_hostid})
        except Exception as e:  # pragma: no cover
            return Response(
                {"error": f"Failed fetching from Zabbix: {e}"},
                status=502,
            )

        # Refresh device after use case execution
        device.refresh_from_db()

        # Re-apply rules for existing devices still lacking classification
        if (not device.monitoring_group_id) or device.category == "backbone":
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
        sync_device_groups_for_device(device)
        device.refresh_from_db()
        if not device.monitoring_group_id and device.groups.exists():
            first_group = device.groups.first()
            if first_group:
                device.monitoring_group = first_group
                device.save(update_fields=["monitoring_group"])

        serializer = self.get_serializer(device)
        return Response({"status": "synced", "device": serializer.data})


class PortViewSet(viewsets.ModelViewSet):  # type: ignore[misc]
    """ViewSet for Port CRUD operations"""

    queryset = Port.objects.select_related("device__site").order_by("name")
    serializer_class = PortSerializer
    permission_classes = [AllowAny]  # Allow public access for dashboard


class FiberCableViewSet(viewsets.ModelViewSet):  # type: ignore[misc]
    """ViewSet for FiberCable CRUD operations"""

    queryset = FiberCable.objects.select_related(
        "origin_port__device__site", "destination_port__device__site"
    ).order_by("name")
    serializer_class = FiberCableSerializer
    permission_classes = [AllowAny]  # Allow public access for dashboard


class DeviceGroupViewSet(viewsets.ReadOnlyModelViewSet):  # type: ignore[misc]
    """ViewSet for DeviceGroup read-only operations"""

    queryset = DeviceGroup.objects.all().order_by("name")
    serializer_class = DeviceGroupSerializer
    permission_classes = [AllowAny]


class ImportRuleViewSet(viewsets.ModelViewSet):  # type: ignore[misc]
    """ViewSet for ImportRule CRUD operations with reordering support."""

    queryset = ImportRule.objects.all().order_by("priority", "id")
    serializer_class = ImportRuleSerializer
    permission_classes = [AllowAny]  # TODO: Restrict to admin in production

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
