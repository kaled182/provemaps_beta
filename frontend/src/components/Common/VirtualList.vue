<template>
  <div 
    ref="containerRef"
    class="virtual-list-container"
    @scroll="handleScroll"
    :style="{ height: `${containerHeight}px`, overflow: 'auto' }"
  >
    <div 
      class="virtual-list-spacer"
      :style="{ height: `${totalHeight}px`, position: 'relative' }"
    >
      <div
        class="virtual-list-content"
        :style="{ transform: `translateY(${visibleRange.offset}px)` }"
      >
        <slot 
          v-for="(item, index) in visibleRange.visibleItems" 
          :key="getItemKey(item, visibleRange.start + index)"
          :item="item"
          :index="visibleRange.start + index"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, toRefs } from 'vue';
import { useVirtualScroll } from '@/composables/usePerformance';

const props = defineProps({
  items: {
    type: Array,
    required: true,
  },
  itemHeight: {
    type: Number,
    default: 80,
  },
  containerHeight: {
    type: Number,
    default: 500,
  },
  buffer: {
    type: Number,
    default: 5,
  },
  itemKey: {
    type: [String, Function],
    default: 'id',
  },
});

const { items } = toRefs(props);

const {
  containerRef,
  visibleRange,
  totalHeight,
  handleScroll,
  scrollToIndex,
  scrollToTop,
} = useVirtualScroll({
  items,
  itemHeight: props.itemHeight,
  containerHeight: props.containerHeight,
  buffer: props.buffer,
});

function getItemKey(item, index) {
  if (typeof props.itemKey === 'function') {
    return props.itemKey(item, index);
  }
  return item[props.itemKey] ?? index;
}

defineExpose({
  scrollToIndex,
  scrollToTop,
});
</script>

<style scoped>
.virtual-list-container {
  position: relative;
  overflow-y: auto;
  overflow-x: hidden;
}

.virtual-list-spacer {
  width: 100%;
}

.virtual-list-content {
  width: 100%;
  will-change: transform;
}
</style>
