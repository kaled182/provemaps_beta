# Redis High Availability Strategy

## Current state (development)
The project ships with a single Redis container (`docker-compose.yml`), creating a single point of failure for:
- Cache (django-redis with SWR pattern)
- Celery (task broker and result backend)
- Channels (WebSocket layer)

If Redis goes down the entire application becomes unavailable.

---

## Production solutions

### Option A: Managed service (recommended)

Use a managed Redis service with built-in high availability.

#### AWS ElastiCache for Redis
- Cluster mode disabled (simpler): one primary plus one to five read replicas, automatic failover in roughly one minute, multi-AZ.
- Cluster mode enabled (higher throughput): shards data across multiple nodes with per-shard failover.

**Configuration example:**
```python
# settings/prod.py
import os

REDIS_URL = os.getenv('REDIS_URL', 'redis://prod-cluster.abc123.0001.use1.cache.amazonaws.com:6379/0')

CACHES = {
  "default": {
    "BACKEND": "django_redis.cache.RedisCache",
    "LOCATION": REDIS_URL,
    "OPTIONS": {
      "CLIENT_CLASS": "django_redis.client.DefaultClient",
      "SOCKET_CONNECT_TIMEOUT": 5,
      "SOCKET_TIMEOUT": 5,
      "CONNECTION_POOL_KWARGS": {
        "max_connections": 50,
        "retry_on_timeout": True,
      },
      "PARSER_CLASS": "redis.connection.HiredisParser",
    },
  }
}

# Celery
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# Channels
CHANNEL_LAYERS = {
  "default": {
    "BACKEND": "channels_redis.core.RedisChannelLayer",
    "CONFIG": {
      "hosts": [REDIS_URL],
      "capacity": 1500,
      "expiry": 10,
    },
  },
}
```

#### Google Cloud Memorystore
Very similar configuration; endpoints usually look like `10.0.0.3:6379`.

#### Azure Cache for Redis
Endpoint example: `myredis.redis.cache.windows.net:6380,ssl=True`.

---

### Option B: Self-managed Redis Sentinel (on-premises)

**Architecture overview:**
```
+------------+    +------------+    +------------+
| Redis      |    | Redis      |    | Redis      |
| Master     |<-->| Replica 1  |<-->| Replica 2  |
| (Primary)  |    |            |    |            |
+-----+------+    +-----+------+    +-----+------+
    |               |               |
    +---------------+---------------+
            |
        +----------------------+ 
        | Sentinel Cluster     |
        | (three instances)    |
        | - Monitor master     |
        | - Auto-failover      |
        | - Config provider    |
        +----------------------+
```

**Docker Compose example:**
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  redis-master:
    image: redis:7-alpine
    container_name: redis-master
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis-master-data:/data
    networks:
      - redis-net
    ports:
      - "6379:6379"

  redis-replica-1:
    image: redis:7-alpine
    container_name: redis-replica-1
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD} --replicaof redis-master 6379 --masterauth ${REDIS_PASSWORD}
    depends_on:
      - redis-master
    volumes:
      - redis-replica-1-data:/data
    networks:
      - redis-net

  redis-replica-2:
    image: redis:7-alpine
    container_name: redis-replica-2
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD} --replicaof redis-master 6379 --masterauth ${REDIS_PASSWORD}
    depends_on:
      - redis-master
    volumes:
      - redis-replica-2-data:/data
    networks:
      - redis-net

  redis-sentinel-1:
    image: redis:7-alpine
    container_name: redis-sentinel-1
    command: >
      sh -c "echo 'port 26379
      sentinel monitor mymaster redis-master 6379 2
      sentinel auth-pass mymaster ${REDIS_PASSWORD}
      sentinel down-after-milliseconds mymaster 5000
      sentinel parallel-syncs mymaster 1
      sentinel failover-timeout mymaster 10000' > /tmp/sentinel.conf &&
      redis-sentinel /tmp/sentinel.conf"
    depends_on:
      - redis-master
    networks:
      - redis-net
    ports:
      - "26379:26379"

  redis-sentinel-2:
    image: redis:7-alpine
    container_name: redis-sentinel-2
    command: >
      sh -c "echo 'port 26379
      sentinel monitor mymaster redis-master 6379 2
      sentinel auth-pass mymaster ${REDIS_PASSWORD}
      sentinel down-after-milliseconds mymaster 5000
      sentinel parallel-syncs mymaster 1
      sentinel failover-timeout mymaster 10000' > /tmp/sentinel.conf &&
      redis-sentinel /tmp/sentinel.conf"
    depends_on:
      - redis-master
    networks:
      - redis-net
    ports:
      - "26380:26379"

  redis-sentinel-3:
    image: redis:7-alpine
    container_name: redis-sentinel-3
    command: >
      sh -c "echo 'port 26379
      sentinel monitor mymaster redis-master 6379 2
      sentinel auth-pass mymaster ${REDIS_PASSWORD}
      sentinel down-after-milliseconds mymaster 5000
      sentinel parallel-syncs mymaster 1
      sentinel failover-timeout mymaster 10000' > /tmp/sentinel.conf &&
      redis-sentinel /tmp/sentinel.conf"
    depends_on:
      - redis-master
    networks:
      - redis-net
    ports:
      - "26381:26379"

volumes:
  redis-master-data:
  redis-replica-1-data:
  redis-replica-2-data:

networks:
  redis-net:
    driver: bridge
```

**Django configuration for Sentinel:**
```python
# settings/prod.py
import os

REDIS_SENTINELS = [
    ('sentinel-1.example.com', 26379),
    ('sentinel-2.example.com', 26379),
    ('sentinel-3.example.com', 26379),
]
REDIS_MASTER_NAME = 'mymaster'
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://mymaster/0",  # Service name, not host
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.SentinelClient",
            "SENTINELS": REDIS_SENTINELS,
            "SENTINEL_KWARGS": {
                "password": REDIS_PASSWORD,
            },
            "PASSWORD": REDIS_PASSWORD,
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 50,
            }
        }
    }
}

# Celery with Sentinel
CELERY_BROKER_URL = f'sentinel://{REDIS_SENTINELS[0][0]}:{REDIS_SENTINELS[0][1]};sentinel://{REDIS_SENTINELS[1][0]}:{REDIS_SENTINELS[1][1]};sentinel://{REDIS_SENTINELS[2][0]}:{REDIS_SENTINELS[2][1]}'
CELERY_BROKER_TRANSPORT_OPTIONS = {
    'master_name': REDIS_MASTER_NAME,
    'sentinel_kwargs': {'password': REDIS_PASSWORD},
}
CELERY_RESULT_BACKEND = CELERY_BROKER_URL

# Channels with Sentinel
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": REDIS_SENTINELS,
            "master_name": REDIS_MASTER_NAME,
            "sentinel_kwargs": {"password": REDIS_PASSWORD},
            "password": REDIS_PASSWORD,
        },
    },
}
```

---

## Failover Testing

### Test Sentinel failover
```powershell
# 1. Check current master
docker compose exec redis-sentinel-1 redis-cli -p 26379 SENTINEL get-master-addr-by-name mymaster

# 2. Simulate master failure
docker compose stop redis-master

# 3. Watch failover (should complete in ~10s)
docker compose exec redis-sentinel-1 redis-cli -p 26379 SENTINEL get-master-addr-by-name mymaster

# 4. Verify new master
docker compose exec redis-replica-1 redis-cli INFO replication

# 5. Restart old master (becomes replica)
docker compose start redis-master
```

### Monitor application during failover
```python
# Add to health checks (core/views_health.py)
from django.core.cache import cache

def check_redis_health():
    try:
        cache.set('health_check', 'ok', timeout=5)
        value = cache.get('health_check')
        return value == 'ok'
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return False
```

---

## Monitoring recommendations

### Metrics to track
1. Redis master to replica lag (seconds of replication delay).
2. Sentinel quorum status (are all three sentinels healthy?).
3. Failover events (count per day or per week).
4. Connection pool exhaustion for django-redis.
5. Cache hit rate (effectiveness of caching strategy).

### Prometheus queries
```promql
# Redis memory usage
redis_memory_used_bytes / redis_memory_max_bytes

# Replication lag
redis_connected_slaves

# Connection pool usage
django_cache_get_total - django_cache_get_hits
```

---

## Cost analysis

### Managed service (AWS ElastiCache example)
- cache.r7g.large (13.07 GB RAM): roughly USD 120 per month.
- Multi-AZ: doubles the cost (about USD 240 per month).
- Backups: included.

Total estimated cost: USD 240 per month for a highly available setup.

### Self-managed (three virtual machines)
- Three t3.small instances (2 vCPU, 2 GB RAM each): roughly USD 45 per month.
- EBS storage (30 GB total): roughly USD 3 per month.
- Manual maintenance: two to four hours per month.

Total estimated cost: USD 50 per month plus operational time.

---

## Decision matrix

| Criteria           | Managed service | Self-managed Sentinel |
|--------------------|-----------------|-----------------------|
| Setup time         | About 30 minutes| Four to six hours     |
| Operations burden  | Minimal         | High                  |
| Failover speed     | About one minute| About ten seconds     |
| Cost               | Around USD 240  | Around USD 50         |
| Scaling            | One-click       | Manual                |
| Security           | Provider managed| Do it yourself        |

Recommendation: choose a managed service for production unless the budget is extremely constrained or you have a dedicated operations team.

---

## Implementation checklist

- [ ] Choose a Redis HA solution (managed or Sentinel).
- [ ] Update `settings/prod.py` with the selected configuration.
- [ ] Set environment variables (`REDIS_URL` or `REDIS_SENTINELS`).
- [ ] Test failover scenarios in staging.
- [ ] Add Redis health checks to the `/health/` endpoint.
- [ ] Configure monitoring and alerting for Redis metrics.
- [ ] Document a runbook for manual failover if needed.
- [ ] Update `DEPLOYMENT.md` with Redis HA setup instructions.

---

## References
- [Django Redis Sentinel](https://github.com/jazzband/django-redis#sentinel-support)
- [Celery Redis Sentinel](https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/redis.html#redis-sentinel-support)
- [Redis Sentinel Documentation](https://redis.io/./management/sentinel/)
- [AWS ElastiCache Best Practices](https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/BestPractices.html)
