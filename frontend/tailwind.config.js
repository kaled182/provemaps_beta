/** @type {import('tailwindcss').Config} */
// EV-0019: Tailwind passa a ser compilado no build (antes vinha do Play CDN,
// que é um compilador em runtime e obriga a `'unsafe-eval'` no CSP).
// EV-0028 (ADR 0007 Fase 1): paleta, neutros em variáveis e fontes iguais ao CRM.
// Os primitivos chegam na Fase 3.

export default {
  darkMode: 'class',
  content: [
    './index.html',
    './src/**/*.{vue,js}',
    // O shell Django do SPA também usa utilitários (body/html).
    '../backend/templates/base_spa.html',
  ],
  safelist: [
    // SiteDetailsModal monta `grid-cols-${cols}` a partir do layout do mosaico.
    { pattern: /^grid-cols-(1|2|3|4|5|6)$/ },
  ],
  theme: {
    extend: {
      // ADR 0007 Fase 1 (EV-0028): os mesmos tokens do CRM (`tailwind.config.ts`
      // de lá). A escala neutra, `surface`, `canvas` e as semânticas são variáveis
      // CSS de design-system/tokens.css, que invertem no tema escuro.
      colors: {
        primary: {
          50: '#F0FAFB',
          100: '#D9F2F4',
          200: '#B4E1E4',
          300: '#8DD0D4',
          400: '#5FBFC3',
          500: '#42B4B8',
          600: '#38989C',
          700: '#2D7A7D',
          800: '#235C5F',
          900: '#19403F',
          950: '#0F2728',
        },
        neutral: {
          50: 'rgb(var(--n-50) / <alpha-value>)',
          100: 'rgb(var(--n-100) / <alpha-value>)',
          200: 'rgb(var(--n-200) / <alpha-value>)',
          300: 'rgb(var(--n-300) / <alpha-value>)',
          400: 'rgb(var(--n-400) / <alpha-value>)',
          500: 'rgb(var(--n-500) / <alpha-value>)',
          600: 'rgb(var(--n-600) / <alpha-value>)',
          700: 'rgb(var(--n-700) / <alpha-value>)',
          800: 'rgb(var(--n-800) / <alpha-value>)',
          900: 'rgb(var(--n-900) / <alpha-value>)',
          950: 'rgb(var(--n-950) / <alpha-value>)',
        },
        surface: 'rgb(var(--surface) / <alpha-value>)',
        canvas: 'rgb(var(--canvas) / <alpha-value>)',
        'accent-warm': { 500: '#F97316', 600: '#EA580C' },
        'accent-cool': { 500: '#10B981', 600: '#059669' },
        success: 'rgb(var(--success) / <alpha-value>)',
        warning: 'rgb(var(--warning) / <alpha-value>)',
        danger: 'rgb(var(--danger) / <alpha-value>)',
        info: 'rgb(var(--info) / <alpha-value>)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Apple Color Emoji', 'Segoe UI Emoji', 'Noto Color Emoji', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
        display: ['Outfit', 'Inter', 'system-ui', 'Apple Color Emoji', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
