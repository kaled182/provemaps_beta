"""Views for system metrics and health monitoring."""
import json
import psutil
import redis
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required, user_passes_test
from django.conf import settings
from django.db import connection
import requests


def _staff_check(user):
    """Check if user is staff."""
    return user.is_staff


@require_http_methods(["GET"])
@login_required
@user_passes_test(_staff_check)
def system_health_metrics(request):
    """Return system health metrics in JSON format."""
    try:
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "services": {},
            "system": {},
        }

        # Redis Status
        try:
            from django.core.cache import cache
            cache.set("health_check", "ok", 1)
            result = cache.get("health_check")
            
            # Try to get Redis info
            redis_url = getattr(settings, 'REDIS_URL', '')
            if redis_url:
                from urllib.parse import urlparse
                parsed = urlparse(redis_url)
                r = redis.Redis(
                    host=parsed.hostname or 'localhost',
                    port=parsed.port or 6379,
                    db=int(parsed.path[1:]) if parsed.path and len(parsed.path) > 1 else 0,
                    socket_connect_timeout=2,
                )
                info = r.info()
                metrics["services"]["redis"] = {
                    "status": "online",
                    "version": info.get('redis_version', 'Unknown'),
                    "uptime_days": info.get('uptime_in_days', 0),
                    "connected_clients": info.get('connected_clients', 0),
                    "used_memory_human": info.get('used_memory_human', '0B'),
                    "response_time_ms": 0,
                }
            else:
                metrics["services"]["redis"] = {
                    "status": "online",
                    "version": "Unknown",
                    "response_time_ms": 0,
                }
        except Exception as e:
            metrics["services"]["redis"] = {
                "status": "offline",
                "error": str(e),
            }

        # PostgreSQL Status
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                start = datetime.now()
                cursor.execute("SELECT version()")
                version_full = cursor.fetchone()[0]
                end = datetime.now()
                response_time = (end - start).total_seconds() * 1000
                
                version = version_full.split(',')[0] if ',' in version_full else version_full
                
                metrics["services"]["postgresql"] = {
                    "status": "online",
                    "version": version,
                    "response_time_ms": round(response_time, 2),
                }
        except Exception as e:
            metrics["services"]["postgresql"] = {
                "status": "offline",
                "error": str(e),
            }

        # Zabbix Status
        try:
            zabbix_url = getattr(settings, 'ZABBIX_API_URL', '')
            if zabbix_url:
                start = datetime.now()
                payload = {
                    "jsonrpc": "2.0",
                    "method": "apiinfo.version",
                    "params": {},
                    "id": 1
                }
                response = requests.post(
                    zabbix_url,
                    json=payload,
                    timeout=5
                )
                end = datetime.now()
                response_time = (end - start).total_seconds() * 1000
                
                data = response.json()
                version = data.get("result", "Unknown")
                
                metrics["services"]["zabbix"] = {
                    "status": "online",
                    "version": version,
                    "response_time_ms": round(response_time, 2),
                }
            else:
                metrics["services"]["zabbix"] = {
                    "status": "not_configured",
                }
        except Exception as e:
            metrics["services"]["zabbix"] = {
                "status": "offline",
                "error": str(e),
            }

        # Celery Status
        try:
            from celery import current_app
            inspect = current_app.control.inspect(timeout=2)
            stats = inspect.stats()
            active = inspect.active()
            
            if stats:
                worker_count = len(stats)
                total_active_tasks = sum(len(tasks) for tasks in (active or {}).values())
                
                metrics["services"]["celery"] = {
                    "status": "online",
                    "workers": worker_count,
                    "active_tasks": total_active_tasks,
                }
            else:
                metrics["services"]["celery"] = {
                    "status": "offline",
                    "workers": 0,
                }
        except Exception as e:
            metrics["services"]["celery"] = {
                "status": "offline",
                "error": str(e),
            }

        # System Metrics
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            metrics["system"] = {
                "cpu_percent": round(cpu_percent, 1),
                "memory_percent": round(memory.percent, 1),
                "memory_used_gb": round(memory.used / (1024**3), 2),
                "memory_total_gb": round(memory.total / (1024**3), 2),
                "disk_percent": round(disk.percent, 1),
                "disk_used_gb": round(disk.used / (1024**3), 2),
                "disk_total_gb": round(disk.total / (1024**3), 2),
            }
        except Exception as e:
            metrics["system"] = {
                "error": str(e),
            }

        return JsonResponse(metrics)

    except Exception as e:
        return JsonResponse(
            {"error": f"Failed to collect metrics: {str(e)}"},
            status=500
        )
