# API Authentication Guide - MapsProveFiber

**Version**: v2.0.0  
**Last Updated**: 2025-11-10  
**Target Audience**: API Developers, Integrators

---

## 📖 Overview

MapsProveFiber API uses Django session-based authentication by default, with support for token-based authentication for programmatic access. This guide covers authentication methods, permissions, and security best practices.

---

## 🔐 Authentication Methods

### 1. Session Authentication (Web Browser)

Default authentication for web-based access. Suitable for:
- Dashboard access
- Admin panel
- Interactive API browsing (Django REST Framework UI)

**How it works:**
1. User logs in via `/admin/login/` or setup wizard
2. Django creates a session cookie
3. Subsequent requests include session cookie automatically
4. Session expires after inactivity (default: 2 weeks)

**Example:**
```python
import requests

# Login
session = requests.Session()
login_url = "http://localhost:8000/admin/login/"
session.post(login_url, data={
    "username": "admin",
    "password": "admin123",
    "csrfmiddlewaretoken": "..."  # Get from login page
})

# API request with session
response = session.get("http://localhost:8000/api/v1/inventory/sites/")
print(response.json())
```

### 2. Token Authentication (API Access)

Recommended for:
- Programmatic access
- CI/CD integrations
- Mobile applications
- Third-party integrations

**Generate Token:**
```powershell
# Via Django shell
python manage.py shell

>>> from django.contrib.auth import get_user_model
>>> from rest_framework.authtoken.models import Token
>>> user = get_user_model().objects.get(username='api_user')
>>> token = Token.objects.create(user=user)
>>> print(token.key)
'9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b'
```

**Use Token:**
```python
import requests

url = "http://localhost:8000/api/v1/inventory/sites/"
headers = {
    "Authorization": "Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"
}

response = requests.get(url, headers=headers)
print(response.json())
```

```bash
# cURL
curl -H "Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b" \
     http://localhost:8000/api/v1/inventory/sites/
```

### 3. Basic Authentication (Testing Only)

**NOT recommended for production.** Use only for testing.

```python
import requests
from requests.auth import HTTPBasicAuth

url = "http://localhost:8000/api/v1/inventory/sites/"
response = requests.get(url, auth=HTTPBasicAuth('admin', 'admin123'))
```

---

## 🛡️ Permissions & Authorization

### Permission Levels

| Permission | Description | Endpoints |
|------------|-------------|-----------|
| **Anonymous** | No authentication required | Health checks (`/healthz`, `/live`, `/ready`) |
| **Authenticated** | Logged-in user | Most read-only endpoints |
| **Staff** | `user.is_staff = True` | Admin panel, configuration, diagnostics |
| **Superuser** | `user.is_superuser = True` | Full system access |

### Common Permission Classes

```python
# In views.py
from rest_framework.permissions import (
    IsAuthenticated,
    IsAdminUser,
    AllowAny
)

class DeviceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]  # Require authentication
```

### Custom Permissions

```python
# permissions.py
from rest_framework import permissions

class IsStaffOrReadOnly(permissions.BasePermission):
    """
    Read-only for authenticated users, write for staff.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        return request.user.is_staff
```

---

## 👥 User Management

### Create API User

```powershell
# Interactive
python manage.py createsuperuser

# Programmatic
python manage.py shell
```

```python
from django.contrib.auth import get_user_model

User = get_user_model()

# Create regular user
user = User.objects.create_user(
    username='api_user',
    email='api@example.com',
    password='secure_password_123'
)

# Create staff user
staff_user = User.objects.create_user(
    username='staff_user',
    email='staff@example.com',
    password='secure_password_456',
    is_staff=True
)

# Create superuser
superuser = User.objects.create_superuser(
    username='admin',
    email='admin@example.com',
    password='admin_password_789'
)
```

### Manage User Permissions

```python
# Grant specific permissions
from django.contrib.auth.models import Permission

user = User.objects.get(username='api_user')

# Add permission
permission = Permission.objects.get(codename='add_site')
user.user_permissions.add(permission)

# Add to group
from django.contrib.auth.models import Group
api_group = Group.objects.get(name='API Users')
user.groups.add(api_group)
```

---

## 🔑 Token Management

### Create Token

```python
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.get(username='api_user')

# Create or get existing token
token, created = Token.objects.get_or_create(user=user)
print(f"Token: {token.key}")
```

### Rotate Token

```python
# Delete old token and create new one
old_token = Token.objects.get(user=user)
old_token.delete()

new_token = Token.objects.create(user=user)
print(f"New Token: {new_token.key}")
```

### List All Tokens

```python
tokens = Token.objects.all()
for token in tokens:
    print(f"{token.user.username}: {token.key}")
```

### Revoke Token

```python
token = Token.objects.get(key='9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b')
token.delete()
```

---

## 🚦 Rate Limiting

### Configure Rate Limits

```python
# settings/base.py
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',    # Anonymous users
        'user': '1000/hour',   # Authenticated users
    }
}
```

### Custom Rate Limits

```python
from rest_framework.throttling import UserRateThrottle

class BurstRateThrottle(UserRateThrottle):
    rate = '60/minute'

class SustainedRateThrottle(UserRateThrottle):
    rate = '1000/day'

# Apply to view
class DeviceViewSet(viewsets.ModelViewSet):
    throttle_classes = [BurstRateThrottle, SustainedRateThrottle]
```

### Rate Limit Response

```json
{
  "detail": "Request was throttled. Expected available in 59 seconds."
}
```

HTTP Status: `429 Too Many Requests`

---

## 🔒 Security Best Practices

### 1. Use HTTPS in Production

```python
# settings/prod.py
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

### 2. Store Tokens Securely

```python
# ❌ BAD: Hardcoded in code
token = "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"

# ✅ GOOD: Environment variable
import os
token = os.getenv('API_TOKEN')

# ✅ BETTER: Secrets manager
from azure.keyvault.secrets import SecretClient
token = secret_client.get_secret("api-token").value
```

### 3. Rotate Tokens Regularly

```python
# Rotate every 90 days
from datetime import timedelta
from django.utils import timezone

def should_rotate_token(token):
    age = timezone.now() - token.created
    return age > timedelta(days=90)
```

### 4. Limit Token Scope

Create separate users/tokens for different integrations:

```python
# Monitoring integration (read-only)
monitoring_user = User.objects.create_user(
    username='monitoring_api',
    password='...'
)

# CI/CD integration (write access to specific endpoints)
cicd_user = User.objects.create_user(
    username='cicd_api',
    is_staff=True,
    password='...'
)
```

### 5. Log Authentication Events

```python
# middleware/auth_logging.py
import logging

logger = logging.getLogger('security')

def process_request(self, request):
    if request.user.is_authenticated:
        logger.info(
            f"API access: {request.user.username} - {request.path}",
            extra={'ip': request.META.get('REMOTE_ADDR')}
        )
```

---

## 🌐 CORS Configuration

For frontend applications on different domains:

```python
# settings/base.py
INSTALLED_APPS += ['corsheaders']

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    ...
]

# Development
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Production
CORS_ALLOWED_ORIGINS = [
    "https://dashboard.example.com",
]

# Allow credentials (cookies)
CORS_ALLOW_CREDENTIALS = True
```

---

## 📝 Example: Complete Integration

### Python Client

```python
# client.py
import requests
import os

class MapsFiberClient:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Token {token}",
            "Content-Type": "application/json"
        }
    
    def get_sites(self):
        """Get all sites"""
        response = requests.get(
            f"{self.base_url}/api/v1/inventory/sites/",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def create_site(self, name, latitude, longitude):
        """Create a new site"""
        data = {
            "name": name,
            "latitude": latitude,
            "longitude": longitude
        }
        response = requests.post(
            f"{self.base_url}/api/v1/inventory/sites/",
            headers=self.headers,
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    def get_device_status(self, device_id):
        """Get device status from monitoring API"""
        response = requests.get(
            f"{self.base_url}/api/v1/monitoring/hosts/status/",
            headers=self.headers,
            params={"device_id": device_id}
        )
        response.raise_for_status()
        return response.json()

# Usage
client = MapsFiberClient(
    base_url=os.getenv('MAPSFIBER_URL'),
    token=os.getenv('MAPSFIBER_TOKEN')
)

# Get sites
sites = client.get_sites()
print(f"Total sites: {len(sites)}")

# Create site
new_site = client.create_site("HQ", -23.5505, -46.6333)
print(f"Created site: {new_site['id']}")
```

### JavaScript Client

```javascript
// client.js
class MapsFiberClient {
  constructor(baseUrl, token) {
    this.baseUrl = baseUrl;
    this.headers = {
      'Authorization': `Token ${token}`,
      'Content-Type': 'application/json'
    };
  }

  async getSites() {
    const response = await fetch(`${this.baseUrl}/api/v1/inventory/sites/`, {
      headers: this.headers
    });
    return response.json();
  }

  async createSite(name, latitude, longitude) {
    const response = await fetch(`${this.baseUrl}/api/v1/inventory/sites/`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({ name, latitude, longitude })
    });
    return response.json();
  }
}

// Usage
const client = new MapsFiberClient(
  process.env.MAPSFIBER_URL,
  process.env.MAPSFIBER_TOKEN
);

const sites = await client.getSites();
console.log(`Total sites: ${sites.length}`);
```

---

## 🔍 Troubleshooting

### Authentication Failed (401)

```json
{
  "detail": "Authentication credentials were not provided."
}
```

**Solution:** Check token in `Authorization` header.

### Permission Denied (403)

```json
{
  "detail": "You do not have permission to perform this action."
}
```

**Solution:** User needs staff privileges for this endpoint.

### Invalid Token

```json
{
  "detail": "Invalid token."
}
```

**Solution:** Token may be expired or revoked. Generate new token.

---

## 📚 Additional Resources

- [API Endpoints Reference](ENDPOINTS.md)
- [API Examples](EXAMPLES.md)
- [Django REST Framework Authentication](https://www.django-rest-framework.org/api-guide/authentication/)
- [Security Guide](../security/SECURITY.md)

---

**Last Updated**: 2025-11-10  
**Maintainers**: API Team
