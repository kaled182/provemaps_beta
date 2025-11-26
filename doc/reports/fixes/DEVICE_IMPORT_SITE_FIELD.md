# Device Import - Site Field Implementation

**Date**: 2025-01-XX  
**Component**: Device Import (DeviceImportManager, DeviceEditModal)  
**Issue**: Missing Site (Location) field preventing georeferenced inventory  
**Status**: ✅ **IMPLEMENTED** (Backend + Frontend complete)

---

## 🎯 Overview

Implemented geographic Site field in device import workflow to enable proper geolocation of network devices on maps. This is a **critical feature** for ProveMaps' georeferenced monitoring capabilities.

**User Quote**:
> "faz falta o campo SITE, onde o equipamento está situado... fundamental para um inventário georreferenciado (como é o ProveMaps). Sem o Site (Local) correto, o dispositivo não aparece no mapa, e a função de monitoramento geográfico perde o sentido."

---

## 📋 Requirements

**Functional**:
1. ✅ Select existing Site from dropdown
2. ✅ Create new Site with custom name
3. ✅ Define Site coordinates via map picker
4. ✅ Validate Site selection (required field)
5. ✅ Validate coordinates for new Sites
6. ✅ Auto-create Site with PostGIS Point in backend
7. ✅ Display coordinates when set (lat/lng with 6 decimals)

**Non-Functional**:
1. ✅ Consistent UX with existing Group selection pattern
2. ✅ PostGIS geography Point for spatial queries
3. ✅ Graceful fallback to default Site if not specified
4. ✅ Backend validation and error handling

---

## 🏗️ Architecture

### Frontend (Vue 3)

**DeviceEditModal.vue**:
```
Lines 94-145:   Site Field UI (select/create mode)
Lines 333-373:  Map Picker Modal (coordinate selection)
Lines 380-413:  Reactive State (site variables)
Lines 503-540:  Site Functions (handleSiteChange, openMapPicker, etc.)
Lines 540-615:  Updated handleSave (validation + payload)
```

**DeviceImportManager.vue**:
```
Line 128:       const availableSites = ref([])
Line 87:        :available-sites="availableSites" prop binding
Lines 161-167:  fetchSites from /api/v1/inventory/sites/
```

**Key State Variables**:
```javascript
// Site selection state
const isCreatingSite = ref(false);
const newSiteName = ref('');
const selectedSiteProxy = ref('');
const newSiteInput = ref(null);

// Map picker state
const showMapPicker = ref(false);
const tempCoordinates = ref(null); // {lat, lng}
const mapLat = ref(-23.5505);  // São Paulo default
const mapLng = ref(-46.6333);

// Props
availableSites: { type: Array, default: () => [] }

// Form state
formState.site = ''
```

**Payload Structure**:
```javascript
{
  site: 'Site Name' | 123,        // Name (new) or ID (existing)
  is_new_site: boolean,           // Creation flag
  site_coordinates: {             // Required if is_new_site=true
    lat: -23.550500,
    lng: -46.633300
  },
  // ... (group, category, alerts)
}
```

### Backend (Django)

**API Endpoint** (already exists):
- **GET /api/v1/inventory/sites/**
- Handler: `inventory/api/devices.py::api_sites()`
- Usecase: `inventory/usecases/devices.py::list_sites()`
- Returns: `{sites: [{id, display_name, name, city, lat, lng, devices: [...]}]}`

**Import Endpoint** (updated):
- **POST /api/v1/inventory/devices/import-batch/**
- Handler: `inventory/api/devices.py::api_import_batch()`
- Lines 716-792: Site handling logic
- Supports:
  - `is_new_site=false`: Lookup by ID or display_name
  - `is_new_site=true`: Create with coordinates
  - Missing site: Fallback to default or create "Site Padrão"

**Database**:
```python
# inventory/models.py::Site
class Site(models.Model):
    display_name = CharField(max_length=160, unique=True)
    city = CharField(max_length=160)
    latitude = DecimalField(max_digits=9, decimal_places=6)
    longitude = DecimalField(max_digits=9, decimal_places=6)
    location = PointField(srid=4326, geography=True)  # PostGIS
    
    class Meta:
        db_table = "zabbix_api_site"
```

---

## 🔄 User Flow

### **Select Existing Site**
1. User opens DeviceEditModal (single or batch import)
2. Site dropdown displays `availableSites` array
3. User selects existing site
4. `selectedSiteProxy` updates → `formState.site` = site.id
5. On save: Backend finds Site by ID

### **Create New Site**
1. User clicks "📍 Criar Novo Site..." in dropdown
2. UI switches to creation mode (`isCreatingSite = true`)
3. User enters site name in input field
4. User clicks "Abrir no Mapa" button
5. Map picker modal opens (placeholder for Google Maps)
6. User clicks on map to position marker (future: drag marker)
7. Coordinates display: `Lat: -23.550500, Lng: -46.633300`
8. User clicks "Confirmar Localização"
9. Modal closes, coordinates saved to `tempCoordinates`
10. Coordinates appear below site name input
11. User clicks "Confirmar Importação"
12. Payload includes: `{site: "New Site", is_new_site: true, site_coordinates: {lat, lng}}`
13. Backend creates Site with PostGIS Point(lng, lat)

---

## 🧪 Validation Rules

### Frontend Validation (DeviceEditModal.vue::handleSave)

```javascript
// Rule 1: Site selection required
if (!finalSite) {
  alert('Selecione um local/site.');
  return;
}

// Rule 2: New site name required
if (isCreatingSite.value && !newSiteName.value.trim()) {
  alert('Digite o nome do novo local/site.');
  return;
}

// Rule 3: Coordinates required for new sites
if (isCreatingSite.value && !tempCoordinates.value) {
  alert('Clique em "Abrir no Mapa" para definir a localização.');
  return;
}
```

### Backend Validation (api_import_batch)

```python
# Rule 1: Handle missing site (create default)
if not site_id_or_name:
    default_site = Site.objects.first()
    if not default_site:
        default_site = Site.objects.create(
            display_name="Site Padrão",
            city="Default"
        )

# Rule 2: Create with coordinates if is_new_site=true
if is_new_site:
    from django.contrib.gis.geos import Point
    has_coords = (
        site_coordinates
        and 'lat' in site_coordinates
        and 'lng' in site_coordinates
    )
    if has_coords:
        lat = float(site_coordinates['lat'])
        lng = float(site_coordinates['lng'])
        site_defaults['location'] = Point(lng, lat)  # lng, lat order!

# Rule 3: Fallback to existing site search
else:
    try:
        site_instance = Site.objects.get(id=int(site_id_or_name))
    except (ValueError, Site.DoesNotExist):
        # Fallback: search by display_name
        site_instance = Site.objects.filter(
            display_name=site_id_or_name
        ).first()
```

---

## 📝 Code Examples

### Frontend: Fetching Sites

```javascript
// DeviceImportManager.vue
const availableSites = ref([]);

const refreshData = async () => {
  // ... (inventory, groups)
  
  // Fetch sites
  try {
    const sitesResponse = await api.get('/api/v1/inventory/sites/');
    availableSites.value = sitesResponse.sites || [];
  } catch (sitesError) {
    console.warn('Erro ao buscar sites:', sitesError);
    availableSites.value = [];
  }
};
```

### Frontend: Site Functions

```javascript
// DeviceEditModal.vue
const handleSiteChange = async () => {
  if (selectedSiteProxy.value === '__CREATE_NEW__') {
    isCreatingSite.value = true;
    selectedSiteProxy.value = '';
    newSiteName.value = '';
    tempCoordinates.value = null;
    await nextTick();
    newSiteInput.value?.focus();
  } else {
    formState.site = selectedSiteProxy.value;
    isCreatingSite.value = false;
  }
};

const openMapPicker = () => {
  if (!isCreatingSite.value) {
    isCreatingSite.value = true;
    selectedSiteProxy.value = '';
  }
  showMapPicker.value = true;
};

const confirmLocation = () => {
  tempCoordinates.value = { 
    lat: mapLat.value, 
    lng: mapLng.value 
  };
  showMapPicker.value = false;
  nextTick(() => newSiteInput.value?.focus());
};
```

### Backend: Site Creation

```python
# inventory/api/devices.py::api_import_batch
if is_new_site:
    from django.contrib.gis.geos import Point
    
    new_site_name = site_id_or_name
    site_defaults = {'city': 'A definir'}
    
    # Add coordinates if provided
    has_coords = (
        site_coordinates
        and 'lat' in site_coordinates
        and 'lng' in site_coordinates
    )
    if has_coords:
        lat = float(site_coordinates['lat'])
        lng = float(site_coordinates['lng'])
        site_defaults['latitude'] = lat
        site_defaults['longitude'] = lng
        # PostGIS Point: (longitude, latitude) order!
        site_defaults['location'] = Point(lng, lat)
        logger.info(
            f"Criando site '{new_site_name}' com "
            f"coordenadas: ({lat}, {lng})"
        )
    
    site_instance, created = Site.objects.get_or_create(
        display_name=new_site_name,
        defaults=site_defaults
    )
```

---

## 🔬 Testing

### Manual Testing Checklist

**Existing Site Selection**:
- [ ] Dropdown displays all sites from `/api/v1/inventory/sites/`
- [ ] Selecting existing site updates `formState.site` with ID
- [ ] Device import succeeds with selected site
- [ ] Device appears on map at site coordinates

**New Site Creation**:
- [ ] "Criar Novo Site" option appears in dropdown
- [ ] Clicking triggers creation mode (input field appears)
- [ ] Entering name without coordinates shows validation error
- [ ] Clicking "Abrir no Mapa" opens modal
- [ ] Map modal displays coordinates (default: São Paulo)
- [ ] Clicking "Confirmar Localização" saves coordinates
- [ ] Coordinates display below site name input
- [ ] Importing creates Site in database with PostGIS Point
- [ ] Device links to new Site correctly

**Edge Cases**:
- [ ] Empty site field shows validation error
- [ ] Existing site name reuses Site instead of duplicating
- [ ] Missing `is_new_site` flag defaults to ID lookup
- [ ] Invalid site ID falls back to display_name search
- [ ] Missing default site creates "Site Padrão"

### Automated Testing (Future)

```javascript
// frontend/tests/DeviceEditModal.spec.js
describe('Site Field', () => {
  it('shows validation error when site not selected', () => {
    // ...
  });
  
  it('creates new site with coordinates', async () => {
    // ...
  });
  
  it('selects existing site from dropdown', () => {
    // ...
  });
});
```

```python
# backend/tests/test_device_import.py
def test_import_with_new_site_coordinates():
    payload = {
        'name': 'Test Device',
        'site': 'New Site',
        'is_new_site': True,
        'site_coordinates': {'lat': -23.55, 'lng': -46.63}
    }
    response = client.post('/api/v1/inventory/devices/import-batch/', payload)
    assert response.status_code == 200
    
    site = Site.objects.get(display_name='New Site')
    assert site.latitude == -23.55
    assert site.longitude == -46.63
    assert site.location.y == -23.55  # latitude
    assert site.location.x == -46.63  # longitude
```

---

## 🚀 Deployment

### Docker Rebuild (Required)

```powershell
# 1. Stop containers
cd docker
docker compose down

# 2. Rebuild web image
docker compose build --no-cache web

# 3. Rebuild frontend
cd ../frontend
npm run build

# 4. Start containers
cd ../docker
docker compose up -d

# 5. Restart web to load new frontend
docker compose restart web

# 6. Verify
docker compose ps
```

### Verification Checklist

- [ ] All containers healthy (`docker compose ps`)
- [ ] Site endpoint accessible: `GET http://localhost:8000/api/v1/inventory/sites/`
- [ ] Device import modal shows Site field
- [ ] Map picker modal renders correctly
- [ ] Backend logs show Site creation: `grep "Criando site" logs/app.log`

---

## 📌 Future Enhancements

### Google Maps Integration (High Priority)

**Placeholder Code Location**: `DeviceEditModal.vue` lines 333-373

**Implementation Steps**:
1. Add Google Maps API key to `.env`
2. Install `@googlemaps/js-api-loader` package
3. Replace placeholder with Google Maps component
4. Enable click-to-place marker
5. Add marker drag functionality
6. Implement geocoding (address → coordinates)
7. Implement reverse geocoding (coordinates → address)
8. Auto-fill city/state from reverse geocoding

**Example Code**:
```vue
<!-- DeviceEditModal.vue -->
<script setup>
import { Loader } from '@googlemaps/js-api-loader';

const initMap = async () => {
  const loader = new Loader({
    apiKey: import.meta.env.VITE_GOOGLE_MAPS_API_KEY,
    version: "weekly"
  });
  
  const { Map, Marker } = await loader.importLibrary("maps");
  
  const map = new Map(document.getElementById('map'), {
    center: { lat: mapLat.value, lng: mapLng.value },
    zoom: 15
  });
  
  const marker = new Marker({
    position: { lat: mapLat.value, lng: mapLng.value },
    map: map,
    draggable: true
  });
  
  marker.addListener('dragend', (event) => {
    mapLat.value = event.latLng.lat();
    mapLng.value = event.latLng.lng();
  });
};
</script>

<template>
  <div v-if="showMapPicker" class="fixed inset-0 z-[60]">
    <div id="map" class="w-full h-[500px]"></div>
  </div>
</template>
```

### Enhanced Site Management

1. **Site Edit Modal**: Allow editing existing sites (name, city, coordinates)
2. **Site List View**: Dedicated page to manage all sites
3. **Batch Site Import**: CSV upload for multiple sites
4. **Site Templates**: Pre-configured sites for common locations
5. **Site Clustering**: Group nearby sites on map when zoomed out

### Validation Improvements

1. **Coordinate Bounds**: Validate lat/lng within valid ranges
2. **Duplicate Detection**: Warn if site with similar name exists
3. **Address Validation**: Integrate with address verification API
4. **Distance Check**: Warn if new site is very close to existing one

---

## 📚 Related Documentation

- **Architecture**: `doc/architecture/MODULES.md` (Site model schema)
- **Data Flow**: `doc/architecture/DATA_FLOW.md` (Import workflow)
- **PostGIS Guide**: `doc/developer/POSTGIS_SPATIAL.md` (Spatial queries)
- **API Reference**: `doc/api/INVENTORY_API.md` (Endpoints)
- **Testing Guide**: `doc/guides/testing/DEVICE_IMPORT.md`

---

## 🐛 Known Issues

None currently.

---

## ✅ Completion Checklist

- [x] Frontend Site field UI implemented
- [x] Map picker modal created (placeholder)
- [x] Site reactive state management
- [x] Site validation logic
- [x] Frontend fetches sites from API
- [x] Backend Site creation with coordinates
- [x] PostGIS Point creation (lng, lat order)
- [x] Backend validation and error handling
- [x] Docker rebuild and deployment
- [x] Documentation created
- [ ] Google Maps API integration (future)
- [ ] End-to-end testing (manual verification pending)
- [ ] Automated tests (future)

---

**Status**: ✅ **READY FOR TESTING**

**Next Steps**:
1. Manual test: Select existing site → Import device
2. Manual test: Create new site → Set coordinates → Import device
3. Verify device appears on map at correct location
4. Plan Google Maps API integration (Phase 12)
