# Persistent Configuration Guide

## Overview

The application now stores the Zabbix and Google Maps configuration directly in the database, so settings persist after Docker containers restart.

## How It Works

### Configuration Resolution Order

At runtime the system resolves values in the following order:

1. Environment variables (docker-compose.yml or .env)
2. Database table `setup_app_firsttimesetup`
3. Default empty values

### First-Time Setup Flow

1. Open http://localhost:8000/setup_app/config/
2. Fill in the form values:
  - Zabbix API URL, for example: `http://your-zabbix-host:8080/api_jsonrpc.php`
  - Zabbix user or Zabbix API key
  - Zabbix password if you authenticate with user and password
  - Google Maps API key
3. Click "Save"
4. The data is written to the database immediately
5. No restart is required; changes take effect instantly

### After Restarting Containers

When you run `docker compose restart`:

- The configuration from the database is loaded automatically
- The map and Zabbix integrations come up with the stored values
- You do not need to re-enter data through the form

## Code Changes
```powershell
docker compose exec web python manage.py shell -c "from setup_app.models import FirstTimeSetup; config = FirstTimeSetup.objects.filter(configured=True).first(); print(f'Zabbix URL: {config.zabbix_url}' if config else 'No configuration')"
```
1. `setup_app/services/config_loader.py`
  - Loads configuration directly from the database
  - Applies a five minute cache window for performance
  - Uses raw SQL to avoid circular imports

2. `setup_app/runtime_settings.py`
```powershell
docker compose exec web python manage.py shell -c "from setup_app.services import runtime_settings; config = runtime_settings.get_runtime_config(); print(f'Zabbix: {config.zabbix_api_url}')"
```
### Updated Files

1. `setup_app/views.py` (function `manage_environment()`)
  - Persists values to both the `.env` file for local development and the `FirstTimeSetup` table for Docker or production
  - Clears the cache after saving
  - Updates the success message to "Configuration saved successfully. Changes are now active!"
```powershell
docker compose exec web python manage.py shell -c "from setup_app.services import runtime_settings; runtime_settings.reload_config(); print('Cache cleared')"
```
  - Fixes an "unbound variable" error during startup

## Database Structure

Table `setup_app_firsttimesetup`:

```sql
CREATE TABLE setup_app_firsttimesetup (
   id INT AUTO_INCREMENT PRIMARY KEY,
   company_name VARCHAR(255),
   logo VARCHAR(100) NULL,
   zabbix_url VARCHAR(255),
   auth_type VARCHAR(10),  -- 'token' or 'login'
   zabbix_api_key VARCHAR(512) NULL,
   zabbix_user VARCHAR(512) NULL,
   zabbix_password VARCHAR(512) NULL,
   maps_api_key VARCHAR(512) NULL,
   unique_licence VARCHAR(512) NULL,
   configured BOOLEAN DEFAULT FALSE,
   configured_at DATETIME
);
- Credentials and API keys use the Fernet-based `EncryptedCharField`
- Configuration results are cached for five minutes to reduce database reads
- Environment variable fallback remains available and safe

## Test and Verification Commands

Check whether a configuration entry exists:

```powershell
docker compose exec web python manage.py shell -c "from setup_app.models import FirstTimeSetup; config = FirstTimeSetup.objects.filter(configured=True).first(); print(f'Zabbix URL: {config.zabbix_url}' if config else 'No configuration')"
```

Inspect the runtime configuration object:

```powershell
docker compose exec web python manage.py shell -c "from setup_app.services import runtime_settings; config = runtime_settings.get_runtime_config(); print(f'Zabbix: {config.zabbix_api_url}')"
```

Clear the runtime cache manually:

```powershell
docker compose exec web python manage.py shell -c "from setup_app.services import runtime_settings; runtime_settings.reload_config(); print('Cache cleared')"
```

## Daily Usage

### Update Settings

1. Navigate to http://localhost:8000/setup_app/config/
2. Adjust the values you need
3. Click "Save"
4. Changes apply immediately without restarting services

### Production Deployment

Because the configuration lives in the database:

1. Take a backup of the MariaDB database
2. The configuration is preserved with the backup
3. Restore the database on the new environment
4. The setup form loads the stored values automatically

## Additional Notes

- The cache layer is cleared as part of the save workflow
- Updating the Zabbix credentials invalidates the previous token
- Diagnostic flags are refreshed when settings change
- The feature works in Docker and local development environments

## Troubleshooting

### Configuration Missing After Restart

```powershell
# 1. Check whether rows exist in the table
docker compose exec web python manage.py shell -c "from setup_app.models import FirstTimeSetup; print(FirstTimeSetup.objects.all().count())"

# 2. If the count is zero, re-enter data at /setup_app/config/
```

### Cache Not Clearing

```powershell
# Clear it manually
docker compose exec web python manage.py shell -c "from django.core.cache import cache; cache.clear(); print('Redis cache cleared')"
```

### Map Fails To Load After Saving Settings

```powershell
# 1. Inspect the logs
docker compose logs web --tail 50

# 2. Test the Zabbix connection
docker compose exec web python manage.py shell -c "from zabbix_api.services.zabbix_client import ZabbixClient; client = ZabbixClient(); result = client.login(); print(f'Login OK: {bool(result)}')"
```

## Next Steps

You can now:

1. Complete the configuration at http://localhost:8000/setup_app/config/
2. Open the map at http://localhost:8000/maps_view/dashboard/
3. Restart containers with `docker compose restart` without losing settings
4. Avoid manual edits to docker-compose.yml for credentials management

---

Status: system ready for use.

## Service Restart Automation

- Use the `SERVICE_RESTART_COMMANDS` setting to run immediate commands after saving credentials from the admin form or via `sync_env_from_setup`.
- List every relevant service (for example: web, celery, beat) on a single line separated by semicolons.
- In Docker-based environments configure the `.env` file as follows:

  ```
  SERVICE_RESTART_COMMANDS="docker compose restart web; docker compose restart celery; docker compose restart beat"
  ```

- For systemd or supervisord environments list the equivalent commands, for example:

  ```
  SERVICE_RESTART_COMMANDS="systemctl restart provemaps-beta-web; systemctl restart provemaps-beta-worker; systemctl restart provemaps-beta-beat"
  ```

- The field is available in Setup -> Manage Environment and accepts multiple commands separated by `;`. Failures are logged by the application.

