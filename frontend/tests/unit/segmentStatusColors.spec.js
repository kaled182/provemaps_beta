import { describe, it, expect } from 'vitest';
import { colorForStatus, SEGMENT_STATUS_COLORS } from '@/constants/segmentStatusColors';

describe('segmentStatusColors', () => {
  it('returns exact color for known status', () => {
    expect(colorForStatus('operational')).toBe(SEGMENT_STATUS_COLORS.operational);
    expect(colorForStatus('degraded')).toBe(SEGMENT_STATUS_COLORS.degraded);
  });
  it('falls back to unknown color', () => {
    expect(colorForStatus('non-existent')).toBe(SEGMENT_STATUS_COLORS.unknown);
    expect(colorForStatus(null)).toBe(SEGMENT_STATUS_COLORS.unknown);
  });
});
