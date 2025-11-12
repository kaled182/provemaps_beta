import { describe, it, expect, vi } from 'vitest';
import { debounce } from '@/utils/debounce';

function wait(ms) { return new Promise(r => setTimeout(r, ms)); }

describe('debounce', () => {
  it('debounces consecutive calls', async () => {
    const spy = vi.fn();
    const d = debounce(spy, 50);
    d(1); d(2); d(3);
    expect(spy).not.toHaveBeenCalled();
    await wait(70);
    expect(spy).toHaveBeenCalledTimes(1);
    expect(spy).toHaveBeenCalledWith(3);
  });
});
