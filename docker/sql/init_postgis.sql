-- PostgreSQL + PostGIS Initialization Script
-- Executed automatically when PostGIS container starts for the first time

-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS postgis_raster;
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;
CREATE EXTENSION IF NOT EXISTS postgis_tiger_geocoder;

-- Create spatial_ref_sys if not exists (usually auto-created by PostGIS)
-- This ensures SRID 4326 (WGS84) is available
SELECT postgis_full_version();

-- Create GiST indexes on geometry columns (will be created via migrations)
-- But we can prepare the database for optimal spatial performance

-- Set timezone to UTC (align with Django)
ALTER DATABASE mapsprovefiber SET timezone TO 'UTC';

-- Grant necessary permissions to application user
GRANT ALL PRIVILEGES ON DATABASE mapsprovefiber TO provemaps;
GRANT ALL PRIVILEGES ON SCHEMA public TO provemaps;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO provemaps;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO provemaps;

-- Allow provemaps user to create extensions (needed for Django migrations)
ALTER USER provemaps WITH SUPERUSER;

-- Create schema for PostGIS if not exists
CREATE SCHEMA IF NOT EXISTS postgis;
GRANT ALL PRIVILEGES ON SCHEMA postgis TO provemaps;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'PostGIS initialization complete. Version: %', postgis_full_version();
END $$;
