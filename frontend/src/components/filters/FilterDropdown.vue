<script setup>
import { ref, computed } from 'vue';
import { onClickOutside } from '@vueuse/core';

const props = defineProps({
  label: {
    type: String,
    required: true,
  },
  options: {
    type: Array,
    required: true,
  },
  selected: {
    type: Array,
    default: () => [],
  },
});

const emit = defineEmits(['toggle', 'clear']);

const isOpen = ref(false);
const dropdownRef = ref(null);

const selectedCount = computed(() => props.selected.length);
const buttonLabel = computed(() => {
  if (selectedCount.value === 0) return props.label;
  if (selectedCount.value === 1) {
    const option = props.options.find(opt => opt.value === props.selected[0]);
    return option?.label || props.label;
  }
  return `${props.label} (${selectedCount.value})`;
});

function toggleDropdown() {
  isOpen.value = !isOpen.value;
}

function handleToggle(value) {
  emit('toggle', value);
}

function handleClear(event) {
  event.stopPropagation();
  emit('clear');
  isOpen.value = false;
}

function isSelected(value) {
  return props.selected.includes(value);
}

onClickOutside(dropdownRef, () => {
  isOpen.value = false;
});
</script>

<template>
  <div ref="dropdownRef" class="filter-dropdown">
    <button
      class="filter-dropdown__button"
      :class="{ 'filter-dropdown__button--active': selectedCount > 0 }"
      @click="toggleDropdown"
    >
      {{ buttonLabel }}
      <svg
        class="filter-dropdown__icon"
        :class="{ 'filter-dropdown__icon--open': isOpen }"
        xmlns="http://www.w3.org/2000/svg"
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
      >
        <polyline points="6 9 12 15 18 9"></polyline>
      </svg>
    </button>

    <div v-if="isOpen" class="filter-dropdown__menu">
      <div class="filter-dropdown__header">
        <span class="filter-dropdown__title">{{ label }}</span>
        <button
          v-if="selectedCount > 0"
          class="filter-dropdown__clear"
          @click="handleClear"
        >
          Clear
        </button>
      </div>

      <div class="filter-dropdown__options">
        <label
          v-for="option in options"
          :key="option.value"
          class="filter-dropdown__option"
        >
          <input
            type="checkbox"
            :checked="isSelected(option.value)"
            @change="handleToggle(option.value)"
          />
          <span class="filter-dropdown__label">
            {{ option.label }}
          </span>
          <span
            v-if="isSelected(option.value)"
            class="filter-dropdown__checkmark"
          >
            ✓
          </span>
        </label>
      </div>
    </div>
  </div>
</template>

<style scoped>
.filter-dropdown {
  position: relative;
  display: inline-block;
}

.filter-dropdown__button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: var(--surface-muted);
  border: 1px solid var(--border-primary);
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-primary);
  cursor: pointer;
  transition: all 0.2s;
}

.filter-dropdown__button:hover {
  border-color: var(--border-secondary);
  background: var(--surface-highlight);
}

.filter-dropdown__button--active {
  background: var(--accent-info);
  color: white;
  border-color: var(--accent-info);
}

.filter-dropdown__icon {
  transition: transform 0.2s;
}

.filter-dropdown__icon--open {
  transform: rotate(180deg);
}

.filter-dropdown__menu {
  position: absolute;
  top: calc(100% + 0.5rem);
  left: 0;
  min-width: 200px;
  background: var(--surface-card);
  border: 1px solid var(--border-primary);
  border-radius: 8px;
  box-shadow: var(--shadow-md);
  backdrop-filter: blur(10px);
  z-index: 10;
}

.filter-dropdown__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--border-primary);
}

.filter-dropdown__title {
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--text-primary);
}

.filter-dropdown__clear {
  font-size: 0.75rem;
  color: var(--accent-info);
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
}

.filter-dropdown__clear:hover {
  text-decoration: underline;
}

.filter-dropdown__options {
  max-height: 300px;
  overflow-y: auto;
  padding: 0.5rem 0;
}

.filter-dropdown__option {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 1rem;
  cursor: pointer;
  transition: background 0.15s;
}

.filter-dropdown__option:hover {
  background: var(--surface-highlight);
}

.filter-dropdown__option input[type="checkbox"] {
  cursor: pointer;
}

.filter-dropdown__label {
  flex: 1;
  font-size: 0.875rem;
  color: var(--text-primary);
}

.filter-dropdown__checkmark {
  color: var(--accent-info);
  font-weight: bold;
}
</style>
