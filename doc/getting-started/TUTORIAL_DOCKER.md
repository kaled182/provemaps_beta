# 🐳 Guia de Implantação com Docker — MapsProveFiber

Este tutorial foi criado para quem tem pouca familiaridade com Docker e deseja subir rapidamente o ambiente completo do **MapsProveFiber** com segurança.

---

## 🧱 Estrutura dos Containers

A pilha Docker é composta pelos seguintes serviços:

| Serviço | Função |
|----------|--------|
| **web** | Django + Gunicorn + Uvicorn (porta 8000) |
| **celery** | Worker Celery (tarefas assíncronas) |
| **beat** | Agendador Celery |
| **redis** | Cache e broker de mensagens |
| **db** | Banco de dados MariaDB |

O script `docker-entrypoint.sh` é responsável por:
- Aguardar o banco e o Redis ficarem disponíveis  
- Rodar migrações automaticamente  
- Coletar arquivos estáticos  
- Iniciar o servidor web  

---

## 🚀 1. Preparação do Ambiente

### Instale Docker e Docker Compose
```bash
sudo apt install docker.io docker-compose-plugin
```

Verifique as versões:
```bash
docker --version
docker compose version
```

### Clone o repositório
```bash
git clone https://github.com/kaled182/provemaps_beta.git
cd mapsprovefiber
```

### Configure o arquivo `.env`
Copie o exemplo e ajuste as variáveis básicas:
```bash
cp .env.example .env
nano .env
```

Exemplo de valores mínimos:
```env
DB_HOST=db
DB_USER=app
DB_PASSWORD=app
REDIS_URL=redis://redis:6379/1
DJANGO_SETTINGS_MODULE=settings.dev
# Rotação automática de tokens de serviço (segundos)
SERVICE_ACCOUNT_ROTATION_INTERVAL_SECONDS=3600
# Timeouts opcionais de webhook (segundos)
SERVICE_ACCOUNT_WEBHOOK_CONNECT_TIMEOUT=3
SERVICE_ACCOUNT_WEBHOOK_READ_TIMEOUT=5
```

Esses parâmetros habilitam a rotação automática das contas de serviço. Ajuste o
intervalo conforme a política interna e configure o webhook para receber os
eventos `service_account.rotation_warning` e `service_account.token_rotated`.

---

## ⚙️ 2. Subir o Ambiente Completo

### Build e inicialização
```bash
docker compose up -d --build
```

Isso:
- Gera as imagens do Django e Celery  
- Cria os volumes persistentes (MariaDB, Redis)  
- Inicia todos os containers necessários

Verifique o status:
```bash
docker compose ps
docker compose logs -f web
```

Acesse o sistema:  
👉 **http://localhost:8000**

---

## 🧭 3. Inicialização Manual (primeira execução)

> ℹ️ **Nota:** O superuser padrão (`admin`/`admin123`) é criado automaticamente com `INIT_ENSURE_SUPERUSER=true` no docker-compose.

Se precisar executar comandos manualmente:
```bash
# Aplicar migrações (já executado automaticamente)
docker compose exec web python manage.py migrate

# Criar superuser customizado (opcional)
docker compose exec web python manage.py createsuperuser

# Collectstatic (já executado automaticamente)
docker compose exec web python manage.py collectstatic --noinput
```

---

## ⚙️ 4. Subida Automática (com script)

Use o **orquestrador de deploy** incluído no projeto:  
`scripts/deploy.sh`

```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh --compose docker-compose.yml --settings settings.prod --health http://localhost:8000/healthz
```

O script executa automaticamente:
1. `docker compose build --pull`
2. `docker compose up -d db redis`
3. Migrações + collectstatic
4. Subida dos serviços (`web`, `celery`, `beat`)
5. Verificação de `/healthz`
6. Rollback automático em caso de falha

---

## 🧪 5. Dicas para Iniciantes

| Ação | Comando |
|------|----------|
| Ver logs de um serviço | `docker compose logs -f web` |
| Reiniciar o app | `docker compose restart web` |
| Parar tudo | `docker compose down` |
| Limpar volumes | `docker compose down -v` |
| Acessar o shell Django | `docker compose exec web python manage.py shell` |

---

## 💻 6. Modo Desenvolvimento (Hot Reload)

Para que o código local recarregue automaticamente:

1. No `docker-compose.yml`, descomente:
   ```yaml
   volumes:
     - .:/app
     - ./logs:/app/logs
   ```

2. Inicie o container de desenvolvimento:
   ```bash
   docker compose up -d web
   ```

3. As alterações no código serão refletidas imediatamente.

---

## 🧰 7. Solução de Problemas

| Sintoma | Solução |
|----------|----------|
| Web não sobe | Verifique `docker compose logs web` |
| Erro de banco | Execute `docker compose exec web python manage.py migrate` |
| Healthcheck falha | Confirme as variáveis do `.env` |
| Redis inativo | Reinicie com `docker compose restart redis` |

---

## 🔄 8. Atualizações e Rollbacks

Atualize o ambiente:
```bash
git pull
docker compose build
docker compose up -d
```

Se algo der errado:
```bash
docker compose down
git checkout <commit-anterior>
docker compose up -d
```

---

## 🧩 9. Estrutura de Diretórios Relevante

```
mapsprovefiber/
├── core/                    # Núcleo Django
├── routes_builder/          # Módulo Fiber Route Builder
├── zabbix_api/              # Integração Zabbix
├── setup_app/               # Configuração inicial via painel
├── docker-compose.yml       # Stack de containers
├── Dockerfile               # Imagem base
├── docker-entrypoint.sh     # Entrypoint
├── scripts/deploy.sh        # Script de deploy automatizado
└── README.md                # Guia principal
```

---

## 🎯 Conclusão

Você agora consegue subir o ambiente completo com um único comando, mesmo sem experiência com Docker.

Para monitorar logs e métricas:
- Django: `/admin/logs/`
- Prometheus: `/metrics/`
- Healthcheck: `/healthz`

🧡 Projeto mantido por **Simples Internet**.  
Para dúvidas ou sugestões, consulte o guia [`CONTRIBUTING.md`](./CONTRIBUTING.md).
