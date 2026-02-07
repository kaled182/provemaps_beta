"""
Zabbix API batching utilities for performance optimization.

Consolida múltiplas chamadas Zabbix em batch requests para reduzir latência.
Sprint 4 Week 2 - Performance Optimization.

Usage:
    from inventory.zabbix_batch import fetch_optical_levels_batch
    
    port_ids = [1, 2, 3, 4, 5]
    results = fetch_optical_levels_batch(port_ids)
    # Returns: {port_id: {'rx_power': -10.5, 'tx_power': -3.2, ...}, ...}
"""

import logging
from typing import Dict, List, Optional, Any
from django.core.cache import cache

logger = logging.getLogger(__name__)


def fetch_optical_levels_batch(port_ids: List[int]) -> Dict[int, Dict[str, Any]]:
    """
    Fetch optical power levels for multiple ports in a single Zabbix batch request.
    
    Performance improvement: ~5x faster than individual requests.
    - Before: 5 ports × 2s = 10s total
    - After: 1 batch request = 2s total
    
    Args:
        port_ids: List of Port IDs to fetch optical data for
        
    Returns:
        Dictionary mapping port_id to optical data:
        {
            port_id: {
                'rx_power': float,  # dBm
                'tx_power': float,  # dBm
                'temperature': float,  # Celsius
                'timestamp': datetime,
                'status': str,  # 'ok', 'timeout', 'error'
            }
        }
    
    Cache strategy:
        - Cache key: f"optical_batch:{sorted(port_ids)}"
        - TTL: 300s (5 minutes)
        - Invalidation: On port update/delete
    """
    from inventory.models import Port
    from integrations.zabbix.zabbix_service import zabbix_request
    from datetime import datetime, timezone
    
    if not port_ids:
        return {}
    
    # Check cache first
    cache_key = f"optical_batch:{':'.join(map(str, sorted(port_ids)))}"
    cached_result = cache.get(cache_key)
    if cached_result:
        logger.debug(f"Cache HIT for optical batch ({len(port_ids)} ports)")
        return cached_result
    
    logger.debug(f"Cache MISS for optical batch ({len(port_ids)} ports)")
    
    # Fetch ports with device info
    ports = Port.objects.filter(
        id__in=port_ids
    ).select_related('device').only(
        'id', 'name', 'rx_power_item_key', 'tx_power_item_key',
        'device__zabbix_hostid', 'device__name'
    )
    
    # Group ports by device (hostid) for efficient batching
    ports_by_host: Dict[str, List[Port]] = {}
    for port in ports:
        if port.device and port.device.zabbix_hostid:
            hostid = port.device.zabbix_hostid
            if hostid not in ports_by_host:
                ports_by_host[hostid] = []
            ports_by_host[hostid].append(port)
    
    results: Dict[int, Dict[str, Any]] = {}
    
    # Batch request per host
    for hostid, host_ports in ports_by_host.items():
        try:
            # Build item keys list for batch request
            item_keys = []
            port_key_mapping = {}  # {item_key: (port_id, 'rx'/'tx')}
            
            for port in host_ports:
                if port.rx_power_item_key:
                    item_keys.append(port.rx_power_item_key)
                    port_key_mapping[port.rx_power_item_key] = (port.id, 'rx')
                
                if port.tx_power_item_key:
                    item_keys.append(port.tx_power_item_key)
                    port_key_mapping[port.tx_power_item_key] = (port.id, 'tx')
            
            if not item_keys:
                logger.warning(f"No item keys configured for ports on host {hostid}")
                continue
            
            # Single batch item.get request
            items_response = zabbix_request(
                method='item.get',
                params={
                    'hostids': hostid,
                    'search': {
                        'key_': item_keys,
                    },
                    'output': ['itemid', 'key_', 'lastvalue', 'lastclock'],
                    'selectHosts': ['name'],
                },
            )
            
            if not items_response:
                logger.warning(f"No items returned for host {hostid}")
                continue
            
            # Parse batch response and map to ports
            for item in items_response:
                item_key = item.get('key_')
                if item_key not in port_key_mapping:
                    continue
                
                port_id, power_type = port_key_mapping[item_key]
                
                # Initialize port result if needed
                if port_id not in results:
                    results[port_id] = {
                        'rx_power': None,
                        'tx_power': None,
                        'temperature': None,
                        'timestamp': None,
                        'status': 'ok',
                    }
                
                # Parse optical power value
                try:
                    value = float(item.get('lastvalue', 0))
                    timestamp = datetime.fromtimestamp(
                        int(item.get('lastclock', 0)),
                        tz=timezone.utc,
                    )
                    
                    if power_type == 'rx':
                        results[port_id]['rx_power'] = value
                    elif power_type == 'tx':
                        results[port_id]['tx_power'] = value
                    
                    # Update timestamp to most recent
                    if not results[port_id]['timestamp'] or timestamp > results[port_id]['timestamp']:
                        results[port_id]['timestamp'] = timestamp
                
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse optical value for port {port_id}: {e}")
                    results[port_id]['status'] = 'error'
        
        except Exception as e:
            logger.error(f"Batch optical fetch failed for host {hostid}: {e}", exc_info=True)
            # Mark all ports of this host as error
            for port in host_ports:
                results[port.id] = {
                    'rx_power': None,
                    'tx_power': None,
                    'temperature': None,
                    'timestamp': None,
                    'status': 'error',
                }
    
    # Cache results for 5 minutes
    cache.set(cache_key, results, timeout=300)
    
    logger.info(f"Batch optical fetch: {len(results)}/{len(port_ids)} ports processed")
    
    return results


def invalidate_optical_batch_cache(port_ids: Optional[List[int]] = None):
    """
    Invalidate cached optical batch data.
    
    Call this when:
    - Port optical configuration changes (item keys updated)
    - Manual refresh requested
    - Port deleted
    
    Args:
        port_ids: Specific ports to invalidate. If None, clears all optical batch cache.
    """
    if port_ids is None:
        # Clear all optical batch caches (pattern matching)
        # Note: Redis supports SCAN with pattern, but django cache abstraction doesn't
        # For now, specific invalidation only
        logger.warning("Bulk optical cache invalidation not fully implemented")
        return
    
    # Invalidate specific batch cache
    cache_key = f"optical_batch:{':'.join(map(str, sorted(port_ids)))}"
    cache.delete(cache_key)
    logger.debug(f"Invalidated optical batch cache for {len(port_ids)} ports")


__all__ = [
    'fetch_optical_levels_batch',
    'invalidate_optical_batch_cache',
]
