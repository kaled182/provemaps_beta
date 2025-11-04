# Fiber Routes API Specification

## Available Endpoints

### 1. List Cables
```
GET /zabbix_api/api/fibers/
```
Response example:
```json
{
  "cables": [
    {
      "id": 1,
      "name": "Cable SP-RJ",
      "status": "up",
      "length_km": 435.5
    }
  ]
}
```

### 2. Cable Details
```
GET /zabbix_api/api/fiber/<cable_id>/
```
Response example:
```json
{
  "id": 1,
  "name": "Cable SP-RJ",
  "status": "up",
  "length_km": 435.5,
  "origin": {
    "site": "Site A",
    "lat": -23.5505,
    "lng": -46.6333,
    "device": "Switch-A",
    "device_id": 1,
    "port": "eth0/1",
    "port_id": 1
  },
  "destination": {
    "site": "Site B",
    "lat": -22.9068,
    "lng": -43.1729,
    "device": "Switch-B",
    "device_id": 2,
    "port": "eth0/1",
    "port_id": 2
  },
  "path": [
    {"lat": -23.5505, "lng": -46.6333},
    {"lat": -23.0000, "lng": -45.0000},
    {"lat": -22.9068, "lng": -43.1729}
  ],
  "single_port": false
}
```

### 3. Update Cable Path
```
PUT /zabbix_api/api/fiber/<cable_id>/
Content-Type: application/json
```
Request example:
```json
{
  "path": [
    {"lat": -23.5505, "lng": -46.6333},
    {"lat": -23.2000, "lng": -45.5000},
    {"lat": -22.9068, "lng": -43.1729}
  ]
}
```
Response example:
```json
{
  "status": "ok",
  "length_km": 450.2,
  "points": 3
}
```

### 4. Create Cable Manually
```
POST /zabbix_api/api/fibers/manual-create/
Content-Type: application/json
```
Request example:
```json
{
  "name": "New Cable",
  "origin_device_id": 1,
  "origin_port_id": 1,
  "dest_device_id": 2,
  "dest_port_id": 2,
  "path": [
    {"lat": -23.5505, "lng": -46.6333},
    {"lat": -22.9068, "lng": -43.1729}
  ],
  "single_port": false
}
```
Response example:
```json
{
  "fiber_id": 3,
  "name": "New Cable",
  "points": 2,
  "length_km": 435.5,
  "origin_port": {...},
  "destination_port": {...}
}
```

### 5. Delete Cable
```
DELETE /zabbix_api/api/fiber/<cable_id>/
```
Response: HTTP 204 No Content

### 6. Import Cable From KML
```
POST /zabbix_api/api/fibers/import-kml/
Content-Type: multipart/form-data
```
Form fields:
- `name`: cable label
- `origin_device_id`: source device identifier
- `origin_port_id`: source port identifier
- `dest_device_id`: destination device identifier
- `dest_port_id`: destination port identifier
- `single_port`: "true" or "false"
- `kml_file`: uploaded KML file

Response example:
```json
{
  "fiber_id": 4,
  "name": "Imported Cable",
  "points": 50,
  "path_coordinates": [...]
}
```

---

## Working With The Path Field

### API Contract
- Requests must use the `"path"` key
- Responses also expose the `"path"` key

### Storage Model
- Database column is `path_coordinates` (JSONField)

### Internal Conversion
The backend maps between the API shape and the stored JSON:
- `inventory_fibers.py` line 158 reads `path = body.get("path")`
- `usecases/fibers.py` line 288 assigns `cable.path_coordinates = sanitized`
- `usecases/fibers.py` line 257 returns `"path": cable.path_coordinates`

Conclusion: frontend JavaScript correctly uses the `path` attribute.

---

## Backend Validation Rules

### Path
- Requires at least two points unless `allow_empty=True`
- Each point must include `lat` and `lng`
- Latitude range: -90.0 to 90.0
- Longitude range: -180.0 to 180.0

### Name
- Mandatory field
- Must be unique (case-insensitive)
- Cannot be blank after trimming whitespace

### Ports
- Both origin and destination must exist
- Ports must belong to the provided devices
- If `single_port=false`, origin and destination must differ
- If `single_port=true`, origin and destination must be the same port

### Single-Port Mode
- Allows monitoring loops that use a single physical port
- Adds the marker `notes = "single-port-monitoring"`

---

## Test Coverage Snapshot

Location: `routes_builder/tests/test_fiber_routes_full.py`

Planned suite of 18 tests covers:
- Listing cables with and without data
- Cable detail responses for existing and missing records
- Manual creation flows
- Path updates
- Metadata edits
- Deletion paths
- Map visualization endpoints
- Model validation rules
- Edge cases (single point, long paths, empty path)
- Permission checks for authenticated and anonymous users

Current status: 4 of 18 tests passing (22%) due to fixtures with incorrect model fields.
