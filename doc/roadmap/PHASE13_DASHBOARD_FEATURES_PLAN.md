# Phase 13: Dashboard Features & UX Enhancement

**Status:** Ready to Start  
**Branch:** `feat/dashboard-enhancements`  
**Base:** `refactor/folder-structure` (after Phase 11 Vue 3 complete)  
**Duration:** 3 weeks (15 dias úteis)  
**Team Size:** 1 developer  
**Priority:** HIGH - Most requested features from users

---

## 📋 Executive Summary

### Strategic Context

After completing Phase 11 (Vue 3 Dashboard Migration at 10% canary rollout) and Phase 12 (Sentry APM + Performance Baseline), we have:

✅ **Solid Foundation:**
- Vue 3 + Vite frontend (44/44 tests passing, 96KB build)
- Performance baseline: 120ms dashboard load (76% better than target)
- Sentry APM capturing errors + 10% performance sampling
- Clean architecture: inventory/monitoring/integrations separated

✅ **Current Limitations (User Feedback):**
- ❌ No filtering - users scroll through ALL devices
- ❌ No search - hard to find specific host/site
- ❌ No drill-down - can't see port/fiber details
- ❌ No exports - users screenshot dashboard manually
- ❌ No offline indicators persistence - status lost on refresh

### Phase 13 Objectives

Transform the dashboard from **read-only monitoring** to **interactive operational tool** by adding:

1. **Advanced Filters** - Status/Type/Location filtering with URL persistence
2. **Search & Autocomplete** - Fast host/site lookup with fuzzy matching
3. **Drill-down Views** - Device → Port → Fiber path visualization
4. **Export Reports** - PDF/Excel with charts and metrics
5. **Browser Notifications** - Real-time alerts for critical events

### Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| **Time to find device** | ~30s (scroll) | <3s (search) | User testing |
| **Dashboard page load** | 120ms | <150ms | Chrome DevTools |
| **Filter application** | N/A | <100ms | Performance API |
| **Export generation** | Manual screenshots | <5s automated | Backend timer |
| **User satisfaction** | 6/10 (feedback) | 9/10 | NPS survey |

---

## 🎯 Sprint 1: Filters & Search (Week 1 - 5 days)

**Goal:** Enable users to quickly find and filter devices/sites  
**Value:** HIGH - Most requested feature  
**Risk:** LOW - Pure frontend work, no schema changes

### Features

#### 1.1 Advanced Filters (2 days)

**UI Components:**
```vue
<FilterBar>
  <FilterDropdown label="Status" :options="statusOptions" />
  <FilterDropdown label="Type" :options="typeOptions" />
  <FilterDropdown label="Location" :options="locationOptions" />
  <FilterClearButton />
</FilterBar>
```

**Filter Options:**

1. **Status Filter:**
   - ✅ Operational (green)
   - ⚠️ Atenção (yellow - packet loss >1%)
   - 🔴 Crítico (red - packet loss >5%)
   - ⚫ Offline (no response)
   - 🔵 Unknown (not monitored)

2. **Type Filter:**
   - OLT (GPON equipment)
   - Switch (Layer 2/3)
   - Router (core/edge)
   - Server (management)
   - Firewall
   - Access Point

3. **Location Filter:**
   - Autocomplete dropdown
   - Fuzzy search on site names
   - Group by city/region
   - Show device count per location

**State Management (Pinia):**
```typescript
// stores/filters.ts
export const useFiltersStore = defineStore('filters', {
  state: () => ({
    status: [] as string[],
    types: [] as string[],
    locations: [] as string[],
    searchQuery: '',
  }),
  getters: {
    filteredDevices: (state) => {
      // Apply all active filters to device list
      return devices.value.filter(device => {
        if (state.status.length && !state.status.includes(device.status)) return false;
        if (state.types.length && !state.types.includes(device.type)) return false;
        if (state.locations.length && !state.locations.includes(device.site_id)) return false;
        if (state.searchQuery && !matchesSearch(device, state.searchQuery)) return false;
        return true;
      });
    },
    activeFilterCount: (state) => {
      return state.status.length + state.types.length + state.locations.length;
    }
  },
  actions: {
    toggleStatus(status: string) { /* ... */ },
    clearAllFilters() { /* ... */ },
  }
});
```

**Performance:**
- Client-side filtering (no backend calls)
- Debounced filter application (50ms)
- Virtual scrolling for large device lists (>100 items)
- Filter count badge: "Filters (3)"

**Testing:**
- ✅ Unit: Filter logic with edge cases
- ✅ Component: FilterDropdown interactions
- ✅ Integration: Multiple filters combined
- ✅ E2E: User applies filters and sees results

#### 1.2 Search & Autocomplete (2 days)

**UI Component:**
```vue
<SearchInput
  v-model="searchQuery"
  placeholder="Search by hostname, IP, or site..."
  :suggestions="searchSuggestions"
  @select="handleSelect"
/>
```

**Search Features:**

1. **Fuzzy Matching:**
   - Levenshtein distance algorithm
   - Match on: hostname, IP address, site name, description
   - Highlight matched characters
   - Max 10 suggestions shown

2. **Debounced Input:**
   - 300ms delay before search triggers
   - Cancel previous search if typing continues
   - Show loading spinner during search

3. **Keyboard Navigation:**
   - Arrow Up/Down: Navigate suggestions
   - Enter: Select highlighted suggestion
   - Escape: Close suggestions dropdown
   - Tab: Accept first suggestion

4. **Search History (Local Storage):**
   - Store last 10 searches
   - Quick access to recent searches
   - Clear history button

**Implementation:**
```typescript
// composables/useSearch.ts
export function useSearch() {
  const searchQuery = ref('');
  const searchResults = ref<Device[]>([]);
  
  const debouncedSearch = useDebounceFn(async (query: string) => {
    if (query.length < 2) {
      searchResults.value = [];
      return;
    }
    
    searchResults.value = devices.value
      .filter(device => fuzzyMatch(device, query))
      .slice(0, 10);
  }, 300);
  
  watch(searchQuery, debouncedSearch);
  
  return { searchQuery, searchResults };
}
```

**Performance:**
- Search on cached data (no API calls)
- Fuzzy matching optimized with early exit
- Virtual scrolling for suggestions
- Highlight only visible text

**Testing:**
- ✅ Unit: Fuzzy matching algorithm
- ✅ Component: SearchInput keyboard navigation
- ✅ Integration: Search + filters combined
- ✅ E2E: User searches and selects device

#### 1.3 URL Persistence & Shareability (1 day)

**Goal:** Persist filters/search in URL for shareable views

**URL Structure:**
```
/maps_view/dashboard/?status=operational,offline&type=OLT&location=POPCentral&search=huawei
```

**Implementation:**
```typescript
// composables/useUrlSync.ts
export function useUrlSync() {
  const route = useRoute();
  const router = useRouter();
  const filtersStore = useFiltersStore();
  
  // Load filters from URL on mount
  onMounted(() => {
    const { status, type, location, search } = route.query;
    if (status) filtersStore.status = (status as string).split(',');
    if (type) filtersStore.types = (type as string).split(',');
    if (location) filtersStore.locations = (location as string).split(',');
    if (search) filtersStore.searchQuery = search as string;
  });
  
  // Update URL when filters change
  watch(
    () => filtersStore.$state,
    (state) => {
      router.replace({
        query: {
          status: state.status.join(',') || undefined,
          type: state.types.join(',') || undefined,
          location: state.locations.join(',') || undefined,
          search: state.searchQuery || undefined,
        },
      });
    },
    { deep: true }
  );
}
```

**Features:**
- ✅ Browser back/forward works with filter changes
- ✅ Shareable URLs (copy link, share with team)
- ✅ Bookmark specific filtered views
- ✅ Deep linking to specific device (future: `?device=123`)

**Testing:**
- ✅ Unit: URL parsing logic
- ✅ Integration: URL updates when filters change
- ✅ E2E: Browser navigation with filters

### Sprint 1 Deliverables

**Vue Components (NEW):**
- `FilterBar.vue` - Main filter container
- `FilterDropdown.vue` - Reusable dropdown component
- `SearchInput.vue` - Search with autocomplete
- `SearchSuggestions.vue` - Suggestions dropdown

**Pinia Stores (NEW):**
- `stores/filters.ts` - Filter state management

**Composables (NEW):**
- `composables/useSearch.ts` - Search logic
- `composables/useUrlSync.ts` - URL synchronization
- `composables/useFuzzyMatch.ts` - Fuzzy matching algorithm

**Tests:**
- 15+ unit tests (filters, search, fuzzy matching)
- 8+ component tests (FilterBar, SearchInput)
- 5+ E2E tests (user workflows)

**Documentation:**
- User guide: "How to filter and search"
- Developer docs: Filter architecture
- API docs: Filter state structure

---

## 🎯 Sprint 2: Drill-down & Details (Week 2 - 5 days)

**Goal:** Enable deep inspection of devices, ports, and fiber paths  
**Value:** HIGH - Critical for troubleshooting  
**Risk:** MEDIUM - Requires backend API extensions

### Features

#### 2.1 Device Details Modal (2 days)

**UI Component:**
```vue
<DeviceModal
  :device="selectedDevice"
  @close="selectedDevice = null"
>
  <TabPanel title="Overview">
    <DeviceOverview :device="device" />
  </TabPanel>
  <TabPanel title="Ports">
    <PortsList :device-id="device.id" />
  </TabPanel>
  <TabPanel title="History">
    <DeviceHistory :device-id="device.id" />
  </TabPanel>
  <TabPanel title="Metrics">
    <DeviceMetrics :device-id="device.id" />
  </TabPanel>
</DeviceModal>
```

**Tabs:**

1. **Overview Tab:**
   - Device name, IP, MAC, serial number
   - Current status (operational/offline/critical)
   - Last seen timestamp
   - Uptime, CPU, memory (from Zabbix cache)
   - Site location with map preview
   - Edit/Delete buttons (admin only)

2. **Ports Tab:**
   - Table of all ports (interface name, status, speed)
   - Filter by: Up/Down, Speed, Type (fiber/copper)
   - Optical levels (TX/RX) for fiber ports
   - Connected devices (from topology discovery)
   - Port utilization graphs

3. **History Tab:**
   - Status change timeline (last 7/30/90 days)
   - Downtime periods with duration
   - Configuration changes audit log
   - Maintenance windows scheduled

4. **Metrics Tab:**
   - Traffic graphs (in/out) - 24h/7d/30d
   - Error rate trends
   - Temperature/power supply status
   - Custom Zabbix metrics

**Backend API Extensions:**

```python
# inventory/api/device_details.py
@api_view(['GET'])
def device_details(request, device_id):
    """Get comprehensive device details with ports and metrics."""
    device = get_object_or_404(Device, id=device_id)
    
    # Get cached Zabbix status
    zabbix_status = cache.get(f'device_status_{device_id}')
    
    # Get ports with optical levels
    ports = device.ports.select_related('connected_to').all()
    
    # Get status history (last 30 days)
    history = DeviceStatusHistory.objects.filter(
        device=device,
        timestamp__gte=timezone.now() - timedelta(days=30)
    ).order_by('-timestamp')
    
    return Response({
        'device': DeviceSerializer(device).data,
        'zabbix_status': zabbix_status,
        'ports': PortSerializer(ports, many=True).data,
        'history': StatusHistorySerializer(history, many=True).data,
    })
```

**Performance:**
- Lazy load tabs (only fetch data when tab opened)
- Cache device details for 60s
- Pagination for port list (50 per page)
- Virtual scrolling for history timeline

**Testing:**
- ✅ Unit: Device detail serializer
- ✅ Component: Tab navigation
- ✅ Integration: API fetches correct data
- ✅ E2E: User opens modal and navigates tabs

#### 2.2 Port Details & Fiber Path Visualization (2 days)

**UI Component:**
```vue
<PortDetailsPanel :port="selectedPort">
  <FiberPathVisualization :port-id="port.id" />
  <OpticalLevelsChart :port-id="port.id" />
  <ConnectedDevices :port-id="port.id" />
</PortDetailsPanel>
```

**Fiber Path Visualization:**

```
[OLT Port 1] ━━━━━━━━━━━━━━ [Fiber Cable: 2.4km] ━━━━━━━━━━━━━━ [Switch Port 24]
   TX: -3.2 dBm         Loss: 0.8 dB/km (Budget: 1.9 dB)         RX: -5.1 dBm
   
   Segment Details:
   ├─ Fiber Type: G.652.D SMF
   ├─ Core Count: 24F
   ├─ Wavelength: 1310nm
   ├─ Connectors: SC/APC → SC/APC
   └─ Installation Date: 2023-08-15
```

**Features:**
1. **Optical Power Budget Calculation:**
   - TX power - RX power - connector losses
   - Visual indicator: ✅ Good / ⚠️ Warning / ❌ Critical
   - Threshold: Good <3dB, Warning 3-6dB, Critical >6dB

2. **Fiber Segment Details:**
   - Fiber type, core count, wavelength
   - Length from Route model
   - Connector types
   - Installation date, maintenance history

3. **Topology Visualization:**
   - Interactive graph: Device → Port → Fiber → Port → Device
   - Zoom/pan controls
   - Export as PNG/SVG
   - Print-friendly view

**Backend API Extensions:**

```python
# inventory/api/fiber_path.py
@api_view(['GET'])
def fiber_path(request, port_id):
    """Get complete fiber path from source port to destination."""
    port = get_object_or_404(Port, id=port_id)
    
    # Find connected fiber segment
    segment = FiberSegment.objects.filter(
        Q(start_port=port) | Q(end_port=port)
    ).select_related('start_port__device', 'end_port__device').first()
    
    if not segment:
        return Response({'error': 'No fiber connection found'}, status=404)
    
    # Calculate optical budget
    budget = calculate_optical_budget(segment)
    
    # Get optical level history (24h)
    levels = OpticalLevelSnapshot.objects.filter(
        port=port,
        timestamp__gte=timezone.now() - timedelta(hours=24)
    ).order_by('timestamp')
    
    return Response({
        'segment': FiberSegmentSerializer(segment).data,
        'optical_budget': budget,
        'optical_levels_history': OpticalLevelSerializer(levels, many=True).data,
    })
```

**Testing:**
- ✅ Unit: Optical budget calculation
- ✅ Component: Fiber path rendering
- ✅ Integration: API returns correct topology
- ✅ E2E: User views fiber path for port

#### 2.3 Breadcrumb Navigation & Mobile Responsive (1 day)

**Breadcrumb Component:**
```vue
<Breadcrumb>
  <BreadcrumbItem to="/maps_view/dashboard/">Dashboard</BreadcrumbItem>
  <BreadcrumbItem>{{ device.name }}</BreadcrumbItem>
  <BreadcrumbItem active>Port {{ port.name }}</BreadcrumbItem>
</Breadcrumb>
```

**Mobile Optimization:**
- Responsive grid: 1 col mobile, 2 col tablet, 3 col desktop
- Touch-friendly tap targets (44x44px minimum)
- Swipe gestures for tab navigation
- Bottom sheet for filters on mobile
- Hamburger menu for navigation

**Testing:**
- ✅ Visual: Mobile/tablet/desktop layouts
- ✅ Touch: Swipe gestures work
- ✅ Accessibility: Screen reader navigation

### Sprint 2 Deliverables

**Vue Components (NEW):**
- `DeviceModal.vue` - Modal with tabs
- `TabPanel.vue` - Reusable tab component
- `PortDetailsPanel.vue` - Port drill-down
- `FiberPathVisualization.vue` - Topology graph
- `OpticalLevelsChart.vue` - Time series chart
- `Breadcrumb.vue` - Navigation breadcrumbs

**Backend APIs (NEW):**
- `GET /api/v1/inventory/devices/<id>/details/` - Device details
- `GET /api/v1/inventory/ports/<id>/fiber-path/` - Fiber path
- `GET /api/v1/inventory/ports/<id>/optical-history/` - Optical levels

**Database (NEW):**
- `DeviceStatusHistory` model - Track status changes
- `OpticalLevelSnapshot` model - Historical optical data

**Tests:**
- 12+ unit tests (budget calculation, serializers)
- 10+ component tests (modals, tabs, charts)
- 6+ API tests (detail endpoints)
- 4+ E2E tests (drill-down workflows)

**Documentation:**
- User guide: "Understanding fiber paths"
- API docs: Device details endpoints
- Architecture: Modal state management

---

## 🎯 Sprint 3: Reports & Notifications (Week 3 - 5 days)

**Goal:** Enable data export and real-time alerting  
**Value:** MEDIUM-HIGH - Operational efficiency  
**Risk:** MEDIUM - Requires PDF generation + push notifications

### Features

#### 3.1 Export Reports (PDF/Excel) (2 days)

**UI Component:**
```vue
<ExportButton @click="handleExport">
  <ExportDropdown>
    <ExportOption format="pdf" label="Export as PDF" />
    <ExportOption format="excel" label="Export as Excel" />
    <ExportOption format="csv" label="Export as CSV" />
  </ExportDropdown>
</ExportButton>
```

**Report Types:**

1. **Dashboard Snapshot (PDF):**
   - Cover page with timestamp, user, filters applied
   - Device status summary table
   - Charts: Status distribution pie chart, uptime graph
   - Full device list with status indicators
   - Footer: Generated by MapsProveFiber v2.0

2. **Device Inventory (Excel):**
   - Columns: Name, IP, Type, Site, Status, Uptime, Last Seen
   - Conditional formatting: Green/Yellow/Red status
   - Pivot tables: Devices by status, devices by type
   - Charts: Status distribution, devices per site

3. **Fiber Routes (CSV):**
   - Columns: Route Name, Distance, Segments, Optical Budget, Status
   - Easy import into spreadsheet tools
   - Suitable for bulk analysis

**Backend Implementation:**

```python
# maps_view/api/export.py
from weasyprint import HTML, CSS
from openpyxl import Workbook
from openpyxl.chart import PieChart
import csv

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def export_dashboard_pdf(request):
    """Generate PDF report of current dashboard state."""
    filters = request.data.get('filters', {})
    
    # Get filtered devices
    devices = get_dashboard_devices(filters)
    
    # Render HTML template
    html_content = render_to_string('exports/dashboard_pdf.html', {
        'devices': devices,
        'timestamp': timezone.now(),
        'user': request.user,
        'filters': filters,
    })
    
    # Generate PDF
    pdf_file = HTML(string=html_content).write_pdf()
    
    # Track in Sentry
    with sentry_sdk.start_span(op="export.pdf", description="Dashboard PDF"):
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="dashboard_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
        return response

@api_view(['POST'])
def export_inventory_excel(request):
    """Generate Excel report with charts and pivot tables."""
    devices = get_dashboard_devices(request.data.get('filters', {}))
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Device Inventory"
    
    # Headers
    headers = ['Name', 'IP', 'Type', 'Site', 'Status', 'Uptime', 'Last Seen']
    ws.append(headers)
    
    # Data rows
    for device in devices:
        ws.append([
            device.name,
            device.ip_address,
            device.device_type,
            device.site.name,
            device.status,
            device.uptime_hours,
            device.last_seen.isoformat() if device.last_seen else '',
        ])
    
    # Add pie chart
    chart = PieChart()
    chart.title = "Devices by Status"
    ws2 = wb.create_sheet("Charts")
    ws2.append(['Status', 'Count'])
    # ... (add chart data)
    
    # Save to bytes
    excel_file = io.BytesIO()
    wb.save(excel_file)
    excel_file.seek(0)
    
    response = HttpResponse(excel_file.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="inventory_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
    return response
```

**Performance:**
- Generate reports asynchronously (Celery task for large datasets)
- Show progress indicator during generation
- Cache report for 5 minutes (same filters)
- Limit report size: Max 1000 devices per PDF, 10,000 per Excel

**Testing:**
- ✅ Unit: PDF generation logic
- ✅ Integration: Excel charts render correctly
- ✅ E2E: User exports report and downloads file

#### 3.2 Browser Push Notifications (2 days)

**UI Component:**
```vue
<NotificationSettings>
  <NotificationToggle
    label="Enable browser notifications"
    v-model="notificationsEnabled"
    @change="handlePermissionRequest"
  />
  <NotificationPreferences v-if="notificationsEnabled">
    <PreferenceToggle label="Device goes offline" v-model="prefs.offline" />
    <PreferenceToggle label="Critical status (>5% packet loss)" v-model="prefs.critical" />
    <PreferenceToggle label="Optical power out of range" v-model="prefs.optical" />
    <PreferenceToggle label="New device discovered" v-model="prefs.newDevice" />
  </NotificationPreferences>
</NotificationSettings>
```

**Notification Flow:**

```
Celery Task detects status change
    ↓
Publish to WebSocket channel (existing infrastructure)
    ↓
Frontend receives WebSocket message
    ↓
Check user notification preferences
    ↓
Show browser notification if enabled
    ↓
Play sound alert (optional)
    ↓
Log notification in database
```

**Implementation:**

```typescript
// composables/useNotifications.ts
export function useNotifications() {
  const { data: preferences } = useFetch('/api/v1/users/notification-preferences/');
  
  async function requestPermission() {
    if (!('Notification' in window)) {
      console.error('Browser does not support notifications');
      return false;
    }
    
    const permission = await Notification.requestPermission();
    return permission === 'granted';
  }
  
  function showNotification(title: string, options: NotificationOptions) {
    if (Notification.permission !== 'granted') return;
    
    const notification = new Notification(title, {
      icon: '/static/img/logo.png',
      badge: '/static/img/badge.png',
      vibrate: [200, 100, 200],
      ...options,
    });
    
    notification.onclick = () => {
      window.focus();
      notification.close();
    };
    
    // Auto-close after 10 seconds
    setTimeout(() => notification.close(), 10000);
  }
  
  return { requestPermission, showNotification, preferences };
}
```

**Backend API:**

```python
# setup_app/api/notification_preferences.py
class NotificationPreferences(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    offline_alerts = models.BooleanField(default=True)
    critical_alerts = models.BooleanField(default=True)
    optical_alerts = models.BooleanField(default=False)
    new_device_alerts = models.BooleanField(default=False)
    email_enabled = models.BooleanField(default=False)
    email_address = models.EmailField(blank=True)
    
    class Meta:
        verbose_name_plural = "Notification preferences"

@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def notification_preferences(request):
    prefs, created = NotificationPreferences.objects.get_or_create(user=request.user)
    
    if request.method == 'PATCH':
        serializer = NotificationPreferencesSerializer(prefs, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)
    
    return Response(NotificationPreferencesSerializer(prefs).data)
```

**WebSocket Integration (Existing):**

```python
# maps_view/realtime/publisher.py (ENHANCED)
def broadcast_status_change(device_id: int, old_status: str, new_status: str):
    """Broadcast device status change to all dashboard clients."""
    device = Device.objects.get(id=device_id)
    
    message = {
        'type': 'status_change',
        'device_id': device_id,
        'device_name': device.name,
        'old_status': old_status,
        'new_status': new_status,
        'timestamp': timezone.now().isoformat(),
    }
    
    # Existing WebSocket broadcast
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        'dashboard_status',
        {
            'type': 'status_update',
            'message': message,
        }
    )
    
    # NEW: Check if notification should be sent
    if should_notify(new_status):
        # Get users with notifications enabled for this event type
        users_to_notify = get_users_for_notification(event_type='status_change', severity=new_status)
        
        for user in users_to_notify:
            # WebSocket will trigger browser notification on client side
            pass  # Client handles notification display
```

**Notification Types:**

1. **Device Offline:**
   - Title: "🔴 Device Offline"
   - Body: "SW-CORE-01 (192.168.1.1) is not responding"
   - Action: Click to view device details

2. **Critical Status:**
   - Title: "⚠️ Critical Status"
   - Body: "OLT-POP-02 has 8% packet loss"
   - Action: Click to view metrics

3. **Optical Power Alert:**
   - Title: "📉 Optical Power Out of Range"
   - Body: "Port 1/1/24 RX power: -28 dBm (critical)"
   - Action: Click to view fiber path

4. **New Device:**
   - Title: "✨ New Device Discovered"
   - Body: "SW-ACCESS-15 added to inventory"
   - Action: Click to configure

**Testing:**
- ✅ Unit: Notification preference logic
- ✅ Component: Settings UI interactions
- ✅ Integration: WebSocket triggers notification
- ✅ E2E: User enables notifications and receives alert

#### 3.3 Notification History & Management (1 day)

**UI Component:**
```vue
<NotificationHistory>
  <NotificationList :notifications="recentNotifications">
    <NotificationItem
      v-for="notif in notifications"
      :key="notif.id"
      :notification="notif"
      @dismiss="dismissNotification(notif.id)"
      @click="navigateToDevice(notif.device_id)"
    />
  </NotificationList>
  <NotificationActions>
    <ClearAllButton @click="clearAllNotifications" />
    <MarkAllReadButton @click="markAllAsRead" />
  </NotificationActions>
</NotificationHistory>
```

**Features:**
- Notification inbox (last 100 notifications)
- Read/unread status
- Dismiss individual notifications
- Clear all notifications
- Filter by: All / Unread / Critical
- Export notification log (CSV)

**Backend Model:**

```python
# setup_app/models.py
class NotificationLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    body = models.TextField()
    notification_type = models.CharField(max_length=50)  # offline, critical, optical, new_device
    device = models.ForeignKey('inventory.Device', null=True, on_delete=models.SET_NULL)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    dismissed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read']),
        ]
```

**Testing:**
- ✅ Unit: Notification log creation
- ✅ Component: Notification list rendering
- ✅ Integration: Mark as read API
- ✅ E2E: User views and dismisses notifications

### Sprint 3 Deliverables

**Vue Components (NEW):**
- `ExportButton.vue` - Export dropdown
- `ExportDropdown.vue` - Format selection
- `NotificationSettings.vue` - Preference manager
- `NotificationHistory.vue` - Notification inbox
- `NotificationItem.vue` - Single notification

**Backend APIs (NEW):**
- `POST /api/v1/maps_view/export/pdf/` - Generate PDF
- `POST /api/v1/maps_view/export/excel/` - Generate Excel
- `POST /api/v1/maps_view/export/csv/` - Generate CSV
- `GET /api/v1/users/notification-preferences/` - Get preferences
- `PATCH /api/v1/users/notification-preferences/` - Update preferences
- `GET /api/v1/users/notifications/` - Get notification history
- `POST /api/v1/users/notifications/<id>/dismiss/` - Dismiss notification

**Database (NEW):**
- `NotificationPreferences` model
- `NotificationLog` model

**Dependencies (NEW):**
- `weasyprint` - PDF generation
- `openpyxl` - Excel generation

**Tests:**
- 10+ unit tests (PDF/Excel generation, notification logic)
- 8+ component tests (export UI, notification settings)
- 6+ API tests (export endpoints, preferences)
- 4+ E2E tests (export workflow, notification flow)

**Documentation:**
- User guide: "Exporting reports"
- User guide: "Managing notifications"
- API docs: Export endpoints
- Developer docs: PDF template structure

---

## 📊 Phase 13 Summary

### Total Effort

| Sprint | Duration | Focus | Components | Tests | APIs |
|--------|----------|-------|------------|-------|------|
| **Sprint 1** | 5 days | Filters & Search | 4 | 28 | 0 |
| **Sprint 2** | 5 days | Drill-down & Details | 6 | 32 | 3 |
| **Sprint 3** | 5 days | Reports & Notifications | 5 | 28 | 7 |
| **TOTAL** | **15 days** | **3 weeks** | **15** | **88** | **10** |

### Dependencies

**External Libraries:**
```json
// frontend/package.json additions
{
  "dependencies": {
    "fuse.js": "^7.0.0",          // Fuzzy search
    "vue3-chart-v2": "^3.2.0",    // Charts for metrics
    "d3": "^7.9.0",                // Fiber path visualization
    "@vueuse/core": "^11.0.0"     // Composables (debounce, etc)
  }
}
```

```python
# backend/requirements.txt additions
weasyprint==62.0        # PDF generation
openpyxl==3.1.2         # Excel generation
```

### Database Migrations

```bash
# Sprint 2
python manage.py makemigrations inventory --name add_device_status_history
python manage.py makemigrations inventory --name add_optical_level_snapshot

# Sprint 3
python manage.py makemigrations setup_app --name add_notification_preferences
python manage.py makemigrations setup_app --name add_notification_log
```

### Performance Impact

**Expected overhead:**
- Filters: 0ms (client-side)
- Search: <50ms (cached data)
- Device details modal: <200ms (API call)
- PDF export: 2-5s (async generation)
- Browser notifications: 0ms (native API)

**Mitigation:**
- All filters/search use cached dashboard data (no new API calls)
- Detail modals lazy-load tabs
- Exports run asynchronously (Celery)
- Notifications use existing WebSocket infrastructure

### Success Criteria

**Sprint 1 (Filters & Search):**
- ✅ User can filter by status, type, location in <100ms
- ✅ Search returns results in <300ms
- ✅ Filters persist in URL for shareability
- ✅ All 28 tests passing

**Sprint 2 (Drill-down):**
- ✅ Device modal loads in <200ms
- ✅ Fiber path visualization renders correctly
- ✅ Optical budget calculation accurate within ±0.1 dB
- ✅ All 32 tests passing

**Sprint 3 (Reports):**
- ✅ PDF export completes in <5s
- ✅ Excel includes charts and pivot tables
- ✅ Browser notifications work in Chrome/Firefox/Edge
- ✅ All 28 tests passing

### Rollout Plan

**Phase 13.1 (Sprint 1):**
- Day 1-2: Filters UI + state management
- Day 3-4: Search + autocomplete
- Day 5: URL persistence + testing

**Phase 13.2 (Sprint 2):**
- Day 6-7: Device modal + tabs
- Day 8-9: Fiber path + optical budget
- Day 10: Mobile responsive + breadcrumbs

**Phase 13.3 (Sprint 3):**
- Day 11-12: PDF/Excel export
- Day 13-14: Browser notifications
- Day 15: Notification history + final testing

### Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| PDF generation slow | MEDIUM | MEDIUM | Use Celery async tasks, cache reports |
| Browser notification support | LOW | LOW | Graceful degradation, show in-app notifications |
| Fiber path complexity | MEDIUM | HIGH | Start with simple visualization, iterate |
| Export file size limits | LOW | MEDIUM | Paginate large datasets, max 10k rows |
| Mobile UX issues | MEDIUM | MEDIUM | Test on real devices, iterate on feedback |

---

## 🎯 Next Steps After Phase 13

### Phase 14: GPON Provisioning (3 weeks)
- ONU provisioning wizard
- VLAN/profile assignment
- Bulk provisioning (CSV import)
- ONU status monitoring
- Signal quality alerts

### Phase 15: Advanced Analytics (4 weeks)
- Predictive maintenance (ML models)
- Traffic forecasting
- Anomaly detection
- Custom dashboards (drag & drop widgets)
- Historical trend analysis

### Phase 16: Mobile App (6 weeks)
- React Native app (iOS/Android)
- Offline mode with sync
- Push notifications (FCM)
- Barcode scanner for device discovery
- Field technician workflow

---

## 📚 References

- **Phase 11 Report:** `doc/reports/phases/PHASE11_VUE3_DASHBOARD_COMPLETE.md`
- **Performance Baseline:** `doc/roadmap/PERFORMANCE_BASELINE_REPORT.md`
- **Sentry APM:** `doc/roadmap/SENTRY_APM_COMPLETE.md`
- **API Documentation:** `doc/api/ENDPOINTS.md`
- **Architecture:** `doc/architecture/ADR/004-refactoring-plan.md`

---

**Author:** AI Assistant (with user validation)  
**Date:** November 12, 2025  
**Version:** 1.0  
**Status:** Ready for Review & Approval
