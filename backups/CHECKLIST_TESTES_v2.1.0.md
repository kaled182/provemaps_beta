# ProveMaps v2.1.0 - Checklist de Testes

**Testador**: ___________________________  
**Data**: ___/___/______  
**Ambiente**: [ ] Windows [ ] Linux [ ] Mac  

---

## ✅ Preparação do Ambiente

### Instalação
- [ ] Extraiu arquivo tar.gz com sucesso
- [ ] Copiou `.env.example` para `.env`
- [ ] Configurou credenciais Zabbix no `.env`
- [ ] Configurou token Mapbox OU chave Google Maps
- [ ] Docker Desktop instalado e rodando
- [ ] Porta 8100 disponível

### Inicialização
- [ ] Executou `docker compose up -d` sem erros
- [ ] Aguardou 30-60 segundos para inicialização
- [ ] Acessou http://localhost:8100 com sucesso
- [ ] Fez login (admin/admin)
- [ ] Alterou senha padrão

**Observações**:
```





```

---

## 🗺️ Configuração de Mapas

### Configurar Provider
- [ ] Acessou **Sistema > Configuração > Mapas**
- [ ] Selecionou provider: [ ] Mapbox [ ] Google Maps
- [ ] Colou token/API key
- [ ] Salvou configuração
- [ ] Recarregou página

**Provider escolhido**: _______________  
**Token válido**: [ ] Sim [ ] Não

**Observações**:
```





```

---

## 📍 NetworkDesign - Funcionalidades Básicas

### Acesso e Visualização
- [ ] Acessou `/Network/NetworkDesign/`
- [ ] Mapa carregou sem erros
- [ ] Console do navegador sem erros críticos (F12)
- [ ] Provider correto está sendo usado (verificar console)
- [ ] Cabos existentes aparecem no mapa (se houver)

**Screenshot do mapa**: (colar aqui ou anexar arquivo)

**Observações**:
```





```

---

## ➕ Criar Novo Cabo Manualmente

### Desenhar Rota
- [ ] Clicou no mapa para adicionar pontos
- [ ] Conseguiu adicionar pelo menos 3 pontos
- [ ] Linha azul aparece conectando os pontos
- [ ] Distância é calculada e exibida

**Número de pontos adicionados**: ______  
**Distância calculada**: ______ km

### Preencher Formulário
- [ ] Botão "Save cable manually" clicável
- [ ] Modal de salvamento abriu
- [ ] Campo "Cable name" funciona
- [ ] Dropdown "Origin device" mostra dispositivos
- [ ] Dropdown "Origin port" mostra portas
- [ ] Checkbox "Monitor origin port only" funciona
- [ ] Campos de destino aparecem/desaparecem corretamente

**Dispositivos disponíveis**: ______  
**Portas disponíveis no device selecionado**: ______

### Salvar Cabo
- [ ] Preencheu todos os campos obrigatórios
- [ ] Clicou em "Save"
- [ ] Cabo foi salvo com sucesso (mensagem verde)
- [ ] Cabo aparece na lista de cabos
- [ ] Cabo é visualizado no mapa após salvar

**Nome do cabo criado**: _______________  
**Sucesso**: [ ] Sim [ ] Não

**Screenshot do cabo criado**: (colar aqui)

**Observações/Erros**:
```





```

---

## ✏️ Editar Cabo Existente

### Selecionar Cabo
- [ ] Botão direito em cabo no mapa
- [ ] Menu de contexto apareceu
- [ ] Opção "Edit cable" disponível
- [ ] Clicou em "Edit cable"
- [ ] Formulário carregou com dados do cabo

### Modificar Cabo
- [ ] Conseguiu alterar nome do cabo
- [ ] Conseguiu trocar dispositivo origem
- [ ] Conseguiu trocar porta origem
- [ ] Conseguiu trocar dispositivo destino
- [ ] Conseguiu adicionar/remover pontos da rota

### Salvar Alterações
- [ ] Clicou em "Save"
- [ ] Alterações foram salvas
- [ ] Cabo atualizado aparece no mapa
- [ ] Dados corretos na lista de cabos

**Cabo editado**: _______________  
**Alterações realizadas**: _______________

**Observações**:
```





```

---

## 📥 Import KML

### Preparar Arquivo
- [ ] Possui arquivo .kml de teste
- [ ] Arquivo contém LineString válido

### Importar
- [ ] Abriu modal de import KML
- [ ] Selecionou arquivo .kml
- [ ] Preencheu nome do cabo
- [ ] Selecionou dispositivos origem/destino
- [ ] Clicou em "Import route"
- [ ] Cabo foi criado a partir do KML
- [ ] Rota do KML corresponde ao desenhado no mapa

**Nome do arquivo KML**: _______________  
**Sucesso**: [ ] Sim [ ] Não

**Observações**:
```





```

---

## 🔍 Monitoramento Backbone

### Visualização
- [ ] Acessou `/monitoring/backbone/`
- [ ] Mapa carregou corretamente
- [ ] Dispositivos aparecem no mapa
- [ ] Status Zabbix sincronizado (cores corretas)
- [ ] Cabos aparecem com cores indicando status

### Interação
- [ ] Clicou em dispositivo no mapa
- [ ] Tooltip/popup com informações apareceu
- [ ] Informações estão corretas
- [ ] Links funcionam

**Dispositivos no mapa**: ______  
**Status funcionando**: [ ] Sim [ ] Não

**Observações**:
```





```

---

## 🔄 Troca de Provider

### Teste de Switching
- [ ] Estava usando provider A: _______________
- [ ] Mudou para provider B: _______________
- [ ] Salvou configuração
- [ ] Recarregou NetworkDesign
- [ ] Provider B carregou corretamente
- [ ] Funcionalidades continuam operacionais

**Provider A**: _______________  
**Provider B**: _______________  
**Switching funcionou**: [ ] Sim [ ] Não

**Observações**:
```





```

---

## 🐛 Problemas Encontrados

### Erro 1
**Descrição**: 
```



```

**Passos para reproduzir**:
1. 
2. 
3. 

**Screenshot/Logs**: (anexar)

**Severidade**: [ ] Crítico [ ] Alto [ ] Médio [ ] Baixo

---

### Erro 2
**Descrição**: 
```



```

**Passos para reproduzir**:
1. 
2. 
3. 

**Screenshot/Logs**: (anexar)

**Severidade**: [ ] Crítico [ ] Alto [ ] Médio [ ] Baixo

---

### Erro 3
**Descrição**: 
```



```

**Passos para reproduzir**:
1. 
2. 
3. 

**Screenshot/Logs**: (anexar)

**Severidade**: [ ] Crítico [ ] Alto [ ] Médio [ ] Baixo

---

## 💡 Sugestões de Melhoria

1. 
2. 
3. 

---

## 📊 Resumo Final

### Estatísticas
- **Testes executados**: _____ / 60
- **Testes bem-sucedidos**: _____
- **Testes falhados**: _____
- **Problemas críticos encontrados**: _____

### Avaliação Geral
**Estabilidade**: [ ] Excelente [ ] Bom [ ] Regular [ ] Ruim  
**Usabilidade**: [ ] Excelente [ ] Boa [ ] Regular [ ] Ruim  
**Performance**: [ ] Excelente [ ] Boa [ ] Regular [ ] Ruim  

### Recomendação
[ ] **Aprovar para produção** - Funciona perfeitamente  
[ ] **Aprovar com ressalvas** - Pequenos ajustes necessários  
[ ] **Reprovar** - Problemas críticos impedem uso  

**Justificativa**:
```





```

---

**Assinatura do Testador**: ___________________________  
**Data de Conclusão**: ___/___/______  
**Tempo Total de Teste**: _____ horas
