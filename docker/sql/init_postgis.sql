-- PostgreSQL + PostGIS Initialization Script
-- Executed automatically when PostGIS container starts for the first time

-- Enable PostGIS extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS postgis_raster;
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;
CREATE EXTENSION IF NOT EXISTS postgis_tiger_geocoder;

-- Verify PostGIS is working
SELECT postgis_full_version();

-- Set timezone to UTC (align with Django)
ALTER DATABASE app SET timezone TO 'UTC';

-- Grant necessary permissions to application user
GRANT ALL PRIVILEGES ON DATABASE app TO app;
GRANT ALL PRIVILEGES ON SCHEMA public TO app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO app;

-- Allow app user to create extensions (needed for Django migrations)
ALTER USER app WITH SUPERUSER;

-- Create schema for PostGIS if not exists
CREATE SCHEMA IF NOT EXISTS postgis;
GRANT ALL PRIVILEGES ON SCHEMA postgis TO app;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'PostGIS initialization complete. Version: %', postgis_full_version();
END $$;
