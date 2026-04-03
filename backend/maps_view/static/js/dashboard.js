// Dashboard Map - Site-based view v2.0 - Updated 2025-11-13 23:07
const STATUS_COLORS = {
    up: '#16a34a', // green
    down: '#dc2626', // red
    degraded: '#f59e0b', // amber
    unknown: '#6b7280' // gray
};
let map; let cablesLayer = []; let markers = [];
let cablePolylines = {}; // id -> polyline
let cableDataCache = {}; // id -> cable object
let bounds; // Tracks map bounds

const initialHostsSnapshot = Array.isArray(window.HOSTS_DATA) ? window.HOSTS_DATA : [];
let currentHostsSnapshot = initialHostsSnapshot.slice();
let currentSummarySnapshot = (window.HOSTS_SUMMARY && typeof window.HOSTS_SUMMARY === 'object')
    ? { ...window.HOSTS_SUMMARY }
    : null;

let dashboardSocket = null;
let activeWsPath = null;
let dashboardReconnectDelay = 5000;
const DASHBOARD_WS_MAX_DELAY = 60000;
const preferredWsPath = (window.location.pathname.startsWith('/maps_view/')
    ? '/maps_view/ws/dashboard/status/'
    : '/ws/dashboard/status/');
const DASHBOARD_WS_PATHS = Array.from(
    new Set([preferredWsPath, '/ws/dashboard/status/', '/maps_view/ws/dashboard/status/'])
);
let wsPathCursor = 0;
let lastSuccessfulWsPath = null;
let connectingTimeoutId = null;

function escapeHtml(value) {
    if (value === null || value === undefined) return '';
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function truncateText(value, limit = 10) {
    const text = value ? String(value) : '';
    if (text.length <= limit) return text;
    const ellipsis = '...';
    if (limit <= ellipsis.length) {
        return ellipsis.slice(0, Math.max(0, limit));
    }
    const safeLength = Math.max(0, limit - ellipsis.length);
    return `${text.slice(0, safeLength)}${ellipsis}`;
}

function computePercent(part, total) {
    if (!total || total <= 0) {
        return 0;
    }
    return Math.max(0, Math.min(100, (Number(part) / Number(total)) * 100));
}

function updateSummaryUI(summary) {
    if (!summary) return;
    
    // Update progress bars
    const progressAvailable = document.getElementById('progress-available');
    const progressUnavailable = document.getElementById('progress-unavailable');
    const progressUnknown = document.getElementById('progress-unknown');
    
    if (progressAvailable && summary.availability_percentage !== undefined) {
        progressAvailable.style.width = `${summary.availability_percentage}%`;
    }
    if (progressUnavailable && summary.total > 0) {
        const unavailablePercent = computePercent(summary.unavailable, summary.total);
        progressUnavailable.style.width = `${unavailablePercent}%`;
    }
    if (progressUnknown && summary.total > 0) {
        const unknownPercent = computePercent(summary.unknown, summary.total);
        progressUnknown.style.width = `${unknownPercent}%`;
    }
    
    // Update text counters if elements exist
    const totalEl = document.getElementById('total-hosts');
    const availableEl = document.getElementById('available-hosts');
    const unavailableEl = document.getElementById('unavailable-hosts');
    const unknownEl = document.getElementById('unknown-hosts');
    
    if (totalEl) totalEl.textContent = summary.total || 0;
    if (availableEl) availableEl.textContent = summary.available || 0;
    if (unavailableEl) unavailableEl.textContent = summary.unavailable || 0;
    if (unknownEl) unknownEl.textContent = summary.unknown || 0;
}


function currentWsPath(forceResolve = false) {
    if (!forceResolve && lastSuccessfulWsPath) {
        return lastSuccessfulWsPath;
    }
    return DASHBOARD_WS_PATHS[wsPathCursor % DASHBOARD_WS_PATHS.length];
}

function advanceWsPath(failedPath) {
    if (DASHBOARD_WS_PATHS.length <= 1) {
        return null;
    }
    const currentIndex = failedPath ? DASHBOARD_WS_PATHS.indexOf(failedPath) : wsPathCursor;
    const nextIndex = (currentIndex + 1) % DASHBOARD_WS_PATHS.length;
    if (nextIndex == currentIndex) {
        return null;
    }
    wsPathCursor = nextIndex;
    return DASHBOARD_WS_PATHS[nextIndex];
}

const realtimeElements = {
    pill: null,
    text: null,
    dot: null,
    currentState: null,
};

const REALTIME_STATUS_CONFIG = {
    connecting: {
        text: 'Connecting to realtime updates...',
        state: 'connecting',
    },
    connected: {
        text: 'Realtime updates active',
        state: 'connected',
    },
    offline: {
        text: 'Realtime updates offline -- using scheduled refresh',
        state: 'offline',
        pulse: true,
    },
};
let fallbackTimeoutId = null;

function cacheRealtimeElements() {
    if (typeof document === 'undefined') return;
    realtimeElements.pill = document.getElementById('realtimeStatusPill');
    realtimeElements.text = document.getElementById('realtimeStatusText');
    realtimeElements.dot = document.getElementById('realtimeStatusDot');
    realtimeElements.currentState = realtimeElements.pill
        ? realtimeElements.pill.dataset.state || null
        : null;
}

function updateRealtimeBanner(state) {
    const config = REALTIME_STATUS_CONFIG[state] || REALTIME_STATUS_CONFIG.connecting;
    if (!realtimeElements.pill && typeof document !== 'undefined') {
        cacheRealtimeElements();
    }

    if (!realtimeElements.pill) {
        return;
    }

    realtimeElements.currentState = config.state;
    realtimeElements.pill.dataset.state = config.state;
    realtimeElements.pill.classList.remove('bg-gray-100', 'border-gray-200', 'text-gray-600');

    if (realtimeElements.text) {
        realtimeElements.text.textContent = config.text;
        realtimeElements.text.dataset.state = config.state;
    }

    if (realtimeElements.dot) {
        realtimeElements.dot.dataset.state = config.state;
    }

    if (config.pulse) {
        realtimeElements.pill.classList.add('animate-pulse');
    } else {
        realtimeElements.pill.classList.remove('animate-pulse');
    }

    if (config.state === 'connecting') {
        if (!connectingTimeoutId) {
            connectingTimeoutId = setTimeout(() => {
                if (realtimeElements.currentState === 'connecting') {
                    updateRealtimeBanner('offline');
                }
            }, 15000);
        }
    } else {
        if (connectingTimeoutId) {
            clearTimeout(connectingTimeoutId);
            connectingTimeoutId = null;
        }
    }
}

function clearFallbackTimer() {
    if (fallbackTimeoutId) {
        clearTimeout(fallbackTimeoutId);
        fallbackTimeoutId = null;
    }
}

async function fetchHostsSnapshot() {
    try {
    const snapshotResponse = await fetchJSON('/api/v1/monitoring/hosts/status/');
        if (!snapshotResponse) {
            return;
        }
        if (!Array.isArray(snapshotResponse.hosts)) {
            return;
        }
        const summary = snapshotResponse.summary
            ? { ...snapshotResponse.summary }
            : currentSummarySnapshot
            ? { ...currentSummarySnapshot }
            : {};

        if (typeof summary.total === 'undefined') {
            summary.total = typeof snapshotResponse.total !== 'undefined'
                ? snapshotResponse.total
                : Array.isArray(snapshotResponse.hosts)
                ? snapshotResponse.hosts.length
                : 0;
        }

        const snapshot = {
            hosts: snapshotResponse.hosts || [],
            summary,
        };
        applyDashboardSnapshot(snapshot);
    } catch (error) {
        console.error('[dashboard] HTTP fallback failed:', error);
    }
}

function scheduleHttpFallback(delay = 15000) {
    if (fallbackTimeoutId) {
        return;
    }
    fallbackTimeoutId = setTimeout(async () => {
        fallbackTimeoutId = null;
        await fetchHostsSnapshot();
        const socketOpen = typeof WebSocket !== 'undefined'
            && dashboardSocket
            && dashboardSocket.readyState === WebSocket.OPEN;
        if (!socketOpen) {
            scheduleHttpFallback(60000);
        }
    }, delay);
}

function updateSummary(summary) {
    if (!summary || typeof summary !== 'object') {
        return;
    }

    const total = Number(summary.total) || 0;
    const available = Number(summary.available) || 0;
    const unavailable = Number(summary.unavailable) || 0;
    const unknown = Number(summary.unknown) || 0;
    const availabilityPercentage = Number(summary.availability_percentage ?? computePercent(available, total));

    const totalEl = document.getElementById('summary-total');
    const availableEl = document.getElementById('summary-available');
    const unavailableEl = document.getElementById('summary-unavailable');
    const unknownEl = document.getElementById('summary-unknown');
    const availabilityEl = document.getElementById('summary-availability');

    if (totalEl) totalEl.textContent = total;
    if (availableEl) availableEl.textContent = available;
    if (unavailableEl) unavailableEl.textContent = unavailable;
    if (unknownEl) unknownEl.textContent = unknown;
    if (availabilityEl) {
        const formatted = availabilityPercentage.toFixed(2);
        availabilityEl.textContent = `${formatted}%`;
        availabilityEl.classList.remove('text-green-600', 'text-yellow-500', 'text-red-600');
        if (availabilityPercentage >= 95) {
            availabilityEl.classList.add('text-green-600');
        } else if (availabilityPercentage >= 80) {
            availabilityEl.classList.add('text-yellow-500');
        } else {
            availabilityEl.classList.add('text-red-600');
        }
    }

    const progressAvailable = document.getElementById('progress-available');
    const progressUnavailable = document.getElementById('progress-unavailable');
    const progressUnknown = document.getElementById('progress-unknown');

    if (progressAvailable) progressAvailable.style.width = `${computePercent(available, total).toFixed(2)}%`;
    if (progressUnavailable) progressUnavailable.style.width = `${computePercent(unavailable, total).toFixed(2)}%`;
    if (progressUnknown) progressUnknown.style.width = `${computePercent(unknown, total).toFixed(2)}%`;
}

function renderHostCard(host) {
    const statusClass = host.status_class || '';
    const color = host.color || STATUS_COLORS.unknown;
    const name = escapeHtml(host.name || 'Unknown host');
    const site = escapeHtml(host.site || 'N/A');
    const badgeText = escapeHtml(host.available_text || 'Unknown');
    const hostId = escapeHtml(host.hostid || '');
    const truncatedHostId = truncateText(hostId, 10);
    const iface = host.interface || {};
    const interfaceIp = iface.ip ? escapeHtml(iface.ip) : '';
    const interfaceName = iface.name ? escapeHtml(iface.name) : '';
    const zabbixError = host.error ? escapeHtml(host.error) : '';

    const ipBlock = interfaceIp
        ? `<div class="flex justify-between items-center">
            <span class="font-medium">IP:</span>
            <button type="button"
                    class="ip-action-trigger text-blue-600 hover:text-blue-800 underline ml-2 truncate max-w-[130px] text-left"
                    data-ip="${interfaceIp}"
                    title="${interfaceIp}">
              ${interfaceIp}
            </button>
          </div>`
        : '';

    const interfaceBlock = interfaceName
        ? `<div class="flex justify-between">
            <span class="font-medium">Interface:</span>
            <span class="text-right truncate ml-2" title="${interfaceName}">${interfaceName}</span>
          </div>`
        : '';

    const errorBlock = zabbixError
        ? `<div class="mt-3 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
            <strong class="block mb-1">Zabbix Error:</strong>
            <span class="break-words">${truncateText(zabbixError, 100)}</span>
          </div>`
        : '';

    return `<div class="device-card p-4 border rounded-lg ${statusClass}" data-host-id="${hostId}">
        <div class="flex items-start justify-between mb-3">
          <div class="flex items-center space-x-2 flex-1 min-w-0">
            <span class="status-indicator" style="background-color: ${color}"></span>
            <span class="font-medium text-sm truncate" title="${name}">${name}</span>
          </div>
          <span class="text-xs px-2 py-1 rounded-full font-medium ${statusClass} whitespace-nowrap">
            ${badgeText}
          </span>
        </div>

        <div class="space-y-2 text-xs text-gray-600">
          <div class="flex justify-between">
            <span class="font-medium">Site:</span>
            <span class="text-right truncate ml-2" title="${site}">${site}</span>
          </div>
          ${ipBlock}
          <div class="flex justify-between">
            <span class="font-medium">Host ID:</span>
            <span class="text-right font-mono text-xs" title="${hostId}">${truncatedHostId}</span>
          </div>
          ${interfaceBlock}
        </div>
        ${errorBlock}
      </div>`;
}

function renderHosts(hosts) {
    const container = document.getElementById('hostsGrid');
    if (!container) return;

    if (!Array.isArray(hosts) || hosts.length === 0) {
        container.innerHTML = `<div class="col-span-full text-center py-8">
            <div class="text-gray-400 mb-3">
              <svg class="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
              </svg>
            </div>
            <p class="text-gray-500">No monitored devices were found.</p>
          </div>`;
        currentHostsSnapshot = [];
        window.HOSTS_DATA = [];
        return;
    }

    const sortedHosts = hosts.slice().sort((a, b) => {
        const nameA = (a.name || '').toLowerCase();
        const nameB = (b.name || '').toLowerCase();
        return nameA.localeCompare(nameB);
    });

    container.innerHTML = sortedHosts.map(renderHostCard).join('');
    currentHostsSnapshot = sortedHosts;
    window.HOSTS_DATA = sortedHosts;
}

function applyDashboardSnapshot(snapshot) {
    if (!snapshot || typeof snapshot !== 'object') {
        return;
    }
    if (snapshot.summary) {
        currentSummarySnapshot = { ...snapshot.summary };
        window.HOSTS_SUMMARY = currentSummarySnapshot;
        updateSummary(currentSummarySnapshot);
    }
    if (snapshot.hosts) {
        renderHosts(snapshot.hosts);
    }
}

function initRealtimeUpdates(forceFallbackPath = false) {
    if (typeof window === 'undefined' || !('WebSocket' in window)) {
        console.warn('[dashboard] WebSocket not supported; realtime updates disabled.');
        updateRealtimeBanner('offline');
        scheduleHttpFallback(0);
        return;
    }

    // Skip the intermediate "connecting" message; attempt connection immediately
    const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const chosenPath = forceFallbackPath ? DASHBOARD_WS_PATHS[wsPathCursor % DASHBOARD_WS_PATHS.length] : currentWsPath();
    const wsUrl = `${scheme}://${window.location.host}${chosenPath}`;
    activeWsPath = chosenPath;

    try {
        dashboardSocket = new WebSocket(wsUrl);
    } catch (err) {
        console.error('[dashboard] Failed to open realtime socket:', err);
        updateRealtimeBanner('offline');
        scheduleHttpFallback(0);
        return;
    }

    dashboardSocket.onopen = () => {
        console.info('[dashboard] realtime socket open', { path: chosenPath });
        clearFallbackTimer();
        updateRealtimeBanner('connected');
        lastSuccessfulWsPath = chosenPath;
        const resolvedIndex = DASHBOARD_WS_PATHS.indexOf(chosenPath);
        if (resolvedIndex >= 0) {
            wsPathCursor = resolvedIndex;
        }
        dashboardReconnectDelay = 5000;
    };

    dashboardSocket.onmessage = (event) => {
        try {
            const payload = JSON.parse(event.data);
            
            // Handle dashboard host status updates
            if (payload && payload.event === 'dashboard.status' && payload.data) {
                applyDashboardSnapshot(payload.data);
                clearFallbackTimer();
            }
            
            // Handle cable status updates (NEW)
            if (payload && payload.type === 'cable_status_update' && payload.cables) {
                applyCableStatusBatch(payload.cables);
            }
        } catch (err) {
            console.error('[dashboard] Failed to parse realtime payload:', err);
        }
    };

    dashboardSocket.onerror = (err) => {
        console.error('[dashboard] Realtime socket error:', err);
        updateRealtimeBanner('offline');
        scheduleHttpFallback(0);
        if (dashboardSocket) {
            try {
                dashboardSocket.close();
            } catch (closeErr) {
                console.debug('[dashboard] Socket close after error failed:', closeErr);
            }
        }
    };

    dashboardSocket.onclose = (event) => {
        dashboardSocket = null;
        activeWsPath = null;
        if (event) {
            console.warn('[dashboard] Realtime socket closed', {
                code: event.code,
                reason: event.reason,
                wasClean: event.wasClean,
                attemptedPath: chosenPath,
            });
        }

        if (event && event.code === 1006) {
            const nextPath = advanceWsPath(chosenPath);
            if (nextPath) {
                console.warn('[dashboard] retrying websocket path', nextPath);
                setTimeout(() => initRealtimeUpdates(true), 0);
                return;
            }
        }

        updateRealtimeBanner('offline');
        scheduleHttpFallback(0);

        if (event && event.code === 4401) {
            console.warn('[dashboard] Realtime socket closed due to authentication; not retrying.');
            return;
        }
        const delay = Math.min(dashboardReconnectDelay, DASHBOARD_WS_MAX_DELAY);
        setTimeout(initRealtimeUpdates, delay);
        dashboardReconnectDelay = Math.min(delay * 2, DASHBOARD_WS_MAX_DELAY);
    };
}

document.addEventListener('DOMContentLoaded', () => {
    cacheRealtimeElements();
    // Keep the realtime banner empty until we connect or fail

    if (currentSummarySnapshot) {
        updateSummary(currentSummarySnapshot);
    } else if (window.HOSTS_SUMMARY) {
        updateSummary(window.HOSTS_SUMMARY);
    }

    if (currentHostsSnapshot.length) {
        renderHosts(currentHostsSnapshot);
    } else if (Array.isArray(window.HOSTS_DATA) && window.HOSTS_DATA.length) {
        renderHosts(window.HOSTS_DATA);
    }

    initRealtimeUpdates();

    if (!currentHostsSnapshot.length) {
        scheduleHttpFallback(0);
    }
});

async function fetchJSON(url) {
    const response = await fetch(url, {
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'application/json',
        },
        credentials: 'same-origin'
    });

    if (!response.ok) {
        const body = await response.text();
    throw new Error(`Request failed: ${response.status} ${response.statusText} - ${body || 'empty response'}`);
    }

    return response.json();
}

function addLegend() {
    const legend = document.createElement('div'); legend.className = 'legend';
    legend.innerHTML = '<div><span class="color" style="background:' + STATUS_COLORS.up + '"></span>Operational</div>' +
        '<div><span class="color" style="background:' + STATUS_COLORS.degraded + '"></span>Degraded</div>' +
        '<div><span class="color" style="background:' + STATUS_COLORS.down + '"></span>Unavailable</div>' +
        '<div><span class="color" style="background:' + STATUS_COLORS.unknown + '"></span>Unknown</div>';
    map.controls[google.maps.ControlPosition.RIGHT_BOTTOM].push(legend);
}

function addHideMarkersButton() {
    const hideMarkersBtn = document.createElement('button');
    hideMarkersBtn.className = 'fit-bounds-btn'; // Reuse the fit button styling
    hideMarkersBtn.textContent = 'Hide markers';
    hideMarkersBtn.title = 'Toggle every marker on the map';

    let markersVisible = true;

    hideMarkersBtn.addEventListener('click', () => {
        markersVisible = !markersVisible;

        // Toggle visibility for all markers
        markers.forEach(marker => {
            marker.setVisible(markersVisible);
        });

        if (markersVisible) {
            hideMarkersBtn.textContent = 'Hide markers';
            hideMarkersBtn.title = 'Hide all markers on the map';
        } else {
            hideMarkersBtn.textContent = 'Show markers';
            hideMarkersBtn.title = 'Show all markers on the map';
        }
    });

    map.controls[google.maps.ControlPosition.TOP_RIGHT].push(hideMarkersBtn);
}


function addFitBoundsButton() {
    const fitBoundsBtn = document.createElement('button');
    fitBoundsBtn.className = 'fit-bounds-btn';
    fitBoundsBtn.textContent = 'Fit to bounds';
    fitBoundsBtn.title = 'Adjust the map to show every feature';
    fitBoundsBtn.addEventListener('click', fitMapToBounds);
    map.controls[google.maps.ControlPosition.TOP_RIGHT].push(fitBoundsBtn);
}


function fitMapToBounds() {
    if (bounds && !bounds.isEmpty()) {
        // Estimate how many points sit inside the bounds
        const ne = bounds.getNorthEast();
        const sw = bounds.getSouthWest();
        
        // Measure how spread out the points are
        const latDiff = Math.abs(ne.lat() - sw.lat());
        const lngDiff = Math.abs(ne.lng() - sw.lng());
        
        // Apply padding based on that spread
        const padding = {
            top: 50,
            right: 50,
            bottom: 50,
            left: 50
        };
        
        map.fitBounds(bounds, padding);
        
        // Adjust zoom intelligently
        const listener = google.maps.event.addListener(map, 'idle', function () {
            const currentZoom = map.getZoom();
            
            // If there is only one point or the points are extremely close, use a medium zoom
            if (latDiff < 0.01 && lngDiff < 0.01) {
                // Very close points - zoom in for detail
                if (currentZoom > 16) map.setZoom(16);
                else if (currentZoom < 12) map.setZoom(12);
            } else if (latDiff < 0.1 && lngDiff < 0.1) {
                // Points in a small area - medium-high zoom
                if (currentZoom > 14) map.setZoom(14);
            } else if (latDiff < 1 && lngDiff < 1) {
                // Points in a medium-sized area - medium zoom
                if (currentZoom > 12) map.setZoom(12);
            }
            // Default to fitBounds behaviour for large areas
            
            google.maps.event.removeListener(listener);
        });
    }
}

function initMap() {
    map = new google.maps.Map(document.getElementById('map'), {
        center: { lat: -16.6869, lng: -49.2648 },
        zoom: 6,
        mapTypeId: 'terrain',
        fullscreenControl: true,
        fullscreenControlOptions: {
            position: google.maps.ControlPosition.RIGHT_TOP
        },
        zoomControl: true,
        zoomControlOptions: {
            position: google.maps.ControlPosition.RIGHT_CENTER
        },
        mapTypeControl: true,
        mapTypeControlOptions: {
            position: google.maps.ControlPosition.TOP_LEFT,
            style: google.maps.MapTypeControlStyle.DROPDOWN_MENU
        },
        streetViewControl: false,
        scaleControl: true
    });
    bounds = new google.maps.LatLngBounds();
    
    // Ensure modals keep working in fullscreen
    setupFullscreenModalSupport();
    
    addLegend();
    addFitBoundsButton();
    addHideMarkersButton();
    loadData();
}

function setupFullscreenModalSupport() {
    // Store the modal's original parent
    const modal = document.getElementById('trafficModal');
    const originalParent = modal ? modal.parentElement : null;
    
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
    document.addEventListener('mozfullscreenchange', handleFullscreenChange);
    document.addEventListener('MSFullscreenChange', handleFullscreenChange);
    
    function handleFullscreenChange() {
        if (!modal || !originalParent) return;
        
        const fullscreenElement = document.fullscreenElement || 
                                 document.webkitFullscreenElement || 
                                 document.mozFullScreenElement ||
                                 document.msFullscreenElement;
        
        if (fullscreenElement) {
            // Entered fullscreen - move modal inside the fullscreen element
            console.log('Map entered fullscreen - shifting modal');
            
            // Remove the modal from the current DOM context
            if (modal.parentElement) {
                modal.parentElement.removeChild(modal);
            }
            
            // Append to the fullscreen element
            fullscreenElement.appendChild(modal);
            
        } else {
            // Exited fullscreen - return modal to the original parent
            console.log('Map left fullscreen - restoring modal');
            
            // Remove from the fullscreen element
            if (modal.parentElement) {
                modal.parentElement.removeChild(modal);
            }
            
            // Re-attach to the original parent
            originalParent.appendChild(modal);
        }
    }
}

function drawCable(c) {
    let path = [];
    if (c.path && c.path.length) {
        path = c.path.map(p => ({ lat: p.lat, lng: p.lng }));
    } else {
        if (c.origin.lat != null && c.destination.lat != null) {
            path = [{ lat: c.origin.lat, lng: c.origin.lng }, { lat: c.destination.lat, lng: c.destination.lng }];
        }
    }
    if (!path.length) return;

    // Extend bounds with cable geometry
    path.forEach(point => bounds.extend(point));

    const poly = new google.maps.Polyline({
        path,
        map,
        strokeColor: STATUS_COLORS[c.status] || STATUS_COLORS.unknown,
        strokeWeight: 4,
        strokeOpacity: .85
    });

    // Build an InfoWindow with detailed information (updated with optical power)
    const info = new google.maps.InfoWindow({
        content: buildCableInfoContent(c)
    });

    poly.addListener('click', (e) => {
        info.setPosition(e.latLng);
        info.open(map);
        if (typeof attachTrafficButtonListeners === 'function') {
            attachTrafficButtonListeners();
        }
    });

    cablesLayer.push(poly);
    cablePolylines[c.id] = poly;

    // Keep a reference to the InfoWindow for later updates
    poly._infoWindow = info;

    return poly;
}

function buildCableInfoContent(cableData) {
    const originOptical = cableData.origin_optical || {};
    const destOptical = cableData.destination_optical || {};
    const singlePort = Boolean(cableData.single_port);

    const formatPower = (dbm) => {
        if (dbm === null || dbm === undefined) return 'N/A';
        const val = parseFloat(dbm);
        if (Number.isNaN(val)) return 'N/A';
        let color = '#16a34a';
        if (val < -20) color = '#f59e0b';
        if (val < -25) color = '#dc2626';
        return `<span style="color: ${color}; font-weight: bold;">${val.toFixed(2)} dBm</span>`;
    };

    const buildTrafficButton = (portInfo, fallbackPortId, fallbackPortName, fallbackDevice) => {
        const portId =
            (portInfo && (portInfo.port_id || portInfo.id)) ||
            fallbackPortId ||
            null;
        if (!portId) return '';

        const portName =
            (portInfo && (portInfo.port || portInfo.name)) ||
            fallbackPortName ||
            `Port ${portId}`;

        const deviceName =
            (portInfo && (portInfo.device || portInfo.device_name)) ||
            fallbackDevice ||
            cableData.name;

        return `<button
            class="traffic-btn"
            data-port-id="${portId}"
            data-port-name="${portName}"
            data-device-name="${deviceName}"
            style="font-size:10px; padding:2px 6px; margin-left:6px; cursor:pointer;
                   background:#3b82f6; color:white; border:none; border-radius:3px;"
            title="View traffic chart">
            Traffic
        </button>`;
    };

    const originSection = `
        <div style="margin-bottom: 8px;">
          <strong>Origin:</strong> ${cableData.origin.site}<br>
          <span style="color: #666; font-size: 12px;">${cableData.origin.port}</span><br>
          <span style="font-size: 12px;">
            RX: ${formatPower(originOptical.rx_dbm)} |
            TX: ${formatPower(originOptical.tx_dbm)}
            ${buildTrafficButton(
                cableData.origin,
                cableData.origin_port_id,
                cableData.origin.port,
                cableData.origin.device
            )}
          </span>
        </div>
    `;

    let destinationSection = '';
    if (singlePort) {
        destinationSection = `
            <div>
              <strong>Destination:</strong> ${cableData.destination.site}<br>
              <span style="color: #666; font-size: 12px;">${cableData.destination.port}</span><br>
              <span style="font-size: 11px; color: #999;">
                Monitoring uses the origin port only for traffic metrics.
              </span>
            </div>
        `;
    } else {
        destinationSection = `
            <div>
              <strong>Destination:</strong> ${cableData.destination.site}<br>
              <span style="color: #666; font-size: 12px;">${cableData.destination.port}</span><br>
              <span style="font-size: 12px;">
                RX: ${formatPower(destOptical.rx_dbm)} |
                TX: ${formatPower(destOptical.tx_dbm)}
                ${buildTrafficButton(
                    cableData.destination,
                    cableData.destination_port_id,
                    cableData.destination.port,
                    cableData.destination.device
                )}
              </span>
            </div>
        `;
    }

    return `
      <div style="min-width: 280px; font-size: 13px;">
        <strong style="font-size: 14px;">${cableData.name}</strong><br>
        <span style="background: ${STATUS_COLORS[cableData.status] || STATUS_COLORS.unknown};
                     color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px;">
          ${cableData.status.toUpperCase()}
        </span>
        <hr style="margin: 8px 0; border: none; border-top: 1px solid #ddd;">
        ${originSection}
        ${destinationSection}
      </div>
    `;
}

function addSiteMarkerWithDevices(site) {
    if (!site.latitude || !site.longitude) return;
    
    const position = { lat: site.latitude, lng: site.longitude };
    bounds.extend(position);

    // Determine marker color based on device status
    let markerColor = '#6b7280'; // gray (unknown)
    const devices = site.devices || [];
    
    console.log(`[addSiteMarkerWithDevices] Site: ${site.site_name}, devices count: ${devices.length}`, devices);
    
    if (devices.length > 0) {
        const hasUnavailable = devices.some(d => d.available === '2');
        const hasAvailable = devices.some(d => d.available === '1');
        
        if (hasUnavailable) {
            markerColor = '#dc2626'; // red
        } else if (hasAvailable) {
            markerColor = '#16a34a'; // green
        }
    }

    const tooltipText = `${site.site_name} (${devices.length} device${devices.length !== 1 ? 's' : ''})`;
    console.log(`[addSiteMarkerWithDevices] Tooltip text: ${tooltipText}`);

    // Create custom marker icon with color
    const marker = new google.maps.Marker({
        position,
        map,
        title: tooltipText,
        icon: {
            path: google.maps.SymbolPath.CIRCLE,
            fillColor: markerColor,
            fillOpacity: 0.9,
            strokeColor: '#ffffff',
            strokeWeight: 2,
            scale: 10
        }
    });

    // Click handler: show modal with device list
    marker.addListener('click', () => {
        showSiteDevicesModal(site);
    });

    markers.push(marker);
}

function showSiteDevicesModal(site) {
    const devices = site.devices || [];
    const modalHtml = `
        <div style="min-width: 350px; max-width: 500px;">
            <div style="border-bottom: 2px solid #e5e7eb; padding-bottom: 12px; margin-bottom: 16px;">
                <h3 style="margin: 0; font-size: 18px; font-weight: 600; color: #1f2937;">${site.site_name}</h3>
                ${site.city ? `<p style="margin: 4px 0 0 0; font-size: 14px; color: #6b7280;">📍 ${site.city}</p>` : ''}
                <p style="margin: 8px 0 0 0; font-size: 14px; color: #6b7280;">
                    ${devices.length} device${devices.length !== 1 ? 's' : ''} at this location
                </p>
            </div>
            <div style="max-height: 400px; overflow-y: auto;">
                ${devices.map(device => `
                    <div class="device-item" style="
                        border: 1px solid #e5e7eb;
                        border-radius: 8px;
                        padding: 12px;
                        margin-bottom: 8px;
                        cursor: pointer;
                        transition: all 0.2s;
                        background: white;
                    " 
                    onmouseover="this.style.background='#f9fafb'; this.style.borderColor='#3b82f6';"
                    onmouseout="this.style.background='white'; this.style.borderColor='#e5e7eb';"
                    onclick="showDeviceDetails(${device.device_id})">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <strong style="font-size: 15px; color: #1f2937;">${device.name || 'Unknown Device'}</strong>
                            <span style="
                                display: inline-block;
                                padding: 4px 8px;
                                border-radius: 12px;
                                font-size: 12px;
                                font-weight: 500;
                                ${device.available === '1' ? 'background: #dcfce7; color: #16a34a;' : 
                                  device.available === '2' ? 'background: #fee2e2; color: #dc2626;' : 
                                  'background: #f3f4f6; color: #6b7280;'}
                            ">${device.available_text || 'Unknown'}</span>
                        </div>
                        ${device.device_type ? `
                            <div style="font-size: 13px; color: #6b7280; margin-bottom: 4px;">
                                🔧 ${device.device_type}
                            </div>
                        ` : ''}
                        ${device.primary_ip ? `
                            <div style="font-size: 13px; color: #6b7280; margin-bottom: 4px;">
                                📍 ${device.primary_ip}
                            </div>
                        ` : ''}
                        <div style="display: flex; gap: 16px; font-size: 12px; color: #6b7280; margin-top: 8px;">
                            ${device.uptime_value ? `<span>⏱️ ${device.uptime_value}</span>` : ''}
                            ${device.cpu_value ? `<span>💻 ${device.cpu_value}</span>` : ''}
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
    `;

    // Create and show InfoWindow
    const infoWindow = new google.maps.InfoWindow({
        content: modalHtml
    });
    
    // Find the marker for this site
    const siteMarker = markers.find(m => 
        m.getPosition().lat() === site.latitude && 
        m.getPosition().lng() === site.longitude
    );
    
    if (siteMarker) {
        infoWindow.open(map, siteMarker);
    }
}

function showDeviceDetails(deviceId) {
    // Find the device in current snapshot
    const device = currentHostsSnapshot.find(d => d.device_id === deviceId);
    if (!device) {
        console.error('Device not found:', deviceId);
        return;
    }
    
    // Close any open InfoWindow and open device detail modal
    // We'll reuse the existing device modal structure
    showDeviceModal(device);
}

function showDeviceModal(device) {
    // Build detailed device modal content
    const modalHtml = `
        <div style="min-width: 300px; max-width: 500px;">
            <div style="border-bottom: 2px solid #e5e7eb; padding-bottom: 12px; margin-bottom: 16px;">
                <h3 style="margin: 0; font-size: 18px; font-weight: 600; color: #1f2937;">${device.name || 'Unknown Device'}</h3>
                <p style="margin: 4px 0 0 0; font-size: 14px; color: #6b7280;">${device.site || 'N/A'}</p>
            </div>
            
            <div style="space-y: 12px;">
                <div style="margin-bottom: 12px;">
                    <div style="font-size: 12px; color: #6b7280; margin-bottom: 4px;">Status</div>
                    <span style="
                        display: inline-block;
                        padding: 6px 12px;
                        border-radius: 12px;
                        font-size: 14px;
                        font-weight: 500;
                        ${device.available === '1' ? 'background: #dcfce7; color: #16a34a;' : 
                          device.available === '2' ? 'background: #fee2e2; color: #dc2626;' : 
                          'background: #f3f4f6; color: #6b7280;'}
                    ">${device.available_text || 'Unknown'}</span>
                </div>
                
                ${device.device_type ? `
                    <div style="margin-bottom: 12px;">
                        <div style="font-size: 12px; color: #6b7280; margin-bottom: 4px;">Device Type</div>
                        <div style="font-size: 14px; color: #1f2937;">🔧 ${device.device_type}</div>
                    </div>
                ` : ''}
                
                ${device.primary_ip ? `
                    <div style="margin-bottom: 12px;">
                        <div style="font-size: 12px; color: #6b7280; margin-bottom: 4px;">IP Address</div>
                        <div style="font-size: 14px; font-family: monospace; color: #1f2937;">📍 ${device.primary_ip}</div>
                    </div>
                ` : ''}
                
                ${device.uptime_value ? `
                    <div style="margin-bottom: 12px;">
                        <div style="font-size: 12px; color: #6b7280; margin-bottom: 4px;">Uptime</div>
                        <div style="font-size: 14px; color: #1f2937;">⏱️ ${device.uptime_value}</div>
                    </div>
                ` : ''}
                
                ${device.cpu_value ? `
                    <div style="margin-bottom: 12px;">
                        <div style="font-size: 12px; color: #6b7280; margin-bottom: 4px;">CPU Usage</div>
                        <div style="font-size: 14px; color: #1f2937;">💻 ${device.cpu_value}</div>
                    </div>
                ` : ''}
                
                <div style="margin-bottom: 12px;">
                    <div style="font-size: 12px; color: #6b7280; margin-bottom: 4px;">Zabbix Host ID</div>
                    <div style="font-size: 14px; font-family: monospace; color: #1f2937;">${device.hostid || 'N/A'}</div>
                </div>
                
                ${device.error ? `
                    <div style="margin-bottom: 12px;">
                        <div style="font-size: 12px; color: #dc2626; margin-bottom: 4px;">Error</div>
                        <div style="font-size: 13px; color: #dc2626; background: #fee2e2; padding: 8px; border-radius: 6px;">${device.error}</div>
                    </div>
                ` : ''}
            </div>
        </div>
    `;
    
    const infoWindow = new google.maps.InfoWindow({
        content: modalHtml
    });
    
    // Open at map center
    infoWindow.setPosition(map.getCenter());
    infoWindow.open(map);
}

function addSiteMarker(s) {
    if (s.lat == null) return;
    const position = { lat: s.lat, lng: s.lng };

    // Extend bounds with the site position
    bounds.extend(position);

    const marker = new google.maps.Marker({ position, map, title: s.name });
    const html = `<div><strong>${s.name}</strong><br>${s.city || ''}<br>Devices: ${s.devices.length}</div>`;
    const iw = new google.maps.InfoWindow({ content: html });
    marker.addListener('click', () => iw.open(map, marker));
    markers.push(marker);
}

function buildDeviceIcon(iconUrl) {
    // Ensure iconUrl is a valid string
    if (!iconUrl || typeof iconUrl !== 'string' || iconUrl.trim() === '') {
        return {
            url: 'https://maps.gstatic.com/mapfiles/api-3/images/spotlight-poi3.png',
            //scaledSize: new google.maps.Size(48, 48),
            //anchor: new google.maps.Point(24, 48)
        };
    }
    return {
        url: iconUrl,
        size: new google.maps.Size(64, 64),
        scaledSize: new google.maps.Size(64, 64),
        anchor: new google.maps.Point(24, 24), // Icon center (half the width and height)
        origin: new google.maps.Point(0, 0)
    };
}

async function addDeviceMarker(dev, siteName, siteCity) {
    if (dev.lat == null || dev.lng == null) return;
    const position = { lat: dev.lat, lng: dev.lng };
    bounds.extend(position);

    // Check icon_url before using it
    const iconUrl = (dev.icon_url && typeof dev.icon_url === 'string') ? dev.icon_url : null;

    const marker = new google.maps.Marker({
        position,
        map,
        title: dev.name,
        icon: buildDeviceIcon(iconUrl)
    });

    const iw = new google.maps.InfoWindow({
        content: '<div style="min-width:200px">Loading...</div>'
    });

    marker.addListener('click', async () => {
        // Reset to loading state
        iw.setContent('<div style="min-width:200px">Loading...</div>');
        iw.open(map, marker);

        let portsInfo = '';

        try {
            // Use optimized endpoint that already returns ports with optical readings
            const portsResp = await fetch(`/api/v1/inventory/devices/${dev.id}/ports/optical/`);

            if (portsResp.ok) {
                const portsData = await portsResp.json();

                if (portsData.ports && portsData.ports.length > 0) {
                    portsInfo = '<hr style="margin: 8px 0; border: none; border-top: 1px solid #ddd;">';
                    portsInfo += '<div style="margin-top: 8px;"><strong>Portas em Uso:</strong></div>';

                    for (const port of portsData.ports) {
                        const formatPower = (dbm) => {
                            if (dbm === null || dbm === undefined) return 'N/A';
                            const val = parseFloat(dbm);
                            if (isNaN(val)) return 'N/A';

                            let color = '#16a34a'; // green (good)
                            if (val < -20) color = '#f59e0b'; // amber (degraded)
                            if (val < -25) color = '#dc2626'; // red (bad)

                            return `<span style="color: ${color}; font-weight: bold;">${val.toFixed(2)} dBm</span>`;
                        };

                        let opticalInfo = '';
                        if (port.optical && (port.optical.rx_dbm !== null || port.optical.tx_dbm !== null)) {
                            opticalInfo = `<br><span style="font-size: 11px;">RX: ${formatPower(port.optical.rx_dbm)} | TX: ${formatPower(port.optical.tx_dbm)}</span>`;
                        } else {
                            opticalInfo = '<br><span style="font-size: 11px; color: #999;">Optical power not configured</span>';
                        }

                        // Add traffic button
                        const trafficBtn = `<button 
                class="traffic-btn" 
                data-port-id="${port.id}" 
                data-port-name="${port.name}" 
                data-device-name="${dev.name}"
                style="font-size:10px; padding:2px 6px; margin-left:6px; cursor:pointer; 
                       background:#3b82f6; color:white; border:none; border-radius:3px;"
                title="View traffic chart"> Traffic</button>`;

                        portsInfo += `<div style="font-size: 12px; color: #666; margin-left: 8px;"> ${port.name}${opticalInfo}${trafficBtn}</div>`;
                    }
                }
            }
        } catch (e) {
            console.error('Error fetching device ports:', e);
        }

        const finalContent = `<div style="min-width:200px">
        <strong>${dev.name}</strong><br>
        Site: ${siteName}${siteCity ? ' - ' + siteCity : ''}<br>
        Zabbix Host: ${dev.zabbix_hostid || ''}
        ${portsInfo}
      </div>`;

        iw.setContent(finalContent);

        // Attach event listeners to traffic buttons (see traffic_chart.js)
        if (typeof attachTrafficButtonListeners === 'function') {
            attachTrafficButtonListeners();
        }
    });

    markers.push(marker);
}

async function loadData() {
    try {
        const [cablesResp, sitesDataResp] = await Promise.all([
            fetchJSON('/api/v1/inventory/fibers/'),
            fetchJSON('/maps_view/api/dashboard/sites/')
        ]);

        // Update dashboard data (hosts_summary and hosts data for sidebar)
        if (sitesDataResp) {
            // Flatten devices from all sites for sidebar display
            const allDevices = [];
            if (Array.isArray(sitesDataResp.sites)) {
                sitesDataResp.sites.forEach(site => {
                    if (Array.isArray(site.devices)) {
                        allDevices.push(...site.devices);
                    }
                });
            }
            
            window.HOSTS_DATA = allDevices;
            currentHostsSnapshot = allDevices.slice();
            
            if (sitesDataResp.hosts_summary) {
                window.HOSTS_SUMMARY = sitesDataResp.hosts_summary;
                currentSummarySnapshot = { ...sitesDataResp.hosts_summary };
            }
            
            // Update UI summary stats
            updateSummaryUI(sitesDataResp.hosts_summary);
        }

        // Render site markers on map (grouped by site)
        const sites = Array.isArray(sitesDataResp?.sites) ? sitesDataResp.sites : [];
        console.log('[loadData] Sites data:', sites);
        sites.forEach((site) => {
            console.log(`[loadData] Processing site: ${site.site_name}, devices: ${site.devices?.length || 0}`);
            addSiteMarkerWithDevices(site);
        });

        // Cables (API may return either `fibers` or `cables`)
        const cables = Array.isArray(cablesResp?.fibers)
            ? cablesResp.fibers
            : Array.isArray(cablesResp?.cables)
                ? cablesResp.cables
                : [];

        const cableUl = document.getElementById('cableList');
        if (cableUl) {
            cableUl.innerHTML = '';

            // Remove stale polylines from previous loads to avoid polling old IDs
            Object.values(cablePolylines).forEach((polyline) => {
                if (polyline && typeof polyline.setMap === 'function') {
                    polyline.setMap(null);
                }
            });
            cablePolylines = {};
            cableDataCache = {};

            cables.forEach((cable) => {
                cableDataCache[cable.id] = cable;
                const polyline = drawCable(cable);
                if (polyline) {
                    cablePolylines[cable.id] = polyline;
                }
                const li = document.createElement('li');
                li.id = `cable-li-${cable.id}`;
                cableUl.appendChild(li);
            });
        }

        // Fit the map after the data loads
        fitMapToBounds();

        startStatusPolling();
    } catch (error) {
        console.error('Failed to load dashboard data', error);
        showNotification('Failed to load dashboard data. Check console for details.', 'error');
    }
}

function normalizeOpticalValue(rawValue) {
    if (rawValue === null || rawValue === undefined) {
        return null;
    }
    const numeric = Number(rawValue);
    return Number.isFinite(numeric) ? numeric : null;
}

function applyCableStatusUpdate(cid, payload) {
    const cableId = String(cid);
    const poly = cablePolylines[cableId];
    const resolvedStatus = payload.status || payload.combined_status || payload.stored_status || 'unknown';

    if (poly) {
        poly.setOptions({
            strokeColor: STATUS_COLORS[resolvedStatus] || STATUS_COLORS.unknown,
        });

        const cachedCable = cableDataCache[cableId];
        if (cachedCable) {
            cachedCable.status = resolvedStatus;
            cachedCable.origin_optical = payload.origin_optical || null;
            cachedCable.destination_optical = payload.destination_optical || null;
            cachedCable.origin_status = payload.origin_status;
            cachedCable.destination_status = payload.destination_status;
            cachedCable.origin_raw = payload.origin_raw;
            cachedCable.destination_raw = payload.destination_raw;
            cachedCable.origin_meta = payload.origin_meta;
            cachedCable.destination_meta = payload.destination_meta;

            if (poly._infoWindow) {
                poly._infoWindow.setContent(buildCableInfoContent(cachedCable));
                if (typeof attachTrafficButtonListeners === 'function') {
                    attachTrafficButtonListeners();
                }
            }
        }
    }

    const listItem = document.getElementById(`cable-li-${cableId}`);
    if (listItem) {
        const dot = listItem.querySelector('.status-dot');
        if (dot) {
            dot.style.background = STATUS_COLORS[resolvedStatus] || STATUS_COLORS.unknown;
        }

        const originOpt = payload.origin_optical || {};
        const destOpt = payload.destination_optical || {};

        const originRx = normalizeOpticalValue(originOpt.rx_dbm);
        const originTx = normalizeOpticalValue(originOpt.tx_dbm);
        const destRx = normalizeOpticalValue(destOpt.rx_dbm);
        const destTx = normalizeOpticalValue(destOpt.tx_dbm);

        if (originRx !== null || originTx !== null || destRx !== null || destTx !== null) {
            const format = (val) => (val !== null ? val.toFixed(2) : 'N/A');
            listItem.title = `Status: ${resolvedStatus}\n` +
                `Origin - RX: ${format(originRx)} dBm | TX: ${format(originTx)} dBm\n` +
                `Destination - RX: ${format(destRx)} dBm | TX: ${format(destTx)} dBm`;
        } else if (payload.origin_raw || payload.destination_raw) {
            listItem.title = `Status: ${resolvedStatus}\n` +
                `Origin raw: ${payload.origin_raw ?? 'N/A'}\n` +
                `Destination raw: ${payload.destination_raw ?? 'N/A'}`;
        } else if (payload.raw_value) {
            listItem.title = `Zabbix value: ${payload.raw_value}`;
        } else {
            listItem.title = `Status: ${resolvedStatus}`;
        }
    }
}

function applyCableStatusBatch(cables) {
    /**
     * Apply multiple cable status updates from WebSocket broadcast.
     * This replaces HTTP polling with real-time push updates.
     */
    if (!Array.isArray(cables)) {
        console.warn('[dashboard] Invalid cable batch:', cables);
        return;
    }
    
    cables.forEach((cableData) => {
        if (cableData && cableData.cable_id) {
            applyCableStatusUpdate(cableData.cable_id, cableData);
        }
    });
    
    console.log(`[dashboard] Applied ${cables.length} cable status updates via WebSocket`);
}


async function refreshCableStatusValueMapped() {
    const ids = Object.keys(cablePolylines);
    if (!ids.length) {
        return;
    }

    const params = new URLSearchParams();
    params.set('ids', ids.join(','));

    try {
        const payload = await fetchJSON(`/api/v1/inventory/fibers/oper-status/?${params.toString()}`);
        const results = Array.isArray(payload?.results) ? payload.results : [];
        const statusById = new Map(results.map((entry) => [String(entry.cable_id), entry]));

        ids.forEach((cid) => {
            const statusPayload = statusById.get(String(cid));
            if (statusPayload) {
                applyCableStatusUpdate(cid, statusPayload);
            }
        });

        if (Array.isArray(payload?.missing_ids) && payload.missing_ids.length) {
            console.warn('Fiber status not found for ids:', payload.missing_ids);
        }
    } catch (e) {
        console.error('Error updating cable status:', e);
    }
}

function startStatusPolling() {
    refreshCableStatusValueMapped();
    setInterval(refreshCableStatusValueMapped, 180000); // 3 minutes
}

// Expose helpers for integration/testing environments
if (typeof window !== 'undefined') {
    window.mapsDashboard = window.mapsDashboard || {};
    Object.assign(window.mapsDashboard, {
        addLegend,
        addHideMarkersButton,
        addFitBoundsButton,
        fitMapToBounds,
    });
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        addLegend,
        addHideMarkersButton,
        addFitBoundsButton,
        fitMapToBounds,
        __setState({ map: newMap, markers: newMarkers, bounds: newBounds } = {}) {
            if (typeof newMap !== 'undefined') map = newMap;
            if (typeof newMarkers !== 'undefined') markers = newMarkers;
            if (typeof newBounds !== 'undefined') bounds = newBounds;
        },
        __getState() {
            return { map, markers, bounds };
        },
    };
}

