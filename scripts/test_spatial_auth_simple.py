#!/usr/bin/env python
"""Simple test to verify spatial API returns 401 without auth."""

import requests

BASE_URL = "http://localhost:8000"
BBOX = "-48,-16,-47.5,-15.5"

# Test without auth
url = f"{BASE_URL}/api/v1/inventory/segments/?bbox={BBOX}"
resp = requests.get(url)

print(f"Status: {resp.status_code}")
print(f"Response: {resp.json()}")

if resp.status_code == 401:
    print("\n✅ Authentication properly enforced on spatial endpoint")
    exit(0)
else:
    print(f"\n❌ Expected 401, got {resp.status_code}")
    exit(1)
