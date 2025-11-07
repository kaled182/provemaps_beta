# 🔌 API Documentation

Complete REST API reference for MapsProveFiber v2.0.0.

---

## 📚 API Documents

| Document | Description | Status | Audience |
|----------|-------------|--------|----------|
| **[ENDPOINTS.md](ENDPOINTS.md)** | ✅ **Complete endpoint reference** (updated 2025-11-07) | Ready | All developers |
| **[AUTHENTICATION.md](AUTHENTICATION.md)** | Auth, permissions, RBAC | Placeholder | Backend, security |
| **[EXAMPLES.md](EXAMPLES.md)** | Usage examples (cURL, Python, JS) | Placeholder | Frontend, integration |

### Recent Updates (2025-11-07)
- ✅ **ENDPOINTS.md** completely rewritten with:
  - All inventory API endpoints (sites, devices, ports, fibers, routes)
  - Monitoring API (hosts status, dashboard snapshot)
  - Health checks and Prometheus metrics
  - Diagnostic endpoints (testing only)
  - Maps View and Setup App endpoints
  - Request/response examples for major endpoints

---

## 🎯 Quick Start

### Base URL

**Development**: `http://localhost:8000`  
**Production**: `https://your-domain.com`

### Authentication

```bash
# Get token (if using token auth)
curl -X POST http://localhost:8000/api/token/ \
  -d "username=admin&password=yourpassword"

# Use token in requests
curl -H "Authorization: Token YOUR_TOKEN" \
  http://localhost:8000/api/v1/inventory/sites/
```

See [AUTHENTICATION.md](AUTHENTICATION.md) for details.

---

## 🗺️ API Structure

### v1 Endpoints

All v2.0.0 endpoints are under `/api/v1/`:

```
/api/v1/
├── inventory/
│   ├── sites/              # GET, POST, PUT, DELETE
│   ├── devices/            # GET, POST, PUT, DELETE
│   ├── ports/              # GET, POST, PUT, DELETE
│   └── routes/             # GET, POST, PUT, DELETE
├── monitoring/
│   ├── status/             # GET (combined inventory + Zabbix)
│   └── health/             # GET (system health)
└── maps/
    └── dashboard/          # GET (dashboard data)
```

See [ENDPOINTS.md](ENDPOINTS.md) for complete reference.

---

## 📖 Common Operations

### List Sites

```bash
GET /api/v1/inventory/sites/
```

**Response**:
```json
{
  "count": 42,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Site A",
      "latitude": -23.5505,
      "longitude": -46.6333,
      "created_at": "2025-01-01T00:00:00Z"
    }
  ]
}
```

---

### Get Site Details

```bash
GET /api/v1/inventory/sites/{id}/
```

**Response**:
```json
{
  "id": 1,
  "name": "Site A",
  "latitude": -23.5505,
  "longitude": -46.6333,
  "devices": [
    {"id": 1, "name": "Device 1", "type": "OLT"}
  ],
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-07T00:00:00Z"
}
```

---

### Create Site

```bash
POST /api/v1/inventory/sites/
Content-Type: application/json

{
  "name": "New Site",
  "latitude": -23.5505,
  "longitude": -46.6333
}
```

**Response** (201 Created):
```json
{
  "id": 43,
  "name": "New Site",
  "latitude": -23.5505,
  "longitude": -46.6333,
  "created_at": "2025-01-07T10:30:00Z"
}
```

---

### Update Site

```bash
PUT /api/v1/inventory/sites/43/
Content-Type: application/json

{
  "name": "Updated Site Name",
  "latitude": -23.5505,
  "longitude": -46.6333
}
```

---

### Delete Site

```bash
DELETE /api/v1/inventory/sites/43/
```

**Response** (204 No Content)

---

## 🔍 Filtering & Pagination

### Filtering

```bash
# Filter sites by name
GET /api/v1/inventory/sites/?name__icontains=central

# Filter devices by type
GET /api/v1/inventory/devices/?type=OLT
```

### Pagination

```bash
# Page 1 (default: 20 items)
GET /api/v1/inventory/sites/?page=1

# Custom page size
GET /api/v1/inventory/sites/?page=1&page_size=50
```

---

## 📊 Monitoring Endpoints

### Get Combined Status

```bash
GET /api/v1/monitoring/status/
```

**Response**:
```json
{
  "sites": [
    {
      "id": 1,
      "name": "Site A",
      "inventory_status": "active",
      "zabbix_status": "ok",
      "devices": [
        {
          "id": 1,
          "name": "Device 1",
          "zabbix_status": "ok",
          "last_seen": "2025-01-07T10:00:00Z"
        }
      ]
    }
  ],
  "summary": {
    "total_sites": 42,
    "healthy_sites": 40,
    "warning_sites": 2,
    "error_sites": 0
  }
}
```

---

### Health Checks

```bash
# Full health check
GET /healthz/

# Readiness probe
GET /ready/

# Liveness probe
GET /live/
```

See [../guides/OBSERVABILITY.md](../guides/OBSERVABILITY.md) for health check details.

---

## 🚨 Error Handling

### Standard Error Response

```json
{
  "error": "ValidationError",
  "message": "Invalid latitude value",
  "details": {
    "latitude": ["Ensure this value is less than or equal to 90."]
  }
}
```

### HTTP Status Codes

| Code | Meaning | When |
|------|---------|------|
| `200` | OK | Successful GET/PUT |
| `201` | Created | Successful POST |
| `204` | No Content | Successful DELETE |
| `400` | Bad Request | Validation error |
| `401` | Unauthorized | Missing/invalid auth |
| `403` | Forbidden | No permission |
| `404` | Not Found | Resource doesn't exist |
| `500` | Internal Server Error | Server error |
| `503` | Service Unavailable | Dependency down |

---

## 🔐 Authentication & Permissions

### Authentication Methods

1. **Session Authentication** (Django default)
   - Used by web UI
   - CSRF token required

2. **Token Authentication** (optional)
   - REST API clients
   - `Authorization: Token YOUR_TOKEN`

3. **Basic Authentication** (development only)
   - `Authorization: Basic base64(username:password)`

See [AUTHENTICATION.md](AUTHENTICATION.md) for setup.

---

### Permissions

| Endpoint | Required Permission |
|----------|---------------------|
| `GET /api/v1/inventory/*` | `view_site`, `view_device`, etc. |
| `POST /api/v1/inventory/*` | `add_site`, `add_device`, etc. |
| `PUT /api/v1/inventory/*` | `change_site`, `change_device`, etc. |
| `DELETE /api/v1/inventory/*` | `delete_site`, `delete_device`, etc. |

---

## 💡 Usage Examples

### Python (requests)

```python
import requests

BASE_URL = "http://localhost:8000"
TOKEN = "your-token-here"

headers = {
    "Authorization": f"Token {TOKEN}",
    "Content-Type": "application/json"
}

# List sites
response = requests.get(f"{BASE_URL}/api/v1/inventory/sites/", headers=headers)
sites = response.json()

# Create site
new_site = {
    "name": "New Site",
    "latitude": -23.5505,
    "longitude": -46.6333
}
response = requests.post(
    f"{BASE_URL}/api/v1/inventory/sites/",
    json=new_site,
    headers=headers
)
```

---

### JavaScript (fetch)

```javascript
const BASE_URL = "http://localhost:8000";
const TOKEN = "your-token-here";

// List sites
fetch(`${BASE_URL}/api/v1/inventory/sites/`, {
  headers: {
    "Authorization": `Token ${TOKEN}`,
    "Content-Type": "application/json"
  }
})
  .then(res => res.json())
  .then(data => console.log(data));

// Create site
fetch(`${BASE_URL}/api/v1/inventory/sites/`, {
  method: "POST",
  headers: {
    "Authorization": `Token ${TOKEN}`,
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    name: "New Site",
    latitude: -23.5505,
    longitude: -46.6333
  })
})
  .then(res => res.json())
  .then(data => console.log(data));
```

See [EXAMPLES.md](EXAMPLES.md) for more examples.

---

## 🔄 Migrating from v1.x

### Removed Endpoints (v2.0.0)

❌ All `/zabbix_api/*` endpoints removed.

**Migration map**:

| Old Endpoint (v1.x) | New Endpoint (v2.0.0) |
|---------------------|------------------------|
| `GET /zabbix_api/sites/` | `GET /api/v1/inventory/sites/` |
| `GET /zabbix_api/devices/` | `GET /api/v1/inventory/devices/` |
| `GET /zabbix_api/status/` | `GET /api/v1/monitoring/status/` |

See [../releases/v2.0.0/BREAKING_CHANGES.md](../releases/v2.0.0/BREAKING_CHANGES.md) for complete migration guide.

---

## 📖 Related Documentation

- **[Architecture](../architecture/)** — System design
- **[Development Guide](../guides/DEVELOPMENT.md)** — Local setup
- **[Operations Guide](../operations/)** — Deployment
- **[Breaking Changes](../releases/v2.0.0/BREAKING_CHANGES.md)** — v2.0.0 migration

---

**Need help?** Check [EXAMPLES.md](EXAMPLES.md) or open an issue.
