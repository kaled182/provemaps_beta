/**
 * RadiusSearchTool - Usage Examples
 * Phase 7 Day 4 - Frontend Integration
 * 
 * Examples demonstrating how to integrate and use the RadiusSearchTool component
 */

<template>
  <div class="usage-examples">
    <h2>RadiusSearchTool - Usage Examples</h2>
    
    <!-- Example 1: Basic Integration -->
    <section class="example">
      <h3>Example 1: Basic Integration with MapView</h3>
      <p>Enable radius search in any map view by passing the <code>enableRadiusSearch</code> prop:</p>
      
      <pre><code>&lt;MapView 
  :enableRadiusSearch="true"
  :sidebarCollapsed="false"
/&gt;</code></pre>
      
      <p>This will render the RadiusSearchTool panel on the map with default settings.</p>
    </section>
    
    <!-- Example 2: Standalone Usage -->
    <section class="example">
      <h3>Example 2: Standalone Usage</h3>
      <p>Use RadiusSearchTool independently with your own Google Maps instance:</p>
      
      <pre><code>&lt;template&gt;
  &lt;div style="position: relative; width: 100%; height: 100vh;"&gt;
    &lt;GoogleMap
      ref="mapRef"
      :api-key="apiKey"
      :center="{ lat: -15.7801, lng: -47.9292 }"
      :zoom="12"
      style="width: 100%; height: 100%;"
    /&gt;
    
    &lt;RadiusSearchTool
      :map-ref="mapRef"
      :initial-radius="20"
      :auto-activate="true"
      @search-completed="onSearchCompleted"
      @search-error="onSearchError"
    /&gt;
  &lt;/div&gt;
&lt;/template&gt;

&lt;script setup&gt;
import { ref } from 'vue';
import { GoogleMap } from 'vue3-google-map';
import RadiusSearchTool from '@/components/Map/RadiusSearchTool.vue';

const mapRef = ref(null);
const apiKey = 'YOUR_GOOGLE_MAPS_API_KEY';

function onSearchCompleted(results) {
  console.log(`Found ${results.count} sites within ${results.radius_km}km`);
  console.log('Sites:', results.sites);
}

function onSearchError(error) {
  console.error('Search failed:', error);
  alert('Erro na busca: ' + error.message);
}
&lt;/script&gt;</code></pre>
    </section>
    
    <!-- Example 3: Programmatic Control -->
    <section class="example">
      <h3>Example 3: Programmatic Control</h3>
      <p>Control the search tool via refs and listen to events:</p>
      
      <pre><code>&lt;template&gt;
  &lt;div&gt;
    &lt;button @click="triggerSearch"&gt;Search Around Brasília&lt;/button&gt;
    
    &lt;RadiusSearchTool
      ref="searchToolRef"
      :map-ref="mapRef"
      :initial-radius="15"
      @results-changed="handleResults"
    /&gt;
    
    &lt;div v-if="nearestSite"&gt;
      Nearest site: {{ nearestSite.display_name }} ({{ nearestSite.distance_km }}km)
    &lt;/div&gt;
  &lt;/div&gt;
&lt;/template&gt;

&lt;script setup&gt;
import { ref } from 'vue';
import RadiusSearchTool from '@/components/Map/RadiusSearchTool.vue';

const searchToolRef = ref(null);
const mapRef = ref(null);
const nearestSite = ref(null);

function handleResults(sites) {
  if (sites.length > 0) {
    nearestSite.value = sites[0]; // Sites are ordered by distance
  }
}

// Note: Direct manipulation via ref would require exposing methods
// Current implementation uses event-driven approach
&lt;/script&gt;</code></pre>
    </section>
    
    <!-- Example 4: Custom Styling -->
    <section class="example">
      <h3>Example 4: Custom Styling</h3>
      <p>Override component styles using CSS:</p>
      
      <pre><code>&lt;style&gt;
/* Position panel on left instead of right */
:deep(.search-panel) {
  left: 10px;
  right: auto;
}

/* Custom theme colors */
:deep(.panel-header) {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
}

:deep(.search-button) {
  background: #10b981;
}

:deep(.search-button:hover:not(:disabled)) {
  background: #059669;
}

/* Custom marker colors */
:deep(.result-item:hover) {
  background: #d1fae5;
  border-color: #10b981;
}
&lt;/style&gt;</code></pre>
    </section>
    
    <!-- Example 5: Integration with Pinia Store -->
    <section class="example">
      <h3>Example 5: Integration with Pinia Store</h3>
      <p>Store search results in global state for cross-component access:</p>
      
      <pre><code>// stores/radiusSearch.js
import { defineStore } from 'pinia';
import { ref } from 'vue';

export const useRadiusSearchStore = defineStore('radiusSearch', () => {
  const searchHistory = ref([]);
  const currentResults = ref(null);
  
  function saveSearch(results) {
    currentResults.value = results;
    searchHistory.value.push({
      timestamp: new Date(),
      center: results.center,
      radius: results.radius_km,
      count: results.count
    });
  }
  
  function clearHistory() {
    searchHistory.value = [];
  }
  
  return {
    searchHistory,
    currentResults,
    saveSearch,
    clearHistory
  };
});

// Component usage
&lt;script setup&gt;
import { useRadiusSearchStore } from '@/stores/radiusSearch';

const radiusSearchStore = useRadiusSearchStore();

function onSearchCompleted(results) {
  radiusSearchStore.saveSearch(results);
}
&lt;/script&gt;</code></pre>
    </section>
    
    <!-- Example 6: API Response Format -->
    <section class="example">
      <h3>Example 6: API Response Format</h3>
      <p>Understanding the response structure from <code>/api/v1/inventory/sites/radius</code>:</p>
      
      <pre><code>{
  "count": 3,
  "center": {
    "lat": -15.7801,
    "lng": -47.9292
  },
  "radius_km": 10,
  "sites": [
    {
      "id": 1,
      "display_name": "Brasília Center",
      "latitude": -15.7801,
      "longitude": -47.9292,
      "distance_km": 0.0
    },
    {
      "id": 2,
      "display_name": "Brasília North",
      "latitude": -15.7350,
      "longitude": -47.9292,
      "distance_km": 5.01
    },
    {
      "id": 3,
      "display_name": "Asa Sul",
      "latitude": -15.8200,
      "longitude": -47.9100,
      "distance_km": 7.45
    }
  ]
}</code></pre>
      
      <p><strong>Notes:</strong></p>
      <ul>
        <li>Sites are always ordered by distance (nearest first)</li>
        <li><code>distance_km</code> is rounded to 2 decimal places</li>
        <li>Maximum 100 results by default (configurable in API call)</li>
        <li>Distances calculated using PostGIS ST_Distance (geodesic, WGS84)</li>
      </ul>
    </section>
    
    <!-- Example 7: Error Handling -->
    <section class="example">
      <h3>Example 7: Error Handling</h3>
      <p>Handle various error scenarios:</p>
      
      <pre><code>&lt;script setup&gt;
function onSearchError(error) {
  // Parse error message
  const errorMsg = error.message || 'Erro desconhecido';
  
  // Handle specific error types
  if (errorMsg.includes('Latitude must be between')) {
    showToast('Coordenada inválida: latitude fora do range', 'error');
  } else if (errorMsg.includes('radius_km cannot exceed')) {
    showToast('Raio muito grande: máximo 1000km', 'warning');
  } else if (errorMsg.includes('HTTP 401')) {
    showToast('Sessão expirada, faça login novamente', 'error');
    router.push('/login');
  } else if (errorMsg.includes('HTTP 500')) {
    showToast('Erro no servidor, tente novamente em alguns minutos', 'error');
  } else {
    showToast('Erro na busca: ' + errorMsg, 'error');
  }
  
  // Log for debugging
  console.error('[RadiusSearch] Error details:', {
    message: errorMsg,
    timestamp: new Date(),
    error
  });
}
&lt;/script&gt;</code></pre>
    </section>
    
    <!-- Props Documentation -->
    <section class="example">
      <h3>Props Documentation</h3>
      <table>
        <thead>
          <tr>
            <th>Prop</th>
            <th>Type</th>
            <th>Required</th>
            <th>Default</th>
            <th>Description</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><code>mapRef</code></td>
            <td>Object</td>
            <td>Yes</td>
            <td>-</td>
            <td>Reference to Google Maps instance ({ map: google.maps.Map })</td>
          </tr>
          <tr>
            <td><code>autoActivate</code></td>
            <td>Boolean</td>
            <td>No</td>
            <td>false</td>
            <td>Auto-expand panel on mount</td>
          </tr>
          <tr>
            <td><code>initialRadius</code></td>
            <td>Number</td>
            <td>No</td>
            <td>10</td>
            <td>Initial search radius in km (1-100)</td>
          </tr>
        </tbody>
      </table>
    </section>
    
    <!-- Events Documentation -->
    <section class="example">
      <h3>Events Documentation</h3>
      <table>
        <thead>
          <tr>
            <th>Event</th>
            <th>Payload</th>
            <th>Description</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><code>search-started</code></td>
            <td>-</td>
            <td>Emitted when search begins</td>
          </tr>
          <tr>
            <td><code>search-completed</code></td>
            <td>Object (API response)</td>
            <td>Emitted when search succeeds</td>
          </tr>
          <tr>
            <td><code>search-error</code></td>
            <td>Error</td>
            <td>Emitted when search fails</td>
          </tr>
          <tr>
            <td><code>results-changed</code></td>
            <td>Array (sites)</td>
            <td>Emitted when results update (subset of search-completed)</td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>
</template>

<style scoped>
.usage-examples {
  max-width: 900px;
  margin: 0 auto;
  padding: 32px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

h2 {
  color: #111827;
  border-bottom: 2px solid #3b82f6;
  padding-bottom: 8px;
  margin-bottom: 32px;
}

.example {
  margin-bottom: 48px;
}

h3 {
  color: #1f2937;
  margin-bottom: 16px;
}

p {
  color: #4b5563;
  line-height: 1.6;
  margin-bottom: 12px;
}

pre {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 16px;
  overflow-x: auto;
  margin: 16px 0;
}

code {
  font-family: 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  color: #111827;
}

p code {
  background: #eff6ff;
  padding: 2px 6px;
  border-radius: 3px;
  border: 1px solid #bfdbfe;
  font-size: 12px;
  color: #1e40af;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
}

th {
  background: #f3f4f6;
  padding: 10px;
  text-align: left;
  font-weight: 600;
  color: #374151;
  border: 1px solid #e5e7eb;
}

td {
  padding: 10px;
  border: 1px solid #e5e7eb;
  color: #4b5563;
}

td code {
  background: #eff6ff;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 12px;
  color: #1e40af;
}

ul {
  margin-left: 24px;
  color: #4b5563;
  line-height: 1.8;
}

li {
  margin-bottom: 8px;
}
</style>
