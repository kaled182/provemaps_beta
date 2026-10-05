# Testing Guide - MapsProveFiber

**Versão do produto**: ver [VERSION](../../VERSION)  
**Last Updated**: 2026-10-04  
**Target Audience**: Developers, QA Engineers

---

## 📖 Overview

This guide covers testing strategies, practices, and workflows for MapsProveFiber. We use pytest as our testing framework with comprehensive coverage requirements.

---

## 🎯 Testing Philosophy

### Principles

1. **Test-Driven Development (TDD)**: Write tests before implementation when possible
2. **Comprehensive Coverage**: aim for >80% (the CI gate is a ratchet, currently 52% across all apps; see [Coverage Targets](#-coverage-targets))
3. **Fast Feedback**: Tests should run quickly (< 2 minutes for full suite)
4. **Isolated Tests**: Each test should be independent and reproducible
5. **Readable Tests**: Tests serve as documentation

### Test Pyramid

```
        /\
       /  \  E2E Tests (Few)
      /____\
     /      \  Integration Tests (Some)
    /________\
   /          \  Unit Tests (Many)
  /____ ______\
```

---

## 🚀 Running Tests

### Quick Commands

Run the backend suite **from the repository root** (the root `pytest.ini` mirrors `backend/pytest.ini`; both set `DJANGO_SETTINGS_MODULE = settings.test`). `settings.test` uses SQLite by default; set `TEST_DB_ENGINE=postgis` (plus `DB_*`) to run against PostGIS like the CI. Install the tooling with `make requirements-dev`.

```bash
# Run all tests (make test)
pytest -q

# Run with verbose output
pytest -v

# Run specific test file
pytest backend/tests/test_smoke.py -v

# Run a specific directory / area
pytest -q backend/inventory/tests

# Run a specific test (file::Class::method, or -k)
pytest -q backend/inventory/tests/test_fibers_api.py -k "some_name"

# Run tests matching pattern
pytest -k "test_site" -v

# Fast subset (skip slow and integration markers)
pytest -q -m "not slow and not integration"

# Stop on first failure
pytest -x

# Show local variables on failure
pytest -l

# Run last failed tests
pytest --lf

# Run failed first, then rest
pytest --ff
```

### Coverage Reports

```bash
# Run with coverage (make test-coverage)
pytest --cov --cov-report=html

# View coverage report
xdg-open htmlcov/index.html

# Coverage for specific module
pytest --cov=inventory --cov-report=term

# Coverage with missing lines
pytest --cov --cov-report=term-missing

# Same as CI: run from backend/ (branch coverage over all first-party apps,
# configured in [tool.coverage.run] of backend/pyproject.toml)
cd backend && coverage run -m pytest -q && coverage report --fail-under=52
```

### Docker Testing

```bash
# Run tests in Docker (dev stack; container workdir is /app/backend)
docker compose -f docker/docker-compose.yml exec web pytest -q

# Run with coverage in Docker
docker compose -f docker/docker-compose.yml exec web pytest --cov --cov-report=html

# Copy coverage report from container
docker compose -f docker/docker-compose.yml cp web:/app/backend/htmlcov ./htmlcov
```

### Frontend Testing

```bash
cd frontend
npm ci
npm run test:unit      # Vitest (unit/component tests in frontend/tests)
npm run test:e2e       # Playwright (specs in frontend/tests/e2e)
```

---

## 📁 Test Structure

### Directory Layout

```
backend/
├── conftest.py                 # Global fixtures
├── pytest.ini                  # Pytest configuration (root pytest.ini mirrors it)
├── tests/                      # Global tests (smoke, Zabbix client, cache, metrics, spatial ...)
├── core/tests/
├── maps_view/tests/
├── setup_app/tests/
├── monitoring/tests/
├── inventory/
│   ├── tests/                  # usecases, API, KML, fusion, Zabbix history ...
│   └── routes/tests/
└── service_accounts/tests/
frontend/tests/                 # Vitest (unit, components) and Playwright (e2e/)
```

### Test Naming Conventions

```python
# Files
test_<module>.py              # e.g., test_models.py

# Classes
class Test<Feature>:          # e.g., TestSiteModel

# Methods
def test_<action>_<expected>: # e.g., test_create_site_success
def test_<action>_<condition>_<expected>:  # e.g., test_create_site_duplicate_name_fails
```

---

## 🧪 Writing Tests

> The snippets below are illustrative: file names such as `test_models.py` / `test_api.py` and some model fields (e.g. `is_active`, `port_type`) are examples, not existing code. Look at `backend/inventory/tests/` and `backend/tests/` for real tests. The models live in `inventory` (`inventory.models`); the `zabbix_api_*` names are only inherited database table names.

### Unit Tests

Test individual functions/methods in isolation.

```python
# backend/inventory/tests/test_models.py
import pytest
from inventory.models import Site

@pytest.mark.django_db
class TestSiteModel:
    def test_site_creation(self):
        """Site can be created with valid data"""
        site = Site.objects.create(
            name="HQ",
            latitude=-23.5505,
            longitude=-46.6333
        )
        assert site.name == "HQ"
        assert site.is_active is True
        assert str(site) == "HQ"
    
    def test_site_unique_name(self):
        """Site names must be unique"""
        Site.objects.create(name="HQ", latitude=0, longitude=0)
        
        with pytest.raises(Exception):  # IntegrityError
            Site.objects.create(name="HQ", latitude=0, longitude=0)
    
    def test_site_coordinates_validation(self):
        """Site coordinates must be valid"""
        site = Site.objects.create(
            name="Test",
            latitude=91,  # Invalid
            longitude=0
        )
        # Validation should fail
        with pytest.raises(ValidationError):
            site.full_clean()
```

### Integration Tests

Test multiple components working together.

```python
# backend/inventory/tests/test_api.py
import pytest
from rest_framework.test import APIClient
from inventory.models import Site

@pytest.mark.django_db
class TestSiteAPI:
    def setup_method(self):
        self.client = APIClient()
        self.url = "/api/v1/inventory/sites/"
    
    def test_list_sites(self):
        """GET /api/v1/inventory/sites/ returns site list"""
        Site.objects.create(name="Site1", latitude=0, longitude=0)
        Site.objects.create(name="Site2", latitude=1, longitude=1)
        
        response = self.client.get(self.url)
        
        assert response.status_code == 200
        assert len(response.json()) == 2
    
    def test_create_site(self):
        """POST /api/v1/inventory/sites/ creates new site"""
        data = {
            "name": "New Site",
            "latitude": -23.5505,
            "longitude": -46.6333
        }
        
        response = self.client.post(self.url, data, format="json")
        
        assert response.status_code == 201
        assert Site.objects.filter(name="New Site").exists()
    
    def test_create_site_invalid_data(self):
        """POST with invalid data returns 400"""
        data = {"name": ""}  # Missing required fields
        
        response = self.client.post(self.url, data, format="json")
        
        assert response.status_code == 400
```

### Smoke Tests

High-level tests to verify critical functionality.

```python
# backend/tests/test_smoke.py
import pytest
from django.test import Client

@pytest.mark.django_db
class TestSmoke:
    def setup_method(self):
        self.client = Client()
    
    def test_health_check(self):
        """Health check endpoint is accessible"""
        response = self.client.get("/healthz")
        assert response.status_code == 200
    
    def test_admin_accessible(self):
        """Admin panel is accessible"""
        response = self.client.get("/admin/")
        assert response.status_code == 302  # Redirect to login
    
    def test_api_root_accessible(self):
        """API root is accessible"""
        response = self.client.get("/api/v1/inventory/")
        assert response.status_code == 200
```

---

## 🔧 Fixtures

### Pytest Fixtures

```python
# backend/inventory/tests/conftest.py
import pytest
from inventory.models import Site, Device, Port

@pytest.fixture
def site():
    """Create a test site"""
    return Site.objects.create(
        name="Test Site",
        latitude=-23.5505,
        longitude=-46.6333
    )

@pytest.fixture
def device(site):
    """Create a test device"""
    return Device.objects.create(
        name="OLT-01",
        site=site,
        device_type="OLT",
        ip_address="192.168.1.1"
    )

@pytest.fixture
def port(device):
    """Create a test port"""
    return Port.objects.create(
        device=device,
        port_number=1,
        port_type="GPON"
    )

@pytest.fixture
def api_client():
    """Create API client"""
    from rest_framework.test import APIClient
    return APIClient()

@pytest.fixture
def authenticated_client(api_client, django_user_model):
    """Create authenticated API client"""
    user = django_user_model.objects.create_user(
        username="testuser",
        password="testpass123"
    )
    api_client.force_authenticate(user=user)
    return api_client
```

### Using Fixtures

```python
def test_device_has_site(device, site):
    """Device is associated with site"""
    assert device.site == site
    assert device.site.name == "Test Site"

def test_create_port_via_api(authenticated_client, device):
    """Authenticated user can create port"""
    url = "/api/v1/inventory/ports/"
    data = {
        "device": device.id,
        "port_number": 2,
        "port_type": "GPON"
    }
    
    response = authenticated_client.post(url, data, format="json")
    assert response.status_code == 201
```

---

## 🎭 Mocking & Patching

### Mock External Services

```python
# illustrative; the real client tests are in backend/tests/test_resilient_zabbix_client.py
import pytest
from unittest.mock import patch, Mock
from integrations.zabbix.client import ZabbixClient

class TestZabbixClient:
    @patch('integrations.zabbix.client.requests.post')
    def test_authenticate_success(self, mock_post):
        """Successful authentication returns token"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "result": "auth_token_123"
        }
        mock_post.return_value = mock_response
        
        client = ZabbixClient(
            url="http://zabbix.test",
            user="admin",
            password="secret"
        )
        token = client.authenticate()
        
        assert token == "auth_token_123"
        mock_post.assert_called_once()
    
    @patch('integrations.zabbix.client.requests.post')
    def test_authenticate_failure(self, mock_post):
        """Failed authentication raises exception"""
        mock_post.side_effect = Exception("Connection error")
        
        client = ZabbixClient(
            url="http://zabbix.test",
            user="admin",
            password="wrong"
        )
        
        with pytest.raises(Exception):
            client.authenticate()
```

### Mock Cache

```python
@pytest.fixture
def mock_cache():
    """Mock Django cache"""
    with patch('django.core.cache.cache') as mock:
        mock.get.return_value = None
        mock.set.return_value = True
        yield mock

def test_cache_miss(mock_cache):
    """Function handles cache miss"""
    from maps_view.cache_swr import get_dashboard_cached
    
    result = get_dashboard_cached()
    
    mock_cache.get.assert_called_once()
    # Function should fetch fresh data
```

---

## 📊 Test Markers

### Built-in Markers

```python
@pytest.mark.django_db
def test_database_access():
    """Test that accesses database"""
    pass

@pytest.mark.slow
def test_long_running():
    """Test that takes >1 second"""
    pass

@pytest.mark.skip(reason="Not implemented yet")
def test_future_feature():
    pass

@pytest.mark.skipif(condition, reason="Conditional skip")
def test_conditional():
    pass

@pytest.mark.xfail
def test_expected_failure():
    """Test expected to fail"""
    pass

@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 3),
    (3, 4),
])
def test_increment(input, expected):
    assert input + 1 == expected
```

### Custom Markers

```python
# backend/pytest.ini (excerpt; `--strict-markers` is on, so register new markers here)
[pytest]
markers =
    slow: slow tests (run with --slow or -m "slow")
    integration: integration tests (require external services)
    unit: unit tests (isolated and fast)
    db: tests using the database
    celery: Celery task tests
    zabbix: Zabbix integration tests
    maps: maps/geolocation tests

# Usage
@pytest.mark.integration
def test_full_workflow():
    pass

# Run only unit tests
pytest -m unit

# Run all except slow tests
pytest -m "not slow"
```

---

## 🔄 Continuous Integration

### GitHub Actions

The workflow lives in `.github/workflows/tests.yml` (jobs `pytest` and `frontend-unit`). Backend job, abridged:

```yaml
# .github/workflows/tests.yml (abridged)
jobs:
  pytest:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgis/postgis:16-3.4
        env:
          POSTGRES_DB: app
          POSTGRES_USER: app
          POSTGRES_PASSWORD: app
        ports:
          - 5432:5432
    env:
      DJANGO_SETTINGS_MODULE: settings.test
      DB_ENGINE: postgis
      TEST_DB_ENGINE: postgis
      DB_NAME: app
      DB_USER: app
      DB_PASSWORD: app
      DB_HOST: 127.0.0.1
      DB_PORT: "5432"
    steps:
      - uses: actions/checkout@v4
      - run: sudo apt-get update && sudo apt-get install -y gdal-bin libgdal-dev libgeos-dev postgresql-client
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - run: pip install -r backend/requirements-dev.txt
      - working-directory: backend
        run: python manage.py migrate --noinput && python manage.py check --tag gis
      - working-directory: backend
        run: coverage run -m pytest -q && coverage report --show-missing --fail-under=52 && coverage xml

  frontend-unit:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - run: npm ci --no-audit --no-fund
      - run: npm run test:unit
```

---

## 🎯 Coverage Targets

### Minimum Requirements

- **Overall (target)**: 80%
- **Critical Paths**: 95% minimum (auth, data integrity)
- **New Code**: 90% minimum

> The CI gate is a ratchet, not the 80% target: since EV-0006 it measures all first-party apps (branch coverage) and fails below the `--fail-under` value in `.github/workflows/tests.yml` (currently 52%). Raise it whenever a change adds tests.

### Checking Coverage

```bash
# Generate report
pytest --cov --cov-report=term-missing

# Fail if below the CI threshold (run from backend/)
cd backend && coverage run -m pytest -q && coverage report --fail-under=52

# Coverage by module
pytest --cov=inventory --cov=monitoring --cov-report=term
```

### Excluded from Coverage

Coverage settings live in `backend/pyproject.toml` (`[tool.coverage.run]` / `[tool.coverage.report]`), not in a `.coveragerc`:

```toml
[tool.coverage.run]
branch = true
source = ["core", "maps_view", "setup_app", "inventory", "integrations", "monitoring", "service_accounts", ...]
```

---

## 🐛 Debugging Tests

### Print Debugging

```python
def test_example():
    result = some_function()
    print(f"Result: {result}")  # Visible with pytest -s
    assert result == expected
```

Run with `-s` to see prints:
```bash
pytest -s
```

### Interactive Debugging

```python
def test_example():
    result = some_function()
    breakpoint()  # Drop into debugger
    assert result == expected
```

Or use `pytest --pdb` to break on failures.

### Verbose Output

```bash
# Show all test names
pytest -v

# Show local variables on failure
pytest -l

# Show full diff on assertion failure
pytest -vv
```

---

## 📚 Best Practices

### Do's

✅ **One assertion per test** (when possible)  
✅ **Use descriptive test names**  
✅ **Test edge cases and error conditions**  
✅ **Keep tests independent**  
✅ **Use fixtures to reduce duplication**  
✅ **Test behavior, not implementation**  
✅ **Write tests for bugs before fixing**

### Don'ts

❌ **Don't test framework code** (e.g., Django ORM)  
❌ **Don't use sleep()** (use proper waits/mocks)  
❌ **Don't share state between tests**  
❌ **Don't skip tests without good reason**  
❌ **Don't test multiple things in one test**  
❌ **Don't commit commented-out tests**

---

## 🚀 Performance Testing

### Load Testing with Locust

```python
# locustfile.py
from locust import HttpUser, task, between

class DashboardUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(3)
    def view_dashboard(self):
        self.client.get("/maps_view/dashboard/")
    
    @task(1)
    def view_api(self):
        self.client.get("/api/v1/inventory/sites/")
```

Run:
```bash
locust -f locustfile.py --host=http://localhost:8100   # Docker dev stack; `make run` serves on 8000
# (locust is not in backend/requirements-dev.txt: `pip install locust`)
```

---

## 📖 Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [Django Testing Documentation](https://docs.djangoproject.com/en/5.2/topics/testing/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Development Guide](DEVELOPMENT.md)
- CI workflow: [`.github/workflows/tests.yml`](../../.github/workflows/tests.yml)
- [Testing Standards](../contributing/TESTING_STANDARDS.md)

---

**Last Updated**: 2026-10-04  
**Maintainers**: QA Team, Development Team
