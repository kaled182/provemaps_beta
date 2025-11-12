// Simple debounce utility used by MapView to limit BBox fetch frequency
export function debounce(fn, wait = 300) {
  let t;
  return function debounced(...args) {
    if (t) clearTimeout(t);
    t = setTimeout(() => fn.apply(this, args), wait);
  };
}
