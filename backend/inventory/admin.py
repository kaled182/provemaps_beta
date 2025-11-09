"""
Django admin configuration for inventory models.
"""
from django.contrib import admin
from django.db.models import Q

from .models import Device, FiberCable, FiberEvent, Port, Site


def _blank_q(field: str) -> Q:
    return Q(**{field: ""}) | Q(**{f"{field}__isnull": True})


class _PresenceFilter(admin.SimpleListFilter):
    """Base helper for yes/no filters that check for a non-empty value."""

    field_name: str
    parameter_name: str
    title: str

    def lookups(self, request, model_admin):  # type: ignore[override]
        return (("yes", "Com valor"), ("no", "Sem valor"))

    def queryset(self, request, queryset):  # type: ignore[override]
        value = self.value()
        if value == "yes":
            return queryset.exclude(**{self.field_name: ""})
        if value == "no":
            return queryset.filter(_blank_q(self.field_name))
        return queryset


class HasZabbixItemKeyFilter(_PresenceFilter):
    title = "Chave Zabbix"
    parameter_name = "has_zabbix_item_key"
    field_name = "zabbix_item_key"


class HasNotesFilter(_PresenceFilter):
    title = "Notas"
    parameter_name = "has_notes"
    field_name = "notes"


class OpticalPowerFilter(admin.SimpleListFilter):
    title = "Sinal Óptico"
    parameter_name = "optical_power"

    def lookups(self, request, model_admin):  # type: ignore[override]
        return (("any", "Possui RX/TX"), ("none", "Sem RX/TX"))

    def queryset(self, request, queryset):  # type: ignore[override]
        value = self.value()
        has_rx = ~_blank_q("rx_power_item_key")
        has_tx = ~_blank_q("tx_power_item_key")
        has_optical = has_rx | has_tx
        if value == "any":
            return queryset.filter(has_optical)
        if value == "none":
            return queryset.exclude(has_optical)
        return queryset


class TrafficItemsFilter(admin.SimpleListFilter):
    title = "Itens de tráfego"
    parameter_name = "traffic_items"

    def lookups(self, request, model_admin):  # type: ignore[override]
        return (
            ("both", "Ingress/Egress configurados"),
            ("partial", "Apenas um lado"),
            ("none", "Ausentes"),
        )

    def queryset(self, request, queryset):  # type: ignore[override]
        value = self.value()
        has_in = ~_blank_q("zabbix_item_id_traffic_in")
        has_out = ~_blank_q("zabbix_item_id_traffic_out")

        if value == "both":
            return queryset.filter(has_in & has_out)
        if value == "partial":
            return queryset.filter((has_in & ~has_out) | (~has_in & has_out))
        if value == "none":
            return queryset.filter(~has_in & ~has_out)
        return queryset


class SiteListFilter(admin.SimpleListFilter):
    title = "Site"
    parameter_name = "site_id"

    def lookups(self, request, model_admin):  # type: ignore[override]
        sites = Site.objects.order_by("display_name")[:200]
        return [
            (str(site.pk), site.display_name or f"Site {site.pk}")
            for site in sites
        ]

    def queryset(self, request, queryset):  # type: ignore[override]
        value = self.value()
        if value:
            return queryset.filter(device__site_id=value)
        return queryset


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = (
        "display_name",
        "city",
        "state",
        "country",
        "postal_code",
        "latitude",
        "longitude",
    )
    search_fields = (
        "display_name",
        "city",
        "state",
        "country",
        "postal_code",
        "slug",
    )
    list_filter = ("country", "state")
    readonly_fields = ("slug",)


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("name", "site", "vendor", "model", "zabbix_hostid")
    search_fields = ("name", "vendor", "model", "zabbix_hostid")
    list_filter = ("site", "vendor")
    raw_id_fields = ("site",)


@admin.register(Port)
class PortAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = (
        "name",
        "device",
        "device_site",
        "zabbix_item_key",
        "notes",
    )
    search_fields = (
        "name",
        "zabbix_item_key",
        "zabbix_item_id_traffic_in",
        "zabbix_item_id_traffic_out",
        "notes",
        "device__name",
        "device__site__display_name",
    )
    list_filter = (
        ("device", admin.RelatedOnlyFieldListFilter),
        SiteListFilter,
        HasZabbixItemKeyFilter,
        TrafficItemsFilter,
        OpticalPowerFilter,
        HasNotesFilter,
    )
    list_select_related = ("device", "device__site")
    raw_id_fields = ("device",)

    @admin.display(description="Site", ordering="device__site__display_name")
    def device_site(self, obj: Port) -> str:
        site = getattr(obj.device, "site", None)
        return str(site) if site else ""


@admin.register(FiberCable)
class FiberCableAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = (
        "name",
        "origin_port",
        "destination_port",
        "status",
        "length_km",
        "last_status_update",
    )
    search_fields = ("name",)
    list_filter = ("status",)
    raw_id_fields = ("origin_port", "destination_port")
    readonly_fields = ("last_status_update",)


@admin.register(FiberEvent)
class FiberEventAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = (
        "fiber",
        "timestamp",
        "previous_status",
        "new_status",
        "detected_reason",
    )
    search_fields = ("fiber__name", "detected_reason")
    list_filter = ("new_status", "timestamp")
    raw_id_fields = ("fiber",)
    readonly_fields = ("timestamp",)
