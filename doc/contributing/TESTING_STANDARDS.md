# Testing Standards - MapsProveFiber

**Version**: v2.0.0  
**Last Updated**: 2025-11-10

---

## 📖 Overview

This document defines testing standards and best practices for MapsProveFiber.

---

## 🎯 Coverage Requirements

### Minimum Coverage

- **Overall**: 80% minimum
- **New Code**: 90% minimum
- **Critical Paths**: 95% minimum
  - Authentication
  - Data integrity
  - External integrations

### Checking Coverage

```powershell
# Run tests with coverage
pytest --cov --cov-report=html

# Fail if below threshold
pytest --cov --cov-fail-under=80

# View report
start htmlcov/index.html
```

---

## 🧪 Test Types

### Unit Tests (Most)

Test individual functions/methods in isolation.

**Characteristics:**
- Fast (< 1ms each)
- No external dependencies
- No database access (or use in-memory DB)
- Mock external services

**Example:**
```python
def test_calculate_fiber_loss():
    """Pure function test"""
    result = calculate_fiber_loss(distance=5000, attenuation=0.25)
    assert result == 1.25
```

### Integration Tests (Some)

Test multiple components working together.

**Characteristics:**
- Slower (10-100ms each)
- May use database
- Test real interactions
- Use fixtures for setup

**Example:**
```python
@pytest.mark.django_db
def test_device_with_ports(device, port):
    """Test device-port relationship"""
    assert port in device.ports.all()
```

### End-to-End Tests (Few)

Test complete user workflows.

**Characteristics:**
- Slowest (100ms-1s each)
- Test full stack
- Simulate user actions
- Use Selenium/Playwright if needed

**Example:**
```python
def test_create_device_workflow(api_client):
    """Complete workflow test"""
    # Create site
    site = api_client.post('/api/v1/inventory/sites/', {...})
    
    # Create device
    device = api_client.post('/api/v1/inventory/devices/', {...})
    
    # Verify device in site
    response = api_client.get(f'/api/v1/inventory/sites/{site.id}/')
    assert device.id in [d['id'] for d in response['devices']]
```

---

## ✅ Writing Good Tests

### Test Structure (AAA)

```python
def test_example():
    # Arrange - Set up test data
    site = Site.objects.create(name="Test Site")
    
    # Act - Perform action
    device = Device.objects.create(name="OLT", site=site)
    
    # Assert - Verify result
    assert device.site == site
```

### Descriptive Names

```python
# ❌ Bad
def test_device():
    ...

# ✅ Good
def test_device_creation_with_valid_data_succeeds():
    ...

# ✅ Good
def test_device_creation_duplicate_name_raises_error():
    ...
```

### One Assertion Per Test (When Possible)

```python
# ✅ Good - Single logical assertion
def test_site_name_required():
    with pytest.raises(ValidationError):
        Site.objects.create(latitude=0, longitude=0)

# ⚠️ Acceptable - Related assertions
def test_site_creation():
    site = Site.objects.create(name="HQ", latitude=0, longitude=0)
    assert site.name == "HQ"
    assert site.is_active is True
    assert str(site) == "HQ"

# ❌ Bad - Unrelated assertions
def test_site():
    site = Site.objects.create(...)
    assert site.name == "HQ"
    assert Device.objects.count() == 0  # Unrelated
```

---

## 🔧 Using Fixtures

### When to Use Fixtures

- Reusable test data
- Complex setup
- Teardown needed
- Cross-test dependencies

### Fixture Scope

```python
@pytest.fixture(scope="function")  # Default, new instance per test
def device():
    return Device.objects.create(...)

@pytest.fixture(scope="class")  # Shared within test class
def api_client():
    return APIClient()

@pytest.fixture(scope="module")  # Shared within module
def database_connection():
    conn = create_connection()
    yield conn
    conn.close()

@pytest.fixture(scope="session")  # Shared across all tests
def django_db_setup():
    ...
```

### Fixture Example

```python
# conftest.py
@pytest.fixture
def site():
    """Create test site"""
    return Site.objects.create(
        name="Test Site",
        latitude=-23.5505,
        longitude=-46.6333
    )

@pytest.fixture
def device(site):
    """Create test device (depends on site fixture)"""
    return Device.objects.create(
        name="OLT-01",
        site=site,
        device_type="OLT"
    )

# test_models.py
def test_device_has_site(device, site):
    assert device.site == site
```

---

## 🎭 Mocking

### When to Mock

- External APIs (Zabbix, Google Maps)
- Time-dependent code
- Slow operations
- Non-deterministic behavior

### Mocking Examples

**Mock External API:**
```python
from unittest.mock import patch, Mock

@patch('integrations.zabbix.client.requests.post')
def test_zabbix_auth(mock_post):
    mock_response = Mock()
    mock_response.json.return_value = {"result": "token123"}
    mock_post.return_value = mock_response
    
    client = ZabbixClient(...)
    token = client.authenticate()
    
    assert token == "token123"
    mock_post.assert_called_once()
```

**Mock Time:**
```python
from unittest.mock import patch
from datetime import datetime

@patch('django.utils.timezone.now')
def test_task_scheduling(mock_now):
    mock_now.return_value = datetime(2025, 11, 10, 10, 0, 0)
    
    task = schedule_task()
    
    assert task.scheduled_time == datetime(2025, 11, 10, 10, 0, 0)
```

---

## 🏷️ Test Markers

### Standard Markers

```python
@pytest.mark.django_db
def test_database_access():
    """Requires database"""
    ...

@pytest.mark.slow
def test_long_operation():
    """Takes >1 second"""
    ...

@pytest.mark.integration
def test_api_integration():
    """Integration test"""
    ...

@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 3),
])
def test_increment(input, expected):
    assert input + 1 == expected
```

### Running Specific Tests

```powershell
# Only unit tests
pytest -m unit

# Skip slow tests
pytest -m "not slow"

# Only integration tests
pytest -m integration
```

---

## 📊 Performance Testing

### Benchmark Tests

```python
def test_query_performance(benchmark):
    """Ensure query completes in < 100ms"""
    def query():
        return Device.objects.select_related('site').all()
    
    result = benchmark(query)
    assert benchmark.stats['mean'] < 0.1  # 100ms
```

### Load Testing

```python
def test_api_load():
    """Ensure API handles 100 requests/second"""
    import concurrent.futures
    
    def make_request():
        return requests.get('http://localhost:8000/api/v1/inventory/sites/')
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_request) for _ in range(100)]
        results = [f.result() for f in futures]
    
    assert all(r.status_code == 200 for r in results)
```

---

## 🐛 Testing Error Conditions

### Test Expected Failures

```python
def test_invalid_coordinates():
    """Site creation fails with invalid coordinates"""
    with pytest.raises(ValidationError) as exc_info:
        Site.objects.create(
            name="Test",
            latitude=91,  # Invalid
            longitude=0
        )
    
    assert 'latitude' in str(exc_info.value)
```

### Test Edge Cases

```python
def test_empty_name():
    """Empty name fails validation"""
    ...

def test_max_length_name():
    """Name at max length succeeds"""
    ...

def test_above_max_length_name():
    """Name above max length fails"""
    ...
```

---

## 📝 Documentation Tests

### Doctest

```python
def calculate_loss(distance: float, attenuation: float) -> float:
    """
    Calculate fiber loss.
    
    >>> calculate_loss(1000, 0.25)
    0.25
    >>> calculate_loss(5000, 0.30)
    1.5
    """
    return (distance / 1000) * attenuation
```

Run doctests:
```powershell
pytest --doctest-modules
```

---

## 🔄 CI/CD Integration

### GitHub Actions

```yaml
- name: Run tests
  run: |
    cd backend
    pytest --cov --cov-report=xml --cov-fail-under=80

- name: Upload coverage
  uses: codecov/codecov-action@v3
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: pytest
      name: pytest
      entry: pytest
      language: system
      pass_filenames: false
      always_run: true
```

---

## 🚫 Testing Anti-Patterns

### Avoid

```python
# ❌ Testing implementation details
def test_internal_cache():
    obj._cache['key'] = 'value'  # Don't test private attributes
    ...

# ❌ Brittle tests
def test_exact_error_message():
    with pytest.raises(ValueError, match="Exact error message"):  # May change
        ...

# ❌ Sleep in tests
def test_async_operation():
    trigger_async()
    time.sleep(5)  # Use proper waits or mocks
    assert result_ready()

# ❌ Order-dependent tests
def test_a():
    global counter
    counter = 1

def test_b():
    assert counter == 1  # Depends on test_a running first
```

---

## ✅ Best Practices Summary

1. **Write tests first** (TDD when possible)
2. **Keep tests fast** (< 2 minutes for full suite)
3. **One logical assertion** per test
4. **Descriptive test names**
5. **Use fixtures** for setup
6. **Mock external services**
7. **Test error conditions**
8. **Maintain coverage** > 80%
9. **Run tests before commit**
10. **Update tests with code**

---

## 📚 Resources

- [pytest Documentation](https://docs.pytest.org/)
- [Testing Guide](../guides/TESTING.md)
- [Django Testing](https://docs.djangoproject.com/en/5.0/topics/testing/)
- [Code Style Guide](CODE_STYLE.md)

---

**Last Updated**: 2025-11-10
