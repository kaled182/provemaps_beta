# Frontend Cleanup Guide - Legacy Code Removal

## 🎯 Objective
Eliminate "split brain" by removing duplicate frontend code and consolidating to Vue 3 SPA.

## 🔍 Phase 1: Discovery (Week 1)

### 1.1 Find All Django Template Views

Run this command to find all Django views that render HTML templates:

```bash
# Find all render() calls (Django templates)
grep -rn "render(request" backend/*/views.py

# Find all template files
find backend -name "*.html" -not -path "*/templates/base*"
```

**Create inventory**: `doc/reports/legacy-frontend-inventory.md`

### 1.2 Identify Static JS/CSS Files

```bash
# Find legacy JavaScript
find backend/static -name "*.js" | grep -v ".min.js"

# Find legacy CSS
find backend/static -name "*.css" | grep -v ".min.css"
```

### 1.3 Check URL Patterns

```bash
# Find all URL routes
grep -rn "path\|re_path" backend/*/urls.py
```

---

## 🚦 Phase 2: Prioritization (Week 1)

### Traffic Analysis

Add temporary logging to measure usage:

```python
# backend/middleware/usage_tracker.py (temporary)
import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('legacy_routes')

class LegacyRouteTracker(MiddlewareMixin):
    LEGACY_ROUTES = [
        '/maps_view/map/',
        '/network/legacy-design/',
        '/zabbix/old-lookup/',
    ]
    
    def process_request(self, request):
        for route in self.LEGACY_ROUTES:
            if request.path.startswith(route):
                logger.warning(
                    f"LEGACY_ROUTE: {request.path} | "
                    f"USER: {request.user.username} | "
                    f"REFERER: {request.META.get('HTTP_REFERER')}"
                )
```

Add to `settings/base.py`:
```python
MIDDLEWARE = [
    # ... existing middleware
    'backend.middleware.usage_tracker.LegacyRouteTracker',  # TEMPORARY
]
```

**Run for 1 week**, then analyze logs:
```bash
grep "LEGACY_ROUTE" logs/django.log | sort | uniq -c | sort -rn
```

### Priority Matrix

| Route | Weekly Traffic | Complexity | Priority |
|-------|---------------|------------|----------|
| `/maps_view/dashboard/` | High | Low | **1 - Migrate First** |
| `/network/design/` | Medium | Medium | **2 - Migrate Next** |
| `/admin-custom/` | Low | High | **3 - Keep for now** |

---

## 🔧 Phase 3: Migration (Weeks 2-3)

### Example: Migrate Map View

#### Step 1: Create Vue Component

```bash
# Create new Vue component
touch frontend/src/views/MapView.vue
```

**`frontend/src/views/MapView.vue`**:
```vue
<template>
  <div class="map-container">
    <LeafletMap :fibers="fibers" @fiber-click="onFiberClick" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import LeafletMap from '@/components/Map/LeafletMap.vue';

const fibers = ref([]);

async function loadFibers() {
  const response = await fetch('/api/v1/fibers/');
  const data = await response.json();
  fibers.value = data.results;
}

function onFiberClick(fiber) {
  console.log('Fiber clicked:', fiber);
}

onMounted(() => {
  loadFibers();
});
</script>
```

#### Step 2: Add Vue Route

**`frontend/src/router/index.js`**:
```javascript
{
  path: '/map',
  name: 'map-view',
  component: () => import('@/views/MapView.vue'),
}
```

#### Step 3: Deprecate Django View

**`backend/maps_view/views.py`**:
```python
from django.shortcuts import redirect
from django.contrib import messages

def old_map_view(request):
    """
    DEPRECATED: This view is being replaced by Vue SPA.
    Redirects to new Vue route.
    """
    messages.warning(
        request,
        "You've been redirected to the new map interface. "
        "The old interface will be removed in Sprint 4."
    )
    return redirect('/map')  # Vue route
```

#### Step 4: Update URLs (Redirect)

**`backend/maps_view/urls.py`**:
```python
urlpatterns = [
    # Old route - DEPRECATED
    path('maps_view/old-map/', views.old_map_view, name='old_map_deprecated'),
    
    # New route - serves Vue SPA
    path('map/', SPAView.as_view(), name='map_spa'),
]
```

#### Step 5: Test Both Versions (1 week)

- ✅ Monitor error logs
- ✅ Collect user feedback
- ✅ Compare performance metrics

#### Step 6: Delete Legacy Code

After 1 week of successful Vue operation:

```bash
# Delete Django template
git rm backend/maps_view/templates/maps_view/old_map.html

# Delete legacy JavaScript
git rm backend/static/js/old_map_controller.js

# Delete legacy CSS
git rm backend/static/css/old_map.css

git commit -m "Remove legacy map view - Migrated to Vue SPA

All traffic successfully redirected to /map (Vue route).
No errors or user complaints during 1-week trial period.

Deleted files:
- templates/maps_view/old_map.html
- static/js/old_map_controller.js
- static/css/old_map.css

Ref: Frontend Cleanup Sprint Week 2"
```

---

## 🗑️ Phase 4: Final Cleanup (Week 4)

### Files to Delete (After All Migrations)

```bash
# Delete entire legacy static directories
git rm -r backend/static/js/legacy/
git rm -r backend/static/css/legacy/

# Delete old templates (keep only base.html, base_spa.html)
find backend/*/templates -name "*.html" \
  -not -name "base.html" \
  -not -name "base_spa.html" \
  -not -name "admin/*" \
  -delete

# Remove jQuery (if Vue handles all interactions)
git rm backend/static/js/vendor/jquery-3.6.0.min.js
```

### Update Base Template

**`backend/templates/base_spa.html`** (keep only this):
```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MapsProveFiber</title>
    
    <!-- CSRF Token -->
    <script>
        window.CSRF_TOKEN = '{{ csrf_token }}';
        window.USER_ID = {{ request.user.id|default:'null' }};
        window.USERNAME = '{{ request.user.username|default:'' }}';
        window.IS_SUPERUSER = {{ request.user.is_superuser|lower }};
    </script>
    
    <!-- Vue SPA Bundle (Vite) -->
    {% load static %}
    <script type="module" src="{% static 'vue-spa/index.js' %}"></script>
    <link rel="stylesheet" href="{% static 'vue-spa/style.css' %}">
</head>
<body>
    <div id="app"></div>
</body>
</html>
```

---

## ✅ Success Criteria

### Before Cleanup:
- ❌ 50+ HTML templates in `backend/*/templates/`
- ❌ 30+ legacy JS files in `backend/static/js/`
- ❌ Django views with `render(request, ...)`
- ❌ Duplicate logic in Vue + jQuery

### After Cleanup:
- ✅ Only 2 HTML templates: `base.html`, `base_spa.html`
- ✅ Zero legacy JS files (all in `frontend/src/`)
- ✅ Django views return **JSON only** (DRF ViewSets)
- ✅ Single source of truth: Vue components

---

## 🚨 Common Pitfalls

### Don't Delete These:
- ❌ `backend/templates/admin/` - Django Admin uses this
- ❌ `backend/templates/registration/` - Auth forms
- ❌ `backend/static/admin/` - Django Admin assets

### Safety Checklist:
```
[ ] Backup database before deleting templates
[ ] Test in staging environment first
[ ] Keep old files in Git history (can revert)
[ ] Monitor error logs for 404s
[ ] Communicate changes to team
```

---

## 📊 Track Progress

**Sprint Board** (GitHub Projects):
- [ ] Week 1: Inventory complete (20 legacy routes identified)
- [ ] Week 2: Top 5 routes migrated to Vue
- [ ] Week 3: Remaining 15 routes migrated
- [ ] Week 4: Legacy code deleted, tests passing

**Metrics**:
- Lines of code in `backend/static/js/`: **5,234** → 🎯 **0**
- Number of Django template views: **18** → 🎯 **0**
- Bundle size (frontend): **450 KB** → 🎯 **350 KB** (after removing duplicates)

---

**Last Updated**: November 18, 2025  
**Status**: 📋 Planning Phase  
**Next Action**: Run discovery commands and create inventory
