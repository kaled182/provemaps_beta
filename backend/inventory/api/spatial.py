"""
Spatial query endpoints for PostGIS-based filtering (Phase 10).

Provides BBox filtering for RouteSegment and FiberCable models
to enable map viewport-based data loading (lazy loading).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

try:  # pragma: no cover - environment dependent import
    from django.contrib.gis.geos import Polygon
    HAS_GIS = True
except (ImportError, ImproperlyConfigured):
    Polygon = None  # type: ignore[assignment]
    HAS_GIS = False
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.http import require_GET

from integrations.zabbix.decorators import api_login_required
from inventory.models import FiberCable, Site
from inventory.models_routes import RouteSegment
from inventory.usecases.spatial import get_sites_within_radius
from inventory.cache.radius_search import get_radius_search_with_cache
from inventory.tasks import refresh_radius_search_cache

logger = logging.getLogger(__name__)


def _parse_bbox(bbox_str: str) -> Polygon | None:
    """
    Parse bbox query parameter into PostGIS Polygon.
    
    Args:
        bbox_str: "lng_min,lat_min,lng_max,lat_max"
        
    Returns:
        Polygon or None if invalid
        
    Example:
        "-48.5,-16.5,-47.5,-15.5" -> polygon covering Brasilia area
    """
    if not HAS_GIS or Polygon is None:
        return None

    try:
        parts = bbox_str.split(',')
        if len(parts) != 4:
            return None
        
        lng_min, lat_min, lng_max, lat_max = map(float, parts)
        
        # Validate coordinate ranges
        if not (-180 <= lng_min <= 180) or not (-180 <= lng_max <= 180):
            return None
        if not (-90 <= lat_min <= 90) or not (-90 <= lat_max <= 90):
            return None
        
        # Validate bbox is not inverted
        if lng_min >= lng_max or lat_min >= lat_max:
            return None
        
        # Create bbox polygon (WGS84 / SRID 4326)
        bbox = Polygon.from_bbox((lng_min, lat_min, lng_max, lat_max))
        bbox.srid = 4326
        
        return bbox
    
    except (ValueError, TypeError):
        return None


def _serialize_route_segment(segment: RouteSegment) -> Dict[str, Any]:
    """
    Serialize RouteSegment for JSON response.
    
    Includes both path (spatial) and path_coordinates (legacy JSON)
    for backward compatibility.
    """
    data: Dict[str, Any] = {
        "id": segment.id,
        "route_id": segment.route_id,
        "order": segment.order,
        "length_km": (
            float(segment.length_km) if segment.length_km else None
        ),
        "estimated_loss_db": (
            float(segment.estimated_loss_db)
            if segment.estimated_loss_db
            else None
        ),
        "measured_loss_db": (
            float(segment.measured_loss_db)
            if segment.measured_loss_db
            else None
        ),
    }
    
    # Add status from parent route (Phase 11 Sprint 3)
    # Maps route status to segment display status
    if segment.route:
        route_status = segment.route.status
        # Map route status to frontend status values
        status_map = {
            'active': 'operational',
            'planned': 'maintenance',
            'degraded': 'degraded',
            'archived': 'unknown',
        }
        data["status"] = status_map.get(route_status, 'unknown')
    else:
        data["status"] = 'unknown'
    
    # Legacy JSONField (deprecated)
    if segment.path_coordinates:
        data["path_coordinates"] = segment.path_coordinates
    
    # Spatial field (PostGIS)
    if segment.path:
        # Convert LineString to GeoJSON coordinates
        # Format: [[lng, lat], [lng, lat], ...]
        data["path_geojson"] = {
            "type": "LineString",
            "coordinates": list(segment.path.coords),
        }
    
    return data


def _serialize_fiber_cable(cable: FiberCable) -> Dict[str, Any]:
    """Serialize FiberCable for JSON response."""
    data: Dict[str, Any] = {
        "id": cable.id,
        "name": cable.name,
        "origin_port_id": cable.origin_port_id,
        "destination_port_id": cable.destination_port_id,
        "length_km": float(cable.length_km) if cable.length_km else None,
        "status": cable.status,
    }
    
    # Legacy JSONField
    if cable.path_coordinates:
        data["path_coordinates"] = cable.path_coordinates
    
    # Spatial field
    if cable.path:
        data["path_geojson"] = {
            "type": "LineString",
            "coordinates": list(cable.path.coords),
        }
    
    return data


@require_GET
@api_login_required
def api_route_segments_bbox(request: HttpRequest) -> HttpResponse:
    """
    GET /api/v1/segments/?bbox=lng_min,lat_min,lng_max,lat_max
    
    Returns RouteSegment instances intersecting the bounding box.
    
    Query params:
        bbox (required): Comma-separated bbox coordinates (WGS84)
        
    Example:
        /api/v1/segments/?bbox=-48.5,-16.5,-47.5,-15.5
        
    Returns:
        {
            "count": 42,
            "bbox": "-48.5,-16.5,-47.5,-15.5",
            "segments": [
                {
                    "id": 123,
                    "route_id": 5,
                    "order": 1,
                    "length_km": 1.234,
                    "path_geojson": {
                        "type": "LineString",
                        "coordinates": [[-47.92, -15.78], ...]
                    }
                },
                ...
            ]
        }
    """
    # Check if PostGIS is enabled
    db_engine = getattr(settings, 'DB_ENGINE', 'mysql')
    if not HAS_GIS:
        return JsonResponse(
            {"error": "Spatial queries require GDAL/GEOS libraries."},
            status=501,
        )
    if db_engine != 'postgis':
        return JsonResponse(
            {
                "error": (
                    "Spatial queries require DB_ENGINE=postgis. "
                    "Current backend: " + db_engine
                )
            },
            status=501,  # Not Implemented
        )
    
    bbox_str = request.GET.get('bbox', '').strip()
    if not bbox_str:
        return JsonResponse(
            {"error": "Missing required parameter: bbox"},
            status=400,
        )
    
    bbox = _parse_bbox(bbox_str)
    if not bbox:
        return JsonResponse(
            {
                "error": (
                    "Invalid bbox format. "
                    "Expected: lng_min,lat_min,lng_max,lat_max"
                )
            },
            status=400,
        )
    
    # Spatial query: find segments overlapping bbox
    segments: QuerySet[RouteSegment] = RouteSegment.objects.filter(
        path__bboverlaps=bbox
    ).select_related('route')
    
    # Serialize results
    results: List[Dict[str, Any]] = [
        _serialize_route_segment(seg) for seg in segments
    ]
    
    return JsonResponse(
        {
            "count": len(results),
            "bbox": bbox_str,
            "segments": results,
        },
        status=200,
    )


@require_GET
@api_login_required
def api_fiber_cables_bbox(request: HttpRequest) -> HttpResponse:
    """
    GET /api/v1/fibers/bbox/?bbox=lng_min,lat_min,lng_max,lat_max
    
    Returns FiberCable instances intersecting the bounding box.
    
    Similar to api_route_segments_bbox but for FiberCable model.
    """
    db_engine = getattr(settings, 'DB_ENGINE', 'mysql')
    if not HAS_GIS:
        return JsonResponse(
            {"error": "Spatial queries require GDAL/GEOS libraries."},
            status=501,
        )
    if db_engine != 'postgis':
        return JsonResponse(
            {
                "error": (
                    "Spatial queries require DB_ENGINE=postgis. "
                    "Current backend: " + db_engine
                )
            },
            status=501,
        )
    
    bbox_str = request.GET.get('bbox', '').strip()
    if not bbox_str:
        return JsonResponse(
            {"error": "Missing required parameter: bbox"},
            status=400,
        )
    
    bbox = _parse_bbox(bbox_str)
    if not bbox:
        return JsonResponse(
            {
                "error": (
                    "Invalid bbox format. "
                    "Expected: lng_min,lat_min,lng_max,lat_max"
                )
            },
            status=400,
        )
    
    # Spatial query with status cache optimization
    cables: QuerySet[FiberCable] = FiberCable.objects.filter(
        path__bboverlaps=bbox
    ).select_related('origin_port', 'destination_port')
    
    results: List[Dict[str, Any]] = [
        _serialize_fiber_cable(cable) for cable in cables
    ]
    
    return JsonResponse(
        {
            "count": len(results),
            "bbox": bbox_str,
            "cables": results,
        },
        status=200,
    )


@require_GET
@api_login_required
def api_sites_within_radius(request: HttpRequest) -> HttpResponse:
    """
    GET /api/v1/inventory/sites/radius?lat=<lat>&lng=<lng>&radius_km=<km>&limit=<n>
    
    Find sites within specified radius using PostGIS ST_DWithin (Phase 7).
    Returns sites ordered by distance from center point.
    
    Query Parameters:
        lat (float, required): Latitude of center point (WGS84)
        lng (float, required): Longitude of center point (WGS84)
        radius_km (float, required): Search radius in kilometers
        limit (int, optional): Max number of results (default: 100, max: 500)
    
    Returns:
        JSON with sites array, each including distance_km field
        
    Example:
        GET /api/v1/inventory/sites/radius?lat=-15.7801&lng=-47.9292&radius_km=10&limit=50
        
    Response:
        {
            "count": 3,
            "center": {"lat": -15.7801, "lng": -47.9292},
            "radius_km": 10,
            "sites": [
                {
                    "id": 1,
                    "display_name": "Brasilia Center",
                    "latitude": -15.7801,
                    "longitude": -47.9292,
                    "distance_km": 0.0
                },
                {
                    "id": 2,
                    "display_name": "Brasilia North",
                    "latitude": -15.7350,
                    "longitude": -47.9292,
                    "distance_km": 5.01
                }
            ]
        }
    """
    # Parse and validate parameters
    try:
        lat = float(request.GET.get('lat', ''))
        lng = float(request.GET.get('lng', ''))
        radius_km = float(request.GET.get('radius_km', ''))
    except (ValueError, TypeError):
        return JsonResponse(
            {
                "error": "Invalid parameters. Required: lat, lng, radius_km (all floats)"
            },
            status=400,
        )
    
    # Validate coordinate ranges
    if not (-90 <= lat <= 90):
        return JsonResponse(
            {"error": "Latitude must be between -90 and 90"},
            status=400,
        )
    
    if not (-180 <= lng <= 180):
        return JsonResponse(
            {"error": "Longitude must be between -180 and 180"},
            status=400,
        )
    
    # Validate radius
    if radius_km <= 0:
        return JsonResponse(
            {"error": "radius_km must be positive"},
            status=400,
        )
    
    if radius_km > 1000:
        return JsonResponse(
            {"error": "radius_km cannot exceed 1000km"},
            status=400,
        )
    
    # Parse limit with sensible defaults
    try:
        limit = int(request.GET.get('limit', '100'))
    except (ValueError, TypeError):
        limit = 100
    
    limit = max(1, min(limit, 500))  # Clamp between 1 and 500
    
    # Execute spatial query with SWR cache (Phase 7 Day 5)
    def fetch_fresh_data():
        """Fetch sites from database."""
        return get_sites_within_radius(
            lat=lat,
            lon=lng,
            radius_km=radius_km,
            limit=limit,
        )
    
    cache_result = get_radius_search_with_cache(
        lat=lat,
        lng=lng,
        radius_km=radius_km,
        limit=limit,
        fetch_fn=fetch_fresh_data,
        async_refresh_task=lambda: refresh_radius_search_cache.delay(
            lat, lng, radius_km, limit
        )
    )
    
    sites = cache_result['data']
    is_stale = cache_result.get('is_stale', False)
    cache_hit = cache_result.get('cache_hit', False)
    
    # Serialize results with distance annotation
    results: List[Dict[str, Any]] = []
    for site in sites:
        # distance is annotated by get_sites_within_radius
        distance_m = getattr(site, 'distance', None)
        distance_km = round(distance_m.m / 1000.0, 2) if distance_m else None
        
        results.append({
            "id": site.id,
            "display_name": site.display_name,
            "latitude": site.latitude,
            "longitude": site.longitude,
            "distance_km": distance_km,
        })
    
    response_data = {
        "count": len(results),
        "center": {"lat": lat, "lng": lng},
        "radius_km": radius_km,
        "sites": results,
    }
    
    # Include cache metadata (helpful for debugging/monitoring)
    if settings.DEBUG or request.GET.get('debug') == '1':
        response_data['_cache'] = {
            'hit': cache_hit,
            'stale': is_stale,
            'timestamp': cache_result.get('timestamp'),
            'age_seconds': cache_result.get('age_seconds'),
        }
    
    return JsonResponse(response_data, status=200)
