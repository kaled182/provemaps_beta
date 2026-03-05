#!/usr/bin/env python3
"""Utility script to list Devices with non-empty zabbix_hostid.

Run inside project container: `python backend/scripts/list_zabbix_devices.py`
"""
import os
import json


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings.dev")
    import django

    django.setup()

    from inventory.models import Device
    qs = Device.objects.exclude(zabbix_hostid__exact="").values("id", "name", "zabbix_hostid")[:50]
    cnt = Device.objects.exclude(zabbix_hostid__exact="").count()

    total = Device.objects.count()
    without_cnt = Device.objects.filter(zabbix_hostid__exact="").count()
    without_samples = list(Device.objects.filter(zabbix_hostid__exact="").values("id", "name")[:10])

    out = {
        "total_devices": total,
        "populated_count": cnt,
        "without_zabbix_count": without_cnt,
        "samples": list(qs),
        "without_samples": without_samples,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
