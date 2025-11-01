# 🚀 Setup Redis + Serviços no Windows

## 📋 Pré-requisitos

- Windows 10/11
- Python 3.13 já instalado ✅
- Django rodando ✅

---

## 🔴 Opção 1: Redis via Docker (Recomendado)

### Vantagens
- ✅ Instalação mais rápida
- ✅ Isolado do sistema
- ✅ Fácil de remover
- ✅ Mesma versão que produção

### Instalação

#### 1. Instalar Docker Desktop
```powershell
# Baixe e instale do site oficial:
# https://www.docker.com/products/docker-desktop/

# Ou use winget (Windows Package Manager)
winget install Docker.DockerDesktop
```

#### 2. Iniciar Docker Desktop
- Abra o Docker Desktop após instalação
- Aguarde inicializar (ícone fica verde)

#### 3. Rodar Redis
```powershell
# Redis standalone
docker run -d --name redis-mapspro -p 6379:6379 redis:alpine

# Verificar se está rodando
docker ps

# Logs
docker logs redis-mapspro

# Parar
docker stop redis-mapspro

# Iniciar novamente
docker start redis-mapspro

# Remover (se necessário)
docker rm -f redis-mapspro
```

---

## 🔴 Opção 2: Redis Nativo no Windows

### Vantagens
- ✅ Sem necessidade de Docker
- ✅ Startup automático possível

### Desvantagens
- ⚠️ Redis oficial não suporta Windows
- ⚠️ Usa port não-oficial da Microsoft (descontinuado)

### Instalação

#### Via Chocolatey
```powershell
# Instalar Chocolatey (se ainda não tem)
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Instalar Redis
choco install redis-64 -y

# Iniciar serviço
redis-server --service-start

# Verificar status
redis-cli ping
# Deve retornar: PONG
```

#### Via Download Manual
```powershell
# 1. Baixar de: https://github.com/tporadowski/redis/releases
# 2. Extrair para C:\Redis
# 3. Adicionar ao PATH

# Iniciar Redis
cd C:\Redis
redis-server.exe

# Em outro terminal, testar
redis-cli ping
```

---

## 🔴 Opção 3: Redis via WSL2 (Windows Subsystem for Linux)

### Vantagens
- ✅ Redis oficial/nativo Linux
- ✅ Performance melhor que Docker Desktop
- ✅ Mais leve

### Instalação

```powershell
# 1. Instalar WSL2
wsl --install

# 2. Reiniciar o computador

# 3. Abrir Ubuntu WSL
wsl

# 4. Dentro do WSL, instalar Redis
sudo apt update
sudo apt install redis-server -y

# 5. Iniciar Redis
sudo service redis-server start

# 6. Verificar
redis-cli ping
# Deve retornar: PONG

# 7. Voltar ao Windows
exit
```

---

## ✅ Verificar Instalação

### Teste de Conexão Python
```powershell
# No diretório do projeto
python -c "import redis; r = redis.Redis(host='localhost', port=6379); print('✅ Redis conectado!', r.ping())"
```

Deve exibir:
```
✅ Redis conectado! True
```

### Teste via Django
```powershell
python manage.py shell
```

```python
from django.core.cache import cache

# Testar set
cache.set('test_key', 'Hello Redis!', 30)

# Testar get
print(cache.get('test_key'))  # Deve exibir: Hello Redis!

# Limpar
cache.delete('test_key')
exit()
```

---

## 🔧 Configuração do Projeto

### 1. Atualizar .env
```bash
# Adicione ou descomente:
REDIS_URL=redis://localhost:6379/0

# Para WSL2 ou Docker com rede específica, use o IP adequado
# REDIS_URL=redis://172.x.x.x:6379/0
```

### 2. Reiniciar Servidor Django
```powershell
# CTRL+C no terminal do servidor
python manage.py runserver 0.0.0.0:8000
```

### 3. Verificar Logs
Agora você **não** deve ver mais:
```
[DEBUG] Cache offline (Redis indisponível)
```

Deve ver cache funcionando normalmente (sem logs, pois está operacional).

---

## 🎯 Serviços Adicionais

### Celery Worker (Tarefas Assíncronas)

```powershell
# Terminal separado - Worker
celery -A core worker -l info --pool=solo

# Pool=solo é necessário no Windows (threads não funcionam bem)
```

### Celery Beat (Tarefas Agendadas)

```powershell
# Terminal separado - Beat
celery -A core beat -l info
```

### Todos os Serviços Juntos

**Terminal 1 - Django:**
```powershell
python manage.py runserver 0.0.0.0:8000
```

**Terminal 2 - Celery Worker:**
```powershell
celery -A core worker -l info --pool=solo
```

**Terminal 3 - Celery Beat:**
```powershell
celery -A core beat -l info
```

**Terminal 4 - Redis (se não for serviço):**
```powershell
redis-server
# Ou docker start redis-mapspro
```

---

## 🐛 Troubleshooting

### Redis não conecta

**Erro:** `ConnectionRefusedError: [WinError 10061]`

**Solução:**
```powershell
# Verificar se Redis está rodando
redis-cli ping

# Se não responder:
# Docker: docker start redis-mapspro
# Nativo: redis-server --service-start
# WSL2: wsl -d Ubuntu -e sudo service redis-server start
```

### Celery não inicia no Windows

**Erro:** `AttributeError: 'module' object has no attribute 'Poll'`

**Solução:**
```powershell
# SEMPRE use --pool=solo no Windows
celery -A core worker -l info --pool=solo
```

### Porta 6379 já em uso

```powershell
# Ver qual processo está usando
netstat -ano | findstr :6379

# Matar processo (substitua PID)
taskkill /PID <número> /F

# Ou usar outra porta no .env
# REDIS_URL=redis://localhost:6380/0
```

### Redis perde dados ao reiniciar

```powershell
# Habilitar persistência (Docker)
docker run -d --name redis-mapspro -p 6379:6379 -v redis-data:/data redis:alpine redis-server --appendonly yes

# Nativo: editar redis.conf
# appendonly yes
# save 900 1
```

---

## 📊 Monitoramento

### Redis CLI
```powershell
# Conectar
redis-cli

# Comandos úteis:
INFO                  # Estatísticas gerais
DBSIZE                # Número de chaves
KEYS *                # Listar todas as chaves (NÃO usar em produção!)
MONITOR               # Ver comandos em tempo real
CLIENT LIST           # Ver conexões ativas
CONFIG GET maxmemory  # Ver configuração de memória
```

### Django Admin
```powershell
# Ver métricas do cache
curl http://localhost:8000/metrics/metrics | findstr cache
```

---

## 🚀 Quickstart (Docker - Mais Rápido)

```powershell
# 1. Instalar Docker Desktop (se não tiver)
winget install Docker.DockerDesktop

# 2. Abrir Docker Desktop e aguardar inicializar

# 3. Rodar Redis
docker run -d --name redis-mapspro -p 6379:6379 redis:alpine

# 4. Verificar
docker ps
python -c "import redis; print(redis.Redis().ping())"

# 5. Atualizar .env
# REDIS_URL=redis://localhost:6379/0

# 6. Reiniciar Django
python manage.py runserver 0.0.0.0:8000

# ✅ Pronto!
```

---

## 🔗 Links Úteis

- **Redis Official:** https://redis.io/
- **Redis Docker Hub:** https://hub.docker.com/_/redis
- **Redis Windows (Tporadowski):** https://github.com/tporadowski/redis
- **Celery Windows Issues:** https://docs.celeryq.dev/en/stable/faq.html#does-celery-support-windows

---

**Qual opção você prefere?** 

- 🐳 **Opção 1 (Docker)** - Mais simples, recomendado
- 💻 **Opção 2 (Nativo)** - Se não quiser Docker
- 🐧 **Opção 3 (WSL2)** - Se já usa Linux no Windows
