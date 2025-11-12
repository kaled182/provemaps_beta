# Testing Guide - MapsProveFiber

**Version**: v2.0.0  
**Last Updated**: 2025-11-10  
**Target Audience**: Developers, QA Engineers

---

## 📖 Overview

This guide covers testing strategies, practices, and workflows for MapsProveFiber. We use pytest as our testing framework with comprehensive coverage requirements.

---

## 🎯 Testing Philosophy

### Principles

1. **Test-Driven Development (TDD)**: Write tests before implementation when possible
2. **Comprehensive Coverage**: Maintain >80% code coverage
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

```powershell
# Run all tests
pytest -q

# Run with verbose output
pytest -v

# Run specific test file
pytest backend/tests/test_smoke.py -v

# Run specific test class
pytest backend/inventory/tests/test_models.py::TestSiteModel -v

# Run specific test method
pytest backend/inventory/tests/test_models.py::TestSiteModel::test_site_creation -v

# Run tests matching pattern
pytest -k "test_site" -v

# Run in parallel (faster)
pytest -n auto

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

```powershell
# Run with coverage
pytest --cov --cov-report=html

# View coverage report
start htmlcov/index.html

# Coverage for specific module
pytest --cov=inventory --cov-report=term

# Coverage with missing lines
pytest --cov --cov-report=term-missing

# Minimum coverage threshold
pytest --cov --cov-fail-under=80
```

### Docker Testing

```powershell
# Run tests in Docker
docker compose exec web pytest -q

# Run with coverage in Docker
docker compose exec web pytest --cov --cov-report=html

# Copy coverage report from container
docker compose cp web:/app/htmlcov ./htmlcov
```

---

## 📁 Test Structure

### Directory Layout

```
backend/
├── tests/                      # Global integration tests
│   ├── conftest.py            # Global fixtures
│   ├── test_smoke.py          # Smoke tests
│   └── test_health.py         # Health check tests
├── inventory/
│   └── tests/
│       ├── conftest.py        # App-specific fixtures
│       ├── test_models.py     # Model tests
│       ├── test_api.py        # API endpoint tests
│       └── test_services.py   # Service layer tests
├── monitoring/
│   └── tests/
│       ├── conftest.py
│       └── test_usecases.py
└── pytest.ini                 # Pytest configuration
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
# backend/integrations/zabbix/tests/test_client.py
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
# pytest.ini
[pytest]
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
    smoke: marks tests as smoke tests

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

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
      
      db:
        image: mariadb:10.11
        env:
          MYSQL_DATABASE: test_db
          MYSQL_ROOT_PASSWORD: root
        ports:
          - 3306:3306
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
      
      - name: Run tests
        env:
          DJANGO_SETTINGS_MODULE: settings.test
          DB_HOST: 127.0.0.1
          REDIS_URL: redis://localhost:6379/1
        run: |
          cd backend
          pytest --cov --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./backend/coverage.xml
```

---

## 🎯 Coverage Targets

### Minimum Requirements

- **Overall**: 80% minimum
- **Critical Paths**: 95% minimum (auth, payments, data integrity)
- **New Code**: 90% minimum

### Checking Coverage

```powershell
# Generate report
pytest --cov --cov-report=term-missing

# Fail if below threshold
pytest --cov --cov-fail-under=80

# Coverage by module
pytest --cov=inventory --cov=monitoring --cov-report=term
```

### Excluded from Coverage

```python
# .coveragerc
[run]
omit =
    */migrations/*
    */tests/*
    */conftest.py
    */__pycache__/*
    */venv/*
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
```powershell
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

```powershell
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
```powershell
locust -f locustfile.py --host=http://localhost:8000
```

---

## 📖 Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [Django Testing Documentation](https://docs.djangoproject.com/en/5.0/topics/testing/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Development Guide](DEVELOPMENT.md)
- [CI/CD Guide](../operations/CICD.md)

---

**Last Updated**: 2025-11-10  
**Maintainers**: QA Team, Development Team
