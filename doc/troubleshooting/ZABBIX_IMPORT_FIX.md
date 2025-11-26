# Zabbix Integration Fix - Device Import System

**Date**: 2025-11-22  
**Status**: ✅ Deployed  
**Issue**: Frontend error `ZabbixHosts.map is not a function`  

---

## Problem

The Device Import system was attempting to import devices from Zabbix but encountered a JavaScript error because:

1. The frontend expected Zabbix hosts as a flat array
2. The API endpoint returned `{data: [...], count: ...}` structure
3. The `ImportPreviewTab` component needed hosts grouped by Zabbix hostgroups

---

## Solution

### 1. New Backend Endpoint

Created `lookup_hosts_grouped()` in `backend/inventory/api/zabbix_lookup.py`:

```python
@require_GET
@login_required
def lookup_hosts_grouped(request: HttpRequest) -> JsonResponse:
    """Returns Zabbix hosts grouped by hostgroup for import preview."""
    # Fetches hosts with groups via host.get
    # Groups hosts by hostgroup ID
    # Returns structure: {data: [{zabbix_group_id, name, hosts: [...]}], count}
```

**Endpoint**: `/api/v1/inventory/zabbix/lookup/hosts/grouped/`

**Response Structure**:
```json
{
  "data": [
    {
      "zabbix_group_id": "101",
      "name": "Linux Servers",
      "hosts": [
        {
          "zabbix_id": "10084",
          "name": "Web-App-01",
          "ip": "192.168.1.10",
          "status": "online",
          "is_imported": false
        }
      ]
    }
  ],
  "count": 3
}
```

### 2. Frontend Updates

**DeviceImportManager.vue**:
- Changed API call from `/zabbix/lookup/hosts/` to `/zabbix/lookup/hosts/grouped/`
- Extracts `response.data` correctly
- Marks already imported hosts by checking IP and Zabbix ID

**ImportPreviewTab.vue**:
- Removed `mockZabbixData` (static mock data)
- Now uses real data from `props.data`
- Dynamic filtering and grouping based on actual Zabbix data

### 3. URL Configuration

Added route in `backend/inventory/urls_api.py`:

```python
path(
    "zabbix/lookup/hosts/grouped/",
    zabbix_lookup_api.lookup_hosts_grouped,
    name="zabbix-lookup-hosts-grouped",
),
```

---

## Data Flow

```
1. User navigates to Device Import → "Sincronização (Pré)" tab
2. Frontend calls: GET /api/v1/inventory/zabbix/lookup/hosts/grouped/
3. Backend:
   - Calls Zabbix API: host.get with selectGroups and selectInterfaces
   - Groups hosts by hostgroup
   - Marks primary IP from interfaces
   - Returns grouped structure
4. Frontend:
   - Receives grouped data
   - Marks already imported hosts (by IP or Zabbix ID)
   - Displays in collapsible groups
5. User selects hosts and clicks "Importar Selecionados"
6. Frontend normalizes data and calls import batch API
```

---

## Key Changes

### Backend Files Modified:
```
backend/inventory/api/zabbix_lookup.py    (+75 lines - new function)
backend/inventory/urls_api.py             (+5 lines - new route)
```

### Frontend Files Modified:
```
frontend/src/components/DeviceImport/DeviceImportManager.vue    (API endpoint change)
frontend/src/components/DeviceImport/ImportPreviewTab.vue       (removed mock data)
```

---

## Testing Checklist

### Backend API Test:
```bash
# Terminal or Postman
curl -X GET "http://localhost:8000/api/v1/inventory/zabbix/lookup/hosts/grouped/" \
  -H "Cookie: sessionid=YOUR_SESSION_ID"

# Expected: JSON with grouped hosts
```

### Frontend UI Test:
1. ✅ Navigate to Device Import page
2. ✅ Click "Sincronização (Pré)" tab
3. ✅ Verify groups appear (e.g., "Linux Servers", "Network Devices")
4. ✅ Click group to expand and see hosts
5. ✅ Verify imported hosts show "Ver Detalhes" (disabled button)
6. ✅ Verify new hosts show "Configurar e Importar" (active button)
7. ✅ Select hosts and click "Importar Selecionados"
8. ✅ Verify import modal opens with correct data

---

## Error Resolution

### Before Fix:
```javascript
// Console Error
TypeError: ZabbixHosts.map is not a function
at DeviceImportManager.js:1474
```

**Cause**: Frontend tried to call `.map()` on API response object `{data: [...]}` instead of array.

### After Fix:
```javascript
// DeviceImportManager.vue (line 172)
const response = await api.get('/api/v1/inventory/zabbix/lookup/hosts/grouped/');
const zabbixGroups = response.data || []; // ✅ Correctly extracts array
```

---

## Configuration Requirements

### Zabbix Server Settings

Ensure runtime settings include valid Zabbix connection:

```python
# Via setup_app.models.FirstTimeSetup
ZABBIX_URL = "http://10.0.0.50/api_jsonrpc.php"
ZABBIX_USERNAME = "your-zabbix-user"
ZABBIX_PASSWORD = "your-zabbix-password"
```

**Check in Django Admin**: `/admin/setup_app/firsttimesetup/`

---

## API Endpoint Details

### `/api/v1/inventory/zabbix/lookup/hosts/grouped/`

**Method**: GET  
**Auth**: Login required  
**Query Params**: None (future: filter by server ID)

**Response Fields**:
```typescript
{
  data: [
    {
      zabbix_group_id: string,      // Zabbix hostgroup ID
      name: string,                  // Hostgroup name
      hosts: [
        {
          zabbix_id: string,         // Zabbix host ID
          name: string,              // Host display name
          ip: string | null,         // Primary interface IP
          status: "online" | "offline",
          is_imported: boolean       // Marked by frontend
        }
      ]
    }
  ],
  count: number                      // Number of groups
}
```

---

## Performance Considerations

**Zabbix API Call**:
- Single `host.get` request with `selectGroups` and `selectInterfaces`
- Efficient grouping in Python (dict-based)
- No N+1 queries

**Frontend Rendering**:
- Collapsible groups (expand only when needed)
- Virtual scrolling not implemented (consider for 1000+ hosts)

**Caching**:
- No caching currently (consider SWR pattern for large Zabbix instances)

---

## Known Limitations

1. **No Multi-Server Support**: Currently fetches from default Zabbix server only
2. **No Pagination**: Loads all hosts at once (may be slow for large Zabbix instances)
3. **No Filtering**: Cannot filter by hostgroup before API call
4. **No Auto-Refresh**: User must manually click "Recarregar Dados"

---

## Future Enhancements

### Planned Improvements:
1. **Multi-Server Support**: Dropdown to select Zabbix server (primary/secondary)
2. **Server-Side Filtering**: Query param to filter by hostgroup IDs
3. **Pagination**: Limit hosts per request, load more on scroll
4. **WebSocket Updates**: Real-time sync when Zabbix hosts change
5. **Caching**: SWR cache for Zabbix data (refresh every 60s)

### Implementation Priority:
- **High**: Multi-server support (required by user request)
- **Medium**: Pagination (for large Zabbix instances)
- **Low**: Real-time updates (nice-to-have)

---

## Related Documentation

- **Backend Integration**: `doc/reports/fixes/DEVICE_IMPORT_BACKEND_INTEGRATION.md`
- **Enhancement Features**: `doc/reports/fixes/DEVICE_IMPORT_ENHANCEMENTS.md`
- **API Reference**: `doc/api/DEVICE_IMPORT_API.md`

---

## Build Information

**Frontend Build**:
```
DeviceImportManager.js: 84.60 kB (gzip: 16.37 kB)
Build time: 1.70s
Status: ✅ Success
```

**Docker Deployment**:
```
Container: docker-web-1
Status: ✅ Restarted
Health: Healthy
```

---

## Troubleshooting

### Issue: "Não foi possível carregar dispositivos do Zabbix"

**Possible Causes**:
1. Zabbix server not configured (check `/admin/setup_app/firsttimesetup/`)
2. Zabbix server unreachable (check network connectivity)
3. Invalid credentials (check Zabbix login)
4. Zabbix API disabled (enable JSON-RPC API in Zabbix settings)

**Debug Steps**:
```python
# Django shell
python manage.py shell

from integrations.zabbix.zabbix_service import zabbix_request
result = zabbix_request("host.get", {"output": ["hostid", "name"], "limit": 10})
print(result)  # Should return list of hosts
```

### Issue: Groups show but no hosts appear

**Cause**: Zabbix hostgroup has no hosts or filtering removed all hosts

**Solution**: Check Zabbix server to ensure hosts are assigned to hostgroups

---

**Status**: ✅ Fix deployed and tested  
**Next Step**: User testing with real Zabbix data
