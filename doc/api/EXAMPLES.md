# API Examples - MapsProveFiber

**Version**: v2.0.0  
**Last Updated**: 2025-11-10  
**Target Audience**: Developers, Integrators

---

## 📖 Overview

This guide provides practical examples for common API operations in MapsProveFiber. Examples are provided in Python, JavaScript, cURL, and PowerShell.

---

## 🚀 Getting Started

### Setup

**Python:**
```python
import requests
import os

BASE_URL = "http://localhost:8000"
TOKEN = os.getenv('MAPSFIBER_TOKEN')
HEADERS = {
    "Authorization": f"Token {TOKEN}",
    "Content-Type": "application/json"
}
```

**JavaScript:**
```javascript
const BASE_URL = 'http://localhost:8000';
const TOKEN = process.env.MAPSFIBER_TOKEN;
const HEADERS = {
  'Authorization': `Token ${TOKEN}`,
  'Content-Type': 'application/json'
};
```

**cURL:**
```bash
export BASE_URL="http://localhost:8000"
export TOKEN="your-token-here"
```

---

## 📍 Sites Management

### List All Sites

**Python:**
```python
response = requests.get(f"{BASE_URL}/api/v1/inventory/sites/", headers=HEADERS)
sites = response.json()

for site in sites:
    print(f"{site['id']}: {site['name']} ({site['latitude']}, {site['longitude']})")
```

**JavaScript:**
```javascript
const response = await fetch(`${BASE_URL}/api/v1/inventory/sites/`, {
  headers: HEADERS
});
const sites = await response.json();

sites.forEach(site => {
  console.log(`${site.id}: ${site.name} (${site.latitude}, ${site.longitude})`);
});
```

**cURL:**
```bash
curl -H "Authorization: Token $TOKEN" \
     $BASE_URL/api/v1/inventory/sites/
```

**PowerShell:**
```powershell
$headers = @{
    "Authorization" = "Token $env:MAPSFIBER_TOKEN"
}
$response = Invoke-RestMethod -Uri "$env:BASE_URL/api/v1/inventory/sites/" -Headers $headers
$response | Format-Table id, name, latitude, longitude
```

### Create Site

**Python:**
```python
data = {
    "name": "New HQ",
    "latitude": -23.5505,
    "longitude": -46.6333,
    "address": "São Paulo, Brazil",
    "is_active": True
}

response = requests.post(
    f"{BASE_URL}/api/v1/inventory/sites/",
    headers=HEADERS,
    json=data
)

if response.status_code == 201:
    site = response.json()
    print(f"Created site ID: {site['id']}")
else:
    print(f"Error: {response.json()}")
```

**JavaScript:**
```javascript
const data = {
  name: 'New HQ',
  latitude: -23.5505,
  longitude: -46.6333,
  address: 'São Paulo, Brazil',
  is_active: true
};

const response = await fetch(`${BASE_URL}/api/v1/inventory/sites/`, {
  method: 'POST',
  headers: HEADERS,
  body: JSON.stringify(data)
});

const site = await response.json();
console.log(`Created site ID: ${site.id}`);
```

**cURL:**
```bash
curl -X POST \
  -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"New HQ","latitude":-23.5505,"longitude":-46.6333}' \
  $BASE_URL/api/v1/inventory/sites/
```

### Get Site Details

**Python:**
```python
site_id = 1
response = requests.get(f"{BASE_URL}/api/v1/inventory/sites/{site_id}/", headers=HEADERS)
site = response.json()

print(f"Site: {site['name']}")
print(f"Location: ({site['latitude']}, {site['longitude']})")
print(f"Devices: {len(site.get('devices', []))}")
```

### Update Site

**Python:**
```python
site_id = 1
data = {
    "name": "Updated HQ Name",
    "is_active": True
}

response = requests.patch(
    f"{BASE_URL}/api/v1/inventory/sites/{site_id}/",
    headers=HEADERS,
    json=data
)

if response.status_code == 200:
    print("Site updated successfully")
```

### Delete Site

**Python:**
```python
site_id = 1
response = requests.delete(
    f"{BASE_URL}/api/v1/inventory/sites/{site_id}/",
    headers=HEADERS
)

if response.status_code == 204:
    print("Site deleted successfully")
```

---

## 🖥️ Devices Management

### List Devices

**Python:**
```python
response = requests.get(f"{BASE_URL}/api/v1/inventory/devices/", headers=HEADERS)
devices = response.json()

for device in devices:
    print(f"{device['id']}: {device['name']} ({device['device_type']}) - {device['ip_address']}")
```

### Get Device with Ports

**Python:**
```python
device_id = 1
response = requests.get(
    f"{BASE_URL}/api/v1/inventory/devices/{device_id}/",
    headers=HEADERS
)
device = response.json()

print(f"Device: {device['name']}")
print(f"Type: {device['device_type']}")
print(f"Ports: {len(device.get('ports', []))}")

for port in device.get('ports', []):
    print(f"  - Port {port['port_number']}: {port['port_type']}")
```

### Import Device from Zabbix

**Python:**
```python
data = {
    "zabbix_host_id": "10084",
    "site_id": 1,
    "create_ports": True
}

response = requests.post(
    f"{BASE_URL}/api/v1/inventory/devices/add-from-zabbix/",
    headers=HEADERS,
    json=data
)

if response.status_code == 201:
    device = response.json()
    print(f"Imported device: {device['name']}")
    print(f"Created {len(device.get('ports', []))} ports")
```

---

## 🔌 Ports & Optical Data

### Get Port Optical Data

**Python:**
```python
port_id = 1
response = requests.get(
    f"{BASE_URL}/api/v1/inventory/ports/{port_id}/optical/",
    headers=HEADERS
)
optical_data = response.json()

print(f"RX Power: {optical_data['rx_power']} dBm")
print(f"TX Power: {optical_data['tx_power']} dBm")
print(f"Temperature: {optical_data['temperature']} °C")
```

### Get Port Traffic Stats

**Python:**
```python
port_id = 1
params = {
    "time_from": "2025-11-09T00:00:00Z",
    "time_till": "2025-11-10T00:00:00Z"
}

response = requests.get(
    f"{BASE_URL}/api/v1/inventory/ports/{port_id}/traffic/",
    headers=HEADERS,
    params=params
)
traffic_data = response.json()

for datapoint in traffic_data:
    print(f"{datapoint['timestamp']}: RX={datapoint['rx_bytes']}, TX={datapoint['tx_bytes']}")
```

---

## 🔗 Fiber Cables Management

### List Fiber Cables

**Python:**
```python
response = requests.get(f"{BASE_URL}/api/v1/inventory/fibers/", headers=HEADERS)
fibers = response.json()

for fiber in fibers:
    print(f"{fiber['id']}: {fiber['port_a']} <-> {fiber['port_b']} (Length: {fiber['length']}m)")
```

### Create Fiber Cable

**Python:**
```python
data = {
    "port_a_id": 1,
    "port_b_id": 2,
    "fiber_type": "single_mode",
    "length": 5000,  # meters
    "attenuation": 0.25,  # dB/km
    "wavelength": 1550  # nm
}

response = requests.post(
    f"{BASE_URL}/api/v1/inventory/fibers/manual-create/",
    headers=HEADERS,
    json=data
)

if response.status_code == 201:
    fiber = response.json()
    print(f"Created fiber cable ID: {fiber['id']}")
```

### Get Fiber Live Status

**Python:**
```python
fiber_id = 1
response = requests.get(
    f"{BASE_URL}/api/v1/inventory/fibers/{fiber_id}/live-status/",
    headers=HEADERS
)
status = response.json()

print(f"Status: {status['operational_status']}")
print(f"Power Loss: {status['power_loss']} dB")
print(f"Last Update: {status['last_update']}")
```

### Update Fiber Operational Status

**Python:**
```python
fiber_id = 1
data = {
    "status": "up"  # or "down", "maintenance"
}

response = requests.put(
    f"{BASE_URL}/api/v1/inventory/fibers/{fiber_id}/oper-status/",
    headers=HEADERS,
    json=data
)

if response.status_code == 200:
    print("Status updated successfully")
```

### Import Fibers from KML

**Python:**
```python
with open('fiber_routes.kml', 'rb') as f:
    files = {'file': ('fiber_routes.kml', f, 'application/vnd.google-earth.kml+xml')}
    
    response = requests.post(
        f"{BASE_URL}/api/v1/inventory/fibers/import-kml/",
        headers={"Authorization": f"Token {TOKEN}"},  # Don't set Content-Type for multipart
        files=files
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"Imported {result['created']} fiber cables")
        print(f"Updated {result['updated']} existing cables")
```

---

## 🗺️ Routes Management

### Trigger Route Build

**Python:**
```python
route_id = 1
data = {
    "route_id": route_id,
    "force_rebuild": False
}

response = requests.post(
    f"{BASE_URL}/api/v1/inventory/routes/tasks/build/",
    headers=HEADERS,
    json=data
)

if response.status_code == 202:
    task = response.json()
    task_id = task['task_id']
    print(f"Route build started. Task ID: {task_id}")
```

### Check Task Status

**Python:**
```python
task_id = "abc-123-def-456"
response = requests.get(
    f"{BASE_URL}/api/v1/inventory/routes/tasks/status/{task_id}/",
    headers=HEADERS
)
status = response.json()

print(f"State: {status['state']}")
print(f"Progress: {status.get('progress', 0)}%")

if status['state'] == 'SUCCESS':
    result = status['result']
    print(f"Total Loss: {result['total_loss']} dB")
    print(f"Segments: {result['segment_count']}")
```

### Batch Build Routes

**Python:**
```python
data = {
    "route_ids": [1, 2, 3, 4, 5],
    "force_rebuild": False
}

response = requests.post(
    f"{BASE_URL}/api/v1/inventory/routes/tasks/batch/",
    headers=HEADERS,
    json=data
)

if response.status_code == 202:
    result = response.json()
    print(f"Started {len(result['tasks'])} route build tasks")
    for task in result['tasks']:
        print(f"  Route {task['route_id']}: Task {task['task_id']}")
```

### Import Route from KML

**Python:**
```python
with open('route.kml', 'rb') as f:
    files = {'file': ('route.kml', f, 'application/vnd.google-earth.kml+xml')}
    data = {
        'name': 'Main Fiber Route',
        'description': 'Primary backbone route'
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/inventory/routes/tasks/import/",
        headers={"Authorization": f"Token {TOKEN}"},
        files=files,
        data=data
    )
    
    if response.status_code == 201:
        route = response.json()
        print(f"Created route ID: {route['id']}")
```

---

## 📊 Monitoring & Dashboard

### Get Dashboard Snapshot

**Python:**
```python
response = requests.get(
    f"{BASE_URL}/api/v1/monitoring/dashboard/snapshot/",
    headers=HEADERS
)
dashboard = response.json()

print(f"Total Hosts: {dashboard['total_hosts']}")
print(f"Online: {dashboard['hosts_online']}")
print(f"Offline: {dashboard['hosts_offline']}")
print(f"Unknown: {dashboard['hosts_unknown']}")

for host in dashboard['hosts']:
    print(f"  {host['name']}: {host['status']}")
```

### Get Hosts Status

**Python:**
```python
response = requests.get(
    f"{BASE_URL}/api/v1/monitoring/hosts/status/",
    headers=HEADERS
)
hosts = response.json()

for host in hosts:
    print(f"{host['hostname']}: {host['availability']}% uptime")
    print(f"  CPU: {host['cpu_usage']}%")
    print(f"  Memory: {host['memory_usage']}%")
    print(f"  Network RX: {host['network_in']} Mbps")
```

---

## 🔍 Zabbix Integration

### Discover Zabbix Hosts

**Python:**
```python
response = requests.get(
    f"{BASE_URL}/api/v1/inventory/zabbix/discover-hosts/",
    headers=HEADERS
)
hosts = response.json()

for host in hosts:
    print(f"{host['hostid']}: {host['name']}")
    print(f"  IP: {host['interfaces'][0]['ip']}")
    print(f"  Groups: {', '.join([g['name'] for g in host['groups']])}")
```

---

## 🏥 Health Checks

### Check System Health

**Python:**
```python
response = requests.get(f"{BASE_URL}/healthz")
health = response.json()

print(f"Status: {health['status']}")
print(f"Version: {health['version']}")

for check, status in health['checks'].items():
    print(f"  {check}: {status}")
```

**PowerShell:**
```powershell
$response = Invoke-RestMethod -Uri "$env:BASE_URL/healthz"
Write-Host "Status: $($response.status)"
$response.checks | Format-Table
```

---

## 🔄 Bulk Operations

### Bulk Create Sites

**Python:**
```python
sites_data = [
    {"name": "Site A", "latitude": -23.5, "longitude": -46.6},
    {"name": "Site B", "latitude": -22.9, "longitude": -43.2},
    {"name": "Site C", "latitude": -15.8, "longitude": -47.9},
]

for site_data in sites_data:
    response = requests.post(
        f"{BASE_URL}/api/v1/inventory/sites/",
        headers=HEADERS,
        json=site_data
    )
    if response.status_code == 201:
        site = response.json()
        print(f"Created: {site['name']} (ID: {site['id']})")
```

### Bulk Import Devices

**Python:**
```python
devices_data = {
    "devices": [
        {
            "name": "OLT-01",
            "site_id": 1,
            "device_type": "OLT",
            "ip_address": "192.168.1.1"
        },
        {
            "name": "OLT-02",
            "site_id": 2,
            "device_type": "OLT",
            "ip_address": "192.168.1.2"
        }
    ],
    "create_ports": True
}

response = requests.post(
    f"{BASE_URL}/api/v1/inventory/bulk/",
    headers=HEADERS,
    json=devices_data
)

if response.status_code == 201:
    result = response.json()
    print(f"Created {result['created_count']} devices")
```

---

## 🛡️ Error Handling

### Proper Error Handling

**Python:**
```python
def create_site_safe(name, lat, lon):
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/inventory/sites/",
            headers=HEADERS,
            json={"name": name, "latitude": lat, "longitude": lon},
            timeout=10
        )
        response.raise_for_status()  # Raises HTTPError for bad status codes
        return response.json()
    
    except requests.exceptions.Timeout:
        print("Request timed out")
        return None
    
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 400:
            print(f"Validation error: {e.response.json()}")
        elif e.response.status_code == 401:
            print("Authentication failed")
        elif e.response.status_code == 403:
            print("Permission denied")
        elif e.response.status_code == 404:
            print("Resource not found")
        elif e.response.status_code >= 500:
            print("Server error")
        return None
    
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None

# Usage
site = create_site_safe("New Site", -23.5, -46.6)
if site:
    print(f"Created site: {site['id']}")
```

---

## 📚 Additional Resources

- [API Endpoints Reference](ENDPOINTS.md)
- [Authentication Guide](AUTHENTICATION.md)
- [Development Guide](../guides/DEVELOPMENT.md)
- [Troubleshooting Guide](../operations/TROUBLESHOOTING.md)

---

**Last Updated**: 2025-11-10  
**Maintainers**: API Team
