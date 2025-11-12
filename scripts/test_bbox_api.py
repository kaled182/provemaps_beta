#!/usr/bin/env python
import requests

r = requests.get(
    'http://localhost:8000/api/v1/inventory/segments/?bbox=-48,-16,-47.5,-15.5',
    auth=('testuser', 'testpass123')
)

print(f'Status: {r.status_code}')
print(f'Content-Type: {r.headers.get("Content-Type")}')

if r.status_code == 200:
    data = r.json()
    print(f'Count: {data.get("count")}')
    print(f'BBox: {data.get("bbox")}')
    print(f'Segments: {len(data.get("segments", []))}')
    if data.get("segments"):
        print(f'First segment ID: {data["segments"][0].get("id")}')
else:
    print(f'Error: {r.text[:200]}')
