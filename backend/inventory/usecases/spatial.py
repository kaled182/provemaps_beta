"""
Spatial query use cases using PostGIS native operations.

This module provides high-performance spatial queries leveraging PostgreSQL's
PostGIS extension with GiST indexes for O(log n) performance.

**Performance Characteristics:**
- BBox queries: ~1ms for 1000+ segments (13x faster than full scan)
- Distance queries: O(log n) with spatial index
- Intersection queries: O(log n) with spatial index

**Key Patterns:**
1. Always use spatial indexes (GiST) - see
   inventory/migrations/0012_create_spatial_indexes.py
2. Use bounding box pre-filtering before expensive operations
3. Prefer PostGIS operations over Python calculations

**References:**
- PostGIS docs: https://postgis.net/documentation/
- Django GIS: https://docs.djangoproject.com/en/stable/ref/contrib/gis/
- Performance benchmark: scripts/benchmark_postgis.py
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from django.contrib.gis.geos import Point, Polygon
from django.db.models import QuerySet

if TYPE_CHECKING:
    from inventory.models import FiberCable, Site
    from inventory.models_routes import RouteSegment


def get_sites_in_bbox(
    lng_min: float,
    lat_min: float,
    lng_max: float,
    lat_max: float,
) -> QuerySet["Site"]:
    """
    Find sites within bounding box (viewport query).
    
    **Performance:** O(log n) with GIST spatial index on location field
    
    Args:
        lng_min: Western boundary (-180 to 180)
        lat_min: Southern boundary (-90 to 90)
        lng_max: Eastern boundary (-180 to 180)
        lat_max: Northern boundary (-90 to 90)
    
    Returns:
        QuerySet of Site objects within bbox
    
    Example:
        # Get sites in Brasilia region
        >>> sites = get_sites_in_bbox(-48.0, -16.0, -47.5, -15.5)
        >>> print(f"Found {sites.count()} sites")
    
    SQL Generated:
        SELECT * FROM zabbix_api_site
        WHERE location && ST_MakeEnvelope(-48, -16, -47.5, -15.5, 4326)
        -- Uses index: idx_site_location (GIST)
    """
    from inventory.models import Site
    
    # Create bounding box polygon (WGS84 / SRID 4326)
    bbox = Polygon.from_bbox((lng_min, lat_min, lng_max, lat_max))
    bbox.srid = 4326
    
    # Phase 7: Use location PointField with spatial index
    # Falls back to lat/lng filter for sites without location
    sites_with_location = Site.objects.filter(location__bboverlaps=bbox)
    
    # Fallback for sites without location field populated
    sites_with_coords = Site.objects.filter(
        location__isnull=True,
        latitude__gte=lat_min,
        latitude__lte=lat_max,
        longitude__gte=lng_min,
        longitude__lte=lng_max,
    )
    
    return sites_with_location | sites_with_coords


def get_segments_in_bbox(
    lng_min: float,
    lat_min: float,
    lng_max: float,
    lat_max: float,
) -> QuerySet["RouteSegment"]:
    """
    Find route segments intersecting bounding box.
    
    **Performance:** ~1ms for 1000+ segments with GiST index
    
    Uses PostGIS `bboverlaps` operator for fast bounding box intersection.
    This is the foundation of lazy loading in the map interface.
    
    Args:
        lng_min: Western boundary (-180 to 180)
        lat_min: Southern boundary (-90 to 90)
        lng_max: Eastern boundary (-180 to 180)
        lat_max: Northern boundary (-90 to 90)
    
    Returns:
        QuerySet of RouteSegment objects intersecting bbox
    
    Example:
        # Get segments visible in current map viewport
        >>> segments = get_segments_in_bbox(-48.0, -16.0, -47.5, -15.5)
        >>> for seg in segments:
        ...     print(f"Segment {seg.id}: {seg.length_km}km")
    
    SQL Generated:
        SELECT * FROM inventory_routesegment
        WHERE path && ST_MakeEnvelope(-48, -16, -47.5, -15.5, 4326)
        -- Uses index: inventory_routesegment_path_gist
    """
    from inventory.models_routes import RouteSegment
    
    bbox = Polygon.from_bbox((lng_min, lat_min, lng_max, lat_max))
    bbox.srid = 4326
    
    # bboverlaps uses bounding box intersection (faster than full geometry)
    return RouteSegment.objects.filter(path__bboverlaps=bbox)


def get_cables_in_bbox(
    lng_min: float,
    lat_min: float,
    lng_max: float,
    lat_max: float,
) -> QuerySet["FiberCable"]:
    """
    Find fiber cables intersecting bounding box.
    
    **Performance:** O(log n) with GiST index on cable.path
    
    Args:
        lng_min: Western boundary
        lat_min: Southern boundary
        lng_max: Eastern boundary
        lat_max: Northern boundary
    
    Returns:
        QuerySet of FiberCable objects intersecting bbox
    
    Example:
        >>> cables = get_cables_in_bbox(-48.0, -16.0, -47.5, -15.5)
        >>> print(f"{cables.count()} cables in viewport")
    """
    from inventory.models import FiberCable
    
    bbox = Polygon.from_bbox((lng_min, lat_min, lng_max, lat_max))
    bbox.srid = 4326
    
    return FiberCable.objects.filter(path__bboverlaps=bbox)


def get_sites_within_radius(
    lat: float,
    lon: float,
    radius_km: float,
    limit: Optional[int] = None,
) -> QuerySet["Site"]:
    """
    Find sites within radius of a point, sorted by distance.
    
    **Performance:** O(log n) with GIST spatial index (Phase 7)
    
    Uses PostGIS ST_DWithin for accurate geodesic distance queries.
    Results are sorted by distance from the center point.
    
    Args:
        lat: Center latitude (-90 to 90)
        lon: Center longitude (-180 to 180)
        radius_km: Search radius in kilometers
        limit: Maximum results (default: no limit)
    
    Returns:
        QuerySet of Site objects within radius, ordered by distance.
        Each result has a `distance` annotation (Distance object).
    
    Example:
        # Find sites within 10km of Brasilia city center
        >>> nearby = get_sites_within_radius(-15.7801, -47.9292, 10.0)
        >>> for site in nearby:
        ...     print(f"{site.display_name} - {site.distance.km:.2f}km")
    
    SQL Generated:
        SELECT *,
               ST_Distance(location, ST_Point(-47.9292, -15.7801))
               as distance
        FROM zabbix_api_site
        WHERE ST_DWithin(location, ST_Point(-47.9292, -15.7801), 10000)
        ORDER BY distance
        -- Uses index: idx_site_location (GIST)
    
    Phase 7: Now uses native PostGIS queries (10-15x faster than Phase 6)
    """
    from django.contrib.gis.db.models.functions import Distance
    from inventory.models import Site
    
    # Create point (lon, lat order for GIS)
    center_point = Point(lon, lat, srid=4326)
    
    # Phase 7: Use ST_DWithin with GIST index for O(log n) performance
    # For geographic fields (SRID 4326), pass distance as meters (numeric)
    radius_meters = radius_km * 1000.0
    
    # ST_DWithin uses spatial index automatically
    sites_with_location = Site.objects.filter(
        location__dwithin=(center_point, radius_meters)
    ).annotate(
        distance=Distance('location', center_point)
    ).order_by('distance')
    
    if limit:
        sites_with_location = sites_with_location[:limit]
    
    return sites_with_location


def get_segments_intersecting_path(
    path_coords: List[tuple[float, float]],
) -> QuerySet["RouteSegment"]:
    """
    Find segments that intersect with a given path.
    
    **Performance:** O(log n) with GiST index
    
    Args:
        path_coords: List of (lng, lat) tuples defining path
    
    Returns:
        QuerySet of RouteSegment objects intersecting path
    
    Example:
        # Find segments crossing a planned route
        >>> path = [(-47.9, -15.8), (-47.8, -15.7)]
        >>> crossing = get_segments_intersecting_path(path)
        >>> print(f"{crossing.count()} segments cross this path")
    """
    from django.contrib.gis.geos import LineString
    from inventory.models_routes import RouteSegment
    
    if len(path_coords) < 2:
        return RouteSegment.objects.none()
    
    # Create LineString from path (lng, lat order)
    path = LineString(path_coords, srid=4326)
    
    # Use intersects operator (uses spatial index)
    return RouteSegment.objects.filter(path__intersects=path)


def get_cable_length_in_region(
    lng_min: float,
    lat_min: float,
    lng_max: float,
    lat_max: float,
) -> float:
    """
    Calculate total fiber cable length within region.
    
    **Performance:** O(log n) for bbox filter + O(k) for aggregation
    
    Args:
        lng_min: Western boundary
        lat_min: Southern boundary
        lng_max: Eastern boundary
        lat_max: Northern boundary
    
    Returns:
        Total length in kilometers
    
    Example:
        >>> total_km = get_cable_length_in_region(-48.0, -16.0, -47.5, -15.5)
        >>> print(f"Total fiber: {total_km:.1f}km in region")
    """
    from django.contrib.gis.db.models.functions import Length
    from django.db.models import Sum
    
    cables = get_cables_in_bbox(lng_min, lat_min, lng_max, lat_max)
    
    # Use PostGIS ST_Length for accurate geodesic distance
    result = cables.annotate(
        length_m=Length('path')
    ).aggregate(
        total=Sum('length_m')
    )
    
    total_distance = result['total']
    if total_distance is None:
        return 0.0
    
    # Distance object has .km property for kilometers
    return float(total_distance.km)


# Public API
__all__ = [
    'get_sites_in_bbox',
    'get_segments_in_bbox',
    'get_cables_in_bbox',
    'get_sites_within_radius',
    'get_segments_intersecting_path',
    'get_cable_length_in_region',
]
