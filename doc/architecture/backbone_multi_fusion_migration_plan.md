# Plano de Migração — Modelo de Fusões Multi-Hop

## Visão Geral

O objetivo é permitir que uma mesma fibra seja emendada em múltiplas caixas (CEOs) ao longo do backbone sem sobrescrever fusões anteriores. Hoje o modelo `FiberStrand` usa campos `fused_to` / `fusion_infrastructure` / `fusion_tray` / `fusion_slot`, o que cria uma relação 1:1 e provoca perdas de histórico quando a mesma fibra é emendada novamente.

A proposta é introduzir o conceito de **eventos de fusão** independentes (`FiberFusion`) e remover o acoplamento direto do filamento (`FiberStrand`) com a fusão atual. Este documento descreve todas as adaptações necessárias para executar essa migração com segurança.

---

## 1. Modelagem & Migrações

### 1.1 Novos modelos
- Criar `FiberFusion` com os campos: — ✅ Concluído
  - `infrastructure` (`FK` → `FiberInfrastructure`)
  - `tray`, `slot`
  - `fiber_a`, `fiber_b` (`FK` → `FiberStrand`)
  - `created_at`
  - `Meta.unique_together = (infrastructure, tray, slot)`
- Criar índices auxiliares em `fiber_a` e `fiber_b` (visando trace route / consultas). — ✅ Concluído

### 1.2 Adequações em `FiberStrand`
- Remover os campos: — ✅ Concluído
  - `fused_to`
  - `fusion_infrastructure`
  - `fusion_tray`
  - `fusion_slot`
- Manter `connected_device_port`, `segment` e metadados existentes. — ✅ Concluído
- Atualizar `__all__` / serializers / admin. — ✅ Concluído (serializers atualizados para multi-hop; alias legado `fused_to` mantido temporariamente)

### 1.3 Migração de dados
- Nova migration com sequência:
  1. Criar tabela `FiberFusion`. — ✅ Concluído
  2. Migrar os dados existentes: para cada `FiberStrand` com `fused_to` preenchido, criar uma entrada `FiberFusion` (considerando apenas um dos pares para evitar duplicata). Utilizar os metadados (`fusion_infrastructure`, `fusion_tray`, `fusion_slot`) para compor o registro. — ✅ Concluído
  3. Remover (ou marcar para remoção) os campos antigos. Ideal: `migrations.RunPython` para copiar dados, depois `AlterField` + `RemoveField`. — ✅ Concluído
  4. Garantir que pares órfãos (sem `fusion_*`) sejam ignorados conscientemente e auditados via log (permitir relatórios pós-migração). — ✅ Concluído (logs na migration registram ids ignorados e duplicados)

### 1.4 Versionamento de backups
- Checklist pré-migração documentado — ✅ Concluído
  1. Gerar snapshot das fusões antes de aplicar a migration:
    - `python scripts/backup_fiber_fusions.py` cria automaticamente um JSON em `database/backups/` (ou use `--output` para definir o caminho).
    - Execução validada em 09/12/2025: `docker compose exec web python manage.py audit_fiber_fusions --output /app/database/backups/validation_pre.json` (total de 24 fusões capturadas).
    - O script delega para `manage.py audit_fiber_fusions`, garantindo o mesmo formato usado na validação pós-migração.
  2. Criar dump completo do banco para rollback:
     - `cd docker`
      - `docker compose exec -T --env PGPASSWORD=app postgres pg_dump -U app app > ../database/backups/pre_multi_fusion_<timestamp>.dump`
      - Ajustar o nome do arquivo conforme data/ambiente. Execução registrada em 09/12/2025 gerou `pre_multi_fusion_20251209_011836.dump`.
- Validação pós-migração — ✅ Concluído
  - Comparar o snapshot salvo com o estado atual: `docker compose exec web python manage.py audit_fiber_fusions --compare /app/database/backups/validation_pre.json`.
  - Execução em 09/12/2025 retornou `Totais coincidem: 24 fusões`, sem slots ausentes/extras, registrando a conclusão da checagem de integridade.
  - O comando emite diferenças de slots ausentes/extras e deve ser parte da checklist de GO/NO-GO.

---

## 2. Backend — Ajustes de Lógica

### 2.1 API de fusões (`inventory/api/splice_matrix.py` e `inventory/api/fusion.py`)
- Refatorar `SpliceBoxMatrixView` para ler `FiberFusion` (via `select_related` em `fiber_a` e `fiber_b`). — ✅ Concluído
- Atualizar `CreateFusionView` / `DeleteFusionView` para operar em cima de `FiberFusion`:
  - `POST`: criar/atualizar `FiberFusion`, reaproveitando a validação de slot único.
  - `DELETE`: remover pelo ID da fusão (ou pelos parâmetros `tray/slot`). — ✅ Concluído
- Ajustar endpoints auxiliares (contexto de caixas) para sinalizar se a fibra está emendada naquela caixa: novo atributo `fused_here` baseado em existência de `FiberFusion` onde a fibra participa. — ✅ Concluído (BoxContext utiliza `FiberFusion` e destaca fusões locais)

### 2.2 Serviços de segmentação / split (`inventory/api/cable_split.py`, `inventory/services/cable_segments.py`)
- Onde hoje migramos `strand.fused_to`, passar a migrar registros `FiberFusion` associados ao cabo original: — ✅ Concluído
  - Identificar fusões cujo `fiber_a` ou `fiber_b` pertencem ao cabo que está sendo rompido. — ✅ Concluído
  - Recriar fusões para as fibras correspondentes nos novos segmentos (utilizando mapamento `strand_id -> novo_strand.id`). — ✅ Concluído

### 2.3 Traçado óptico (`inventory/api/trace_route.py`)
- Revisar o algoritmo: atualmente segue `strand.fused_to`. Passará a consultar `FiberFusion` para descobrir o próximo filamento:
  - Método auxiliar para obter vizinhos: `find_next_fusion(strand)` retorna lista de fusões onde a fibra participa.
  - Renderização do passo de fusão passa a usar os metadados da tabela nova. — ✅ Concluído
- Considerar múltiplos saltos (branching). Definir estratégia de escolha (ex.: seguir primeira fusão encontrada ou todas?). Documentar a decisão. — ⏳ Parcial (algoritmo cobre múltiplas fusões, mas documentação ainda não atualizada)

### 2.4 Serializers / DTOs
- Atualizar serializers que expõem `fused_to` diretamente, p.ex. `inventory/serializers.py`. — ✅ Concluído (payload detalhado de fusões disponível; campo `fused_to` mantido como alias de compatibilidade)
- Adicionar serializer para `FiberFusion` se necessário (usado em REST ou WebSocket). — ⏳ Avaliar demanda

### 2.5 Testes automáticos
- Revisar testes unitários e de integração:
  - `inventory/tests/test_fusion_atomic.py` — ✅ Atualizado
  - `inventory/tests/test_trace_route.py` — ✅ Atualizado
  - Scripts em `inventory/management/commands/test_fusion_atomic.py` — ⏳ Pendente (ainda usa campos legados)
- Atualizar fixtures de teste que criam fusões manualmente. — ✅ Ajustado nos testes principais

### 2.6 Observabilidade
- Ajustar logs e métricas que atualmente contam fusões via `FiberStrand`. — ⏳ Não iniciado
- Avaliar impacto em relatórios/exports que consultam dados de fusão. — ⏳ Não iniciado

### 2.7 Lógica de Segmentação Virtual (Daisy Chain Support)
- **Refatorar `box_context`**: o endpoint deve retornar segmentos virtuais baseados na topologia, e não apenas objetos `FiberCable` crus. — ✅ Concluído (segmentos virtuais com `virtual_id` e contexto multi-hop)
- **Ordenação por distância**: montar a "linha do tempo" do cabo usando `distance_from_origin` para identificar quem é o vizinho anterior e o seguinte da caixa atual. — ✅ Concluído
- **IDs únicos virtuais**: gerar `virtual_id` com sufixos direcionais/posicionais (ex.: `50_PREV`, `50_NEXT`) para cada lado exposto na caixa. — ✅ Concluído
- **Serialização local**: `_serialize_tubes_for_box` precisa destacar, via `is_fused_here`, apenas as fibras efetivamente fusionadas nesta caixa usando a nova tabela `FiberFusion`. — ✅ Concluído
- **Benefício**: impede colisão de IDs em topologias longas (20+ caixas) e mantém o contexto local — cada caixa só enxerga os segmentos que chegam e saem dela. — ✅ Validado com payload estendido


## 3. Frontend — Ajustes Necessários
### 3.1 Splice Matrix (SpliceMatrixModal.vue)
- Atualizar consumo da nova API:
  - `matrix` passa a vir com objetos `fiber_a`/`fiber_b` (incluindo `color_hex`, `cable`). — ⏳ Não iniciado
  - Lógica de destaque `is_fused` deve usar presença em `FiberFusion` (provavelmente campo `fused_here` na resposta de segmentos). — ⏳ Não iniciado
- Adaptação para virtual IDs:
  - Seletores e stores devem aceitar identificadores string (ex.: `50_PREV`) além de inteiros. — ⏳ Não iniciado
  - A busca pelos segmentos usa `cables.find(c => c.virtual_id === selectedId)`. — ⏳ Não iniciado
- Interface de seleção flexível:
  - Manter seletores independentes para "lado A" e "lado B", permitindo usar o mesmo cabo físico com virtual IDs distintos (passagem/sangria). — ⏳ Não iniciado
- Mostrar status local:
  - Aplicar `strand.is_fused_here` para indicar se a fibra já foi manipulada na caixa atual, mesmo que existam fusões em caixas anteriores. — ⏳ Não iniciado
- Atualizar filtros visualizando múltiplas fusões de uma mesma fibra em caixas diferentes (exibir status `fused_elsewhere`). — ⏳ Não iniciado

### 3.2 Map editor (`FiberRouteEditor.vue`)
- Hooks que checam `is_fused`/`fused_elsewhere` precisam usar dados novos. — ⏳ Não iniciado
- Validar fluxo de split e recálculo do contexto da caixa (após migração o backend devolve a nova estrutura). — ⏳ Não iniciado

### 3.3 Outros componentes
- Revisar qualquer tela que apresente `fusion_infrastructure` diretamente (detalhes de fibras, relatórios). — ⏳ Não iniciado

---

## 4. Plano de Execução

### 4.1 Preparação
1. Criar branch dedicado (ex.: `feature/multi-hop-fusion`). — ⏳ Não realizado (trabalho em `inicial`)
2. Gerar snapshot do banco (dump) antes da migration. — ⏳ Não registrado
3. Escrever scripts temporários para validar contagem de fusões (antes/depois). — ⏳ Pendente

### 4.2 Etapas de desenvolvimento
1. Implementar modelos + migração (incluindo script `RunPython`). — ✅ Concluído
2. Ajustar serviços backend e testes unitários até passarem localmente. — ✅ Concluído (pytest completo)
3. Atualizar front-end (Splice Matrix, editor de rotas) com mock/stubs. — ⏳ Pendente
4. Rodar suíte completa (`make test`, `npm run test:unit`). — ✅ Pytest executado; testes frontend pendentes (`npm run test:unit`)

### 4.3 Validação integrada
1. Subir stack docker local. — ✅ Contêineres ativos durante pytest
2. Executar migração real em base de desenvolvimento (docker). — ⏳ Aguardando aplicação em ambiente real
3. Fluxos de teste:
  - Abrir CEO com fusões existentes e garantir que todos os slots continuam ocupados corretamente. — ⏳ Planejado (aguarda validação manual)
  - Criar nova fusão, remover, reordenar — checar consistência. — ⏳ Planejado
  - Romper cabo, migrar fusões para novos segmentos, abrir splice matrix em todas as caixas do backbone. — ⏳ Planejado
  - Rodar trace route para fibra com múltiplas fusões. — ✅ Coberto pelos testes automatizados `pytest inventory/tests/test_trace_route.py` em 09/12/2025
  - Validar payload do box context com fusões multi-hop. — ✅ `pytest inventory/tests/test_box_context_payload.py` em 09/12/2025

### 4.4 Deploy / rollback
- Deploy executado em janela controlada (pode exigir downtime curto pela migration). — ⏳ Não agendado
- Rollback: restaurar dump anterior + voltar branch. — ⏳ Planejado
- Após deploy, rodar script de verificação das fusões (comparar contagens e amostras manuais). — ⏳ Pendente

---

## 5. Riscos & Mitigações

| Risco | Mitigação |
|-------|-----------|
| Perda de fusões durante migração | Backup completo + script de validação pós-migração |
| Algoritmo de trace route não suportar múltiplas fusões | Ajustar para percorrer `FiberFusion`; adicionar testes cobrindo ramificações |
| Impacto em performance (mais joins) | Criar índices (`fiber_a_id`, `fiber_b_id`, `infrastructure_id`) e validar plano de consulta |
| Frontend exibindo dados inconsistentes | Atualizar contratos da API, versionar endpoints se necessário |
| Colisão de IDs em topologias longas (daisy chain) | Gerar `virtual_id` com sufixo direcional/posicional no contexto da caixa |

---

## 6. Pontos em Aberto

1. **Sincronização com históricos OTDR**: há relatórios que usam `fusion_infrastructure`. Precisam ser revisados para usar `FiberFusion`.
2. **WebSockets / atualizações em tempo real**: hoje broadcasta via pendência nos caches? Verificar se dependem dos campos antigos.
3. **Auditoria de fusões**: mover `created_at`/`updated_at` para a nova entidade é suficiente ou precisamos armazenar usuário responsável?

---

## 7. Próximos Passos

1. Validar este plano com o time (especialmente quem mantém relatórios e trace route).
2. Depois do aval, iniciar implementação pela migração e ajustes de backend.
3. Coordenar com frontend para alinhar novos formatos de payload antes do merge final.

---

> **Checklist de Go/No-Go**
> - [x] Plano aprovado. — Em execução
> - [x] Backup e scripts de verificação preparados. — Snapshot `validation_pre.json` + comparação registrada em 09/12/2025
> - [ ] Migração aplicada em ambiente de staging com validação manual. — ⏳ Pendente
> - [ ] Testes automatizados e manuais passando. — ⏳ Backend automatizado ok; frontend/manuais pendentes
> - [ ] Janela de deploy acordada. — ⏳ Pendente

---

## Resumo Técnico — Segmentação Virtual em Topologia Linear

- Cenário alvo: um mesmo cabo atravessa cadeia de CEOs (ex.: 20 caixas).
- Para a infraestrutura `CEO-n`, a API `box_context` deve retornar somente:
  - Segmento virtual **vindo de** `CEO-(n-1)` (ou origem do cabo).
  - Segmento virtual **indo para** `CEO-(n+1)` (ou destino final).
- Cada segmento é identificado por `virtual_id` (`<cable_id>_<sufixo>`), evitando colisões quando o cabo aparece múltiplas vezes na mesma visualização.
- O campo `strand.is_fused_here` indica se a fibra foi manipulada na caixa atual, isolando o histórico local das intervenções anteriores.
- A lógica garante que o frontend trate entrada e saída como entidades distintas, eliminando loops visuais em topologias longas.
