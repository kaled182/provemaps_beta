# 📂 scripts/

Este diretório contém scripts automatizados para infraestrutura, deploy e manutenção do sistema **MapsProve**.

---

## 📁 Estrutura do Diretório

```text
scripts/
├── infra/                  # Infraestrutura principal
│   ├── setup-server.sh     # Provisionamento completo do servidor
│   ├── deploy.sh           # Deploy automatizado
│   └── backup/
│       ├── db-backup.sh    # Backup do PostgreSQL
│       └── restore-db.sh   # Restauração de banco
├── tools/                  # Utilitários
│   ├── monitor.sh          # Monitoramento de recursos
│   └── cleanup.sh          # Limpeza de arquivos temporários
└── LICENSE                 # Licença MIT
```

---

## 🚀 Script Principal: `setup-server.sh`

### 🔍 Visão Geral

Configuração automatizada de servidor Ubuntu para o MapsProve incluindo:

- 🟢 Node.js + npm  
- 🗃️ PostgreSQL  
- 🌐 Nginx + Certbot (SSL)  
- 🐳 Docker + Docker Compose  
- 🛡️ Segurança: UFW + Fail2Ban  

---

## 📋 Pré-requisitos

### Sistema Operacional

```text
- Ubuntu Server 22.04 LTS (recomendado)
- Acesso root/sudo
- Conexão com internet
```

### Hardware Mínimo

| Componente   | Especificação |
|--------------|----------------|
| CPU          | 2 vCPUs        |
| Memória RAM  | 4GB            |
| Armazenamento| 20GB SSD       |

---

## ⚡ Modos de Execução

```bash
# Execução completa (recomendado)
sudo bash scripts/infra/setup-server.sh --full

# Modos específicos:
--node-only     # Instala apenas Node.js
--db-only       # Configura apenas PostgreSQL
--docker-only   # Instala apenas Docker
--security      # UFW + Fail2Ban
```

---

## 📂 Estrutura Gerada

```text
~/mapsprove/
├── backend/              # Código backend
├── frontend/             # Código frontend
├── database/
│   ├── .db_credentials   # Arquivo protegido (chmod 600)
│   └── backups/          # Backups automáticos
└── logs/
    └── setup.log         # Log detalhado
```

---

## 🔄 Fluxo de Trabalho

### Configuração Inicial

```bash
sudo bash scripts/infra/setup-server.sh --full
```

### Deploy Diário

```bash
bash scripts/infra/deploy.sh --env=production
```

### Backup Automático (via cron)

```bash
0 2 * * * bash ~/mapsprove/scripts/infra/backup/db-backup.sh
```

---

## 🔐 Melhores Práticas

| Prática             | Comando                                  |
|---------------------|-------------------------------------------|
| Validar sintaxe     | `bash -n setup-server.sh`                |
| Proteger credenciais| `chmod 600 *.credentials`                |
| Monitorar recursos  | `bash scripts/tools/monitor.sh`          |

---

## 🛠️ Troubleshooting

### Problemas Comuns

#### 1. Pacotes não encontrados

```bash
sudo apt update && sudo apt --fix-broken install
```

#### 2. Erros no PostgreSQL

```bash
sudo systemctl status postgresql
sudo journalctl -u postgresql --since "1 hour ago"
```

#### 3. Problemas de Permissão

```bash
sudo chown -R $USER:$USER ~/mapsprove
sudo chmod -R 755 ~/mapsprove/logs
```

---

## 📜 Licença

Este projeto está licenciado sob a **MIT License**.

---

## 📞 Contato

| Tipo               | Detalhes                              |
|--------------------|----------------------------------------|
| Responsável Técnico| [paulo@msimplesinternet.net.br](mailto:paulo@msimplesinternet.net.br) |
| Reportar Bugs      | [GitHub Issues](https://github.com/kaled182/mapsprove/issues)         |

---

⬆️ [Voltar ao topo](#scripts)
