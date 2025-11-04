# MariaDB Testing Guide (Docker)

**Date:** 27 October 2025  
**Goal:** Run pytest against MariaDB (Docker) instead of SQLite

---

## 🎯 Why run tests against MariaDB?

### ✅ Advantages
- **Production parity:** Same engine and SQL dialect as production.
- **Constraint validation:** Exercises MariaDB-specific constraints.
- **Incompatibility detection:** Catches bugs SQLite would miss.
- **Real migrations:** Validates migrations under MariaDB.

### ⚠️ Trade-offs
- **Slower:** roughly 10–15× slower than SQLite (0.8s → 10–15s).
- **Docker required:** containers must be up.
- **Initial setup:** permissions must be granted once.

---

## 🚀 Initial Setup (one time)

### 1. Start Docker containers

```powershell
# From the project root
docker compose up -d

# Confirm they are running
docker compose ps
```

### 2. Grant database permissions

```powershell
# Run the automated script
.\scripts\setup_test_db.ps1
```

**What the script does:**
1. ✅ Checks that containers are running.
2. ✅ Grants `CREATE/DROP DATABASE` to user `app`.
3. ✅ Exercises database create/drop.
4. ✅ Verifies everything is configured.

**Expected output:**
```
🔧 Configuring MariaDB test permissions...
═══════════════════════════════════════════════════

1️⃣  Checking Docker...
   ✅ Docker is running

2️⃣  Checking MariaDB container...
   ✅ Service located: db

3️⃣  Configuring permissions...
   ✅ Permissions applied successfully

4️⃣  Validating permissions...
   ✅ User 'app' holds the right grants

5️⃣  Testing database creation...
   ✅ User 'app' can create/drop databases

═══════════════════════════════════════════════════
✅ Setup finished successfully!
```

### 3. Manual alternative: grant permissions yourself

If you prefer to do it manually:

```powershell
# Connect to the MariaDB service as root
docker compose exec db mariadb -u root -proot

# Run the SQL
GRANT ALL PRIVILEGES ON *.* TO 'app'@'%' WITH GRANT OPTION;
FLUSH PRIVILEGES;
EXIT;
```

---

## 🧪 Running Tests

### Option 1: automated script (recommended)

```powershell
# All tests
.\scripts\run_tests.ps1

# Specific tests
.\scripts\run_tests.ps1 -Path tests/test_metrics.py

# With coverage
.\scripts\run_tests.ps1 -Coverage

# Verbose mode
.\scripts\run_tests.ps1 -Verbose

# Reuse database (faster for multiple runs)
.\scripts\run_tests.ps1 -KeepDb
```

### Option 2: direct Docker command

```powershell
# Run pytest inside the container
docker compose exec web bash -lc "DJANGO_SETTINGS_MODULE=settings.test pytest tests/ -v"

# With coverage
docker compose exec web bash -lc "DJANGO_SETTINGS_MODULE=settings.test pytest tests/ -v --cov=core --cov-report=html"
```

### Option 3: attach to the container (interactive shell)

```powershell
# Enter the container
docker compose exec web bash

# Inside the container
export DJANGO_SETTINGS_MODULE=settings.test
pytest tests/ -v
pytest tests/test_metrics.py::TestMetricsInitialization::test_init_metrics_sets_application_info -vvs
exit
```

---

## 📊 Test Structure

### Test databases

**Primary database:** `app`  
**Test database:** `test_app` (auto-created and dropped)

```python
# settings/test.py
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "app",  # Primary DB
        "USER": "app",
        "PASSWORD": "app",
        "HOST": "db",  # Service name in docker-compose.yml
        "PORT": "3306",
        "TEST": {
            # pytest-django auto-creates 'test_app'
            "CHARSET": "utf8mb4",
            "COLLATION": "utf8mb4_unicode_ci",
        },
    }
}
```

### Test database lifecycle

```
pytest starts
   ↓
Connects to MariaDB (host='db', database='app')
   ↓
Creates 'test_app' (DROP IF EXISTS + CREATE)
   ↓
Runs migrations on 'test_app'
   ↓
Executes tests
   ↓
Drops 'test_app' (DROP DATABASE)
   ↓
pytest exits
```

---

## 🔍 Troubleshooting

### Error: Access denied (1044)

```
E   django.db.utils.OperationalError: (1044, "Access denied for user 'app'@'%' to database 'test_app'")
```

**Cause:** user `app` cannot create databases.

**Fix:**
```powershell
.\scripts\setup_test_db.ps1
```

---

### Error: Can't connect to MySQL server (2002)

```
E   django.db.utils.OperationalError: (2002, "Can't connect to server on 'db' (115)")
```

**Cause:** MariaDB container is not running.

**Fix:**
```powershell
docker compose up -d
docker compose ps  # Ensure the db service is Up
```

---

### Error: Access denied (1045)

```
E   pymysql.err.OperationalError: (1045, "Access denied for user 'app'@'%' (using password: YES)")
```

**Cause:** Incorrect password.

**Fix:** check environment variables in `docker-compose.yml`
```yaml
environment:
   - DB_PASSWORD=app  # Must match settings/test.py
```

---

### Tests feel slow

**Cause:** MariaDB is slower than SQLite.

**Options:**

1. **Use `--reuse-db`** (keeps the database between runs):
```powershell
.\scripts\run_tests.ps1 -KeepDb
```

2. **Run only the tests you changed:**
```powershell
.\scripts\run_tests.ps1 -Path tests/test_metrics.py
```

3. **For fast dev loops, switch to SQLite:**
```powershell
# Create settings/test_sqlite.py (copy of the old test.py)
$env:DJANGO_SETTINGS_MODULE='settings.test_sqlite'
pytest tests/
```

---

## 📈 Comparison: MariaDB vs SQLite

| Aspect | MariaDB (Docker) | SQLite (in-memory) |
|--------|------------------|--------------------|
| **Speed** | ~10–15s (35 tests) | ~0.8s (35 tests) |
| **Setup** | Docker + grants | Zero config |
| **Production parity** | ✅ Identical | ⚠️ Different |
| **CI/CD** | ⚠️ Requires Docker | ✅ Simple |
| **Isolation** | ✅ Good (`test_app`) | ✅ Perfect (`:memory:`) |
| **Best use** | ✅ Integration tests | ✅ Fast unit tests |

### Hybrid recommendation

```powershell
# Local development (fast)
$env:DJANGO_SETTINGS_MODULE='settings.test_sqlite'
pytest tests/

# Pre-commit (full validation)
.\scripts\run_tests.ps1 -Coverage

# CI/CD (GitHub Actions)
# Use MariaDB via services
```

---

## 🎯 Best Practices

### 1. Separate tests by type

```
tests/
├── unit/              # Fast, no DB (use SQLite)
├── integration/       # Slower, hits DB (use MariaDB)
└── e2e/               # Very slow (Selenium, etc.)
```

### 2. Use efficient fixtures

```python
# conftest.py
import pytest

@pytest.fixture(scope="session")
def django_db_setup():
    """Set up the database once per session."""
    pass

@pytest.fixture
def sample_device(db):
    """Reusable helper to create a device."""
    from inventory.models import Device
    return Device.objects.create(name="Test Device")
```

### 3. Use transactions

```python
@pytest.mark.django_db(transaction=True)
def test_with_transaction():
   # Each test runs in an isolated transaction
   # Automatic rollback after the test
   pass
```

### 4. Mock external calls

```python
from unittest.mock import patch

@patch('zabbix_api.client.ZabbixAPIClient.request')
def test_zabbix_integration(mock_request):
    mock_request.return_value = {"result": []}
   # Test avoids real calls to the Zabbix API
```

---

## 📚 References

- [pytest-django Documentation](https://pytest-django.readthedocs.io/)
- [Django Test Database](https://docs.djangoproject.com/en/5.0/topics/testing/overview/#the-test-database)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

---

**Created on:** 27/10/2025  
**Author:** GitHub Copilot  
**Version:** 2.0 – MariaDB Integration
