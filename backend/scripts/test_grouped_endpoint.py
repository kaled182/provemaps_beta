#!/usr/bin/env python
"""
Test script to verify the grouped hosts endpoint is working with reverse lookup.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings.dev")
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User
from inventory.api.zabbix_lookup import lookup_hosts_grouped


def main():
    # Create a fake request with authenticated user
    factory = RequestFactory()
    request = factory.get('/api/v1/inventory/zabbix/lookup/hosts/grouped/')
    
    # Get or create admin user for testing
    user, _ = User.objects.get_or_create(
        username='admin',
        defaults={'is_staff': True, 'is_superuser': True}
    )
    request.user = user
    
    print("🔍 Testing lookup_hosts_grouped endpoint with reverse lookup...")
    print("=" * 80)
    
    # Call the endpoint
    response = lookup_hosts_grouped(request)
    
    if response.status_code != 200:
        print(f"❌ ERROR: Status {response.status_code}")
        print(response.content.decode())
        return 1
    
    # Parse JSON response
    import json
    data = json.loads(response.content.decode())
    
    groups = data.get("data", [])
    count = data.get("count", 0)
    
    print(f"✅ SUCCESS: Received {count} groups\n")
    
    # Display summary
    total_hosts = 0
    for group in groups:
        group_name = group.get("name", "Unknown")
        group_id = group.get("zabbix_group_id", "N/A")
        hosts = group.get("hosts", [])
        num_hosts = len(hosts)
        total_hosts += num_hosts
        
        print(f"📂 {group_name} (ID: {group_id})")
        print(f"   └─ {num_hosts} host(s)")
        
        # Show first 3 hosts as sample
        for i, host in enumerate(hosts[:3]):
            host_name = host.get("name", "Unknown")
            host_ip = host.get("ip", "N/A")
            host_groups = host.get("groups", [])
            is_imported = "✓" if host.get("is_imported") else "✗"
            print(f"      {i+1}. [{is_imported}] {host_name} ({host_ip})")
            if host_groups:
                print(f"         └─ Groups: {', '.join(host_groups[:3])}")
        
        if num_hosts > 3:
            print(f"      ... and {num_hosts - 3} more")
        print()
    
    print("=" * 80)
    print(f"📊 SUMMARY:")
    print(f"   Total groups: {count}")
    print(f"   Total hosts: {total_hosts}")
    
    # Check if hosts are properly distributed
    sem_grupo = next((g for g in groups if g.get("name") == "Sem Grupo Definido"), None)
    if sem_grupo:
        print(f"   ⚠️  Hosts without groups: {len(sem_grupo.get('hosts', []))}")
    
    # Check if reverse lookup worked
    hosts_with_multiple_groups = 0
    for group in groups:
        for host in group.get("hosts", []):
            if len(host.get("groups", [])) > 1:
                hosts_with_multiple_groups += 1
    
    if hosts_with_multiple_groups > 0:
        print(f"   ✅ Reverse lookup working: {hosts_with_multiple_groups} hosts belong to multiple groups")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
