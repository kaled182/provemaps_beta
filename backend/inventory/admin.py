"""
Django admin configuration for inventory models.
"""
from django.contrib import admin

from .models import Device, FiberCable, FiberEvent, Port, Site


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "latitude", "longitude")
    search_fields = ("name", "city")
    list_filter = ("city",)


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("name", "site", "vendor", "model", "zabbix_hostid")
    search_fields = ("name", "vendor", "model", "zabbix_hostid")
    list_filter = ("site", "vendor")
    raw_id_fields = ("site",)


@admin.register(Port)
class PortAdmin(admin.ModelAdmin):
    list_display = ("name", "device", "zabbix_item_key", "notes")
    search_fields = ("name", "zabbix_item_key", "notes")
    list_filter = ("device__site",)
    raw_id_fields = ("device",)


@admin.register(FiberCable)
class FiberCableAdmin(admin.ModelAdmin):
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
class FiberEventAdmin(admin.ModelAdmin):
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
