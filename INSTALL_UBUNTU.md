# Guia de Instalação — Ubuntu Linux

**Requisitos:** Ubuntu 22.04 LTS ou 24.04 LTS · 4 GB RAM mínimo (8 GB recomendado) · 20 GB de disco livre

---

## 1. Instalar Docker e Docker Compose

```bash
# Atualizar pacotes
sudo apt-get update

# Instalar dependências
sudo apt-get install -y ca-certificates curl gnupg

# Adicionar repositório oficial do Docker
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Instalar Docker Engine + Compose
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Adicionar seu usuário ao grupo docker (evitar sudo em todo comando)
sudo usermod -aG docker $USER
newgrp docker

# Iniciar o serviço Docker e habilitar no boot
sudo systemctl start docker
sudo systemctl enable docker

# Verificar instalação
docker --version
docker compose version
```

---

## 2. Instalar Node.js (para build do frontend)

O frontend Vue 3 precisa ser compilado no servidor, **fora do Docker**.

```bash
# Instalar Node.js 20 LTS via NodeSource
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Verificar
node --version   # deve mostrar v20.x.x
npm --version
```

---

## 3. Clonar o repositório

```bash
# Escolha onde instalar (exemplo: /opt/provemaps)
sudo mkdir -p /opt/provemaps
sudo chown $USER:$USER /opt/provemaps

git clone https://github.com/kaled182/provemaps_beta.git /opt/provemaps
cd /opt/provemaps
```

---

## 4. Criar o arquivo .env (mínimo, sem edição necessária)

O `.env` precisa existir, mas pode estar **completamente vazio** — todas as configurações essenciais já estão no `docker/docker-compose.yml`. As configurações de Zabbix, Google Maps e SMTP são feitas pelo painel web após a instalação.

```bash
touch /opt/provemaps/.env
```

> **Configuração avançada (opcional):** Se quiser sobrescrever alguma variável padrão, copie o exemplo e edite:
> ```bash
> cp /opt/provemaps/.env.example /opt/provemaps/.env
> nano /opt/provemaps/.env
> ```
>
> Variáveis que podem ser úteis sobrescrever em produção:
>
> | Variável | Descrição |
> |---|---|
> | `SECRET_KEY` | Chave secreta Django (padrão inseguro já definido no compose) |
> | `FERNET_KEY` | Gerada automaticamente na primeira inicialização |
> | `GOOGLE_MAPS_API_KEY` | Chave Google Maps (pode ser configurada pelo painel web) |

---

## 5. Compilar o frontend (Vue 3)

Este passo deve ser executado **no servidor, fora do Docker**:

```bash
cd /opt/provemaps/frontend

# Instalar dependências Node
npm install

# Compilar o frontend
npm run build
```

Isso gera os arquivos em `backend/staticfiles/vue-spa/`, que o Docker monta automaticamente.

---

## 6. Subir os serviços com Docker Compose

```bash
cd /opt/provemaps/docker

# Subir todos os serviços em background
docker compose up -d
```

Na primeira inicialização, o Docker vai:
- Baixar as imagens base (~2–5 minutos dependendo da internet)
- Construir a imagem da aplicação
- Iniciar PostgreSQL + PostGIS, Redis e todos os serviços
- Executar migrações do banco automaticamente
- Criar o superusuário padrão automaticamente

**Verificar se os serviços subiram:**

```bash
docker compose ps
```

Todos os serviços devem estar com status `Up` ou `healthy`.

---

## 7. Verificar saúde da aplicação

```bash
# Health check básico (aguardar ~30 segundos após o up -d)
curl http://localhost:8100/healthz

# Deve retornar algo como: {"status": "ok", ...}
```

Se retornar erro, verifique os logs:

```bash
# Logs de todos os serviços
docker compose logs -f

# Logs apenas da aplicação web
docker compose logs -f web
```

---

## 8. Primeiro acesso

Abra o navegador e acesse:

```
http://SEU_IP_OU_DOMINIO:8100
```

**Credenciais padrão:**
- Usuário: `admin`
- Senha: `admin123`

> **Troque a senha imediatamente após o primeiro login!**
> Acesse: http://SEU_IP:8100/admin → clique no usuário `admin` → altere a senha.

---

## 9. Configuração inicial (Setup Wizard)

Após o login, acesse o painel de configuração:

```
http://SEU_IP:8100/setup_app/
```

Configure:
1. **Servidor de monitoramento** — adicione suas credenciais Zabbix
2. **Perfil da empresa** — nome, logotipo
3. **Gateways de notificação** — WhatsApp, Telegram, e-mail (opcional)
4. **Templates de alerta** — mensagens para cada tipo de evento

---

## Portas dos serviços

| Serviço | Porta local | Descrição |
|---|---|---|
| Aplicação web | `8100` | Interface principal |
| PostgreSQL | `5433` | Banco de dados (acesso externo) |
| Redis | `6380` | Cache e broker |
| Prometheus | `9090` | Métricas |
| Grafana | `3002` | Dashboards de métricas |
| Video HLS | `8083` | Player de câmeras |
| WhatsApp QR | `3001` | Serviço de notificação WhatsApp |

---

## Comandos úteis

```bash
# Parar todos os serviços
cd /opt/provemaps/docker
docker compose down

# Reiniciar apenas a aplicação web
docker compose restart web

# Ver logs em tempo real
docker compose logs -f web

# Executar comando Django no container
docker compose exec web python manage.py shell

# Backup do banco de dados
docker compose exec postgres pg_dump -U app app > backup_$(date +%Y%m%d).sql
```

---

## Atualização

```bash
cd /opt/provemaps

# Baixar atualizações
git pull

# Recompilar o frontend se houver alterações
cd /opt/provemaps/frontend
npm install
npm run build
cd /opt/provemaps

# Rebuild e restart dos containers
cd docker
docker compose build
docker compose up -d
```

---

## Solução de problemas

**Containers não sobem:**
```bash
docker compose logs postgres   # verificar se o banco iniciou corretamente
docker compose logs web        # verificar erros da aplicação
```

**Erro de permissão no Docker:**
```bash
sudo usermod -aG docker $USER
# Fazer logout e login novamente, ou executar:
newgrp docker
```

**Frontend não carrega (tela em branco):**
```bash
# Verificar se o build foi executado
ls backend/staticfiles/vue-spa/

# Se vazio, executar novamente fora do Docker:
cd /opt/provemaps/frontend
npm run build
docker compose restart web
```

**Erro `PermissionError` no collectstatic (web não sobe):**

O container monta o diretório `backend/` do host como volume. Se `staticfiles/` tiver arquivos com permissão errada de execuções anteriores, o collectstatic falha.

```bash
# Remover arquivos estáticos gerados (exceto vue-spa)
find /opt/provemaps/backend/staticfiles/ -maxdepth 1 -type f -delete  # apaga só arquivos na raiz, sem entrar em vue-spa/
chmod -R 755 /opt/provemaps/backend/staticfiles/
docker compose restart web
```

**Conexão com Zabbix falha:**
- Verifique se `ZABBIX_API_URL` no `.env` está acessível a partir do servidor
- Teste: `curl http://SEU_ZABBIX/api_jsonrpc.php`
- Verifique as credenciais no Setup Wizard em `/setup_app/`
