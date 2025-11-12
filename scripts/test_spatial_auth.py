#!/usr/bin/env python
"""Test spatial API authentication after re-enabling decorators."""

import sys
import requests

BASE_URL = "http://localhost:8000"
BBOX = "-48,-16,-47.5,-15.5"

def test_without_auth():
    """Should return 401."""
    url = f"{BASE_URL}/api/v1/inventory/segments/?bbox={BBOX}"
    resp = requests.get(url)
    print(f"❌ Without auth: {resp.status_code}")
    if resp.status_code == 401:
        print(f"   ✅ Correctly rejected: {resp.json()}")
        return True
    else:
        print(f"   ❌ Expected 401, got {resp.status_code}: {resp.text[:200]}")
        return False

def test_with_session():
    """Login via session and test."""
    session = requests.Session()
    
    # Login
    login_url = f"{BASE_URL}/login/"
    csrf_resp = session.get(login_url)
    csrftoken = session.cookies.get('csrftoken', '')
    
    login_data = {
        'username': 'admin',
        'password': 'admin',
        'csrfmiddlewaretoken': csrftoken
    }
    login_resp = session.post(login_url, data=login_data, headers={'Referer': login_url})
    
    if login_resp.status_code not in [200, 302]:
        print(f"❌ Login failed: {login_resp.status_code}")
        return False
    
    # Test API
    url = f"{BASE_URL}/api/v1/inventory/segments/?bbox={BBOX}"
    resp = session.get(url)
    print(f"🔐 With session auth: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"   ✅ Success: returned {data.get('count', 0)} segments")
        return True
    else:
        print(f"   ❌ Expected 200, got {resp.status_code}: {resp.text[:200]}")
        return False

if __name__ == "__main__":
    print("Testing spatial API authentication...\n")
    
    results = []
    results.append(test_without_auth())
    print()
    results.append(test_with_session())
    
    print(f"\n{'='*60}")
    if all(results):
        print("✅ All authentication tests passed")
        sys.exit(0)
    else:
        print("❌ Some authentication tests failed")
        sys.exit(1)
