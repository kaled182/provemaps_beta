# Changelog — ProVemaps

Todas as mudanças relevantes deste projeto são documentadas aqui.  
Formato: **Funcionalidades** | **Melhorias** | **Correções**

> **Regra:** sempre que um bug for corrigido ou um novo recurso for adicionado,  
> atualizar este arquivo **E** o array `changelog` em  
> `frontend/src/components/Layout/ChangelogModal.vue`.

---

## [1.4.1] — 2026-04-03

### Melhorias
- Menu lateral: paleta de cores unificada com o restante das páginas (removido tom azul-escuro `rgba(30,33,57)`, substituído por cinza-neutro `#111827` / `#0f172a`)
- Botão "Conectado" (status WebSocket) removido do rodapé do menu; substituído por ícone colorido compacto na linha de ações (verde/amarelo/vermelho conforme estado)
- Todos os valores de cor hardcoded no menu substituídos por variáveis CSS do design system (`--status-online`, `--shadow-sm`, etc.)

---

## [1.4.0] — 2026-04-03

### Funcionalidades
- Importação em lote de dispositivos com configurações comuns (site, categoria, alertas, chaves Zabbix)
- Regra de proximidade 100 m: evita criação de sites duplicados durante importação KML
- Overlay de progresso durante importação em lote com contagem de itens
- Modal de Changelog e Sugestões (ícone `ⓘ` no rodapé do menu)

### Melhorias
- Menu lateral reorganizado — Admin e Docs movidos para dentro do submenu System
- Botão "Salvar Device" agora salva site, categoria e alertas além das chaves Zabbix
- Ícones compactos para Tema e Sair no rodapé do menu (sem texto)
- Site opcional no modo batch — cada device mantém seu local original se não informado
- Após importação em lote, navegação automática para a aba de inventário

### Correções
- Importação de múltiplos devices ignorava os itens selecionados pelo usuário
- Validação de nome de device rejeitava espaços, hífens e parênteses
- `PATCH /api/v1/devices/<id>/` retornava 400 — campos `CharField` não aceitavam `null`
- Endpoint `/api/v1/inventory/devices/<id>/` era apenas `DELETE`; `PATCH` não existia

---

## [1.3.0] — 2026-03-28

### Funcionalidades
- Gráficos de tráfego IN/OUT na aba de tráfego do `FiberCableDetailModal`
- Exportação de gráficos em PNG e PDF no modal de cabo e de porta
- Exportação combinada (tráfego + sinal óptico) em arquivo único

### Melhorias
- Performance: carregamento paralelo de dados no `DeviceDetailsModal` e `PortTrafficModal`
- Modal de device mais estreito e proporcionado
- Badges de sinal óptico sem quebra de linha (`white-space: nowrap`)
- `PortTrafficModal` 10% mais largo

### Correções
- Triple-`nextTick` causava atraso de 400 ms+ no `PortTrafficModal`
- Canvas do gráfico de tráfego não encontrado na primeira carga

---

## [1.2.0] — 2026-03-15

### Funcionalidades
- Painel de detalhes de cabo com preview (Fase 1.3 — Network Design)
- Tips FAB com lógica reativa Vue (substituiu `getElementById`)
- `ResizeObserver` no `mapContainer` para notificar providers ao redimensionar (nav toggle, fullscreen)

### Melhorias
- Lazy-load de providers de mapa: Google Maps e Mapbox carregam apenas quando necessário

### Correções
- Overlays acima de modais Vue usam vanilla JS + `body.appendChild` em vez de `Teleport` + scoped CSS

---

## [2.0.0] — 2025-01-07  *(refatoração interna — sem impacto no usuário final)*

### Mudanças internas
- Aplicação `zabbix_api/` completamente removida; funcionalidades migradas para `inventory/` e `integrations/zabbix/`
- Endpoints legados `/zabbix/api/*` descontinuados
- Migração `inventory.0003` — move modelos Route para `inventory` (zero downtime)
- 199/199 testes passando após remoção de 1 teste de compatibilidade legado
