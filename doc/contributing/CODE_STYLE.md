# Code Style Guide - MapsProveFiber

**Version**: v2.0.0  
**Last Updated**: 2025-11-10

---

## 📖 Overview

This document defines code style standards for MapsProveFiber. We use automated tools (ruff, black, isort) to enforce most rules.

---

## 🐍 Python Style

### PEP 8 Compliance

Follow [PEP 8](https://pep8.org/) with these modifications:
- Line length: **100 characters** (not 79)
- String quotes: **Double quotes preferred** (`"` not `'`)

### Formatting Tools

```powershell
# Format all code
make fmt

# Individual tools
ruff check --fix backend/
black backend/
isort backend/
```

### Naming Conventions

```python
# Classes: PascalCase
class DeviceManager:
    pass

# Functions/methods: snake_case
def get_device_status():
    pass

# Constants: UPPER_SNAKE_CASE
MAX_RETRY_ATTEMPTS = 3

# Private: _leading_underscore
def _internal_helper():
    pass

# Module-level "private": _leading_underscore
_cache = {}
```

### Imports

```python
# Standard library
import os
import sys
from datetime import datetime

# Third-party
import requests
from django.db import models

# Local
from inventory.models import Site
from monitoring.usecases import get_devices_with_zabbix
```

Use `isort` to maintain order automatically.

### Docstrings

```python
def calculate_fiber_loss(distance: float, attenuation: float) -> float:
    """
    Calculate total fiber optic cable loss.
    
    Args:
        distance: Cable length in meters
        attenuation: Loss per kilometer in dB/km
    
    Returns:
        Total loss in dB
    
    Example:
        >>> calculate_fiber_loss(5000, 0.25)
        1.25
    """
    return (distance / 1000) * attenuation
```

### Type Hints

```python
from typing import List, Optional, Dict, Any

def get_devices(site_id: int) -> List[Dict[str, Any]]:
    """Get devices for a site."""
    ...

def find_device(device_id: int) -> Optional[Device]:
    """Find device by ID, returns None if not found."""
    ...
```

---

## 📂 File Organization

### Module Structure

```python
"""Module docstring explaining purpose."""

# Imports (standard, third-party, local)
import os
from django.db import models
from inventory.models import Site

# Constants
DEFAULT_TIMEOUT = 30

# Private helpers
def _internal_function():
    pass

# Public API
def public_function():
    pass

# Classes
class MyClass:
    pass
```

### Django App Structure

```
inventory/
├── __init__.py
├── admin.py              # Django admin config
├── apps.py               # App configuration
├── models.py             # Database models (or models/ package)
├── serializers.py        # DRF serializers
├── views.py              # Views (or views/ package)
├── urls.py               # URL routing
├── services.py           # Business logic
├── usecases.py           # Use case orchestration
├── tasks.py              # Celery tasks
├── signals.py            # Django signals
└── tests/                # Test package
    ├── conftest.py
    ├── test_models.py
    └── test_services.py
```

---

## 🧪 Testing Style

### Test Naming

```python
class TestSiteModel:
    def test_site_creation(self):
        """Basic site creation works"""
        ...
    
    def test_site_creation_duplicate_name_fails(self):
        """Creating site with duplicate name raises error"""
        ...
```

### AAA Pattern

```python
def test_device_update():
    # Arrange
    device = Device.objects.create(name="OLT-01")
    
    # Act
    device.name = "OLT-02"
    device.save()
    
    # Assert
    assert device.name == "OLT-02"
```

---

## 🎨 Frontend Style

### JavaScript

```javascript
// Use const/let, not var
const API_URL = '/api/v1/inventory';
let deviceCount = 0;

// Function names: camelCase
function getDeviceStatus(deviceId) {
    return fetch(`${API_URL}/devices/${deviceId}/`);
}

// Classes: PascalCase
class DashboardManager {
    constructor() {
        this.devices = [];
    }
}
```

### HTML/Templates

```django
{% load static %}

<!-- Consistent indentation (2 spaces) -->
<div class="container">
  <h1>{{ page_title }}</h1>
  <ul>
    {% for device in devices %}
      <li>{{ device.name }}</li>
    {% endfor %}
  </ul>
</div>
```

---

## 📋 Git Commit Messages

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting (no code change)
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance

### Examples

```
feat(inventory): add fiber cable import from KML

Implement KML parser and bulk import endpoint for fiber cables.
Includes validation and error handling.

Closes #123
```

```
fix(monitoring): handle missing Zabbix hosts gracefully

Previously crashed when Zabbix host was deleted but inventory
device still existed. Now logs warning and continues.
```

---

## 🚫 Anti-Patterns to Avoid

### Don't

```python
# ❌ Magic numbers
if user_count > 100:
    ...

# ❌ Nested ifs
if condition1:
    if condition2:
        if condition3:
            ...

# ❌ Mutable defaults
def func(items=[]):
    items.append(1)
    return items

# ❌ Bare except
try:
    risky_operation()
except:
    pass
```

### Do

```python
# ✅ Named constants
MAX_USERS = 100
if user_count > MAX_USERS:
    ...

# ✅ Early returns
if not condition1:
    return
if not condition2:
    return
if not condition3:
    return
...

# ✅ None as default
def func(items=None):
    if items is None:
        items = []
    items.append(1)
    return items

# ✅ Specific exceptions
try:
    risky_operation()
except ValueError as e:
    logger.error(f"Invalid value: {e}")
```

---

## 📚 Resources

- [PEP 8](https://pep8.org/)
- [Black](https://black.readthedocs.io/)
- [Ruff](https://docs.astral.sh/ruff/)
- [Django Coding Style](https://docs.djangoproject.com/en/dev/internals/contributing/writing-code/coding-style/)

---

**Last Updated**: 2025-11-10
