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
    version: '1.4.13.2',
    date: '03 Mai 2026',
    latest: true,
    features: [],
    improvements: [],
    fixes: [
      'Botão "Atualizar agora" do popup óptico retornava HTTP 405. O handler de refresh chamava internamente a view de cached-status (que tem @require_GET), e esse decorator bloqueava o POST original. Refatorado extraindo o builder de payload em uma função pura que ambos endpoints reusam.',
    ],
  },
  {
    version: '1.4.13.1',
    date: '03 Mai 2026',
    latest: false,
    features: [
      'Botão "Atualizar agora" no popup óptico do mapa: força leitura em tempo real do Zabbix (POST /api/v1/inventory/fibers/{id}/refresh-optical/) e atualiza o cache em uma única chamada batch — útil quando você quer ver IMEDIATAMENTE se um enlace voltou.',
    ],
    improvements: [
      'Coleta de níveis ópticos refatorada para batch: agora é 1 chamada Zabbix por device em vez de 1 por porta. Intervalo da task reduzido de 5 min → 1 min sem aumentar carga no Zabbix.',
      'Popup óptico mostra "Atualizado há Xs/min" para transparência da freshness dos dados.',
    ],
    fixes: [
      'Delay perceptível na detecção de normalização: tráfego subia rápido mas níveis RX/TX demoravam até 5 min para refletir. Agora atualiza em até ~60s.',
    ],
  },
  {
    version: '1.4.13.0',
    date: '03 Mai 2026',
    latest: false,
    features: [
      'Email automático no dispatcher: notificações de cabo agora vão também por e-mail (HTML formatado com tabela de Origem/Destino) quando o canal está habilitado na config.',
      'Snooze por config: botão "Silenciar" 🔕 em cada card de alarme (1h/4h/24h/7d/personalizado). Badge "🔕 Silenciado até HH:MM" aparece no header e botão "Retomar" cancela. Útil para manutenção planejada — não inunda WhatsApp dos responsáveis.',
      'Métricas Prometheus: novo counter provemaps_alarm_notifications_total{channel,status,alert_type} permite gráficos no Grafana de notificações enviadas/falhas por canal e tipo de evento.',
    ],
    improvements: [
      'Retry inteligente: se o gateway WhatsApp/SMTP estiver offline temporariamente, o dispatcher tenta de novo automaticamente com backoff exponencial (1, 2, 4, 8, 16 min — máx 5 tentativas). Após sucesso de 1 destinatário, considera processado. Evita inundar logs e dá tempo ao gateway recuperar.',
      'Janela de scan ampliada de 10 para 30 min para cobrir o pior caso de retry.',
    ],
    fixes: [],
  },
  {
    version: '1.4.12.0',
    date: '03 Mai 2026',
    latest: false,
    features: [
      'Histórico de Avisos no modal de alarmes (Fase C): nova seção colapsável mostra os últimos 50 envios para o cabo — automáticos do dispatcher e manuais (Enviar Teste). Cada item traz: ícone do tipo (🚨 rompimento / ⚠️ atenuação / ✅ normalização), timestamp, canal, destinatário, status (✓ enviado / ✗ falhou + mensagem de erro), tag TESTE quando manual. Atualização automática após enviar teste.',
    ],
    improvements: [],
    fixes: [],
  },
  {
    version: '1.4.11.0',
    date: '03 Mai 2026',
    latest: false,
    features: [
      'Avisos automáticos de cabo (Fase A): Celery beat a cada 1 min lê FiberEvents novos, classifica a transição (up→down=rompimento, up→degraded=atenuação, down/degraded→up=normalização) e dispara WhatsApp para todos os FiberCableAlarmConfig que correspondem ao tipo de evento. Inclui dedupe via FiberAlarmNotificationLog (mesmo evento nunca é notificado 2x) e respeita persist_minutes (eventos curtos demais são ignorados). Agora quando o técnico restabelece o serviço, os responsáveis recebem aviso de normalização sem ação manual.',
    ],
    improvements: [],
    fixes: [],
  },
  {
    version: '1.4.10.3',
    date: '03 Mai 2026',
    latest: false,
    features: [],
    improvements: [
      'Mensagem do alerta de manutenção é opcional: em branco, usa "ENLACE OFF." como default. O bloco de Cabos com Origem/Destino é sempre enviado, então o técnico já recebe tudo que precisa sem o operador digitar nada — basta selecionar destinatários e clicar Enviar.',
    ],
    fixes: [],
  },
  {
    version: '1.4.10.2',
    date: '03 Mai 2026',
    latest: false,
    features: [
      'Modal Notificar Responsáveis: nova aba "Contatos da agenda" — permite enviar avisos para contatos cadastrados em Setup > Contatos via WhatsApp/Email, sem precisar transformá-los em usuários do sistema. type_label mostra empresa ou primeiro grupo do contato.',
    ],
    improvements: [],
    fixes: [],
  },
  {
    version: '1.4.10.1',
    date: '03 Mai 2026',
    latest: false,
    features: [],
    improvements: [
      'Alerta de Manutenção (WhatsApp + Email): cada cabo afetado agora vem com Origem/Destino completos — Device + Porta + Site. Substitui o "Equipamentos: —" pelo endpoint físico real (ex: "Huawei - Switch Vila Mandi / XGigabitEthernet0/0/1 (SITE - VILA MANDI)"). Técnico identifica onde verificar sem abrir o sistema.',
    ],
    fixes: [],
  },
  {
    version: '1.4.10.0',
    date: '03 Mai 2026',
    latest: false,
    features: [
      'Botão "Enviar Teste" nas configurações de alarme de cabo: dispara WhatsApp real para os destinatários (qualquer target — contato/grupo/usuário/departamento) sem precisar esperar um evento óptico. Mensagem com prefixo [TESTE] e detalhes da config. Resultado inline (sucesso/parcial/falha por destinatário).',
    ],
    improvements: [],
    fixes: [],
  },
  {
    version: '1.4.9.13',
    date: '03 Mai 2026',
    latest: false,
    features: [],
    improvements: [
      'PortTrafficModal abre com seções "Tráfego" e "Óptico" colapsadas por padrão — modal aparece instantâneo. Dados pré-carregam em background; ao expandir uma seção, o gráfico renderiza com cache (sem nova requisição).',
    ],
    fixes: [],
  },
  {
    version: '1.4.9.12',
    date: '03 Mai 2026',
    latest: false,
    features: [],
    improvements: [],
    fixes: [
      'Gráfico de tráfego não carregava após PortTrafficModal virar lazy-loaded — watcher de props.isOpen agora roda com immediate:true. Mesmo bug que tivemos com SiteDetailsModal (v-if + defineAsyncComponent monta o componente já com isOpen=true).',
    ],
  },
  {
    version: '1.4.9.11',
    date: '03 Mai 2026',
    latest: false,
    features: [],
    improvements: [
      'PortTrafficModal abre instantâneo: Chart.js (430 KB) agora é chunk dinâmico — só baixa quando o gráfico vai renderizar pela primeira vez',
      'AlarmConfigModal e PortTrafficModal viraram defineAsyncComponent — bundle do SiteDetailsModal caiu de 175 KB para 135 KB',
      'Computeds duplicados de "última atividade" unificados em um — antes iteravam o histórico 2x a cada acesso reativo',
    ],
    fixes: [],
  },
  {
    version: '1.4.9.10',
    date: '03 Mai 2026',
    latest: false,
    features: [],
    improvements: [
      'Pin de device offline agora é amarelo (atenção) em vez de cinza — atende o pedido original. Cinza foi removido da paleta porque era pouco visível em mapas claros e não comunicava urgência.',
    ],
    fixes: [],
  },
  {
    version: '1.4.9.9',
    date: '03 Mai 2026',
    latest: false,
    features: [],
    improvements: [],
    fixes: [
      'Backend: hosts_status promove availability=2→1 quando uptime via SNMP > 0. Resolve caso onde Zabbix marca o host como offline (ICMP/agent falham) mas o device responde via SNMP. Mapa e modal agora usam a mesma fonte de verdade.',
    ],
  },
  {
    version: '1.4.9.8',
    date: '03 Mai 2026',
    latest: false,
    features: [],
    improvements: [],
    fixes: [
      'Pin ficava cinza para devices online quando o Zabbix retornava availability inconclusiva (unknown). Agora unknown é presumido online (verde) — só fica cinza quando o Zabbix confirma offline (avail=2). Resolve divergência entre modal (mostrava ONLINE) e mapa (pin cinza).',
    ],
  },
  {
    version: '1.4.9.7',
    date: '03 Mai 2026',
    latest: false,
    features: [
      'Pin do mapa reflete agregado do site: device offline com pelo menos um irmão online vira amarelo (atenção). Site totalmente offline mantém cinza.',
    ],
    improvements: [],
    fixes: [],
  },
  {
    version: '1.4.9.6',
    date: '03 Mai 2026',
    latest: false,
    features: [
      'PortTrafficModal: indicador "Última atividade: há X tempo" no header (verde se recente, vermelho se >5 min) — facilita identificar quando um incidente aconteceu',
    ],
    improvements: [
      'Tráfego e óptico desacoplados: porta offline com timeout no tráfego ainda mostra histórico óptico (RX/TX) para diagnosticar quando a luz caiu',
      'Timeout de 20s no fetch de tráfego — sai do estado loading com mensagem clara em vez de ficar travado',
      'Empty state quando o histórico está vazio (sugere tentar período maior)',
    ],
    fixes: [],
  },
  {
    version: '1.4.9.5',
    date: '03 Mai 2026',
    latest: false,
    features: [],
    improvements: [
      'PortTrafficModal abre instantâneo: decimação client-side limita Chart.js a 800 pontos (era até 2152) preservando forma do gráfico',
      'Dedup de fetch óptico: watch(props.isOpen) e watch(opticalChartCanvas) compartilham a mesma promise — uma única requisição',
    ],
    fixes: [],
  },
  {
    version: '1.4.9.4',
    date: '03 Mai 2026',
    latest: false,
    features: [],
    improvements: [],
    fixes: [
      'Gráfico óptico no PortTrafficModal não renderizava: canvas ficava indisponível na 1ª tentativa por delay de Transition+Teleport. Helper _waitForCanvas espera até 30 frames (≈500ms)',
      'Cache de dados ópticos: se busca completa antes do canvas montar, o watcher re-renderiza sem nova requisição',
      'Mesmo padrão aplicado ao gráfico de tráfego (substituiu setTimeout 200ms)',
    ],
  },
  {
    version: '1.4.9.3',
    date: '03 Mai 2026',
    latest: false,
    features: [],
    improvements: [],
    fixes: [
      'Mapa Mapbox era inicializado 2x em paralelo (watcher do provider + onMounted) — overlays não apareciam por race condition. Watcher agora ignora a primeira inicialização',
      'renderOverlays usa listeners defensivos (load + idle + styledata) — cobre caso em que o evento load já foi emitido antes do listener ser registrado',
    ],
  },
  {
    version: '1.4.9.2',
    date: '03 Mai 2026',
    latest: false,
    features: [],
    improvements: [],
    fixes: [
      'Mapa carregava sem markers nem cabos: guard isMapReady evita que o polling do Zabbix dispare addSource/addLayer no Mapbox antes do evento load (exception silenciosa que deixava o mapa em branco)',
    ],
  },
  {
    version: '1.4.9.1',
    date: '03 Mai 2026',
    latest: false,
    features: [],
    improvements: [],
    fixes: [
      'Modais (Site, Cabo, Tooltip Óptico, Notificação) abriam vazios após o lazy-load — watchers agora rodam com immediate:true',
      'Mapa carregava em branco e exigia F5 — substituído setTimeout(500ms) pelo evento load do Mapbox (determinístico independente da latência)',
    ],
  },
  {
    version: '1.4.9.0',
    date: '03 Mai 2026',
    latest: false,
    features: [
      'Endpoint agregado /maps_view/api/backbone/init/: 6 requests do mapa viraram 1',
      'Endpoint batch /api/v1/devices/metrics-batch/?ids=...: métricas de N devices em 1 chamada',
    ],
    improvements: [
      'Mapa /monitoring/backbone/map carrega ~3x mais rápido — inventário, system-config e metadados disparados em paralelo',
      'Bundle inicial reduzido em ~500 kB: SiteDetailsModal, FiberCableDetailModal, MapInventoryPanel viraram chunks lazy',
      'Modais carregam só ao primeiro abrir; tabs do modal de cabo (Óptico/Tráfego/Alarmes/Histórico) montam só quando ativadas',
      'WebSocket /ws/dashboard/status/ singleton: 1 conexão compartilhada em vez de uma por modal aberto',
      'Polling Zabbix (10s) agora redesenha o mapa só quando algum status realmente muda',
      'SiteDetailsModal filtra devices server-side (?site=ID) em vez de baixar todos',
    ],
    fixes: [],
  },
  {
    version: '1.4.8.5',
    date: '08 Abr 2026',
    latest: false,
    features: [
      'Botão "Ver Detalhes do Cabo" abre diretamente o modal completo com abas (Nível Óptico, Tráfego, Alarmes, Histórico)',
    ],
    improvements: [],
    fixes: [
      'Modal pequeno intermediário não aparece mais ao clicar em Ver Detalhes',
    ],
  },
  {
    version: '1.4.8.4',
    date: '08 Abr 2026',
    latest: false,
    features: [
      'Painel óptico exibe botão "Ver Detalhes do Cabo" que abre o modal completo — sem precisar de duplo clique',
    ],
    improvements: [
      'Interação com cabos simplificada: clique abre o painel óptico, botão dentro do painel abre os detalhes',
    ],
    fixes: [],
  },
  {
    version: '1.4.8.3',
    date: '08 Abr 2026',
    latest: false,
    features: [
      'Clique simples no cabo abre o painel de sinal óptico — funciona em mobile (sem precisar de hover)',
      'Painel óptico arrastável pelo cabeçalho, com botão Fechar — não fecha automaticamente ao mover o mouse',
    ],
    improvements: [
      'Comportamento de interação com cabos unificado entre desktop (hover + clique) e mobile (apenas clique)',
    ],
    fixes: [],
  },
  {
    version: '1.4.8.2',
    date: '08 Abr 2026',
    latest: false,
    features: [
      'Modal de cabo flutuante e arrastável: sem overlay que bloqueia o mapa — arraste pelo cabeçalho para reposicionar',
      'Modal centralizado automaticamente no mapa ao abrir (mobile e desktop)',
    ],
    improvements: [
      'Mapa permanece interativo com o modal aberto — sem backdrop escuro bloqueante',
      'Grip visual (⠿) no header indica que o modal é arrastável',
      'Responsivo em mobile: em telas ≤520px o modal ocupa toda a largura com layout de 2 colunas',
      'Status DEGRADADO adicionado ao modal (além de ONLINE, INOPERANTE, CRÍTICO)',
    ],
    fixes: [
      'Modal não respondia adequadamente a telas pequenas de celular/tablet',
    ],
  },
  {
    version: '1.4.8.1',
    date: '08 Abr 2026',
    latest: false,
    features: [
      'Limites de sinal óptico por categoria de distância: SFP LR (≤10km), ER (≤40km), ZR (≤80km) e DWDM/EZR (>80km)',
      'Cabos coloridos no mapa conforme nível real de sinal: verde (ok), âmbar (atenção), vermelho (crítico)',
      'Comprimento do cabo detectado automaticamente pelo traçado no mapa para identificar categoria SFP',
    ],
    improvements: [
      'Configuração de limites ópticos expandida em Servidores de Monitoramento: tabela por distância com atenção e crítico individuais',
      'Sinal nulo ou zero classificado como crítico automaticamente (sem sinal = fibra rompida ou SFP desconectado)',
      'Versionamento intra-dia: 1.X.Y.Z para múltiplos ciclos no mesmo dia',
    ],
    fixes: [
      'Cabos ficavam verdes mesmo com sinal degradado (limiar -50 dBm era permissivo demais — corrigido para padrões industriais)',
      'Todos os cabos no mapa apareciam cinza (status up/down/degraded não mapeados para cores)',
    ],
  },
  {
    version: '1.4.8',
    date: '08 Abr 2026',
    latest: false,
    features: [
      'Backup inclui fernet_key no config.json — restore em qualquer ambiente descriptografa dados automaticamente',
      'Suporte a backup sem senha: ZIP padrão quando nenhuma senha está configurada',
      'Restore lê fernet_key do config.json e atualiza database/fernet.key antes de reiniciar',
    ],
    improvements: [
      'pg_restore com --if-exists, --no-owner e --no-privileges — elimina falsos erros em banco limpo',
      'Restore de ZIP sem criptografia usa zipfile nativo (sem dependência do pyzipper)',
      'Resposta do backup inclui campo encrypted para indicar se o arquivo está protegido',
      'Versionamento por dia: uma versão por dia de trabalho, não por alteração',
    ],
    fixes: [
      'Restore retornava 500 mesmo quando pg_restore concluía com sucesso (exit status 1 era warnings, não erros)',
      'Restore de ZIP falhava quando backup foi criado sem senha (tentava abrir com pyzipper AES)',
      'Após restore em ambiente local, tokens Mapbox, Zabbix e demais campos criptografados ficavam ilegíveis',
    ],
  },
  {
    version: '1.4.7',
    date: '07 Abr 2026',
    latest: false,
    features: [],
    improvements: [],
    fixes: [
      'Botão "Atualizar agora" não reportava mais erros falsos: git pull dentro do container é não-crítico (código baked na imagem)',
      'Avisos de arquivo duplicado do collectstatic tratados como warning, não como erro — progresso conclui com sucesso',
      'Ícone âmbar (⚠) para etapas com aviso; apenas falhas reais marcam a atualização como erro',
    ],
  },
  {
    version: '1.4.6',
    date: '07 Abr 2026',
    latest: false,
    features: [
      'Script update.sh — atualização automática com 4 passos: git pull, npm build, rebuild dos containers e health check',
    ],
    improvements: [
      'update.sh sempre reconstrói web + celery + beat, garantindo que backend Python e frontend estejam sempre sincronizados',
      'Script segue o mesmo padrão visual do install_ubuntu.sh: spinner, cores, log em /var/log/provemaps_update.log',
      'Exibe versão antes e depois da atualização',
    ],
    fixes: [],
  },
  {
    version: '1.4.5',
    date: '07 Abr 2026',
    latest: false,
    features: [
      'Botão "Atualizar agora" no Painel do Sistema — com confirmação de comandos, barra de progresso e log em tempo real via SSE',
    ],
    improvements: [
      'Bind mount de staticfiles no container web: builds do frontend refletidos imediatamente sem rebuild da imagem',
      'Changelog e versão agora sempre atualizados após cada entrega',
    ],
    fixes: [
      'Changelog exibia versão anterior porque o container web servia arquivos baked na imagem, não o build do host',
    ],
  },
  {
    version: '1.4.4',
    date: '07 Abr 2026',
    latest: false,
    features: [],
    improvements: [
      'Menu lateral recolhido automaticamente ao acessar via dispositivo móvel',
      'Botão hambúrguer fixo (canto superior esquerdo) para abrir o menu no mobile',
      'Backdrop semitransparente ao abrir o menu no mobile — clique fora para fechar',
      'Mapa ocupa 100% da tela em mobile (margin-left zerada via CSS e CSS variable)',
      'Transição desktop ↔ mobile: estado do menu restaurado corretamente ao girar o dispositivo',
    ],
    fixes: [
      'Serviços Celery e Beat em loop de restart — imagem Docker reconstruída com django-celery-beat instalado',
      'CustomMapViewer aplicava margin-left de 72–280px no mobile mesmo com menu como overlay fixo',
      'data-nav-menu-open e --nav-menu-width não eram zerados ao montar em mobile, causando deslocamento no mapa',
    ],
  },
  {
    version: '1.4.3',
    date: '07 Abr 2026',
    latest: false,
    features: [
      'Gerenciamento de Cron Jobs via UI em Configurações > Sistema > Cron — crie, edite, ative/desative e aplique tarefas agendadas no servidor sem editar arquivos manualmente',
    ],
    improvements: [
      'Novo Cron Job "Limpeza Docker Semanal" pré-configurável para remover cache de build acumulado (docker builder prune)',
      'Botão "Aplicar no Servidor" gera o arquivo crontab em /app/database/provemaps.crontab com instruções de ativação',
      'Modal de criação de cron com presets de agendamento (A cada hora, Todo dia 3h, Semanal, Mensal, Seg-Sex)',
    ],
    fixes: [
      'Modal de teste SMTP: ao clicar no ⚡ do gateway, abre modal pedindo destinatário e mensagem antes de enviar — mesmo padrão do teste SMS',
      'Erro "int object has no attribute strip" nos endpoints de teste SMTP, DB e FTP — porta enviada como número inteiro pelo frontend agora convertida corretamente',
      'Modal LocationPicker (seleção de ponto no mapa) não respeitava o modo escuro — reescrito com classes Tailwind dark:',
      'SiteEditModal substituiu mapa inline por botão PIN que abre o LocationPickerModal — interface mais limpa e mapa maior',
      'Geocode reverso automático ao digitar lat/lng manualmente no formulário de novo site',
      'Bug crítico em _load_runtime_env(): Path("") é truthy em Python, impedindo leitura da senha real do banco em runtime',
      'Opções inválidas read_timeout/write_timeout removidas do settings/prod.py — causavam ProgrammingError no psycopg',
    ],
  },
  {
    version: '1.4.2',
    date: '06 Abr 2026',
    latest: false,
    features: [
      'Seletor de localização com mapa e PIN arrastável em Setup > Mapas — clique ou arraste o marcador para definir as coordenadas iniciais',
    ],
    improvements: [
      'Botão "Reenquadrar" no mapa do backbone para ajustar a visão a todos os itens visíveis',
      '"Selecionar todos" no painel lateral reenquadra automaticamente o mapa',
      'CSP ampliada para permitir verificação de atualizações via api.github.com',
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
