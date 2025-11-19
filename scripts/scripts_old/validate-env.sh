#!/bin/bash

# ======================================
# 📜 VALIDADOR .env PARA O MAPSPROVE
# ======================================
# Versão 1.1 - Março 2025
# ======================================

# Cores para mensagens
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Arquivos de ambiente
ENV_FILE={1:-.env}
EXAMPLE_FILE={2:-.env.example}
SILENT=false

# Log de validação
LOG_FILE="logs/env_validation_$(date +%Y%m%d_%H%M%S).log"
mkdir -p logs

if [[ "$1" == "--silent" ]]; then
  SILENT=true
  ENV_FILE=".env"
  EXAMPLE_FILE=".env.example"
fi

log() {
  [[ "$SILENT" = false ]] && echo -e "$1"
  echo -e "$(date '+%F %T') $1" >> "$LOG_FILE"
}

# Verifica variáveis ausentes
check_missing_vars() {
  log "\n${YELLOW}🔍 Verificando variáveis ausentes...${NC}"
  REQUIRED_VARS=$(grep -oE '^[A-Z][A-Z0-9_]+=' "$EXAMPLE_FILE" | cut -d '=' -f1 | sort | uniq)
  MISSING_COUNT=0
  for var in $REQUIRED_VARS; do
    if ! grep -q "^$var=" "$ENV_FILE"; then
      log "${RED}❌ Ausente: $var${NC}"
      suggest=$(grep "^$var=" "$EXAMPLE_FILE" | cut -d '=' -f2-)
      log "${YELLOW}💡 Sugestão: $var=$suggest${NC}"
      ((MISSING_COUNT++))
    fi
  done
  if [ "$MISSING_COUNT" -eq 0 ]; then
    log "${GREEN}✅ Todas variáveis obrigatórias presentes!${NC}"
  else
    log "\n${RED}⚠️  $MISSING_COUNT variável(is) ausente(s)${NC}"
  fi
}

# Verifica valores inseguros
check_unsafe_values() {
  log "\n${YELLOW}🔒 Verificando valores inseguros...${NC}"
  DANGEROUS_PATTERNS=("your_password" "123456" "admin" "changeme")
  UNSAFE_COUNT=0
  for pattern in "${DANGEROUS_PATTERNS[@]}"; do
    while IFS= read -r line; do
      if [[ "$line" == *"$pattern"* ]]; then
        var_name=$(echo "$line" | cut -d '=' -f1)
        log "${RED}❌ Valor inseguro em: $var_name${NC}"
        ((UNSAFE_COUNT++))
      fi
    done < "$ENV_FILE"
  done
  if [ "$UNSAFE_COUNT" -eq 0 ]; then
    log "${GREEN}✅ Nenhum valor inseguro detectado!${NC}"
  else
    log "\n${RED}⚠️  $UNSAFE_COUNT valor(es) inseguros${NC}"
  fi
}

# Valida Google Maps API Key
check_gmaps_key() {
  GMAPS_KEY=$(grep '^GOOGLE_MAPS_API_KEY=' "$ENV_FILE" | cut -d '=' -f2)
  if [[ -z "$GMAPS_KEY" ]]; then
    log "${RED}❌ Google Maps API Key não configurada${NC}"
  elif [[ "$GMAPS_KEY" == "your_google_maps_api_key_here" ]]; then
    log "${RED}❌ Google Maps API Key está com valor padrão${NC}"
  elif [[ ! "$GMAPS_KEY" =~ ^AIza[0-9A-Za-z_-]{35}$ ]]; then
    log "${YELLOW}⚠️  Google Maps API Key com formato suspeito${NC}"
  else
    log "${GREEN}✅ Google Maps API Key válida${NC}"
  fi
}

# Verifica emails válidos
check_email_format() {
  log "\n${YELLOW}📧 Verificando formato de e-mails...${NC}"
  EMAILS=$(grep -E '^(SMTP_USER|SMTP_FROM_EMAIL)=' "$ENV_FILE" | cut -d '=' -f2)
  for email in $EMAILS; do
    if [[ ! "$email" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
      log "${YELLOW}⚠️  E-mail com formato suspeito: $email${NC}"
    else
      log "${GREEN}✅ E-mail válido: $email${NC}"
    fi
  done
}

# Principal
main() {
  if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}❌ Arquivo $ENV_FILE não encontrado${NC}"
    echo -e "Use: cp .env.example .env"
    exit 1
  fi
  log "\n${GREEN}=== VALIDAÇÃO DO ARQUIVO $ENV_FILE ===${NC}"
  check_missing_vars
  check_unsafe_values
  check_gmaps_key
  check_email_format
  log "\n${YELLOW}ℹ️  Log salvo em: $LOG_FILE${NC}"
}

main
