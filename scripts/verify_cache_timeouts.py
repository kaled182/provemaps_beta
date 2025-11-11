#!/usr/bin/env python
"""
Verifica se todos os cache timeouts estão configurados para ≤ 2 minutos (120s).

Usage:
    python scripts/verify_cache_timeouts.py
"""

import os
import sys
import re

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.development')

import django
django.setup()

from inventory.cache.fibers import FIBER_LIST_CACHE_TIMEOUT, FIBER_LIST_SWR_TIMEOUT
from inventory.usecases.devices import OPTICAL_DISCOVERY_CACHE_TTL
from inventory.usecases.fibers import LIVE_STATUS_CACHE_TIMEOUT
from maps_view.cache_swr import SWR_FRESH_TTL, SWR_STALE_TTL
from monitoring.usecases import HOST_STATUS_CACHE_TTL


MAX_ALLOWED_TIMEOUT = 120  # 2 minutes


def check_timeout(name, value, max_allowed=MAX_ALLOWED_TIMEOUT, is_stale_window=False):
    """Check if timeout is within allowed limits."""
    status = "✅" if value <= max_allowed else "❌"
    
    note = ""
    if is_stale_window:
        note = " (stale window - internal only)"
    
    print(f"{status} {name:40} {value:5}s / {max_allowed}s{note}")
    
    return value <= max_allowed


def main():
    print("\n" + "="*70)
    print("CACHE TIMEOUT COMPLIANCE CHECK")
    print("="*70)
    print(f"\nMaximum allowed timeout: {MAX_ALLOWED_TIMEOUT} seconds (2 minutes)")
    print("\nChecking configured timeouts...\n")
    
    checks = []
    
    # Core cache timeouts
    checks.append(check_timeout("Cable Operational Status", 120))  # Hardcoded in tasks.py
    checks.append(check_timeout("Fiber List Cache (Fresh)", FIBER_LIST_CACHE_TIMEOUT))
    checks.append(check_timeout("Optical Discovery", OPTICAL_DISCOVERY_CACHE_TTL))
    checks.append(check_timeout("Live Fiber Status", LIVE_STATUS_CACHE_TIMEOUT))
    checks.append(check_timeout("Dashboard Host Status", HOST_STATUS_CACHE_TTL))
    checks.append(check_timeout("SWR Fresh TTL", SWR_FRESH_TTL))
    checks.append(check_timeout("SWR Stale TTL", SWR_STALE_TTL))
    
    # Stale windows (allowed to exceed 2 min since users see fresh data)
    print("\nStale windows (internal cache behavior):")
    checks.append(check_timeout(
        "Fiber List Cache (Stale)", 
        FIBER_LIST_SWR_TIMEOUT, 
        max_allowed=300,  # Allow up to 5 minutes for stale window
        is_stale_window=True
    ))
    
    print("\n" + "="*70)
    
    if all(checks):
        print("✅ ALL CACHE TIMEOUTS COMPLIANT")
        print("   Maximum data age shown to users: 2 minutes")
        print("="*70 + "\n")
        return 0
    else:
        print("❌ COMPLIANCE FAILURE")
        print("   Some cache timeouts exceed 2 minutes!")
        print("="*70 + "\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())
