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

function handleOptionClick(value) {
  const shouldEnable = !isSelected(value);
  emit('toggle', value, shouldEnable);
}

function handleOptionKeydown(event, value) {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault();
    handleOptionClick(value);
  }
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
          :class="{ 'filter-dropdown__option--selected': isSelected(option.value) }"
          role="checkbox"
          :aria-checked="isSelected(option.value)"
          tabindex="0"
          @click.prevent="handleOptionClick(option.value)"
          @keydown="handleOptionKeydown($event, option.value)"
        >
          <span
            class="filter-dropdown__checkbox"
            :class="{ 'filter-dropdown__checkbox--checked': isSelected(option.value) }"
            aria-hidden="true"
          >
            <svg
              v-if="isSelected(option.value)"
              class="filter-dropdown__checkbox-icon"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fill-rule="evenodd"
                d="M16.707 5.293a1 1 0 0 1 0 1.414l-8 8a1 1 0 0 1-1.414 0l-4-4a1 1 0 0 1 1.414-1.414L8 12.586l7.293-7.293a1 1 0 0 1 1.414 0z"
                clip-rule="evenodd"
              />
            </svg>
          </span>

          <span class="filter-dropdown__label">
            {{ option.label }}
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
  border-radius: 6px;
  outline: none;
}

.filter-dropdown__option:hover,
.filter-dropdown__option:focus-visible {
  background: var(--surface-highlight);
}

.filter-dropdown__option--selected {
  background: var(--surface-muted);
}

.filter-dropdown__checkbox {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1rem;
  height: 1rem;
  border-radius: 0.3rem;
  border: 1px solid var(--border-primary);
  background: var(--surface-card);
  transition: all 0.15s;
}

.filter-dropdown__checkbox--checked {
  background: var(--accent-info);
  border-color: var(--accent-info);
  color: var(--surface-card);
}

.filter-dropdown__checkbox-icon {
  width: 0.85rem;
  height: 0.85rem;
}

.filter-dropdown__label {
  flex: 1;
  font-size: 0.875rem;
  color: var(--text-primary);
}
</style>
