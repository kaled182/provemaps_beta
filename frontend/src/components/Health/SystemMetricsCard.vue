<template>
  <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
    <div class="flex items-center justify-between mb-4">
      <div class="flex items-center gap-2">
        <span class="text-2xl">{{ icon }}</span>
        <h3 class="text-sm font-medium text-gray-600 dark:text-gray-400 uppercase">
          {{ title }}
        </h3>
      </div>
    </div>
    
    <div class="space-y-3">
      <div class="flex items-end gap-2">
        <span
          :class="[
            'text-4xl font-bold',
            isOverThreshold ? 'text-red-600 dark:text-red-400' : 'text-gray-900 dark:text-gray-100'
          ]"
        >
          {{ displayValue }}
        </span>
        <span class="text-lg text-gray-600 dark:text-gray-400 pb-1">{{ unit }}</span>
      </div>
      
      <!-- Progress Bar -->
      <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
        <div
          :class="[
            'h-2 rounded-full transition-all duration-300',
            isOverThreshold ? 'bg-red-500' : 'bg-blue-500'
          ]"
          :style="{ width: `${Math.min(value || 0, 100)}%` }"
        ></div>
      </div>
      
      <div v-if="details" class="text-sm text-gray-600 dark:text-gray-400">
        {{ details }}
      </div>
      
      <div v-if="isOverThreshold" class="flex items-center gap-2 text-sm text-red-600 dark:text-red-400">
        <span>⚠️</span>
        <span>Above threshold ({{ threshold }}{{ unit }})</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  title: {
    type: String,
    required: true,
  },
  value: {
    type: Number,
    default: 0,
  },
  unit: {
    type: String,
    default: '',
  },
  icon: {
    type: String,
    default: '📊',
  },
  threshold: {
    type: Number,
    default: 100,
  },
  details: {
    type: String,
    default: '',
  },
});

const displayValue = computed(() => {
  return props.value?.toFixed(1) || '0.0';
});

const isOverThreshold = computed(() => {
  return (props.value || 0) > props.threshold;
});
</script>
