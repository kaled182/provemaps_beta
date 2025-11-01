-- Initializes application database users and ensure test database grants.
CREATE DATABASE IF NOT EXISTS `test_app`;
GRANT ALL PRIVILEGES ON `app`.* TO 'app'@'%';
GRANT ALL PRIVILEGES ON `test_app`.* TO 'app'@'%';
FLUSH PRIVILEGES;
