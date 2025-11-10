-- ============================================================================
-- Test database permissions setup for MariaDB
-- ============================================================================
--
-- Grants the `app` user the privileges required to:
-- 1. Create the test database (test_app)
-- 2. Run migrations
-- 3. Create/drop tables during test runs
-- 4. Insert/update/delete test data
--
-- Usage:
--   docker compose -f docker/docker-compose.yml exec db mariadb -u root -proot < scripts/setup_test_db_permissions.sql
-- Interactive alternative:
--   docker compose -f docker/docker-compose.yml exec db mariadb -u root -proot
-- Grant all privileges to user `app` so it can manage test databases
GRANT ALL PRIVILEGES ON *.* TO 'app'@'%' WITH GRANT OPTION;

-- Apply changes immediately
FLUSH PRIVILEGES;

-- Inspect the granted permissions
SHOW GRANTS FOR 'app'@'%';

-- Confirmation messages
SELECT 'OK: Test permissions configured successfully.' AS Status;
SELECT 'INFO: User app can now create/drop test databases.' AS Info;
