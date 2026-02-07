#!/bin/bash

# ==============================================
# CONFIGURAÇÕES GLOBAIS
# ==============================================
DB_USER="mapsprove_user"
DB_PASS=$(openssl rand -base64 16)  # Senha aleatória forte
DB_NAME="mapsprove_db"
PROJECT_DIR="$HOME/mapsprove"
LOG_FILE="/var/log/mapsprove_setup_$(date +%Y%m%d_%H%M%S).log"  # Log com timestamp
SYSTEM_USER=$(logname)  # Usuário real (mesmo com sudo)

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ==============================================
# FUNÇÕES PRINCIPAIS
# ==============================================

# Logger aprimorado com níveis e cores
log() {
    local level=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        "INFO") echo -e "${BLUE}[${timestamp} INFO] ${message}${NC}" | tee -a $LOG_FILE ;;
        "WARN") echo -e "${YELLOW}[${timestamp} WARN] ${message}${NC}" | tee -a $LOG_FILE ;;
        "ERROR") echo -e "${RED}[${timestamp} ERROR] ${message}${NC}" | tee -a $LOG_FILE ;;
        "SUCCESS") echo -e "${GREEN}[${timestamp} SUCCESS] ${message}${NC}" | tee -a $LOG_FILE ;;
        *) echo "[${timestamp} ${level}] ${message}" | tee -a $LOG_FILE ;;
    esac
}

# Instalador de pacotes com verificação
install_package() {
    local package=$1
    local friendly_name=$2
    
    if dpkg -l | grep -q "^ii  $package "; then
        log "INFO" "ℹ️ $friendly_name já está instalado"
        return 0
    fi
    
    log "INFO" "📦 Instalando $friendly_name..."
    if apt install -y $package >> $LOG_FILE 2>&1; then
        log "SUCCESS" "✅ $friendly_name instalado com sucesso"
        return 0
    else
        log "ERROR" "❌ Falha crítica na instalação de $friendly_name"
        return 1
    fi
}

# Verificador de serviços
check_service() {
    local service=$1
    if systemctl is-active --quiet $service; then
        log "SUCCESS" "✅ $service está rodando corretamente"
        return 0
    else
        log "ERROR" "❌ $service não está rodando"
        systemctl status $service >> $LOG_FILE 2>&1
        return 1
    fi
}

# ==============================================
# LISTA DE PACOTES (ORGANIZADA POR CATEGORIA)
# ==============================================

declare -A PACKAGES=(
    # Básicos do sistema
    ["build-essential"]="Compiladores"
    ["libssl-dev"]="Bibliotecas SSL"
    ["zlib1g-dev"]="Biblioteca de compressão"
    
    # Servidor Web
    ["nginx"]="Servidor web Nginx"
    ["certbot"]="Certbot para SSL"
    ["python3-certbot-nginx"]="Integração Nginx+Certbot"
    
    # Banco de Dados
    ["postgresql"]="PostgreSQL"
    ["postgresql-contrib"]="Extensões PostgreSQL"
    ["postgresql-client"]="Cliente PostgreSQL"
    ["pgcli"]="CLI avançado para PostgreSQL"
    
    # Containerização
    ["docker.io"]="Docker"
    ["docker-compose-plugin"]="Docker Compose"
    
    # Node.js
    ["nodejs"]="Node.js"
    ["npm"]="Gerenciador de pacotes Node"
    
    # Utilitários
    ["git"]="Controle de versão"
    ["htop"]="Monitoramento"
    ["net-tools"]="Ferramentas de rede"
    ["jq"]="Processamento JSON"
    ["unzip"]="Descompactação"
    ["curl"]="Transferência de dados"
    ["wget"]="Download de arquivos"
    ["tmux"]="Terminal multiplexer"
    ["ufw"]="Firewall"
    ["pv"]="Monitor de progresso"
    ["gnupg2"]="GPG"
    ["fail2ban"]="Proteção contra ataques"
)

# ==============================================
# VALIDAÇÕES INICIAIS
# ==============================================

# Verificação de root
if [ "$(id -u)" -ne 0 ]; then
    echo -e "${RED}❌ Este script deve ser executado como root ou com sudo${NC}"
    exit 1
fi

# Verificação de conexão
if ! ping -c 1 google.com &> /dev/null; then
    log "ERROR" "Sem conexão com a internet. Verifique sua rede."
    exit 1
fi

log "INFO" "🚀 Iniciando configuração do servidor MapsProve..."
log "INFO" "👤 Usuário do sistema: $SYSTEM_USER"
log "INFO" "📝 Log detalhado em: $LOG_FILE"

# ==============================================
# ATUALIZAÇÃO DO SISTEMA
# ==============================================

log "INFO" "🔄 Atualizando lista de pacotes..."
if ! apt update >> $LOG_FILE 2>&1; then
    log "ERROR" "Falha ao atualizar lista de pacotes"
    exit 1
fi

log "INFO" "🛠️ Atualizando sistema..."
if ! DEBIAN_FRONTEND=noninteractive apt upgrade -y >> $LOG_FILE 2>&1; then
    log "ERROR" "Falha na atualização do sistema"
    exit 1
fi

# ==============================================
# INSTALAÇÃO DE PACOTES
# ==============================================

log "INFO" "📦 Instalando pacotes essenciais..."
for package in "${!PACKAGES[@]}"; do
    install_package "$package" "${PACKAGES[$package]}" || exit 1
done

# Configuração especial para Node.js
log "INFO" "🔧 Configurando Node.js..."
curl -fsSL https://deb.nodesource.com/setup_18.x | bash - >> $LOG_FILE 2>&1
install_package "nodejs" "Node.js" || exit 1
install_package "npm" "NPM" || exit 1
npm install -g npm@latest pm2 >> $LOG_FILE 2>&1

# ==============================================
# CONFIGURAÇÃO DE SERVIÇOS
# ==============================================

# Nginx
log "INFO" "🌐 Configurando Nginx..."
systemctl enable nginx >> $LOG_FILE 2>&1
systemctl start nginx >> $LOG_FILE 2>&1

# PostgreSQL
log "INFO" "🗃️ Configurando PostgreSQL..."
sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';" >> $LOG_FILE 2>&1
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" >> $LOG_FILE 2>&1
sudo -u postgres psql -c "ALTER SYSTEM SET listen_addresses = '*';" >> $LOG_FILE 2>&1
echo "host $DB_NAME $DB_USER 0.0.0.0/0 md5" >> /etc/postgresql/*/main/pg_hba.conf
systemctl restart postgresql >> $LOG_FILE 2>&1

# Docker
log "INFO" "🐳 Configurando Docker..."
usermod -aG docker $SYSTEM_USER >> $LOG_FILE 2>&1
systemctl enable docker >> $LOG_FILE 2>&1
systemctl start docker >> $LOG_FILE 2>&1

# Firewall
log "INFO" "🔥 Configurando firewall..."
ufw allow OpenSSH >> $LOG_FILE 2>&1
ufw allow 'Nginx Full' >> $LOG_FILE 2>&1
ufw --force enable >> $LOG_FILE 2>&1

# Fail2Ban
log "INFO" "🛡️ Configurando Fail2Ban..."
systemctl enable fail2ban >> $LOG_FILE 2>&1
systemctl start fail2ban >> $LOG_FILE 2>&1

# ==============================================
# ESTRUTURA DE DIRETÓRIOS
# ==============================================

log "INFO" "📂 Criando estrutura de diretórios..."
mkdir -p $PROJECT_DIR/{backend,frontend,database/{backups,schemas},scripts,nginx/config,logs,.ssh} >> $LOG_FILE 2>&1
chown -R $SYSTEM_USER:$SYSTEM_USER $PROJECT_DIR >> $LOG_FILE 2>&1

# Arquivo de credenciais
log "INFO" "🔐 Salvando credenciais do banco..."
cat > $PROJECT_DIR/database/.db_credentials <<EOF
# MapsProve Database Credentials
DB_HOST=localhost
DB_PORT=5432
DB_USER=$DB_USER
DB_PASS=$DB_PASS
DB_NAME=$DB_NAME

# Connection URL:
# postgresql://$DB_USER:$DB_PASS@localhost:5432/$DB_NAME
EOF

chmod 600 $PROJECT_DIR/database/.db_credentials
chown $SYSTEM_USER:$SYSTEM_USER $PROJECT_DIR/database/.db_credentials

# ==============================================
# VERIFICAÇÃO FINAL
# ==============================================

log "INFO" "🔍 Verificando serviços..."
services=("nginx" "postgresql" "docker" "fail2ban")
for service in "${services[@]}"; do
    check_service $service
done

# ==============================================
# RELATÓRIO FINAL
# ==============================================

# Copiar log para o diretório do projeto
cp $LOG_FILE $PROJECT_DIR/logs/ >> $LOG_FILE 2>&1
chown $SYSTEM_USER:$SYSTEM_USER $PROJECT_DIR/logs/*.log

# Mensagem final
echo -e "\n${GREEN}==============================================${NC}"
echo -e "${GREEN}🎉 CONFIGURAÇÃO CONCLUÍDA COM SUCESSO!${NC}"
echo -e "${GREEN}==============================================${NC}"
echo -e "\n${YELLOW}⚠️ INFORMAÇÕES IMPORTANTES:${NC}"
echo -e "• Credenciais do banco salvas em: ${BLUE}$PROJECT_DIR/database/.db_credentials${NC}"
echo -e "• Log completo da instalação: ${BLUE}$PROJECT_DIR/logs/$(basename $LOG_FILE)${NC}"
echo -e "\n${YELLOW}🚀 PRÓXIMOS PASSOS:${NC}"
echo -e "1. Reinicie sua sessão: ${BLUE}newgrp docker && exit${NC}"
echo -e "2. Acesse o diretório do projeto: ${BLUE}cd $PROJECT_DIR${NC}"
echo -e "3. Configure certificados SSL: ${BLUE}sudo certbot --nginx${NC}"
echo -e "\n${GREEN}✅ Servidor pronto para o projeto MapsProve!${NC}"

log "SUCCESS" "Configuração concluída com sucesso em $(date)"
exit 0
