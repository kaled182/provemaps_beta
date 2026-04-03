import { ref, onErrorCaptured } from 'vue';

/**
 * Composable for handling errors in components with graceful fallback
 * @returns {Object} Error state and handler functions
 */
export function useErrorHandler() {
  const error = ref(null);
  const hasError = ref(false);
  const errorDetails = ref(null);

  /**
   * Capture errors within component tree
   */
  onErrorCaptured((err, instance, info) => {
    console.error('[Error Boundary]', {
      error: err,
      component: instance?.$options?.name || 'Unknown',
      info,
    });

    error.value = err.message || 'An unexpected error occurred';
    hasError.value = true;
    errorDetails.value = {
      message: err.message,
      stack: err.stack,
      component: instance?.$options?.name,
      info,
    };

    // Prevent error from propagating further
    return false;
  });

  /**
   * Handle async errors (API calls, WebSocket, etc.)
   * @param {Function} asyncFn - Async function to execute
   * @param {Object} options - Error handling options
   * @returns {Promise<any>} Result of async function or null on error
   */
  async function handleAsync(asyncFn, options = {}) {
    const { 
      fallbackValue = null,
      errorMessage = 'Operation failed',
      silent = false,
    } = options;

    try {
      return await asyncFn();
    } catch (err) {
      if (!silent) {
        console.error(`[Async Error] ${errorMessage}:`, err);
        error.value = errorMessage;
        hasError.value = true;
        errorDetails.value = {
          message: err.message,
          stack: err.stack,
          context: errorMessage,
        };
      }
      return fallbackValue;
    }
  }

  /**
   * Clear error state
   */
  function clearError() {
    error.value = null;
    hasError.value = false;
    errorDetails.value = null;
  }

  /**
   * Retry a failed operation
   * @param {Function} retryFn - Function to retry
   * @param {number} maxRetries - Maximum retry attempts
   * @param {number} delay - Delay between retries in ms
   */
  async function retry(retryFn, maxRetries = 3, delay = 1000) {
    let attempt = 0;
    
    while (attempt < maxRetries) {
      try {
        const result = await retryFn();
        clearError();
        return result;
      } catch (err) {
        attempt++;
        if (attempt >= maxRetries) {
          error.value = `Failed after ${maxRetries} attempts`;
          hasError.value = true;
          throw err;
        }
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
  }

  return {
    error,
    hasError,
    errorDetails,
    handleAsync,
    clearError,
    retry,
  };
}

/**
 * Global error handler for uncaught errors
 * Should be registered in main.js
 */
export function setupGlobalErrorHandler(app) {
  app.config.errorHandler = (err, instance, info) => {
    console.error('[Global Error Handler]', {
      error: err,
      component: instance?.$options?.name || 'Unknown',
      info,
    });

    // Could send to error tracking service (Sentry, etc.)
    // trackError({ error: err, component: instance?.$options?.name, info });
  };

  // Handle unhandled promise rejections
  window.addEventListener('unhandledrejection', (event) => {
    console.error('[Unhandled Promise Rejection]', event.reason);
    // trackError({ error: event.reason, type: 'unhandledRejection' });
  });
}
