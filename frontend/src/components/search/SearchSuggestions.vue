<script setup>
import { computed, watch } from 'vue';
import { useDashboardStore } from '@/stores/dashboard';
import { useFuzzySearch } from '@/composables/useFuzzySearch';
import { useSearchHistory } from '@/composables/useSearchHistory';

const props = defineProps({
  query: {
    type: String,
    required: true,
  },
  selectedIndex: {
    type: Number,
    default: -1,
  },
});

const emit = defineEmits(['select']);

const dashboardStore = useDashboardStore();
const { history, addToHistory } = useSearchHistory();

// Fuzzy search on all hosts
const searchKeys = ['name', 'ip', 'description', 'site_name'];
const { searchQuery, results: fuzzyResults } = useFuzzySearch(
  computed(() => dashboardStore.hostsList),
  searchKeys,
  { threshold: 0.3, maxResults: 10 }
);

// Sync query from parent
watch(() => props.query, (newQuery) => {
  searchQuery.value = newQuery;
}, { immediate: true });

const suggestions = computed(() => {
  // Show search results if query is >= 2 chars
  if (props.query.length >= 2 && fuzzyResults.value.length > 0) {
    return fuzzyResults.value.map(result => ({
      device: result.item,
      score: result.score,
      matches: result.matches,
    }));
  }
  
  // Show history when no query or no results
  if (props.query.length < 2 && history.value.length > 0) {
    return history.value.slice(0, 5).map(query => ({
      isHistory: true,
      query,
    }));
  }
  
  return [];
});

function handleSelect(suggestion) {
  if (suggestion.isHistory) {
    emit('select', { name: suggestion.query });
  } else {
    addToHistory(suggestion.device.name);
    emit('select', suggestion.device);
  }
}

function getStatusColor(status) {
  const colors = {
    operational: '#10b981',
    warning: '#f59e0b',
    critical: '#ef4444',
    offline: '#6b7280',
    unknown: '#3b82f6',
  };
  return colors[status] || colors.unknown;
}

function getStatusIcon(status) {
  const icons = {
    operational: '✅',
    warning: '⚠️',
    critical: '🔴',
    offline: '⚫',
    unknown: '🔵',
  };
  return icons[status] || icons.unknown;
}
</script>

<template>
  <div class="search-suggestions" role="listbox" aria-label="Search suggestions">
    <div 
      v-if="suggestions.length === 0 && query.length >= 2" 
      class="suggestions-empty"
      role="status"
      aria-live="polite"
    >
      No devices found matching "{{ query }}"
    </div>
    
    <div
      v-for="(suggestion, index) in suggestions"
      :key="suggestion.isHistory ? `history-${suggestion.query}` : `device-${suggestion.device.id}`"
      :id="`suggestion-${index}`"
      class="search-suggestion"
      :class="{ 'selected': index === selectedIndex }"
      role="option"
      :aria-selected="index === selectedIndex"
      @click="handleSelect(suggestion)"
    >
      <template v-if="suggestion.isHistory">
        <svg class="suggestion-icon history-icon" aria-hidden="true" focusable="false" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"></circle>
          <polyline points="12 6 12 12 16 14"></polyline>
        </svg>
        <span class="suggestion-text">{{ suggestion.query }}</span>
        <span class="sr-only">(from search history)</span>
      </template>
      
      <template v-else>
        <span 
          class="suggestion-status" 
          :style="{ color: getStatusColor(suggestion.device.status) }"
          :aria-label="`Status: ${suggestion.device.status}`"
        >
          {{ getStatusIcon(suggestion.device.status) }}
        </span>
        <div class="suggestion-info">
          <div class="suggestion-name">{{ suggestion.device.name }}</div>
          <div class="suggestion-meta" aria-label="Device details">
            {{ suggestion.device.type || 'Unknown Type' }} • {{ suggestion.device.site_name || 'Unknown Site' }}
          </div>
        </div>
      </template>
    </div>
    
    <div 
      v-if="history.length === 0 && query.length < 2" 
      class="suggestions-hint"
      role="status"
      aria-live="polite"
    >
      Start typing to search...
    </div>
  </div>
</template>

<style scoped>
.search-suggestions {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
  max-height: 400px;
  overflow-y: auto;
  z-index: 20;
}

.search-suggestion {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  cursor: pointer;
  transition: background 0.15s;
  border-bottom: 1px solid #f3f4f6;
}

.search-suggestion:last-child {
  border-bottom: none;
}

.search-suggestion:hover,
.search-suggestion.selected {
  background: #f9fafb;
}

.suggestion-icon {
  flex-shrink: 0;
  color: #6b7280;
}

.history-icon {
  color: #9ca3af;
}

.suggestion-status {
  flex-shrink: 0;
  font-size: 1.25rem;
  line-height: 1;
}

.suggestion-info {
  flex: 1;
  min-width: 0;
}

.suggestion-name {
  font-weight: 500;
  font-size: 0.875rem;
  color: #111827;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.suggestion-meta {
  font-size: 0.75rem;
  color: #6b7280;
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.suggestion-text {
  font-size: 0.875rem;
  color: #374151;
}

.suggestions-empty,
.suggestions-hint {
  padding: 1rem;
  text-align: center;
  font-size: 0.875rem;
  color: #6b7280;
}

/* Screen reader only text */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}
</style>
