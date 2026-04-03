# Redis Graceful Degradation – Local Development

## 🎯 Goal

Allow the application to run **without Redis** in the development environment, gracefully degrading to a cache-less mode instead of throwing HTTP 500 errors.

---

## 🐛 Original Problem

### Symptom
```
[ERROR] zabbix_api.views: Error in lookup_hosts endpoint: Error 10061 connecting to 127.0.0.1:6379
redis.exceptions.ConnectionError: Error 10061 connecting to 127.0.0.1:6379.
No connection could be made because the target machine actively refused it.
[ERROR] django.server: "GET /zabbix_api/lookup/hosts/?groupids=22 HTTP/1.1" 500 37
```

> Observação: os endpoints de `lookup` ainda residem em `/zabbix_api/` até concluirmos a migração dos autocompletes; demais recursos já usam `/api/v1/inventory/`.

### Root Cause
The code invoked `cache.get()` and `cache.set()` without exception handling, which led to:
- ❌ HTTP 500 (Internal Server Error) whenever Redis was offline
- ❌ Long stack traces cluttering the error logs
- ❌ Poor developer experience (Redis had to be running locally)

---

## ✅ Implemented Solution

### 1. Safe cache wrappers

Three helpers were created in `integrations/zabbix/zabbix_service.py`:

```python
def safe_cache_get(key, default=None):
    """Safe wrapper around cache.get() that ignores Redis connection failures."""
    try:
        return cache.get(key, default=default)
    except Exception as exc:
        logger.debug(
            "Cache offline (Redis unavailable), continuing without cache: %s",
            exc.__class__.__name__,
        )
        return default

def safe_cache_set(key, value, timeout=None):
    """Safe wrapper around cache.set() that ignores Redis connection failures."""
    try:
        cache.set(key, value, timeout=timeout)
    except Exception as exc:
        logger.debug(
            "Cache offline (Redis unavailable), not storing value: %s",
            exc.__class__.__name__,
        )

def safe_cache_delete(key):
    """Safe wrapper around cache.delete() that ignores Redis connection failures."""
    try:
        cache.delete(key)
    except Exception as exc:
        logger.debug(
            "Cache offline (Redis unavailable), not deleting: %s",
            exc.__class__.__name__,
        )
```

### 2. Replacements applied

#### integrations/zabbix/zabbix_service.py
- ✅ `search_hosts()` – line ~585
- ✅ `search_hosts()` cache set – line ~666
- ✅ `get_host_interfaces()` – line ~677
- ✅ `get_host_interfaces()` cache set – line ~705
- ✅ `search_hosts_by_name_ip()` – line ~719
- ✅ `search_hosts_by_name_ip()` cache set – line ~796
- ✅ `get_host_interfaces_detailed()` – line ~806
- ✅ `get_host_interfaces_detailed()` cache set – line ~836
- ✅ `test_host_connectivity()` – line ~900
- ✅ `test_host_connectivity()` cache set – line ~935

Total: **10 replacements** in `zabbix_service.py`

#### zabbix_api/inventory_cache.py
- ✅ `invalidate_fiber_cache()` – wrapped with try/except

#### routes_builder/views_tasks.py
- ✅ `_check_rate_limit()` – wrapped with try/except (fail-open)

---

## 🎭 Current Behavior

### With Redis online
```
[DEBUG] integrations.zabbix.zabbix_service: Cache HIT for search_hosts:q=test...
→ Optimized performance, instant results
```

### With Redis offline
```
[DEBUG] integrations.zabbix.zabbix_service: Cache offline (Redis unavailable), continuing without cache: ConnectionError
→ Application keeps working, falls back to direct Zabbix queries (slower but functional)
```

### Comparison

| Aspect | Before (error) | After (graceful) |
|---------|------------------|-------------------|
| **HTTP Status** | 500 (error) | 200 (success) |
| **Logs** | [ERROR] with stack trace | [DEBUG] short message |
| **Performance** | N/A (crash) | No cache, direct to Zabbix |
| **Dev Experience** | ❌ Redis required | ✅ Works standalone |

---

## 📊 Impact

### Files touched
- `integrations/zabbix/zabbix_service.py` – 10 cache calls
- `zabbix_api/inventory_cache.py` – 1 cache call
- `routes_builder/views_tasks.py` – 1 rate-limiting hook

### Benefits
- ✅ **Easier development:** no need to install/configure Redis locally
- ✅ **Resilience:** app tolerates temporary Redis failures in production
- ✅ **Clean logs:** DEBUG instead of ERROR for expected situations
- ✅ **Fail-open:** rate limiting keeps responding if Redis is offline

### Trade-offs
- ⚠️ **Reduced performance:** without cache, every call hits Zabbix
- ⚠️ **Rate limiting disabled:** when Redis is offline, rate limiting is fail-open
- ℹ️ **Resource usage:** more load on Zabbix without caching

---

## 🔧 Configuration

### Local development (`.env`)
```bash
# Optional cache – works without Redis
HEALTHCHECK_IGNORE_CACHE=true
DEBUG=True
```

### Production (`.env`)
```bash
# Redis must remain available in production
REDIS_URL=redis://localhost:6379/0
HEALTHCHECK_IGNORE_CACHE=false
DEBUG=False
```

---

## ✅ Validation

### Manual test
1. **With Redis stopped:**
   ```powershell
    # Ensure Redis is NOT running
   curl http://localhost:8000/zabbix_api/lookup/hosts/?groupids=22
   ```
    - ✅ Should return HTTP 200 (not 500)
    - ✅ Logs show [DEBUG], not [ERROR]

2. **With Redis running:**
   ```powershell
    # Start Redis
   redis-server
   
    # Call the endpoint
   curl http://localhost:8000/zabbix_api/lookup/hosts/?groupids=22
   ```
    - ✅ Should return HTTP 200
    - ✅ Second call should be faster (cache hit)

### Automated test
```python
# tests/test_cache_graceful_degradation.py
def test_zabbix_lookup_without_redis(mocker):
    """Endpoint must keep working even when Redis is offline."""
    # Mock cache.get to raise ConnectionError
    mocker.patch('django.core.cache.cache.get', side_effect=ConnectionError)
    
    response = client.get('/zabbix_api/lookup/hosts/?groupids=22')
    
    # Must not return an error
    assert response.status_code == 200
```

---

## 📚 References

- Django Cache Framework: https://docs.djangoproject.com/en/5.2/topics/cache/
- Redis Exception Handling: https://redis-py.readthedocs.io/en/stable/exceptions.html
- Graceful Degradation Pattern: https://en.wikipedia.org/wiki/Graceful_degradation

---

## 🚀 Next Steps (Optional)

- [ ] Add Prometheus metrics for cache hit/miss rate
- [ ] Implement an in-memory fallback cache (`django.core.cache.backends.locmem`)
- [ ] Configure a short Redis timeout to avoid long stalls
- [ ] Add a non-critical Redis-specific health check

---

**Developed:** 25/10/2025  
**Owners:** DevOps + Backend Team  
**Status:** ✅ Implemented and validated
