# 🧪 Plano de Teste Manual - Frontend Modularizado

**Data:** 27 de Outubro de 2025  
**Objetivo:** Validar que a refatoração modular do `fiber_route_builder.js` não introduziu regressões  
**Escopo:** Todos os workflows de criação, edição, exclusão e visualização de cabos

---

## 📋 Pré-requisitos

### Ambiente
- [ ] Docker containers rodando (`docker ps`)
- [ ] Django web server acessível em http://localhost:8000
- [ ] MariaDB com dados de teste
- [ ] Redis cache funcional
- [ ] Usuário autenticado no sistema

### Dados de Teste Necessários
- [ ] Pelo menos 2 Sites cadastrados
- [ ] Pelo menos 3 Devices cadastrados
- [ ] Google Maps API Key configurada (se aplicável)

---

## 🗺️ Cenários de Teste

### 1️⃣ Inicialização do Mapa

**Objetivo:** Validar que o mapa carrega corretamente com módulos ES6

#### Passos:
1. Acessar http://localhost:8000/routes/builder/
2. Aguardar carregamento completo da página
3. Verificar console do navegador (F12)

#### Critérios de Sucesso:
- [ ] **Mapa renderizado:** Leaflet map visível com tiles carregados
- [ ] **Sem erros JS:** Console sem erros de import/export
- [ ] **Módulos carregados:** Verificar via DevTools > Network > JS files
  - [ ] `apiClient.js` carregado
  - [ ] `mapCore.js` carregado
  - [ ] `contextMenu.js` carregado
  - [ ] `modalEditor.js` carregado
  - [ ] `cableService.js` carregado
  - [ ] `pathState.js` carregado
  - [ ] `uiHelpers.js` carregado
- [ ] **Botões visíveis:** "Novo Cabo", "Salvar", "Cancelar"
- [ ] **Sidebar funcional:** Panel lateral com lista de cabos (se houver)

#### Notas de Teste:
```
Data/Hora: _________________
Navegador: _________________
Resultado: ☐ PASS  ☐ FAIL
Observações:
_________________________________
_________________________________
```

---

### 2️⃣ Criar Novo Cabo (Workflow Completo)

**Objetivo:** Validar criação de cabo do início ao fim

#### Passos:
1. Clicar no botão "Novo Cabo" ou equivalente
2. Verificar se o cursor muda para modo desenho (crosshair)
3. Clicar em 3-5 pontos no mapa para desenhar a rota
4. Clicar com botão direito ou duplo-clique para finalizar
5. Preencher modal com dados:
   - Nome do cabo: `TESTE_CABO_001`
   - Tipo: Selecionar da dropdown
   - Distância: (auto-calculada)
   - Observações: `Teste de modularização`
6. Clicar em "Salvar"
7. Aguardar confirmação

#### Critérios de Sucesso:
- [ ] **Modo desenho ativado:** Cursor muda para crosshair
- [ ] **Polyline renderizada:** Linha aparece no mapa conforme cliques
- [ ] **Cores corretas:** Linha com cor padrão definida
- [ ] **Modal abre:** Form de edição aparece após finalizar desenho
- [ ] **Campos preenchidos:** Distância auto-calculada corretamente
- [ ] **Validação funciona:** Campos obrigatórios validados
- [ ] **POST successful:** Request 201 Created no Network tab
- [ ] **Cabo salvo:** Aparece na lista de cabos
- [ ] **Notificação exibida:** Toast/alert de sucesso
- [ ] **Estado limpo:** Modo desenho desativado após salvar

#### Notas de Teste:
```
Data/Hora: _________________
ID do cabo criado: _________
Resultado: ☐ PASS  ☐ FAIL
Observações:
_________________________________
_________________________________
```

---

### 3️⃣ Visualizar Cabos Existentes

**Objetivo:** Validar renderização de cabos salvos no BD

#### Passos:
1. Recarregar a página
2. Aguardar carregamento dos cabos existentes
3. Verificar lista de cabos na sidebar
4. Clicar em diferentes cabos na lista

#### Critérios de Sucesso:
- [ ] **Cabos carregados:** GET /api/cables/ retorna 200
- [ ] **Polylines renderizadas:** Todas as rotas aparecem no mapa
- [ ] **Cores distintas:** Cada tipo de cabo com cor diferente
- [ ] **Hover funciona:** Tooltip aparece ao passar mouse
- [ ] **Click funciona:** Cabo selecionado ao clicar
- [ ] **Zoom to cable:** Mapa centraliza no cabo selecionado
- [ ] **Detalhes visíveis:** Informações do cabo aparecem (nome, distância, tipo)
- [ ] **Performance:** Carregamento < 2s para 50 cabos

#### Notas de Teste:
```
Data/Hora: _________________
Quantidade de cabos: _______
Resultado: ☐ PASS  ☐ FAIL
Observações:
_________________________________
_________________________________
```

---

### 4️⃣ Editar Cabo Existente

**Objetivo:** Validar edição de propriedades e geometria

#### Passos:
1. Selecionar um cabo na lista ou clicar no mapa
2. Clicar em "Editar" ou botão direito > "Editar"
3. **Editar Propriedades:**
   - Alterar nome para `TESTE_CABO_001_EDITADO`
   - Alterar tipo de cabo
   - Adicionar observação
4. **Editar Geometria:**
   - Ativar modo edição de vértices
   - Arrastar um vértice para nova posição
   - Adicionar novo vértice no meio da linha
   - Remover um vértice existente
5. Clicar em "Salvar Alterações"
6. Verificar atualização no mapa e BD

#### Critérios de Sucesso:
- [ ] **Modal abre:** Form de edição com dados pre-populados
- [ ] **Dados carregados:** Todos os campos com valores corretos
- [ ] **Edição de vértices:** Arrastar funciona suavemente
- [ ] **Adicionar vértice:** Novo ponto inserido corretamente
- [ ] **Remover vértice:** Ponto removido sem quebrar linha
- [ ] **Distância recalculada:** Valor atualizado após mudanças geométricas
- [ ] **PUT successful:** Request 200 OK no Network tab
- [ ] **Mapa atualizado:** Polyline reflete mudanças imediatamente
- [ ] **Lista atualizada:** Nome e dados atualizados na sidebar
- [ ] **Sem duplicação:** Apenas um cabo, não dois

#### Notas de Teste:
```
Data/Hora: _________________
Cabo editado (ID): _________
Resultado: ☐ PASS  ☐ FAIL
Observações:
_________________________________
_________________________________
```

---

### 5️⃣ Deletar Cabo

**Objetivo:** Validar exclusão com confirmação

#### Passos:
1. Selecionar cabo `TESTE_CABO_001_EDITADO`
2. Clicar em "Deletar" ou botão direito > "Deletar"
3. Verificar modal de confirmação
4. Clicar em "Sim, deletar"
5. Aguardar confirmação
6. Recarregar página para validar persistência

#### Critérios de Sucesso:
- [ ] **Modal de confirmação:** Pergunta "Tem certeza?"
- [ ] **Dados exibidos:** Nome e detalhes do cabo no modal
- [ ] **Cancelar funciona:** Fechar modal sem deletar
- [ ] **DELETE successful:** Request 204 No Content no Network tab
- [ ] **Polyline removida:** Cabo desaparece do mapa
- [ ] **Lista atualizada:** Cabo removido da sidebar
- [ ] **Notificação exibida:** Toast de sucesso
- [ ] **Persistido:** Após reload, cabo não reaparece

#### Notas de Teste:
```
Data/Hora: _________________
Cabo deletado (ID): ________
Resultado: ☐ PASS  ☐ FAIL
Observações:
_________________________________
_________________________________
```

---

### 6️⃣ Menu de Contexto (Botão Direito)

**Objetivo:** Validar menu contextual em cabos e mapa

#### Passos:
1. **Menu no Cabo:**
   - Clicar botão direito em uma polyline
   - Verificar opções: Editar, Deletar, Ver Detalhes, etc.
   - Clicar em "Ver Detalhes"
2. **Menu no Mapa:**
   - Clicar botão direito em área vazia
   - Verificar opções: Novo Cabo, Centralizar Mapa, etc.
3. **Fechar menu:** Clicar fora ou pressionar ESC

#### Critérios de Sucesso:
- [ ] **Menu aparece:** Popup contextual visível
- [ ] **Posição correta:** Menu próximo ao cursor
- [ ] **Opções corretas:** Ações relevantes ao contexto
- [ ] **Ícones visíveis:** Cada ação com ícone apropriado
- [ ] **Hover funciona:** Itens destacados ao passar mouse
- [ ] **Click funciona:** Ação executada ao clicar
- [ ] **Fechar funciona:** ESC ou click fora fecha menu
- [ ] **Sem sobreposição:** Menu não fica cortado pela tela

#### Notas de Teste:
```
Data/Hora: _________________
Resultado: ☐ PASS  ☐ FAIL
Observações:
_________________________________
_________________________________
```

---

### 7️⃣ Filtros e Busca

**Objetivo:** Validar funcionalidades de filtro (se existirem)

#### Passos:
1. Usar filtro por tipo de cabo (dropdown)
2. Usar busca por nome (input text)
3. Filtrar por distância (range slider)
4. Limpar todos os filtros

#### Critérios de Sucesso:
- [ ] **Filtro tipo:** Apenas cabos do tipo selecionado visíveis
- [ ] **Busca nome:** Resultados filtrados em tempo real
- [ ] **Filtro distância:** Cabos fora do range ocultados
- [ ] **Limpar filtros:** Todos os cabos reaparecem
- [ ] **Performance:** Filtro instantâneo (< 100ms)
- [ ] **Contador atualizado:** "Mostrando X de Y cabos"

#### Notas de Teste:
```
Data/Hora: _________________
Resultado: ☐ PASS  ☐ FAIL
Observações:
_________________________________
_________________________________
```

---

### 8️⃣ Interações do Mapa

**Objetivo:** Validar controles Leaflet básicos

#### Passos:
1. Zoom in/out com botões
2. Zoom in/out com scroll do mouse
3. Pan (arrastar) o mapa
4. Usar layers control (se existir)
5. Usar fullscreen (se existir)

#### Critérios de Sucesso:
- [ ] **Zoom botões:** + e - funcionam
- [ ] **Zoom scroll:** Roda do mouse funciona
- [ ] **Pan suave:** Arrastar sem lag
- [ ] **Layers:** Trocar entre Street/Satellite/Terrain
- [ ] **Fullscreen:** Expande e colapsa corretamente
- [ ] **Bounds preservados:** Estado do mapa mantido

#### Notas de Teste:
```
Data/Hora: _________________
Resultado: ☐ PASS  ☐ FAIL
Observações:
_________________________________
_________________________________
```

---

### 9️⃣ Erros e Edge Cases

**Objetivo:** Validar tratamento de erros

#### Passos:
1. **Criar cabo sem nome:** Tentar salvar form vazio
2. **Editar cabo inexistente:** Manipular URL para ID inválido
3. **Deletar durante edição:** Deletar cabo em outra aba enquanto edita
4. **Rede offline:** Desconectar internet e tentar salvar
5. **Request duplicado:** Double-click rápido em "Salvar"

#### Critérios de Sucesso:
- [ ] **Validação frontend:** Mensagens de erro claras
- [ ] **404 tratado:** Mensagem "Cabo não encontrado"
- [ ] **Conflito tratado:** Detecção de mudanças concorrentes
- [ ] **Offline detectado:** Mensagem "Sem conexão"
- [ ] **Loading state:** Botão desabilitado durante request
- [ ] **Sem crash:** Aplicação permanece funcional
- [ ] **Rollback automático:** Estado inconsistente revertido

#### Notas de Teste:
```
Data/Hora: _________________
Resultado: ☐ PASS  ☐ FAIL
Observações:
_________________________________
_________________________________
```

---

### 🔟 Performance e Responsividade

**Objetivo:** Validar performance com carga

#### Passos:
1. Criar 20 cabos rapidamente
2. Selecionar vários cabos em sequência
3. Fazer zoom in/out rápido várias vezes
4. Testar em mobile/tablet (DevTools responsive mode)

#### Critérios de Sucesso:
- [ ] **Renderização rápida:** 20 cabos < 1s
- [ ] **Sem lag:** Seleção instantânea
- [ ] **Zoom suave:** Sem stuttering
- [ ] **Mobile ok:** Touch funciona, botões acessíveis
- [ ] **Memory ok:** Sem memory leaks (DevTools Performance tab)

#### Notas de Teste:
```
Data/Hora: _________________
Resultado: ☐ PASS  ☐ FAIL
Observações:
_________________________________
_________________________________
```

---

## 📊 Matriz de Compatibilidade

Testar em múltiplos navegadores:

| Cenário | Chrome | Firefox | Edge | Safari | Mobile |
|---------|--------|---------|------|--------|--------|
| 1. Inicialização | ☐ | ☐ | ☐ | ☐ | ☐ |
| 2. Criar Cabo | ☐ | ☐ | ☐ | ☐ | ☐ |
| 3. Visualizar | ☐ | ☐ | ☐ | ☐ | ☐ |
| 4. Editar | ☐ | ☐ | ☐ | ☐ | ☐ |
| 5. Deletar | ☐ | ☐ | ☐ | ☐ | ☐ |
| 6. Menu Contexto | ☐ | ☐ | ☐ | ☐ | ☐ |
| 7. Filtros | ☐ | ☐ | ☐ | ☐ | ☐ |
| 8. Interações Mapa | ☐ | ☐ | ☐ | ☐ | ☐ |
| 9. Erros | ☐ | ☐ | ☐ | ☐ | ☐ |
| 10. Performance | ☐ | ☐ | ☐ | ☐ | ☐ |

---

## 🐛 Registro de Bugs

| ID | Cenário | Descrição | Severidade | Status |
|----|---------|-----------|------------|--------|
| BUG-001 | | | ☐ Crítico ☐ Alto ☐ Médio ☐ Baixo | ☐ Aberto ☐ Resolvido |
| BUG-002 | | | ☐ Crítico ☐ Alto ☐ Médio ☐ Baixo | ☐ Aberto ☐ Resolvido |
| BUG-003 | | | ☐ Crítico ☐ Alto ☐ Médio ☐ Baixo | ☐ Aberto ☐ Resolvido |

**Severidade:**
- **Crítico:** Aplicação não funciona, perda de dados
- **Alto:** Feature principal quebrada, workaround difícil
- **Médio:** Feature secundária quebrada, workaround existe
- **Baixo:** Cosmético, UX ruim mas funciona

---

## ✅ Critérios de Aceitação Final

Para considerar a refatoração **APROVADA**:

- [ ] **Todos os 10 cenários PASSARAM** em pelo menos 1 navegador
- [ ] **Zero bugs críticos** encontrados
- [ ] **< 2 bugs altos** encontrados
- [ ] **Performance aceitável** (< 2s para operações principais)
- [ ] **Console sem erros** (exceto warnings aceitáveis)
- [ ] **Compatibilidade:** Chrome + Firefox funcionando
- [ ] **Mobile básico:** Touch e navegação ok

---

## 📝 Relatório de Execução

**Testador:** _________________________  
**Data início:** ______________________  
**Data fim:** ________________________  
**Duração total:** ___________________  

**Resumo:**
- Cenários executados: ____/10
- Cenários PASS: ____
- Cenários FAIL: ____
- Bugs encontrados: ____
- Bugs críticos: ____

**Decisão Final:**
☐ **APROVADO** - Refatoração sem regressões  
☐ **APROVADO COM RESSALVAS** - Bugs menores a corrigir  
☐ **REPROVADO** - Regressões críticas encontradas

**Observações Gerais:**
```
______________________________________________
______________________________________________
______________________________________________
______________________________________________
```

---

**Próximos Passos:**
1. Se APROVADO: Merge para branch main
2. Se REPROVADO: Corrigir bugs e re-testar
3. Documentar lições aprendidas
4. Criar testes automatizados (Jest/Playwright) para os cenários críticos

---

*Documento gerado em 27/10/2025*  
*Baseado na refatoração modular ES6 do fiber_route_builder.js*
