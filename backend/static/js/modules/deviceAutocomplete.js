/**
 * Device Autocomplete Component
 * 
 * Intelligent autocomplete with:
 * - Fuzzy search using Fuse.js
 * - Real-time Zabbix status indicators
 * - Proximity sorting based on map location
 * - Keyboard navigation (Arrow keys, Enter, Escape)
 */

import Fuse from 'fuse.js';
import { request } from './apiClient.js';

// Cache de dispositivos
let devicesCache = [];
let lastFetchTime = 0;
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutos

// Instância Fuse.js
let fuseInstance = null;

// Configuração Fuse.js para busca fuzzy
const FUSE_OPTIONS = {
    keys: [
        { name: 'name', weight: 3 },        // Nome do device (peso maior)
        { name: 'ip', weight: 2 },          // IP address
        { name: 'site', weight: 2 },        // Nome do site
        { name: 'location', weight: 1 },    // Cidade/Estado
        { name: 'vendor', weight: 1 },      // Vendor
        { name: 'model', weight: 1 },       // Model
    ],
    threshold: 0.4,  // 0 = exact match, 1 = match anything
    distance: 100,
    includeScore: true,
    minMatchCharLength: 1,
};

/**
 * Fetch devices from backend with cache.
 */
async function fetchDevices() {
    const now = Date.now();
    
    // Return cached data if still fresh
    if (devicesCache.length > 0 && (now - lastFetchTime) < CACHE_DURATION) {
        return devicesCache;
    }
    
    const data = await request('/devices/autocomplete/', { method: 'GET' });
    devicesCache = data.devices || [];
    lastFetchTime = now;
    
    // Initialize Fuse instance
    fuseInstance = new Fuse(devicesCache, FUSE_OPTIONS);
    
    return devicesCache;
}

/**
 * Calculate distance between two coordinates using Haversine formula.
 * 
 * @param {number} lat1 - Latitude of point 1
 * @param {number} lng1 - Longitude of point 1
 * @param {number} lat2 - Latitude of point 2
 * @param {number} lng2 - Longitude of point 2
 * @returns {number} Distance in kilometers
 */
function calculateDistance(lat1, lng1, lat2, lng2) {
    const R = 6371; // Earth radius in km
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLng = (lng2 - lng1) * Math.PI / 180;
    
    const a =
        Math.sin(dLat / 2) * Math.sin(dLat / 2) +
        Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
        Math.sin(dLng / 2) * Math.sin(dLng / 2);
    
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
}

/**
 * Search devices with fuzzy matching.
 * 
 * @param {string} query - Search query
 * @param {Object} options - Search options
 * @param {number} options.maxResults - Maximum results to return (default: 10)
 * @param {Object} options.proximity - {lat, lng} for proximity sorting
 * @returns {Array} Filtered devices with distance
 */
function searchDevices(query, options = {}) {
    const { maxResults = 10, proximity = null } = options;
    
    if (!query || query.trim().length === 0) {
        // No query - return all devices, optionally sorted by proximity
        let results = [...devicesCache];
        
        if (proximity && proximity.lat && proximity.lng) {
            results = addProximityData(results, proximity);
            results.sort((a, b) => (a.distance || Infinity) - (b.distance || Infinity));
        }
        
        return results.slice(0, maxResults);
    }
    
    // Fuzzy search using Fuse.js
    const fuseResults = fuseInstance.search(query);
    let results = fuseResults.map(result => ({
        ...result.item,
        score: result.score,
    }));
    
    // Add proximity data if coordinates provided
    if (proximity && proximity.lat && proximity.lng) {
        results = addProximityData(results, proximity);
        
        // Sort by combination of relevance score and distance
        results.sort((a, b) => {
            const scoreA = (a.score || 0) * 0.6 + (a.distance ? a.distance / 100 : 0) * 0.4;
            const scoreB = (b.score || 0) * 0.6 + (b.distance ? b.distance / 100 : 0) * 0.4;
            return scoreA - scoreB;
        });
    } else {
        // Sort by relevance score only
        results.sort((a, b) => (a.score || 0) - (b.score || 0));
    }
    
    return results.slice(0, maxResults);
}

/**
 * Add distance field to devices based on proximity point.
 */
function addProximityData(devices, proximity) {
    return devices.map(device => {
        if (device.lat != null && device.lng != null) {
            const distance = calculateDistance(
                proximity.lat,
                proximity.lng,
                device.lat,
                device.lng
            );
            return { ...device, distance };
        }
        return device;
    });
}

/**
 * Fetch Zabbix status for multiple devices.
 * 
 * @param {Array<number>} deviceIds - Device IDs
 * @returns {Object} Map of deviceId -> status
 */
async function fetchZabbixStatuses(deviceIds) {
    if (!deviceIds || deviceIds.length === 0) {
        return {};
    }
    
    try {
        const idsParam = deviceIds.join(',');
        const data = await request(`/devices/zabbix-status/?device_ids=${idsParam}`, {
            method: 'GET'
        });
        return data.statuses || {};
    } catch (error) {
        console.error('[DeviceAutocomplete] Failed to fetch Zabbix statuses:', error);
        return {};
    }
}

/**
 * Create autocomplete dropdown component.
 * 
 * @param {HTMLInputElement} inputElement - Input element to attach autocomplete to
 * @param {Object} options - Configuration options
 * @param {Function} options.onSelect - Callback when device is selected
 * @param {Function} options.getProximity - Optional function that returns {lat, lng}
 * @param {number} options.maxResults - Maximum results to show (default: 8)
 * @param {boolean} options.showZabbixStatus - Show Zabbix status indicators (default: true)
 * @returns {Object} Autocomplete instance with destroy() method
 */
export function createDeviceAutocomplete(inputElement, options = {}) {
    const {
        onSelect = () => {},
        getProximity = null,
        maxResults = 8,
        showZabbixStatus = true,
    } = options;
    
    let dropdownElement = null;
    let selectedIndex = -1;
    let currentResults = [];
    let zabbixStatuses = {};
    let searchTimeout = null;
    
    // Create dropdown element
    function createDropdown() {
        dropdownElement = document.createElement('div');
        dropdownElement.className = 'device-autocomplete-dropdown';
        dropdownElement.style.cssText = `
            position: absolute;
            z-index: 9999;
            background: white;
            border: 1px solid #cbd5e1;
            border-radius: 0.5rem;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
            max-height: 320px;
            overflow-y: auto;
            display: none;
            min-width: 100%;
        `;
        
        // Position dropdown below input
        const rect = inputElement.getBoundingClientRect();
        dropdownElement.style.top = `${rect.bottom + window.scrollY + 4}px`;
        dropdownElement.style.left = `${rect.left + window.scrollX}px`;
        dropdownElement.style.width = `${Math.max(rect.width, 400)}px`;
        
        document.body.appendChild(dropdownElement);
        return dropdownElement;
    }
    
    // Render search results
    async function renderResults(devices) {
        if (!dropdownElement) {
            dropdownElement = createDropdown();
        }
        
        currentResults = devices;
        selectedIndex = -1;
        
        if (devices.length === 0) {
            dropdownElement.innerHTML = `
                <div style="padding: 12px; text-align: center; color: #64748b; font-size: 14px;">
                    <i class="fas fa-search" style="margin-right: 6px;"></i>
                    No devices found
                </div>
            `;
            dropdownElement.style.display = 'block';
            return;
        }
        
        // Fetch Zabbix statuses if enabled
        if (showZabbixStatus) {
            const deviceIds = devices
                .filter(d => d.zabbix_hostid)
                .map(d => d.id);
            if (deviceIds.length > 0) {
                zabbixStatuses = await fetchZabbixStatuses(deviceIds);
            }
        }
        
        dropdownElement.innerHTML = devices.map((device, index) => {
            const statusIcon = getStatusIcon(device.id);
            const distanceLabel = device.distance != null 
                ? `<span style="color: #64748b; font-size: 11px; margin-left: auto;">${device.distance.toFixed(1)} km</span>`
                : '';
            
            return `
                <div class="autocomplete-item" data-index="${index}" style="
                    padding: 10px 12px;
                    cursor: pointer;
                    border-bottom: 1px solid #f1f5f9;
                    transition: background-color 0.15s;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                ">
                    ${statusIcon}
                    <div style="flex: 1; min-width: 0;">
                        <div style="font-weight: 500; font-size: 14px; color: #1e293b; margin-bottom: 2px;">
                            ${escapeHTML(device.name)}
                        </div>
                        <div style="font-size: 12px; color: #64748b; display: flex; gap: 12px; flex-wrap: wrap;">
                            ${device.ip ? `<span><i class="fas fa-network-wired" style="margin-right: 4px; opacity: 0.7;"></i>${escapeHTML(device.ip)}</span>` : ''}
                            ${device.site ? `<span><i class="fas fa-map-marker-alt" style="margin-right: 4px; opacity: 0.7;"></i>${escapeHTML(device.site)}</span>` : ''}
                            ${device.vendor ? `<span>${escapeHTML(device.vendor)}</span>` : ''}
                        </div>
                    </div>
                    ${distanceLabel}
                </div>
            `;
        }).join('');
        
        dropdownElement.style.display = 'block';
        attachResultHandlers();
    }
    
    // Get status icon based on Zabbix status
    function getStatusIcon(deviceId) {
        if (!showZabbixStatus) {
            return '<div style="width: 8px; height: 8px;"></div>';
        }
        
        const status = zabbixStatuses[String(deviceId)] || 'unknown';
        let color, title;
        
        switch (status) {
            case 'online':
                color = '#22c55e';
                title = 'Online';
                break;
            case 'offline':
                color = '#ef4444';
                title = 'Offline';
                break;
            case 'disabled':
                color = '#94a3b8';
                title = 'Disabled';
                break;
            default:
                color = '#f59e0b';
                title = 'Unknown';
        }
        
        return `<div style="
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: ${color};
            flex-shrink: 0;
        " title="${title}"></div>`;
    }
    
    // Escape HTML to prevent XSS
    function escapeHTML(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
    
    // Attach click handlers to results
    function attachResultHandlers() {
        const items = dropdownElement.querySelectorAll('.autocomplete-item');
        items.forEach((item, index) => {
            item.addEventListener('mouseenter', () => {
                highlightItem(index);
            });
            item.addEventListener('click', () => {
                selectItem(index);
            });
        });
    }
    
    // Highlight item at index
    function highlightItem(index) {
        const items = dropdownElement.querySelectorAll('.autocomplete-item');
        items.forEach((item, i) => {
            if (i === index) {
                item.style.backgroundColor = '#f1f5f9';
                selectedIndex = index;
            } else {
                item.style.backgroundColor = 'white';
            }
        });
    }
    
    // Select item at index
    function selectItem(index) {
        if (index < 0 || index >= currentResults.length) return;
        
        const device = currentResults[index];
        inputElement.value = device.name;
        onSelect(device);
        hideDropdown();
    }
    
    // Hide dropdown
    function hideDropdown() {
        if (dropdownElement) {
            dropdownElement.style.display = 'none';
        }
        selectedIndex = -1;
    }
    
    // Handle input changes with debounce
    async function handleInput() {
        clearTimeout(searchTimeout);
        
        searchTimeout = setTimeout(async () => {
            const query = inputElement.value.trim();
            
            // Initialize devices if not loaded
            if (devicesCache.length === 0) {
                await fetchDevices();
            }
            
            // Get proximity if function provided
            let proximity = null;
            if (getProximity && typeof getProximity === 'function') {
                proximity = getProximity();
            }
            
            // Search devices
            const results = searchDevices(query, { maxResults, proximity });
            
            await renderResults(results);
        }, 200); // 200ms debounce
    }
    
    // Handle keyboard navigation
    function handleKeydown(event) {
        if (!dropdownElement || dropdownElement.style.display === 'none') {
            return;
        }
        
        switch (event.key) {
            case 'ArrowDown':
                event.preventDefault();
                selectedIndex = Math.min(selectedIndex + 1, currentResults.length - 1);
                highlightItem(selectedIndex);
                break;
            
            case 'ArrowUp':
                event.preventDefault();
                selectedIndex = Math.max(selectedIndex - 1, 0);
                highlightItem(selectedIndex);
                break;
            
            case 'Enter':
                event.preventDefault();
                if (selectedIndex >= 0) {
                    selectItem(selectedIndex);
                }
                break;
            
            case 'Escape':
                event.preventDefault();
                hideDropdown();
                break;
        }
    }
    
    // Handle click outside
    function handleClickOutside(event) {
        if (inputElement.contains(event.target)) return;
        if (dropdownElement && dropdownElement.contains(event.target)) return;
        hideDropdown();
    }
    
    // Attach event listeners
    inputElement.addEventListener('input', handleInput);
    inputElement.addEventListener('keydown', handleKeydown);
    inputElement.addEventListener('focus', handleInput);
    document.addEventListener('click', handleClickOutside);
    
    // Initialize devices cache on creation
    fetchDevices().catch(error => {
        console.error('[DeviceAutocomplete] Failed to load devices:', error);
    });
    
    // Return instance with destroy method
    return {
        destroy() {
            inputElement.removeEventListener('input', handleInput);
            inputElement.removeEventListener('keydown', handleKeydown);
            inputElement.removeEventListener('focus', handleInput);
            document.removeEventListener('click', handleClickOutside);
            
            if (dropdownElement && dropdownElement.parentNode) {
                dropdownElement.parentNode.removeChild(dropdownElement);
            }
            
            dropdownElement = null;
            currentResults = [];
            zabbixStatuses = {};
        },
        
        refresh() {
            // Force cache refresh
            devicesCache = [];
            lastFetchTime = 0;
            return fetchDevices();
        },
    };
}

// Export additional utilities
export { fetchDevices, searchDevices, calculateDistance, fetchZabbixStatuses };
