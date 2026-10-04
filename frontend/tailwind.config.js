/** @type {import('tailwindcss').Config} */
// EV-0019: Tailwind passa a ser compilado no build (antes vinha do Play CDN,
// que é um compilador em runtime e obriga a `'unsafe-eval'` no CSP).
// O `tailwind.config` alinhado com o CRM e os primitivos chegam na Fase 3 do
// ADR 0007; aqui está só o necessário para reproduzir o que o CDN gerava.
import colors from 'tailwindcss/colors';

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
      colors: {
        // `primary-*` é usado em 163 sítios mas nunca existiu no CDN (ficava
        // sem estilo). Hoje é o acento verde de theme.css (#10b981/#059669);
        // o EV-0028 (ADR 0007, Fase 1) troca-o pelos tokens teal do CRM.
        primary: colors.emerald,
      },
    },
  },
  plugins: [],
};
