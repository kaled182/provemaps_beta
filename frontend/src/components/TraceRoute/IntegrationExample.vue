<!-- 
  EXEMPLO DE INTEGRAÇÃO - Trace Route Button
  
  Este arquivo mostra como adicionar o botão "Trace Route" em componentes existentes.
  Copie e adapte conforme necessário.
-->

<template>
  <div class="fiber-actions">
    <!-- Botão Trace Route -->
    <button
      v-if="selectedStrand"
      class="btn-trace"
      @click="openTraceRoute"
      title="Rastrear caminho óptico completo"
    >
      🔍 Trace Route
    </button>

    <!-- Modal de Trace Route -->
    <TraceRouteModal
      :strand-id="traceStrandId"
      :is-open="showTraceModal"
      @close="closeTraceModal"
      @fault-located="handleFaultLocated"
    />
  </div>
</template>

<script>
import { ref } from 'vue';
import TraceRouteModal from '@/components/TraceRoute/TraceRouteModal.vue';

export default {
  name: 'FiberActionsExample',

  components: {
    TraceRouteModal,
  },

  props: {
    selectedStrand: {
      type: Object,
      default: null,
    },
  },

  setup(props) {
    const showTraceModal = ref(false);
    const traceStrandId = ref(null);

    function openTraceRoute() {
      if (props.selectedStrand) {
        traceStrandId.value = props.selectedStrand.id;
        showTraceModal.value = true;
      }
    }

    function closeTraceModal() {
      showTraceModal.value = false;
      traceStrandId.value = null;
    }

    function handleFaultLocated(event) {
      console.log('Localização de falha:', event);
      // TODO: Integrar com OTDR ou plotar no mapa
      // event.trace - Objeto completo do trace
      // event.fiberStrands - Lista de fibras com atenuação medida
    }

    return {
      showTraceModal,
      traceStrandId,
      openTraceRoute,
      closeTraceModal,
      handleFaultLocated,
    };
  },
};
</script>

<style scoped>
.btn-trace {
  padding: 0.5rem 1rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.btn-trace:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.btn-trace:active {
  transform: translateY(0);
}
</style>

<!--
  COMO USAR EM OUTROS COMPONENTES:

  1. Em FiberEditModal.vue ou FiberCablesList.vue:
     - Importe TraceRouteModal
     - Adicione o botão no template (geralmente em "Ações" ou menu de contexto)
     - Use o composable useTraceRoute para lógica mais complexa

  2. Menu de Contexto (clique direito):
     <context-menu>
       <menu-item @click="openTraceRoute">
         🔍 Trace Route
       </menu-item>
     </context-menu>

  3. Dropdown de Ações:
     <dropdown>
       <dropdown-item @click="openTraceRoute">
         Rastrear Caminho Óptico
       </dropdown-item>
     </dropdown>

  4. Tabela de Fibras:
     <td class="actions">
       <button @click="openTraceRoute(fiber.strand_id)">
         🔍
       </button>
     </td>
-->
