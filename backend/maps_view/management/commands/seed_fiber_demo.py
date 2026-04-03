from django.core.management.base import BaseCommand

from maps_view.models import Device, FiberCable, FiberEvent, Port, Site

# Approximate coordinates for demo entities
SITES_DATA = [
    {
        "name": "Goiania-POP",
        "city": "Goiania",
        "latitude": -16.6869,
        "longitude": -49.2648,
        "description": "Primary site in Goiania.",
    },
    {
        "name": "Aparecida-POP",
        "city": "Aparecida de Goiania",
        "latitude": -16.8198,
        "longitude": -49.2473,
        "description": "Site covering Aparecida de Goiania.",
    },
    {
        "name": "Brasilia-POP",
        "city": "Brasilia",
        "latitude": -15.793889,
        "longitude": -47.882778,
        "description": "Brasilia backbone link.",
    },
    {
        "name": "Anapolis-POP",
        "city": "Anapolis",
        "latitude": -16.3281,
        "longitude": -48.9530,
        "description": "Regional presence in Anapolis.",
    },
]

DEVICES_DATA = [
    # (site_name, device_name, vendor, model, zabbix_hostid)
    ("Goiania-POP", "SW-GYN-01", "Cisco", "C9300", "10101"),
    ("Goiania-POP", "SW-GYN-02", "Cisco", "C9300", "10102"),
    ("Aparecida-POP", "SW-APC-01", "Huawei", "S5720", "10201"),
    ("Brasilia-POP", "RTR-BSB-01", "Juniper", "MX240", "10301"),
    ("Anapolis-POP", "SW-ANA-01", "Cisco", "C9200", "10401"),
]

# (device_name, port_name, zabbix_item_key)
PORTS_DATA = [
    ("SW-GYN-01", "Gi1/0/10", "net.if.status[Gi1/0/10]"),
    ("SW-GYN-02", "Gi1/0/5", "net.if.status[Gi1/0/5]"),
    ("SW-APC-01", "GigabitEthernet0/0/5", "net.if.status[GigabitEthernet0/0/5]"),
    ("RTR-BSB-01", "xe-0/0/0", "net.if.status[xe-0/0/0]"),
    ("RTR-BSB-01", "xe-0/0/1", "net.if.status[xe-0/0/1]"),
    ("SW-ANA-01", "Gi0/0/1", "net.if.status[Gi0/0/1]"),
]

FIBERS_DATA = [
    # name, origin_device, origin_port, dest_device, dest_port, length_km, path(optional)
    (
        "BACKBONE-GYN-APC",
        "SW-GYN-01",
        "Gi1/0/10",
        "SW-APC-01",
        "GigabitEthernet0/0/5",
        18.5,
        [
            {"lat": -16.6869, "lng": -49.2648},  # Goiania
            {"lat": -16.7300, "lng": -49.2600},
            {"lat": -16.7800, "lng": -49.2550},
            {"lat": -16.8198, "lng": -49.2473},  # Aparecida
        ],
    ),
    (
        "BACKBONE-GYN-BSB",
        "SW-GYN-02",
        "Gi1/0/5",
        "RTR-BSB-01",
        "xe-0/0/0",
        200.0,
        [
            {"lat": -16.6869, "lng": -49.2648},  # Goiania
            {"lat": -16.2, "lng": -48.5},
            {"lat": -15.9, "lng": -48.2},
            {"lat": -15.793889, "lng": -47.882778},  # Brasilia
        ],
    ),
    (
        "BACKBONE-GYN-ANA",
        "SW-GYN-01",
        "Gi1/0/10",
        "SW-ANA-01",
        "Gi0/0/1",
        55.3,
        [
            {"lat": -16.6869, "lng": -49.2648},
            {"lat": -16.5, "lng": -49.0},
            {"lat": -16.4, "lng": -48.98},
            {"lat": -16.3281, "lng": -48.9530},
        ],
    ),
    (
        "LONGHAUL-BSB-ANA",
        "RTR-BSB-01",
        "xe-0/0/1",
        "SW-ANA-01",
        "Gi0/0/1",
        120.0,
        [
            {"lat": -15.793889, "lng": -47.882778},
            {"lat": -16.05, "lng": -48.3},
            {"lat": -16.2, "lng": -48.6},
            {"lat": -16.3281, "lng": -48.9530},
        ],
    ),
]


class Command(BaseCommand):
    help = "Seed demo data for sites, devices, ports and fibers."

    def handle(self, *args, **options):
        created_counts = {"sites": 0, "devices": 0, "ports": 0, "fibers": 0}

        site_map = {}
        for site_data in SITES_DATA:
            site, created = Site.objects.get_or_create(
                name=site_data["name"],
                defaults={
                    "city": site_data.get("city", ""),
                    "latitude": site_data.get("latitude"),
                    "longitude": site_data.get("longitude"),
                    "description": site_data.get("description", ""),
                },
            )
            site_map[site.name] = site
            if created:
                created_counts["sites"] += 1

        device_map = {}
        for site_name, dev_name, vendor, model, hostid in DEVICES_DATA:
            site = site_map[site_name]
            device, created = Device.objects.get_or_create(
                site=site,
                name=dev_name,
                defaults={"vendor": vendor, "model": model, "zabbix_hostid": hostid},
            )
            device_map[device.name] = device
            if created:
                created_counts["devices"] += 1

        port_map = {}
        for dev_name, port_name, key in PORTS_DATA:
            device = device_map[dev_name]
            port, created = Port.objects.get_or_create(
                device=device,
                name=port_name,
                defaults={"zabbix_item_key": key},
            )
            port_map[(dev_name, port_name)] = port
            if created:
                created_counts["ports"] += 1

        for name, o_dev, o_port, d_dev, d_port, length, path in FIBERS_DATA:
            origin_port = port_map[(o_dev, o_port)]
            dest_port = port_map[(d_dev, d_port)]
            fiber, created = FiberCable.objects.get_or_create(
                name=name,
                defaults={
                    "origin_port": origin_port,
                    "destination_port": dest_port,
                    "length_km": length,
                    "path_coordinates": path,
                    "status": FiberCable.STATUS_UNKNOWN,
                },
            )
            if created:
                created_counts["fibers"] += 1
                FiberEvent.objects.create(
                    fiber=fiber,
                    previous_status="",
                    new_status=fiber.status,
                    detected_reason="Seed initial",
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Seed completed: sites={sites} devices={devices} ports={ports} fibers={fibers}".format(
                    **created_counts
                )
            )
        )
