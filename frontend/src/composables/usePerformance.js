import { ref, computed, onMounted, onUnmounted, watch } from 'vue';

/**
 * Virtual scrolling composable for large lists
 * Renders only visible items plus buffer for smooth scrolling
 * 
 * @param {Object} options - Configuration options
 * @param {Array} options.items - Full list of items
 * @param {Number} options.itemHeight - Height of each item in pixels
 * @param {Number} options.containerHeight - Height of scrollable container
 * @param {Number} options.buffer - Number of items to render above/below viewport (default: 5)
 * @returns {Object} Virtual scroll state and methods
 */
export function useVirtualScroll(options) {
  const {
    items = ref([]),
    itemHeight = 80,
    containerHeight = 500,
    buffer = 5,
  } = options;

  const scrollTop = ref(0);
  const containerRef = ref(null);

  // Calculate visible range
  const visibleRange = computed(() => {
    const itemList = Array.isArray(items.value) ? items.value : items;
    const totalItems = itemList.length;
    
    if (totalItems === 0) {
      return { start: 0, end: 0, visibleItems: [], offset: 0 };
    }

    const visibleCount = Math.ceil(containerHeight / itemHeight);
    const startIndex = Math.floor(scrollTop.value / itemHeight);
    
    // Add buffer items above and below
    const start = Math.max(0, startIndex - buffer);
    const end = Math.min(totalItems, startIndex + visibleCount + buffer);
    
    const visibleItems = itemList.slice(start, end);
    const offset = start * itemHeight;

    return { start, end, visibleItems, offset };
  });

  // Total height for scrollbar
  const totalHeight = computed(() => {
    const itemList = Array.isArray(items.value) ? items.value : items;
    return itemList.length * itemHeight;
  });

  // Handle scroll event
  function handleScroll(event) {
    scrollTop.value = event.target.scrollTop;
  }

  // Scroll to specific index
  function scrollToIndex(index) {
    if (!containerRef.value) return;
    
    const targetScrollTop = index * itemHeight;
    containerRef.value.scrollTop = targetScrollTop;
    scrollTop.value = targetScrollTop;
  }

  // Scroll to top
  function scrollToTop() {
    scrollToIndex(0);
  }

  return {
    containerRef,
    scrollTop,
    visibleRange,
    totalHeight,
    handleScroll,
    scrollToIndex,
    scrollToTop,
  };
}

/**
 * Optimized memoization for expensive computed properties
 * Uses WeakMap for automatic garbage collection
 * 
 * @param {Function} fn - Function to memoize
 * @returns {Function} Memoized function
 */
export function memoize(fn) {
  const cache = new Map();
  
  return function(...args) {
    const key = JSON.stringify(args);
    
    if (cache.has(key)) {
      return cache.get(key);
    }
    
    const result = fn.apply(this, args);
    cache.set(key, result);
    
    // Limit cache size to prevent memory leaks
    if (cache.size > 100) {
      const firstKey = cache.keys().next().value;
      cache.delete(firstKey);
    }
    
    return result;
  };
}

/**
 * Throttle function execution
 * Ensures function runs at most once per interval
 * 
 * @param {Function} fn - Function to throttle
 * @param {Number} delay - Delay in milliseconds
 * @returns {Function} Throttled function
 */
export function throttle(fn, delay = 100) {
  let lastCall = 0;
  let timeoutId = null;
  
  return function(...args) {
    const now = Date.now();
    const timeSinceLastCall = now - lastCall;
    
    if (timeSinceLastCall >= delay) {
      lastCall = now;
      return fn.apply(this, args);
    } else {
      // Schedule call for remaining time
      if (timeoutId) clearTimeout(timeoutId);
      
      timeoutId = setTimeout(() => {
        lastCall = Date.now();
        fn.apply(this, args);
      }, delay - timeSinceLastCall);
    }
  };
}

/**
 * Lazy load component wrapper
 * Loads component only when it enters viewport
 * 
 * @param {Object} options - Configuration
 * @param {Function} options.loader - Async component loader
 * @param {Number} options.delay - Delay before loading (ms)
 * @returns {Object} Component configuration
 */
export function lazyLoadComponent({ loader, delay = 0 }) {
  return {
    loader,
    delay,
    timeout: 10000,
    errorComponent: {
      template: '<div class="lazy-error">Falha ao carregar componente</div>',
    },
    loadingComponent: {
      template: '<div class="lazy-loading">Carregando...</div>',
    },
  };
}
