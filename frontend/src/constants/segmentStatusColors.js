// Mapping of segment operational statuses to stroke colors
// Extend as backend introduces more granular states.
export const SEGMENT_STATUS_COLORS = {
  operational: '#16a34a', // green-600
  degraded: '#f59e0b',    // amber-500
  down: '#dc2626',        // red-600
  maintenance: '#3b82f6', // blue-500
  unknown: '#6b7280',     // gray-500
};

export function colorForStatus(status) {
  if (!status) return SEGMENT_STATUS_COLORS.unknown;
  return SEGMENT_STATUS_COLORS[status] || SEGMENT_STATUS_COLORS.unknown;
}
