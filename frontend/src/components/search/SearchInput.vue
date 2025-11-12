<script setup>
import { ref, computed } from 'vue';
import { useDebounceFn } from '@vueuse/core';
import { useFiltersStore } from '@/stores/filters';
import SearchSuggestions from './SearchSuggestions.vue';

const filtersStore = useFiltersStore();

const inputRef = ref(null);
const localQuery = ref('');
const isInputFocused = ref(false);
const selectedIndex = ref(-1);

const emit = defineEmits(['search', 'select']);

// Debounce search to avoid excessive filtering (300ms)
const debouncedSearch = useDebounceFn((query) => {
  filtersStore.setSearchQuery(query);
  emit('search', query);
}, 300);

function handleInput(event) {
  const value = event.target.value;
  localQuery.value = value;
  debouncedSearch(value);
  selectedIndex.value = -1; // Reset selection when typing
}

function handleClear() {
  localQuery.value = '';
  filtersStore.setSearchQuery('');
  selectedIndex.value = -1;
  inputRef.value?.focus();
}

function handleFocus() {
  isInputFocused.value = true;
}

function handleBlur() {
  // Delay to allow clicking on suggestions
  setTimeout(() => {
    isInputFocused.value = false;
  }, 200);
}

function handleKeyDown(event) {
  const suggestions = document.querySelectorAll('.search-suggestion');
  const maxIndex = suggestions.length - 1;
  
  switch (event.key) {
    case 'ArrowDown':
      event.preventDefault();
      selectedIndex.value = Math.min(selectedIndex.value + 1, maxIndex);
      break;
    case 'ArrowUp':
      event.preventDefault();
      selectedIndex.value = Math.max(selectedIndex.value - 1, -1);
      break;
    case 'Enter':
      event.preventDefault();
      if (selectedIndex.value >= 0 && suggestions[selectedIndex.value]) {
        suggestions[selectedIndex.value].click();
      }
      break;
    case 'Escape':
      event.preventDefault();
      inputRef.value?.blur();
      isInputFocused.value = false;
      break;
  }
}

function handleSelectSuggestion(device) {
  localQuery.value = device.name;
  filtersStore.setSearchQuery(device.name);
  isInputFocused.value = false;
  emit('select', device);
}

const showClearButton = computed(() => localQuery.value.length > 0);
const showSuggestions = computed(() => isInputFocused.value);
</script>

<template>
  <div class="search-input-container" role="search">
    <div class="search-input-wrapper">
      <svg class="search-icon" aria-hidden="true" focusable="false" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="11" cy="11" r="8"></circle>
        <path d="m21 21-4.35-4.35"></path>
      </svg>
      
      <input
        ref="inputRef"
        type="text"
        class="search-input"
        :value="localQuery"
        placeholder="Search by hostname, IP, or site..."
        @input="handleInput"
        @focus="handleFocus"
        @blur="handleBlur"
        @keydown="handleKeyDown"
        aria-label="Search devices by name, IP, or site"
        aria-describedby="search-hint"
        :aria-expanded="showSuggestions"
        :aria-controls="showSuggestions ? 'search-suggestions' : undefined"
        :aria-activedescendant="selectedIndex >= 0 ? `suggestion-${selectedIndex}` : undefined"
        role="combobox"
        aria-autocomplete="list"
      />
      
      <span id="search-hint" class="sr-only">
        Type to search devices. Use arrow keys to navigate suggestions.
      </span>
      
      <button
        v-if="showClearButton"
        class="search-clear"
        @click="handleClear"
        aria-label="Clear search query"
        type="button"
      >
        <svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </button>
    </div>
    
    <SearchSuggestions
      v-if="showSuggestions"
      id="search-suggestions"
      :query="localQuery"
      :selected-index="selectedIndex"
      @select="handleSelectSuggestion"
    />
  </div>
</template>

<style scoped>
.search-input-container {
  position: relative;
  width: 100%;
}

.search-input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 12px;
  color: #6b7280;
  pointer-events: none;
  z-index: 1;
}

.search-input {
  width: 100%;
  padding: 0.75rem 2.75rem 0.75rem 2.75rem;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 0.875rem;
  line-height: 1.25rem;
  transition: all 0.2s;
  outline: none;
  background: white;
}

.search-input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.search-input::placeholder {
  color: #9ca3af;
}

.search-clear {
  position: absolute;
  right: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: none;
  border: none;
  border-radius: 4px;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.2s;
  z-index: 1;
}

.search-clear:hover {
  background: #f3f4f6;
  color: #374151;
}

.search-clear:active {
  background: #e5e7eb;
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
