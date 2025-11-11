# backend/inventory/migrations/0011_populate_spatial_fields.py
"""
Phase 10: Data migration to convert path_coordinates JSON -> path LineString.

This migration:
1. Iterates all RouteSegment and FiberCable instances
2. Converts path_coordinates [{lat, lng}] -> LineString([(lng, lat)])
3. Handles errors gracefully (logs + skips invalid data)
4. Only runs when DB_ENGINE=postgis (safe for MySQL deployments)
"""
from django.contrib.gis.geos import LineString
from django.db import migrations


def convert_json_to_linestring(path_coords):
    """
    Convert path_coordinates JSON to LineString geometry.
    
    Args:
        path_coords: List of dicts [{'lat': -15.7, 'lng': -47.9}, ...]
        
    Returns:
        LineString or None if conversion fails
    """
    if not path_coords or not isinstance(path_coords, list):
        return None
    
    if len(path_coords) < 2:
        # LineString requires at least 2 points
        return None
    
    try:
        # Extract (lng, lat) tuples - IMPORTANT: PostGIS uses (lng, lat) order!
        points = []
        for coord in path_coords:
            if not isinstance(coord, dict):
                return None
            
            lat = coord.get('lat')
            lng = coord.get('lng')
            
            if lat is None or lng is None:
                return None
            
            # Validate coordinate ranges
            if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                return None
            
            points.append((float(lng), float(lat)))
        
        # Create LineString with SRID 4326 (WGS84)
        return LineString(points, srid=4326)
    
    except (ValueError, TypeError, AttributeError):
        return None


def populate_routesegment_spatial_fields(apps, schema_editor):
    """Convert RouteSegment.path_coordinates -> path"""
    from django.conf import settings
    
    # Only run for PostGIS backend
    db_engine = getattr(settings, 'DB_ENGINE', 'mysql')
    if db_engine != 'postgis':
        print("SKIP: spatial migration requires DB_ENGINE=postgis")
        return
    
    RouteSegment = apps.get_model('inventory', 'RouteSegment')
    
    total = RouteSegment.objects.count()
    converted = 0
    skipped = 0
    errors = 0
    
    print(f"\nConverting {total} RouteSegment records...")
    
    for segment in RouteSegment.objects.all():
        if not segment.path_coordinates:
            skipped += 1
            continue
        
        linestring = convert_json_to_linestring(segment.path_coordinates)
        
        if linestring:
            segment.path = linestring
            segment.save(update_fields=['path'])
            converted += 1
        else:
            errors += 1
            print(
                f"WARN: RouteSegment {segment.id} has invalid coordinates"
            )
    
    print(
        f"DONE: RouteSegment converted={converted} skipped={skipped}"
        f" errors={errors}"
    )


def populate_fibercable_spatial_fields(apps, schema_editor):
    """Convert FiberCable.path_coordinates -> path"""
    from django.conf import settings
    
    # Only run for PostGIS backend
    db_engine = getattr(settings, 'DB_ENGINE', 'mysql')
    if db_engine != 'postgis':
        return
    
    FiberCable = apps.get_model('inventory', 'FiberCable')
    
    total = FiberCable.objects.count()
    converted = 0
    skipped = 0
    errors = 0
    
    print(f"\nConverting {total} FiberCable records...")
    
    for cable in FiberCable.objects.all():
        if not cable.path_coordinates:
            skipped += 1
            continue
        
        linestring = convert_json_to_linestring(cable.path_coordinates)
        
        if linestring:
            cable.path = linestring
            cable.save(update_fields=['path'])
            converted += 1
        else:
            errors += 1
            print(
                f"WARN: FiberCable {cable.id} has invalid coordinates"
            )
    
    print(
        f"DONE: FiberCable converted={converted} skipped={skipped}"
        f" errors={errors}"
    )


def reverse_migration(apps, schema_editor):
    """Rollback: clear spatial fields"""
    from django.conf import settings
    
    db_engine = getattr(settings, 'DB_ENGINE', 'mysql')
    if db_engine != 'postgis':
        return
    
    RouteSegment = apps.get_model('inventory', 'RouteSegment')
    FiberCable = apps.get_model('inventory', 'FiberCable')
    
    RouteSegment.objects.update(path=None)
    FiberCable.objects.update(path=None)
    
    print("ROLLBACK: spatial fields cleared")


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0010_add_spatial_fields'),
    ]

    operations = [
        migrations.RunPython(
            populate_routesegment_spatial_fields,
            reverse_migration,
        ),
        migrations.RunPython(
            populate_fibercable_spatial_fields,
            migrations.RunPython.noop,
        ),
    ]
