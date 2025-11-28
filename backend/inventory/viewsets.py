"""DRF ViewSets for Inventory API."""

import logging

from django.db.models import Count, Q
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from inventory.models import (
    Device,
    DeviceGroup,
    FiberCable,
    FiberProfile,
    Port,
    Site,
    ImportRule,
)

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


class PortViewSet(viewsets.ModelViewSet):  # type: ignore[misc]
    """ViewSet for Port CRUD operations with device filtering"""

    queryset = Port.objects.select_related("device__site").order_by("name")
    serializer_class = PortSerializer
    permission_classes = [AllowAny]  # Allow public access for dashboard

    def get_queryset(self):
        """Filter ports by device if device query param is provided"""
        queryset = super().get_queryset()
        device_id = self.request.query_params.get('device')
        
        if device_id:
            queryset = queryset.filter(device_id=device_id)
        
        return queryset


class FiberCableViewSet(viewsets.ModelViewSet):  # type: ignore[misc]
    """ViewSet for FiberCable CRUD operations"""

    queryset = FiberCable.objects.select_related(
        "origin_port__device__site", "destination_port__device__site"
    ).order_by("name")
    serializer_class = FiberCableSerializer
    permission_classes = [AllowAny]  # Allow public access for dashboard

    @action(detail=True, methods=["get"])
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
        
        serializer = FiberCableStructureSerializer(cable)
        return Response(serializer.data)

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
    permission_classes = [AllowAny]

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
