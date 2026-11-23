/**
 * Secções da navegação do shell (ADR 0007 Fase 2, EV-0044).
 *
 * Fonte única para a linha 2 do `AppHeader` e para as «Páginas» da paleta de
 * comandos (Ctrl K). Rótulos em PT-BR; `external: true` = link servido pelo
 * Django (fora do vue-router).
 * @module useNavSections
 */
import {
  PhPulse,
  PhListBullets,
  PhShareNetwork,
  PhTreeStructure,
  PhWaveform,
  PhGitBranch,
  PhPlusCircle,
  PhVideoCamera,
  PhGear,
  PhUsers,
  PhMegaphone,
  PhChartBar,
  PhBook,
  PhFaders,
  PhLineSegments,
} from '@phosphor-icons/vue';

export const NAV_SECTIONS = Object.freeze([
  {
    id: 'monitoramento',
    label: 'Monitoramento',
    icon: PhPulse,
    items: [
      { label: 'Visão geral', path: '/monitoring/monitoring-all', icon: PhListBullets },
      { label: 'Backbone', path: '/monitoring/backbone', icon: PhShareNetwork },
      { label: 'GPON', path: '/monitoring/gpon', icon: PhTreeStructure },
      { label: 'DWDM', path: '/monitoring/dwdm', icon: PhWaveform },
    ],
  },
  {
    id: 'rede',
    label: 'Rede',
    icon: PhShareNetwork,
    items: [
      { label: 'Enlaces & fibra', path: '/enlaces', icon: PhLineSegments },
      { label: 'Projeto de rede', path: '/Network/NetworkDesign/', icon: PhGitBranch },
      { label: 'Inventário', path: '/network/inventory', icon: PhListBullets },
      { label: 'Importar dispositivos', path: '/Network/DeviceImport/', icon: PhPlusCircle },
    ],
  },
  {
    id: 'video',
    label: 'Vídeo',
    icon: PhVideoCamera,
    items: [{ label: 'Monitoramento visual', path: '/video', icon: PhVideoCamera }],
  },
  {
    id: 'sistema',
    label: 'Sistema',
    icon: PhGear,
    items: [
      { label: 'Configuração', path: '/setup/config', icon: PhGear },
      { label: 'Usuários', path: '/system/users', icon: PhUsers },
      { label: 'Central de Evolução', path: '/system/evolucao', icon: PhMegaphone },
      { label: 'Saúde do sistema', path: '/metrics/health', icon: PhChartBar },
      { label: 'Documentação', path: '/docs', icon: PhBook },
      { label: 'Admin Django', path: '/admin/', icon: PhFaders, external: true },
    ],
  },
]);

/** `/a/b/` → `/a/b`, comparação sem distinguir maiúsculas (há rotas `/Network/...`). */
export function normalizePath(path = '/') {
  const p = (path || '/').toLowerCase();
  return p.length > 1 && p.endsWith('/') ? p.slice(0, -1) : p;
}

/** O caminho atual pertence ao item (igual ou subcaminho)? */
export function isPathActive(currentPath, itemPath) {
  const cur = normalizePath(currentPath);
  const target = normalizePath(itemPath);
  if (target === '/') return cur === '/';
  return cur === target || cur.startsWith(`${target}/`);
}

/** Secção a que pertence o caminho atual, ou `null`. */
export function activeSectionId(currentPath, sections = NAV_SECTIONS) {
  const hit = sections.find((s) => s.items.some((i) => isPathActive(currentPath, i.path)));
  return hit ? hit.id : null;
}

/** Remove acentos e baixa a caixa, para a busca de páginas. */
export function foldText(text = '') {
  return String(text)
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase();
}

/** Páginas cujo rótulo (ou o da secção) contém o termo. Lista vazia sem termo. */
export function searchPages(term, sections = NAV_SECTIONS) {
  const q = foldText(term).trim();
  if (!q) return [];
  const out = [];
  for (const section of sections) {
    for (const item of section.items) {
      const haystack = foldText(`${item.label} ${section.label}`);
      if (haystack.includes(q)) out.push({ ...item, section: section.label });
    }
  }
  return out;
}
