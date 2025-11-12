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
from inventory.models import FiberCable
from inventory.models_routes import RouteSegment

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
