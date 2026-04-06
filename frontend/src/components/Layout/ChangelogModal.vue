<template>
  <Teleport to="body">
    <div v-if="show" class="cl-overlay" @click.self="$emit('close')">
      <div class="cl-modal">

        <!-- Header -->
        <div class="cl-header">
          <div class="cl-header-left">
            <span class="cl-version-badge">v{{ latestVersion }}</span>
            <div>
              <h2 class="cl-title">ProVeMaps Beta</h2>
              <p class="cl-subtitle">Histórico de versões e novidades</p>
            </div>
          </div>
          <button class="cl-close" @click="$emit('close')">
            <PhX :size="20" weight="bold" />
          </button>
        </div>

        <!-- Tabs -->
        <div class="cl-tabs">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            class="cl-tab"
            :class="{ active: activeTab === tab.id }"
            @click="activeTab = tab.id"
          >
            <component :is="tab.icon" :size="16" weight="regular" />
            {{ tab.label }}
          </button>
        </div>

        <!-- Tab: Changelog -->
        <div v-if="activeTab === 'changelog'" class="cl-body">
          <div v-for="entry in changelog" :key="entry.version" class="cl-entry">
            <div class="cl-entry-header">
              <span class="cl-entry-version">v{{ entry.version }}</span>
              <span class="cl-entry-date">{{ entry.date }}</span>
              <span v-if="entry.latest" class="cl-latest-badge">Atual</span>
            </div>

            <!-- Novas funcionalidades -->
            <div v-if="entry.features?.length" class="cl-section">
              <div class="cl-section-title feature">
                <PhStar :size="13" weight="fill" /> Novas Funcionalidades
              </div>
              <ul class="cl-list">
                <li v-for="(item, i) in entry.features" :key="i" class="cl-item feature">
                  <span class="cl-dot feature"></span>
                  {{ item }}
                </li>
              </ul>
            </div>

            <!-- Melhorias -->
            <div v-if="entry.improvements?.length" class="cl-section">
              <div class="cl-section-title improvement">
                <PhArrowsClockwise :size="13" weight="fill" /> Melhorias
              </div>
              <ul class="cl-list">
                <li v-for="(item, i) in entry.improvements" :key="i" class="cl-item improvement">
                  <span class="cl-dot improvement"></span>
                  {{ item }}
                </li>
              </ul>
            </div>

            <!-- Correções -->
            <div v-if="entry.fixes?.length" class="cl-section">
              <div class="cl-section-title fix">
                <PhBug :size="13" weight="fill" /> Correções de Bug
              </div>
              <ul class="cl-list">
                <li v-for="(item, i) in entry.fixes" :key="i" class="cl-item fix">
                  <span class="cl-dot fix"></span>
                  {{ item }}
                </li>
              </ul>
            </div>
          </div>
        </div>

        <!-- Tab: Sugestões -->
        <div v-if="activeTab === 'suggestions'" class="cl-body">
          <div v-if="submitted" class="cl-success">
            <PhCheckCircle :size="48" weight="duotone" class="cl-success-icon" />
            <h3>Obrigado pelo feedback!</h3>
            <p>Sua sugestão foi registrada e será analisada pela equipe.</p>
            <button class="cl-btn-primary" @click="resetForm">Enviar outra</button>
          </div>

          <form v-else class="cl-form" @submit.prevent="submitSuggestion">
            <p class="cl-form-intro">
              Encontrou um bug ou tem uma ideia para melhorar o sistema? Nos conte!
            </p>

            <div class="cl-field">
              <label class="cl-label">Tipo</label>
              <div class="cl-type-group">
                <button
                  v-for="t in types"
                  :key="t.id"
                  type="button"
                  class="cl-type-btn"
                  :class="{ active: form.type === t.id }"
                  @click="form.type = t.id"
                >
                  <component :is="t.icon" :size="15" weight="fill" />
                  {{ t.label }}
                </button>
              </div>
            </div>

            <div class="cl-field">
              <label class="cl-label">Título <span class="cl-required">*</span></label>
              <input
                v-model="form.title"
                class="cl-input"
                placeholder="Resumo em uma linha..."
                maxlength="120"
                required
              />
            </div>

            <div class="cl-field">
              <label class="cl-label">Descrição <span class="cl-required">*</span></label>
              <textarea
                v-model="form.description"
                class="cl-textarea"
                placeholder="Descreva com detalhes o que aconteceu ou o que gostaria de ver..."
                rows="5"
                required
              ></textarea>
              <span class="cl-char-count">{{ form.description.length }} / 1000</span>
            </div>

            <div class="cl-field">
              <label class="cl-label">Seu nome (opcional)</label>
              <input v-model="form.author" class="cl-input" placeholder="Ex: João Silva" maxlength="80" />
            </div>

            <div class="cl-form-footer">
              <button type="submit" class="cl-btn-primary" :disabled="submitting">
                <PhPaperPlaneTilt v-if="!submitting" :size="16" weight="fill" />
                <span v-if="submitting" class="cl-spinner"></span>
                {{ submitting ? 'Enviando…' : 'Enviar Feedback' }}
              </button>
            </div>
          </form>
        </div>

      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed } from 'vue';
import {
  PhX, PhStar, PhBug, PhArrowsClockwise, PhCheckCircle,
  PhPaperPlaneTilt, PhListBullets, PhChatText, PhWarning, PhLightbulb,
} from '@phosphor-icons/vue';

defineProps({ show: Boolean });
defineEmits(['close']);

const activeTab = ref('changelog');

const tabs = [
  { id: 'changelog', label: 'Changelog', icon: PhListBullets },
  { id: 'suggestions', label: 'Sugestões & Bugs', icon: PhChatText },
];

// ── Dados do changelog ──────────────────────────────────────────────────────
const changelog = [
  {
    version: '1.4.2',
    date: '06 Abr 2026',
    latest: true,
    features: [],
    improvements: [
      'Botão "Reenquadrar" no mapa do backbone para ajustar a visão a todos os itens visíveis',
      '"Selecionar todos" no painel lateral reenquadra automaticamente o mapa',
    ],
    fixes: [
      'Coordenadas padrão do mapa (lat/lng em Setup > Mapas) não persistiam após salvar — .env sobrescrevia o valor do banco',
      'Mapa do Network Design agora respeita a localização inicial configurada em Setup > Mapas',
      'Modal de localização do site (importação de dispositivos) usa o provider configurado (Mapbox/Google)',
      'Importação de rotas KML bloqueada incorretamente quando diagnósticos estavam desabilitados',
      'Network Design inicializa mapa com Mapbox sem aguardar Google Maps API',
      'Botão "Verificar atualizações" chamava API do GitHub pelo servidor (sem internet no container) — movido para o browser',
      'Mapa do backbone não reenquadrava automaticamente ao selecionar itens após carga inicial',
    ],
  },
  {
    version: '1.4.1',
    date: '03 Abr 2026',
    latest: false,
    features: [],
    improvements: [
      'Paleta de cores do menu unificada com as páginas — removido tom azul-escuro',
      'Status WebSocket exibido como ícone compacto colorido no rodapé do menu',
      'Todas as cores do menu migradas para variáveis CSS do design system',
    ],
    fixes: [],
  },
  {
    version: '1.4.0',
    date: '03 Abr 2026',
    latest: false,
    features: [
      'Importação em lote de dispositivos com configurações comuns',
      'Regra de proximidade 100m: evita criação de sites duplicados',
      'Overlay de progresso durante importação em lote',
      'Modal de Changelog e Sugestões',
    ],
    improvements: [
      'Menu lateral reorganizado — Admin e Docs movidos para dentro de System',
      'Botão "Salvar Device" agora salva site, categoria e alertas além das chaves Zabbix',
      'Ícones compactos para Tema e Sair no rodapé do menu',
      'Site opcional no modo batch — cada device mantém seu local original',
    ],
    fixes: [
      'Importação de múltiplos devices ignorava os itens selecionados',
      'Validação de nome de device rejeitava espaços e hífens',
      'PATCH /api/v1/devices/<id>/ retornava 400 por campos CharField com valor null',
      'Rota de PATCH não existia — endpoint era apenas DELETE',
    ],
  },
  {
    version: '1.3.0',
    date: '28 Mar 2026',
    features: [
      'Gráficos de tráfego IN/OUT na aba de tráfego do FiberCableDetailModal',
      'Exportação de gráficos em PNG e PDF no modal de cabo e de porta',
      'Exportação combinada (tráfego + sinal óptico) em arquivo único',
    ],
    improvements: [
      'Performance: carregamento paralelo de dados no DeviceDetailsModal e PortTrafficModal',
      'Modal de device mais estreito e proporcionado',
      'Badges de sinal óptico sem quebra de linha (nowrap)',
      'PortTrafficModal 10% mais largo',
    ],
    fixes: [
      'Triple-nextTick causava atraso de 400ms+ no PortTrafficModal',
      'Canvas do gráfico de tráfego não encontrado na primeira carga',
    ],
  },
  {
    version: '1.2.0',
    date: '15 Mar 2026',
    features: [
      'Painel de detalhes de cabo com preview (Fase 1.3 Network Design)',
      'Tips FAB com lógica reativa Vue',
      'ResizeObserver no mapa para notificar providers ao redimensionar',
    ],
    improvements: [
      'Lazy-load de providers de mapa (Google Maps e Mapbox)',
    ],
    fixes: [
      'Overlays acima de modais Vue usam vanilla JS + body.appendChild',
    ],
  },
];

const latestVersion = computed(() => changelog[0].version);

// ── Formulário de sugestões ─────────────────────────────────────────────────
const types = [
  { id: 'bug',         label: 'Bug',        icon: PhBug },
  { id: 'feature',     label: 'Funcionalidade', icon: PhLightbulb },
  { id: 'improvement', label: 'Melhoria',   icon: PhArrowsClockwise },
  { id: 'other',       label: 'Outro',      icon: PhWarning },
];

const form = ref({ type: 'bug', title: '', description: '', author: '' });
const submitting = ref(false);
const submitted = ref(false);

const submitSuggestion = async () => {
  submitting.value = true;
  // Simula envio (pode integrar com API real futuramente)
  await new Promise(r => setTimeout(r, 800));
  submitting.value = false;
  submitted.value = true;
};

const resetForm = () => {
  form.value = { type: 'bug', title: '', description: '', author: '' };
  submitted.value = false;
};
</script>

<style scoped>
.cl-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(0,0,0,0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.cl-modal {
  background: var(--surface-primary, #1e2433);
  border: 1px solid var(--border-primary, #2d3748);
  border-radius: 16px;
  width: 100%;
  max-width: 580px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 24px 64px rgba(0,0,0,0.5);
  overflow: hidden;
}

/* Header */
.cl-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px 16px;
  border-bottom: 1px solid var(--border-primary, #2d3748);
  gap: 12px;
}
.cl-header-left { display: flex; align-items: center; gap: 14px; }
.cl-version-badge {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 20px;
  letter-spacing: 0.5px;
  white-space: nowrap;
}
.cl-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary, #f1f5f9);
  margin: 0;
}
.cl-subtitle {
  font-size: 12px;
  color: var(--text-tertiary, #94a3b8);
  margin: 2px 0 0;
}
.cl-close {
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--text-tertiary, #94a3b8);
  padding: 6px;
  border-radius: 8px;
  display: flex;
  transition: background 0.15s, color 0.15s;
}
.cl-close:hover { background: var(--surface-muted, #2d3748); color: var(--text-primary, #f1f5f9); }

/* Tabs */
.cl-tabs {
  display: flex;
  gap: 4px;
  padding: 12px 24px 0;
  border-bottom: 1px solid var(--border-primary, #2d3748);
}
.cl-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-tertiary, #94a3b8);
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;
  margin-bottom: -1px;
}
.cl-tab:hover { color: var(--text-primary, #f1f5f9); }
.cl-tab.active { color: #6366f1; border-bottom-color: #6366f1; }

/* Body */
.cl-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* Changelog entry */
.cl-entry {
  border: 1px solid var(--border-primary, #2d3748);
  border-radius: 12px;
  padding: 16px;
  background: var(--surface-secondary, #161b27);
}
.cl-entry-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}
.cl-entry-version {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary, #f1f5f9);
}
.cl-entry-date {
  font-size: 12px;
  color: var(--text-tertiary, #94a3b8);
  flex: 1;
}
.cl-latest-badge {
  background: rgba(99,102,241,0.15);
  color: #818cf8;
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 20px;
  border: 1px solid rgba(99,102,241,0.3);
}

/* Sections */
.cl-section { margin-bottom: 12px; }
.cl-section:last-child { margin-bottom: 0; }
.cl-section-title {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  margin-bottom: 6px;
}
.cl-section-title.feature  { color: #34d399; }
.cl-section-title.improvement { color: #60a5fa; }
.cl-section-title.fix     { color: #f87171; }

.cl-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
.cl-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 13px;
  color: var(--text-secondary, #cbd5e1);
  line-height: 1.5;
}
.cl-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  margin-top: 5px;
  flex-shrink: 0;
}
.cl-dot.feature    { background: #34d399; }
.cl-dot.improvement { background: #60a5fa; }
.cl-dot.fix        { background: #f87171; }

/* Form */
.cl-form-intro {
  font-size: 13px;
  color: var(--text-secondary, #cbd5e1);
  margin: 0 0 16px;
}
.cl-form { display: flex; flex-direction: column; gap: 16px; }
.cl-field { display: flex; flex-direction: column; gap: 6px; }
.cl-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary, #cbd5e1);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.cl-required { color: #f87171; }

.cl-type-group { display: flex; gap: 8px; flex-wrap: wrap; }
.cl-type-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 500;
  border-radius: 20px;
  border: 1px solid var(--border-primary, #2d3748);
  background: transparent;
  color: var(--text-secondary, #cbd5e1);
  cursor: pointer;
  transition: all 0.15s;
}
.cl-type-btn:hover { border-color: #6366f1; color: #818cf8; }
.cl-type-btn.active { background: rgba(99,102,241,0.15); border-color: #6366f1; color: #818cf8; }

.cl-input, .cl-textarea {
  background: var(--surface-secondary, #161b27);
  border: 1px solid var(--border-primary, #2d3748);
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 13px;
  color: var(--text-primary, #f1f5f9);
  outline: none;
  transition: border-color 0.15s;
  font-family: inherit;
  resize: vertical;
}
.cl-input:focus, .cl-textarea:focus { border-color: #6366f1; }
.cl-textarea { min-height: 100px; }
.cl-char-count { font-size: 11px; color: var(--text-tertiary, #94a3b8); text-align: right; }

.cl-form-footer { display: flex; justify-content: flex-end; }
.cl-btn-primary {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 10px 20px;
  background: #6366f1;
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
}
.cl-btn-primary:hover:not(:disabled) { background: #4f46e5; }
.cl-btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }

.cl-spinner {
  width: 14px; height: 14px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Success */
.cl-success {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 12px;
  padding: 32px 0;
}
.cl-success-icon { color: #34d399; }
.cl-success h3 { font-size: 18px; font-weight: 700; color: var(--text-primary, #f1f5f9); margin: 0; }
.cl-success p  { font-size: 13px; color: var(--text-secondary, #cbd5e1); margin: 0; }
</style>
