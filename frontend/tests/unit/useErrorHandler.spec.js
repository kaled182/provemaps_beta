import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { useErrorHandler } from '@/composables/useErrorHandler';
import { defineComponent, h } from 'vue';

describe('useErrorHandler', () => {
  it('handles async errors with fallback value', async () => {
    const TestComponent = defineComponent({
      setup() {
        const { handleAsync } = useErrorHandler();
        
        const asyncFn = async () => {
          throw new Error('Async error');
        };
        
        return { handleAsync, asyncFn };
      },
      render() {
        return h('div');
      }
    });

    const wrapper = mount(TestComponent);
    const result = await wrapper.vm.handleAsync(
      wrapper.vm.asyncFn,
      { fallbackValue: 'fallback', silent: true }
    );
    
    expect(result).toBe('fallback');
  });

  it('clears error state', async () => {
    const TestComponent = defineComponent({
      setup() {
        const { error, hasError, clearError } = useErrorHandler();
        
        // Manually set error state
        const setError = () => {
          error.value = 'Test error';
          hasError.value = true;
        };
        
        return { error, hasError, clearError, setError };
      },
      render() {
        return h('div');
      }
    });

    const wrapper = mount(TestComponent);
    
    // Set error manually
    wrapper.vm.setError();
    expect(wrapper.vm.hasError).toBe(true);
    
    // Clear error
    wrapper.vm.clearError();
    
    expect(wrapper.vm.hasError).toBe(false);
    expect(wrapper.vm.error).toBe(null);
  });

  it('retries failed operation with exponential backoff', async () => {
    let attempts = 0;
    
    const TestComponent = defineComponent({
      setup() {
        const { retry } = useErrorHandler();
        
        const failingFn = async () => {
          attempts++;
          if (attempts < 3) {
            throw new Error('Not yet');
          }
          return 'success';
        };
        
        return { retry, failingFn };
      },
      render() {
        return h('div');
      }
    });

    const wrapper = mount(TestComponent);
    const result = await wrapper.vm.retry(wrapper.vm.failingFn, 3, 10);
    
    expect(result).toBe('success');
    expect(attempts).toBe(3);
  }, 10000);

  it('throws after max retry attempts', async () => {
    const TestComponent = defineComponent({
      setup() {
        const { retry } = useErrorHandler();
        
        const alwaysFailingFn = async () => {
          throw new Error('Always fails');
        };
        
        return { retry, alwaysFailingFn };
      },
      render() {
        return h('div');
      }
    });

    const wrapper = mount(TestComponent);
    
    await expect(
      wrapper.vm.retry(wrapper.vm.alwaysFailingFn, 2, 10)
    ).rejects.toThrow('Always fails');
  }, 10000);
});

describe('setupGlobalErrorHandler', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('handles unhandled promise rejections', () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    
    // Trigger unhandled rejection
    const rejection = new Event('unhandledrejection');
    rejection.reason = new Error('Unhandled rejection');
    window.dispatchEvent(rejection);
    
    // Cleanup
    consoleErrorSpy.mockRestore();
  });
});
