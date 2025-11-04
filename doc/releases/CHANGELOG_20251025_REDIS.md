# Changelog – 2025-10-25: Redis Graceful Degradation

## 🎯 Executive Summary

**Problem:** The application returned HTTP 500 when Redis was offline  
**Solution:** Implement graceful degradation – the app works without Redis and logs at DEBUG  
**Impact:** ✅ Local development without hard dependency + production resiliency  

---

## 🔧 Technical Changes

### Modified Files

#### 1. `zabbix_api/services/zabbix_service.py`
**Added:**
- `safe_cache_get(key, default=None)` – Safe wrapper for cache.get()
- `safe_cache_set(key, value, timeout=None)` – Safe wrapper for cache.set()
- `safe_cache_delete(key)` – Safe wrapper for cache.delete()

**Replaced:** 10 cache access points:
- `search_hosts()` – 2x (get + set)
- `get_host_interfaces()` – 2x (get + set)
- `search_hosts_by_name_ip()` – 2x (get + set)
- `get_host_interfaces_detailed()` – 2x (get + set)
- `test_host_connectivity()` – 2x (get + set)

#### 2. `zabbix_api/inventory_cache.py`
**Changed:**
- `invalidate_fiber_cache()` – Wrapped in try/except to ignore offline Redis

#### 3. `routes_builder/views_tasks.py`
**Changed:**
- `_check_rate_limit()` – Wrapped in try/except (fail-open when Redis is offline)

---

## 📊 Before vs After

| Aspect | ❌ Before | ✅ After |
|---------|---------|----------|
| **Redis offline** | HTTP 500 | HTTP 200 |
| **Logs** | [ERROR] + stack trace | [DEBUG] short message |
| **Dev experience** | Requires Redis running | Works standalone |
| **Production** | Total failure if Redis goes down | Graceful degradation |
| **Performance** | N/A (broken) | Reduced but functional |

---

## 🧪 Validation

### Manual test executed
```powershell
# Server running WITHOUT Redis
curl http://localhost:8000/zabbix_api/lookup/hosts/?groupids=22
```

**Resultado:**
```
[DEBUG] zabbix_api.services.zabbix_service: Cache offline (Redis unavailable), continuing without cache: ConnectionError
HTTP/1.1 200 OK
```

✅ **Success:** Endpoint returns 200, application keeps working

### Endpoints tested
- ✅ `/zabbix/lookup/` – Lookup interface (200 OK)
- ✅ `/zabbix_api/lookup/hosts/?groupids=22` – Lookup API (200 OK)
- ✅ `/maps_view/dashboard/` – Dashboard (200 OK)
- ✅ `/zabbix_api/api/fibers/` – Fibers API (200 OK)

---

## 📝 Documentation created

1. **`doc/reference/REDIS_GRACEFUL_DEGRADATION.md`**
    - Detailed problem statement
    - Implemented solution
    - Before/after comparison
    - Validation tests
    - Configuration notes

2. **`QUICKSTART_LOCAL.md` (updated)**
    - Section describing cache behavior
    - Troubleshooting for offline Redis
    - Cross-reference to the detailed document

---

## 🎓 Patterns applied

### 1. Graceful Degradation
**Concept:** The system keeps working (with reduced functionality) when a component fails

**Implementation:**
```python
def safe_cache_get(key, default=None):
    try:
        return cache.get(key, default=default)
    except Exception:
        logger.debug("Cache offline, continuing without cache")
        return default  # ← Degraded: no cache, but still works
```

### 2. Fail-Open (Rate Limiting)
**Concept:** If the safety mechanism fails, allow access (instead of blocking everything)

**Implementation:**
```python
def _check_rate_limit(request, action, limit=10, window=60):
    try:
        # ... verificação de rate limiting com Redis ...
    except Exception:
        # Redis offline: allow the request (fail-open)
        pass
    return True
```

### 3. Defensive Logging
**Concept:** Logs should reflect the real severity (DEBUG for expected scenarios, ERROR for actual problems)

**Implementation:**
```python
# ❌ Before: logger.error("Redis connection failed")
# ✅ After: logger.debug("Cache offline (expected in dev)")
```

---

## 🚀 Next Steps

### Delivered today ✅
- [x] Safe cache wrappers
- [x] Replacement inside `zabbix_api/services/`
- [x] Handling in `inventory_cache`
- [x] Rate limiting fail-open
- [x] Full documentation
- [x] Manual tests

### Future suggestions 📋
- [ ] Add automated tests `test_cache_graceful_degradation.py`
- [ ] Prometheus metrics for cache hit/miss rate
- [ ] Fallback to `django.core.cache.backends.locmem` (in-memory cache)
- [ ] Non-critical Redis health check
- [ ] Circuit breaker pattern for the Redis connection pool

---

## 🔍 Additional Context

### Why did this happen?
The original code assumed Redis would always be available, which is common in production. However, for local development that creates unnecessary friction.

### Why not use in-memory cache?
In-memory cache (locmem) was considered, but:
- ✅ Graceful degradation is simpler
- ✅ Closer to the production behavior (no cache vs cache)
- ✅ Highlights real dependencies (forces us to consider performance without cache)

### Production impact
**Positive:** If Redis goes down momentarily, the application keeps working (degraded mode)  
**Neutral:** Reduced performance until Redis comes back  
**Negative:** No rate limiting (risk of abuse), but still better than a full outage  

---

## 📞 Contact

**Related issues:** #N/A (proactive fix)  
**Pull Request:** TBD  
**Author:** DevOps + Backend Team  
**Date:** 2025-10-25  

---

**Test environment:**
- OS: Windows 11
- Python: 3.13
- Django: 5.2.7
- Redis: N/A (intentionally offline)
- Database: SQLite (development)
