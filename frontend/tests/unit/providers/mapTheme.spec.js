/**
 * EV-0045 — o mapa segue o tema da interface (classe `.dark` do <html>).
 */
import { describe, it, expect, vi, afterEach } from 'vitest';
import {
  currentDocumentTheme,
  followDocumentTheme,
  mapboxStyleForTheme,
  OSM_DARK_FILTER,
} from '@/providers/maps/mapTheme.js';

const MB = 'mapbox://styles/mapbox/';

afterEach(() => {
  document.documentElement.classList.remove('dark');
  document.documentElement.removeAttribute('data-theme');
});

describe('mapTheme', () => {
  it('lê o tema da classe ou do data-theme', () => {
    expect(currentDocumentTheme()).toBe('light');
    document.documentElement.setAttribute('data-theme', 'dark');
    expect(currentDocumentTheme()).toBe('dark');
    document.documentElement.removeAttribute('data-theme');
    document.documentElement.classList.add('dark');
    expect(currentDocumentTheme()).toBe('dark');
  });

  it('chama setTheme só quando o tema muda, até desligar', async () => {
    const map = { setTheme: vi.fn() };
    const stop = followDocumentTheme(map);
    document.documentElement.classList.add('dark');
    await Promise.resolve();
    document.documentElement.classList.add('outra-classe');
    await Promise.resolve();
    expect(map.setTheme.mock.calls).toEqual([['dark']]);
    stop();
    document.documentElement.classList.remove('dark');
    await Promise.resolve();
    expect(map.setTheme).toHaveBeenCalledTimes(1);
  });

  it('variantes Mapbox por tema', () => {
    expect(mapboxStyleForTheme(`${MB}streets-v12`, 'dark')).toBe(`${MB}dark-v11`);
    expect(mapboxStyleForTheme(`${MB}streets-v12`, 'light')).toBe(`${MB}streets-v12`);
    expect(mapboxStyleForTheme(`${MB}dark-v11`, 'light')).toBe(`${MB}light-v11`);
    expect(mapboxStyleForTheme(`${MB}navigation-day-v1`, 'dark')).toBe(`${MB}navigation-night-v1`);
    expect(mapboxStyleForTheme(`${MB}satellite-v9`, 'dark')).toBe(`${MB}satellite-v9`);
    expect(mapboxStyleForTheme('mapbox://styles/x/custom', 'dark')).toBe('mapbox://styles/x/custom');
    expect(mapboxStyleForTheme(`${MB}streets-v12`, undefined)).toBe(`${MB}streets-v12`);
  });

  it('o filtro do OSM escuro inverte e corrige o matiz', () => {
    expect(OSM_DARK_FILTER).toMatch(/invert\(1\).*hue-rotate\(180deg\)/);
  });
});
