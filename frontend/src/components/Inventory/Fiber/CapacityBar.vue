<template>
  <div class="w-full min-w-[120px]">
    <div class="flex justify-between mb-1">
      <span class="text-[10px] font-medium text-gray-500 dark:text-gray-400">
        {{ used }} / {{ total }} fios
      </span>
      <span :class="['text-[10px] font-bold', textClass]">
        {{ percentage }}%
      </span>
    </div>
    <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
      <div
        class="h-2 rounded-full transition-all duration-500 ease-out"
        :class="barColor"
        :style="{ width: `${percentage}%` }"
      ></div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  used: { type: Number, default: 0 },
  total: { type: Number, default: 1 },
});

const percentage = computed(() => {
  if (!props.total) return 0;
  return Math.min(Math.round((props.used / props.total) * 100), 100);
});

const barColor = computed(() => {
  if (percentage.value >= 90) return 'bg-red-500';
  if (percentage.value >= 70) return 'bg-orange-500';
  return 'bg-blue-500';
});

const textClass = computed(() => {
  if (percentage.value >= 90) return 'text-red-600 dark:text-red-400';
  if (percentage.value >= 70) return 'text-orange-600 dark:text-orange-400';
  return 'text-blue-600 dark:text-blue-400';
});
</script>
