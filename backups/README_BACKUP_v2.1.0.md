# ProveMaps Beta v2.1.0 - Pacote de Teste

**Data**: 05/03/2026  
**Versão**: 2.1.0 - Map Provider Pattern  
**Branch**: refactor/lazy-load-map-providers  
**Status**: ✅ Pronto para Testes

---

## 📋 O Que Há de Novo Nesta Versão

### ✅ Implementações Principais

#### 1. Provider Pattern para Mapas Multi-Provider
- **Antes**: Sistema hard-coded para Google Maps
- **Agora**: Suporte configurável para múltiplos providers:
  - ✅ **Mapbox GL JS** v3.8.0 (padrão)
  - ✅ **Google Maps** JavaScript API
  - 🔜 OpenStreetMap/Leaflet
  - 🔜 Esri ArcGIS

#### 2. NetworkDesign Completamente Refatorado
- **URL**: `/Network/NetworkDesign/`
- Todas as funcionalidades operacionais:
  - ✅ Desenhar cabos no mapa
  - ✅ Editar cabos existentes
  - ✅ Import KML
  - ✅ Vincular dispositivos e portas
  - ✅ Salvar no banco de dados

#### 3. Configuração Database-First
- **Local**: Sistema > Configurações > Mapas
- Escolha o provider sem alterar código
- Troca de provider em tempo real

---

## 🚀 Início Rápido

### Pré-requisitos
- Docker Desktop instalado
- 8GB RAM mínimo
- Porta 8100 disponível

### Passo 1: Descompactar
```bash
# Windows (PowerShell)
tar -xzf provemaps_beta_v2.1.0_2026-03-05_011158.tar.gz
cd provemaps_beta

# Linux/Mac
tar -xzf provemaps_beta_v2.1.0_2026-03-05_011158.tar.gz
cd provemaps_beta
```

### Passo 2: Configurar Ambiente
```bash
# Copiar template de configuração
cp .env.example .env

# Editar .env com suas credenciais
# Editar manualmente ou usar:
nano .env  # Linux/Mac
notepad .env  # Windows
```

**Variáveis essenciais**:
```env
# Zabbix (obrigatório)
ZABBIX_URL=https://seu-zabbix.com.br
ZABBIX_USER=Admin
ZABBIX_PASSWORD=sua-senha

# Provider de Mapas (escolher 1)
MAPBOX_TOKEN=pk.eyJ1... # Se usar Mapbox
GOOGLE_MAPS_API_KEY=AIzaSy... # Se usar Google Maps
```

### Passo 3: Iniciar Aplicação
```bash
# Subir todos os containers
docker compose -f docker/docker-compose.yml up -d

# Aguardar inicialização (30-60 segundos)
# Monitorar logs:
docker compose -f docker/docker-compose.yml logs -f web
```

### Passo 4: Acessar Sistema
- **URL Principal**: http://localhost:8100
- **Login Padrão**:
  - Usuário: `admin`
  - Senha: `admin`
  - ⚠️ **Alterar após primeiro acesso!**

---

## 🗺️ Configurar Provider de Mapas

### Opção 1: Mapbox (Recomendado)

1. Obter token gratuito: https://account.mapbox.com/
2. Acessar: **Sistema > Configuração > Mapas**
3. Selecionar **Provider**: Mapbox
4. Colar **Mapbox Token**: `pk.eyJ...`
5. Salvar
6. Recarregar página NetworkDesign

**Vantagens Mapbox**:
- ✅ 200.000 requisições/mês grátis
- ✅ Mapas modernos e rápidos
- ✅ Ótima performance em dispositivos móveis

### Opção 2: Google Maps

1. Obter API key: https://console.cloud.google.com/
2. Habilitar: Maps JavaScript API + Geocoding API
3. Acessar: **Sistema > Configuração > Mapas**
4. Selecionar **Provider**: Google Maps
5. Colar **Google Maps API Key**: `AIzaSy...`
6. Salvar
7. Recarregar página NetworkDesign

**Vantagens Google Maps**:
- ✅ Compatibilidade com código legado
- ✅ Rico em dados de localização
- ⚠️ $200/mês grátis (pode não ser suficiente)

---

## 🧪 Checklist de Testes

### Testes Básicos
- [ ] Login no sistema funciona
- [ ] Painel principal carrega
- [ ] Configurações de mapas acessíveis
- [ ] Provider de mapas configurado

### Testes do NetworkDesign
- [ ] Acessar `/Network/NetworkDesign/`
- [ ] Mapa carrega corretamente
- [ ] Criar novo cabo:
  - [ ] Clicar no mapa para desenhar rota
  - [ ] Preencher formulário (nome, dispositivos, portas)
  - [ ] Salvar com sucesso
- [ ] Editar cabo existente:
  - [ ] Botão direito no cabo
  - [ ] Editar rota
  - [ ] Salvar alterações
- [ ] Import KML:
  - [ ] Selecionar arquivo .kml
  - [ ] Cabo criado com rota do arquivo

### Testes de Monitoramento
- [ ] Acessar `/monitoring/backbone/`
- [ ] Mapa de status carrega
- [ ] Dispositivos aparecem no mapa
- [ ] Status Zabbix sincronizado

---

## 📁 Estrutura do Projeto

```
provemaps_beta/
├── backend/                      # Django 5.x application
│   ├── core/                     # Configuração principal
│   ├── inventory/                # Gestão de cabos e dispositivos
│   ├── monitoring/               # Integração Zabbix
│   ├── integrations/             # APIs externas
│   └── manage.py                 # Django CLI
│
├── frontend/                     # Vue 3 + Vite
│   ├── src/
│   │   ├── providers/maps/       # 🆕 Provider Pattern
│   │   │   ├── IMapProvider.js
│   │   │   ├── MapboxProvider.js
│   │   │   ├── GoogleMapsProvider.js
│   │   │   └── MapProviderFactory.js
│   │   ├── components/
│   │   ├── features/
│   │   └── utils/mapUtils.js     # 🆕 Utilidades
│   └── package.json
│
├── docker/                       # Docker Compose
│   ├── docker-compose.yml
│   └── nginx/
│
├── doc/                          # Documentação
│   ├── features/
│   │   └── MAP_PROVIDER_PATTERN.md  # 🆕 Arquitetura detalhada
│   └── roadmap/
│       └── network-design-improvements.md  # 🆕 Melhorias planejadas
│
├── database/                     # Scripts SQL
├── .env.example                  # Template de configuração
└── README.md                     # Documentação principal
```

---

## 🔧 Comandos Úteis

### Docker
```bash
# Ver logs do container web
docker compose -f docker/docker-compose.yml logs -f web

# Reiniciar aplicação
docker compose -f docker/docker-compose.yml restart web

# Parar todos os containers
docker compose -f docker/docker-compose.yml down

# Reconstruir containers (após mudanças)
docker compose -f docker/docker-compose.yml up -d --build
```

### Django
```bash
# Acessar shell do container
docker compose -f docker/docker-compose.yml exec web bash

# Dentro do container:
python manage.py migrate            # Aplicar migrations
python manage.py createsuperuser    # Criar novo admin
python manage.py collectstatic      # Coletar arquivos estáticos
```

### Frontend
```bash
# Instalar dependências (se node_modules não existir)
cd frontend
npm install

# Build para produção
npm run build

# Desenvolvimento local (fora do Docker)
npm run dev
```

---

## 🐛 Solução de Problemas

### Problema: Mapa não carrega no NetworkDesign
**Sintomas**: Tela cinza, console mostra erros
**Soluções**:
1. Verificar se provider está configurado em **Sistema > Configurações > Mapas**
2. Verificar se token/API key é válido
3. Abrir console do navegador (F12) e verificar erros
4. Recarregar página com Ctrl+Shift+R (hard refresh)

### Problema: Erro 403 ao salvar cabo
**Sintomas**: "Forbidden" ao clicar "Save"
**Solução**:
1. Recarregar página (F5)
2. Fazer logout e login novamente
3. Verificar logs: `docker compose logs -f web`

### Problema: Dispositivos não aparecem no mapa
**Sintomas**: Formulário de criação de cabo vazio
**Soluções**:
1. Verificar se Zabbix está configurado corretamente
2. Ir em **Inventário > Dispositivos** e verificar se há dispositivos
3. Verificar se dispositivos têm latitude/longitude configuradas
4. Executar sync: `docker compose exec web python manage.py sync_zabbix_inventory`

### Problema: Container não inicia
**Sintomas**: `docker compose up` falha
**Soluções**:
1. Verificar porta 8100 não está em uso: `netstat -ano | findstr :8100`
2. Verificar Docker Desktop está rodando
3. Verificar logs: `docker compose logs web`
4. Remover volumes antigos: `docker compose down -v`

---

## 📊 Arquivos Excluídos do Backup

Por questões de tamanho e segurança, os seguintes arquivos/pastas **NÃO** estão inclusos:

- `node_modules/` - Executar `npm install` para instalar
- `venv/` - Python virtual environment (Docker gerencia)
- `__pycache__/`, `*.pyc` - Cache Python
- `staticfiles/` - Gerado por `collectstatic`
- `media/` - Uploads de usuários
- `logs/` - Arquivos de log
- `.git/` - Histórico Git (use clone do GitHub)
- Bancos de dados SQLite de teste

---

## 📚 Documentação Completa

### Documentos Técnicos
- **Provider Pattern**: [`doc/features/MAP_PROVIDER_PATTERN.md`](doc/features/MAP_PROVIDER_PATTERN.md)
  - Arquitetura detalhada
  - Exemplos de código
  - Problemas resolvidos durante implementação
  
- **Roadmap de Melhorias**: [`doc/roadmap/network-design-improvements.md`](doc/roadmap/network-design-improvements.md)
  - 12 melhorias propostas
  - Matriz de priorização
  - Exemplos de implementação

### Guias de Início
- **Docker Quickstart**: [`DOCKER_QUICKREF.md`](DOCKER_QUICKREF.md)
- **README Principal**: [`README.md`](README.md)

### APIs
- **Backend API**: http://localhost:8100/api/
- **Documentação Swagger**: http://localhost:8100/api/schema/swagger/

---

## 🎯 Próximas Melhorias Planejadas

### Sprint 1 - Visual (1 semana)
- Indicadores visuais de origem/destino (marcadores diferenciados)
- Preview antes de salvar (modal de confirmação)
- Copiar cabo como template

### Sprint 2 - Validações (1 semana)
- Validação em tempo real (portas em uso)
- Prevenção de conflitos (nomes duplicados)
- Autocomplete de dispositivos

### Sprint 3 - Edição Avançada (2 semanas)
- Undo/Redo
- Edição interativa de vértices (Mapbox GL Draw)
- Importar GeoJSON/GPX

---

## 🤝 Suporte

### Reportar Problemas
- **GitHub Issues**: https://github.com/kaled182/provemaps_beta/issues
- Incluir:
  - Versão do backup
  - Logs relevantes
  - Screenshots de erros
  - Passos para reproduzir

### Contato
- **Repositório**: https://github.com/kaled182/provemaps_beta
- **Branch desta versão**: `refactor/lazy-load-map-providers`

---

## ✅ Checklist Pré-Distribuição

Antes de enviar este pacote para testes, verificar:

- [x] Código commitado no GitHub
- [x] Documentação atualizada
- [x] Backup criado e testado
- [x] README de distribuição incluído
- [x] Todos os testes manuais passando
- [x] Provider pattern funcionando com Mapbox
- [x] Provider pattern funcionando com Google Maps
- [x] CSRF token corrigido
- [x] NetworkDesign totalmente funcional

---

**Versão do Backup**: v2.1.0  
**Data de Criação**: 05/03/2026 01:11:58  
**Tamanho**: 2.68 MB  
**Formato**: tar.gz (compatível Windows/Linux/Mac)  

**Status**: ✅ **PRONTO PARA TESTES**
