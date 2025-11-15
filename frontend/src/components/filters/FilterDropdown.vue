<script setup>
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue';
import { onClickOutside } from '@vueuse/core';
import { PhCheck } from '@phosphor-icons/vue';

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
const menuRef = ref(null);
const menuPlacement = ref('bottom');
const menuStyles = ref({
  left: '0px',
  top: '0px',
  width: '200px',
  maxHeight: '300px',
});

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

function getIconStyle(option) {
  const color = option?.iconColor || option?.color;
  return color ? { color } : undefined;
}

onClickOutside(dropdownRef, () => {
  isOpen.value = false;
});

async function updateMenuDimensions() {
  if (!dropdownRef.value) return;

  const rect = dropdownRef.value.getBoundingClientRect();
  const viewportHeight = window.innerHeight;
  const viewportWidth = window.innerWidth;
  const viewportPadding = 16;
  const verticalPadding = 16;
  const maxUsableHeight = Math.max(viewportHeight - verticalPadding * 2, 120);
  const computeHeight = (available) => {
    const safeAvailable = Math.max(available, 0);
    const capped = Math.min(safeAvailable, maxUsableHeight);
    if (capped > 0) {
      return capped;
    }
    return Math.min(maxUsableHeight, 200);
  };

  const desiredWidth = Math.max(rect.width, 200);
  const maxWidthAvailable = Math.max(viewportWidth - viewportPadding * 2, 140);
  let width = Math.min(Math.max(desiredWidth, 160), maxWidthAvailable);
  const boundaryEl = dropdownRef.value.closest('aside') || dropdownRef.value.closest('.filter-bar__row') || dropdownRef.value.parentElement;
  const boundaryRect = boundaryEl?.getBoundingClientRect();
  const centerX = rect.left + rect.width / 2;
  let left = centerX - width / 2;

  const clampToViewport = () => {
    if (left < viewportPadding) {
      left = viewportPadding;
    }
    if (left + width > viewportWidth - viewportPadding) {
      left = viewportWidth - viewportPadding - width;
    }
  };

  if (boundaryRect) {
    const boundaryPadding = 12;
    const boundaryLeft = Math.max(boundaryRect.left + boundaryPadding, viewportPadding);
    const boundaryRight = Math.min(boundaryRect.right - boundaryPadding, viewportWidth - viewportPadding);
    const boundaryWidth = Math.max(boundaryRight - boundaryLeft, rect.width);
    width = Math.min(width, boundaryWidth);
    if (width < rect.width) {
      width = rect.width;
    }
    left = Math.min(Math.max(left, boundaryLeft), boundaryRight - width);
    if (left + width > boundaryRight) {
      left = boundaryRight - width;
    }
    if (left < boundaryLeft) {
      left = boundaryLeft;
    }
    clampToViewport();
  } else {
    clampToViewport();
  }

  menuPlacement.value = 'bottom';
  menuStyles.value = {
    left: `${left}px`,
    top: `${Math.min(rect.bottom + 8, viewportHeight - verticalPadding)}px`,
    width: `${width}px`,
    maxHeight: `${computeHeight(viewportHeight - rect.bottom - verticalPadding)}px`,
  };

  await nextTick();

  if (!menuRef.value) {
    return;
  }

  const menuRect = menuRef.value.getBoundingClientRect();
  const bottomOverflow = menuRect.bottom + viewportPadding - viewportHeight;
  if (bottomOverflow > 0) {
    const availableAbove = rect.top - verticalPadding;
    if (availableAbove > menuRect.height || availableAbove > viewportHeight - rect.bottom - verticalPadding) {
      menuPlacement.value = 'top';
      menuStyles.value = {
        ...menuStyles.value,
        top: `${Math.max(rect.top - 8, verticalPadding)}px`,
        maxHeight: `${computeHeight(availableAbove)}px`,
      };
      await nextTick();
      const updatedRect = menuRef.value?.getBoundingClientRect();
      if (updatedRect && updatedRect.top < viewportPadding) {
        menuPlacement.value = 'bottom';
        const availableBelow = viewportHeight - rect.bottom - verticalPadding;
        menuStyles.value = {
          ...menuStyles.value,
          top: `${Math.min(rect.bottom + 8, viewportHeight - verticalPadding)}px`,
          maxHeight: `${computeHeight(availableBelow)}px`,
        };
      }
    } else {
      const availableBelow = viewportHeight - rect.bottom - verticalPadding;
      menuStyles.value = {
        ...menuStyles.value,
        maxHeight: `${computeHeight(availableBelow)}px`,
      };
    }
  } else {
    const availableBelow = viewportHeight - rect.bottom - verticalPadding;
    menuStyles.value = {
      ...menuStyles.value,
      maxHeight: `${computeHeight(availableBelow)}px`,
    };
  }
}

function detachListeners() {
  window.removeEventListener('resize', updateMenuDimensions);
  window.removeEventListener('scroll', updateMenuDimensions, true);
}

watch(isOpen, async (open) => {
  if (open) {
    await nextTick();
    await updateMenuDimensions();
    window.addEventListener('resize', updateMenuDimensions);
    window.addEventListener('scroll', updateMenuDimensions, true);
  } else {
    detachListeners();
  }
});

onBeforeUnmount(() => {
  detachListeners();
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
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <path d="M19 9l-7 7-7-7" />
      </svg>
    </button>

    <div
      v-if="isOpen"
      class="filter-dropdown__menu"
      :class="{ 'filter-dropdown__menu--top': menuPlacement === 'top' }"
      :style="menuStyles"
      ref="menuRef"
    >
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
            v-if="option.icon"
            class="filter-dropdown__option-icon"
            :style="getIconStyle(option)"
            aria-hidden="true"
          >
            <component
              :is="option.icon"
              :size="18"
              :weight="isSelected(option.value) ? 'fill' : 'regular'"
            />
          </span>

          <span class="filter-dropdown__label">{{ option.label }}</span>

          <span
            v-if="typeof option.count === 'number'"
            class="filter-dropdown__count"
            aria-hidden="true"
          >
            {{ option.count }}
          </span>

          <span
            v-if="isSelected(option.value)"
            class="filter-dropdown__selected-icon"
            aria-hidden="true"
          >
            <PhCheck :size="16" weight="bold" />
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
  position: fixed;
  background: var(--surface-card);
  border: 1px solid var(--border-primary);
  border-radius: 8px;
  box-shadow: var(--shadow-md);
  backdrop-filter: blur(10px);
  z-index: 100;
  transform: translateY(0);
  transform-origin: top center;
}

.filter-dropdown__menu--top {
  transform: translateY(-100%);
  transform-origin: bottom center;
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
  background: var(--accent-info-light);
  color: var(--text-primary);
}

.filter-dropdown__option--selected .filter-dropdown__label {
  color: var(--accent-info-dark);
  font-weight: 600;
}

.filter-dropdown__option--selected .filter-dropdown__option-icon {
  color: var(--accent-info);
}

.filter-dropdown__option--selected .filter-dropdown__count {
  color: var(--accent-info-dark);
}

.filter-dropdown__option-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.25rem;
  height: 1.25rem;
  color: var(--text-tertiary);
}

.filter-dropdown__label {
  flex: 1;
  font-size: 0.875rem;
  color: var(--text-primary);
}

.filter-dropdown__count {
  font-size: 0.75rem;
  color: var(--text-tertiary);
  margin-left: auto;
}

.filter-dropdown__selected-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--accent-info);
  margin-left: 0.5rem;
}
</style>
