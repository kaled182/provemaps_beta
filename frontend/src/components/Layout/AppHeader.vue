<template>
  <header ref="rootEl" class="app-header relative z-[1000] shrink-0 border-b border-neutral-200 bg-surface text-neutral-800">
    <!-- Linha 1: marca · busca · estado · ações · utilizador -->
    <div class="flex h-12 items-center gap-3 px-3 sm:px-4">
      <RouterLink to="/" class="flex shrink-0 items-center gap-2" title="Início">
        <span class="flex h-7 w-7 items-center justify-center rounded-md bg-primary-500 font-display text-xs font-bold text-white">SI</span>
        <span class="hidden flex-col leading-tight sm:flex">
          <span class="font-display text-sm font-semibold text-neutral-900">ProVeMaps</span>
          <span class="text-[10px] text-neutral-500">Simples Internet</span>
        </span>
      </RouterLink>

      <button
        type="button"
        class="ml-2 flex h-8 min-w-0 flex-1 items-center gap-2 rounded-md border border-neutral-200 bg-canvas px-2.5 text-left text-xs text-neutral-500 hover:border-neutral-300 sm:max-w-md"
        title="Busca rápida (Ctrl K)"
        data-testid="header-search"
        @click="paletteOpen = true"
      >
        <PhMagnifyingGlass :size="15" class="shrink-0" />
        <span class="truncate">Buscar site, cabo, dispositivo…</span>
        <kbd class="ml-auto hidden rounded border border-neutral-200 px-1 font-mono text-[10px] sm:inline">Ctrl K</kbd>
      </button>

      <div class="ml-auto flex items-center gap-1">
        <span
          class="hidden items-center gap-1.5 rounded-md px-2 text-[11px] text-neutral-500 md:flex"
          :title="realtime.title"
          data-testid="header-realtime"
        >
          <span class="h-2 w-2 rounded-full" :class="realtime.dot"></span>
          {{ realtime.label }}
        </span>

        <button type="button" class="icon-btn" title="Sistema e servidores" @click="showSystemPanel = true">
          <PhHardDrives :size="18" />
        </button>
        <button
          type="button"
          class="icon-btn"
          title="Reportar problema ou ideia"
          data-testid="nav-reportar"
          @click="showReportar = true"
        >
          <PhMegaphone :size="18" />
        </button>
        <button type="button" class="icon-btn" title="Novidades da versão" @click="showChangelog = true">
          <PhInfo :size="18" />
        </button>
        <button
          type="button"
          class="icon-btn"
          :title="uiStore.theme === 'dark' ? 'Mudar para modo claro' : 'Mudar para modo escuro'"
          data-testid="header-theme"
          @click="uiStore.toggleTheme()"
        >
          <PhSun v-if="uiStore.theme === 'dark'" :size="18" />
          <PhMoon v-else :size="18" />
        </button>

        <div class="relative">
          <button
            type="button"
            class="flex h-8 items-center gap-1.5 rounded-md px-1.5 text-xs text-neutral-700 hover:bg-neutral-100"
            :aria-expanded="openMenu === 'user'"
            title="Conta"
            data-testid="header-user"
            @click="toggleMenu('user')"
          >
            <PhUserCircle :size="20" />
            <span class="hidden max-w-[10rem] truncate lg:inline">{{ userName }}</span>
            <PhCaretDown :size="12" />
          </button>
          <div v-if="openMenu === 'user'" class="dropdown right-0">
            <RouterLink to="/profile" class="dropdown-item"><PhUser :size="15" /> Meu perfil</RouterLink>
            <RouterLink to="/meu-cadastro" class="dropdown-item"><PhIdentificationCard :size="15" /> Meu cadastro</RouterLink>
            <div class="my-1 border-t border-neutral-200"></div>
            <form action="/accounts/logout/" method="post">
              <input type="hidden" name="csrfmiddlewaretoken" :value="csrfToken" />
              <button type="submit" class="dropdown-item w-full text-danger"><PhSignOut :size="15" /> Sair</button>
            </form>
          </div>
        </div>
      </div>
    </div>

    <!-- Linha 2: secções -->
    <nav class="flex h-10 items-stretch gap-1 overflow-x-auto border-t border-neutral-200 px-2 sm:px-3" aria-label="Navegação principal">
      <div v-for="section in sections" :key="section.id" class="relative flex">
        <RouterLink
          v-if="section.items.length === 1"
          :to="section.items[0].path"
          class="tab"
          :class="{ 'tab-active': currentSection === section.id }"
          :data-testid="`nav-${section.id}`"
        >
          <component :is="section.icon" :size="16" />
          {{ section.label }}
        </RouterLink>
        <button
          v-else
          type="button"
          class="tab"
          :class="{ 'tab-active': currentSection === section.id }"
          :aria-expanded="openMenu === section.id"
          :data-testid="`nav-${section.id}`"
          @click="toggleMenu(section.id)"
        >
          <component :is="section.icon" :size="16" />
          {{ section.label }}
          <PhCaretDown :size="11" />
        </button>
      </div>
    </nav>

    <!-- Menus das secções fora do <nav> com overflow, para não serem cortados -->
    <template v-for="section in sections" :key="`menu-${section.id}`">
      <div
        v-if="openMenu === section.id"
        class="dropdown"
        :style="{ left: `${menuLeft}px`, top: '88px' }"
        :data-testid="`menu-${section.id}`"
      >
        <template v-for="item in section.items" :key="item.path">
          <a v-if="item.external" :href="item.path" class="dropdown-item">
            <component :is="item.icon" :size="15" /> {{ item.label }}
          </a>
          <RouterLink
            v-else
            :to="item.path"
            class="dropdown-item"
            :class="{ 'dropdown-item-active': isPathActive(route.path, item.path) }"
          >
            <component :is="item.icon" :size="15" /> {{ item.label }}
          </RouterLink>
        </template>
      </div>
    </template>

    <CommandPalette v-model:open="paletteOpen" />
    <ChangelogModal
      :show="showChangelog"
      @close="showChangelog = false"
      @reportar="showChangelog = false; showReportar = true"
    />
    <ReportarModal :show="showReportar" @close="showReportar = false" />
    <SystemPanel :show="showSystemPanel" @close="showSystemPanel = false" />
  </header>
</template>

<script setup>
/**
 * Shell da aplicação — cabeçalho de duas linhas, sem menu lateral
 * (ADR 0007 Fase 2, EV-0044). Substitui o antigo `TheNavMenu.vue`.
 */
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue';
import { useRoute, RouterLink } from 'vue-router';
import {
  PhMagnifyingGlass,
  PhHardDrives,
  PhMegaphone,
  PhInfo,
  PhSun,
  PhMoon,
  PhUserCircle,
  PhUser,
  PhIdentificationCard,
  PhSignOut,
  PhCaretDown,
} from '@phosphor-icons/vue';
import { useUiStore } from '@/stores/ui';
import { useCurrentUser } from '@/composables/useCurrentUser';
import { useWebSocket } from '@/composables/useWebSocket';
import { dashboardWsUrl } from '@/composables/useRealtimeStatus';
import { NAV_SECTIONS, activeSectionId, isPathActive } from '@/composables/useNavSections';
import CommandPalette from './CommandPalette.vue';
import ChangelogModal from './ChangelogModal.vue';
import SystemPanel from './SystemPanel.vue';
import ReportarModal from '@/components/Evolucao/ReportarModal.vue';

const sections = NAV_SECTIONS;
const uiStore = useUiStore();
const route = useRoute();
const { user, load: loadUser } = useCurrentUser();

const rootEl = ref(null);
const openMenu = ref(null);
const menuLeft = ref(0);
const paletteOpen = ref(false);
const showChangelog = ref(false);
const showReportar = ref(false);
const showSystemPanel = ref(false);
const csrfToken = ref(window.CSRF_TOKEN || '');

const currentSection = computed(() => activeSectionId(route.path));

const userName = computed(() => {
  const u = user.value;
  if (!u) return 'Conta';
  const full = [u.first_name, u.last_name].filter(Boolean).join(' ');
  return full || u.username || 'Conta';
});

// Indicador do canal em tempo real (o mesmo socket que o mapa usa).
const { connected, connecting } = useWebSocket(dashboardWsUrl(), { maxReconnectAttempts: Infinity });
const realtime = computed(() => {
  if (connected.value) {
    return { label: 'Tempo real', dot: 'bg-success', title: 'Canal em tempo real ligado' };
  }
  if (connecting.value) {
    return { label: 'Conectando', dot: 'bg-warning', title: 'A ligar ao canal em tempo real' };
  }
  return { label: 'Desconectado', dot: 'bg-danger', title: 'Sem canal em tempo real; os dados podem estar atrasados' };
});

function toggleMenu(id) {
  if (openMenu.value === id) {
    openMenu.value = null;
    return;
  }
  if (id !== 'user' && rootEl.value) {
    const btn = rootEl.value.querySelector(`[data-testid="nav-${id}"]`);
    const headerBox = rootEl.value.getBoundingClientRect();
    menuLeft.value = btn ? btn.getBoundingClientRect().left - headerBox.left : 0;
  }
  openMenu.value = id;
}

function onDocumentClick(event) {
  if (!openMenu.value) return;
  const target = event.target;
  const insideTrigger = target.closest?.('[aria-expanded]');
  const insideMenu = target.closest?.('.dropdown');
  if (!insideTrigger && !insideMenu) openMenu.value = null;
}

function onKeydown(event) {
  if (event.key === 'Escape') openMenu.value = null;
}

watch(() => route.fullPath, () => {
  openMenu.value = null;
});

onMounted(() => {
  loadUser();
  document.addEventListener('click', onDocumentClick);
  document.addEventListener('keydown', onKeydown);
});

onBeforeUnmount(() => {
  document.removeEventListener('click', onDocumentClick);
  document.removeEventListener('keydown', onKeydown);
});
</script>

<style scoped>
.icon-btn {
  display: flex;
  height: 2rem;
  width: 2rem;
  align-items: center;
  justify-content: center;
  border-radius: 0.375rem;
  color: rgb(var(--n-500));
}
.icon-btn:hover {
  background: rgb(var(--n-100));
  color: rgb(var(--n-800));
}
.tab {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  white-space: nowrap;
  border-bottom: 2px solid transparent;
  padding: 0 0.625rem;
  font-size: 0.8125rem;
  font-weight: 500;
  color: rgb(var(--n-600));
}
.tab:hover {
  color: rgb(var(--n-900));
}
.tab-active {
  border-bottom-color: rgb(var(--primary-500));
  color: rgb(var(--n-900));
}
.dropdown {
  position: absolute;
  z-index: 1001;
  margin-top: 0.25rem;
  min-width: 13rem;
  border-radius: 0.5rem;
  border: 1px solid rgb(var(--n-200));
  background: rgb(var(--surface));
  padding: 0.25rem 0;
  box-shadow: 0 10px 25px -5px rgb(0 0 0 / 0.2);
}
.dropdown-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.75rem;
  font-size: 0.8125rem;
  color: rgb(var(--n-700));
}
.dropdown-item:hover {
  background: rgb(var(--n-100));
  color: rgb(var(--n-900));
}
.dropdown-item-active {
  color: rgb(var(--primary-700));
  font-weight: 600;
}
:global(.dark) .dropdown-item-active {
  color: rgb(var(--primary-400));
}
</style>
