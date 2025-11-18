<template>
  <div class="space-y-2">
    <div class="flex items-center justify-between">
      <span class="text-sm font-medium text-gray-700 dark:text-gray-300 capitalize">
        {{ name }}
      </span>
      <span class="text-sm font-mono text-gray-600 dark:text-gray-400">
        {{ responseTime }}ms
      </span>
    </div>
    <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
      <div
        :class="[
          'h-2 rounded-full transition-all duration-300',
          responseTimeClass
        ]"
        :style="{ width: `${Math.min(widthPercent, 100)}%` }"
      ></div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  name: {
    type: String,
    required: true,
  },
  responseTime: {
    type: Number,
    required: true,
  },
});

const widthPercent = computed(() => {
  // Scale: 0ms = 0%, 1000ms = 100%
  return (props.responseTime / 1000) * 100;
});

const responseTimeClass = computed(() => {
  if (props.responseTime < 50) return 'bg-green-500';
  if (props.responseTime < 200) return 'bg-yellow-500';
  if (props.responseTime < 500) return 'bg-orange-500';
  return 'bg-red-500';
});
</script>
