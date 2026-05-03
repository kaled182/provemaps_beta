#!/bin/sh
# nginx + certbot entrypoint
# - Sem domínio: sobe em HTTP puro (porta 80), proxies para web:8000
# - Com domínio:  obtém certificado Let's Encrypt e sobe em HTTPS (80+443)
#   Renova automaticamente a cada 12h

set -e

DOMAIN="${DOMAIN_NAME:-}"
EMAIL="${CERTBOT_EMAIL:-}"
SETUP_DIR="/etc/nginx/setup"
CONF_DIR="/etc/nginx/conf.d"
CERT_PATH="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"

log()  { echo "[nginx-init] $*"; }
ok()   { echo "[nginx-init] ✓ $*"; }
warn() { echo "[nginx-init] ⚠ $*"; }

# ── Renovação automática a cada 12h ──────────────────────────────────────────
start_renewal_loop() {
    (
        while true; do
            sleep 12h
            log "Renovando certificado..."
            certbot renew --webroot -w /var/www/certbot --quiet \
                && nginx -s reload \
                && ok "Certificado renovado"
        done
    ) &
}

# ── Modo HTTP puro (sem domínio) ──────────────────────────────────────────────
start_http_only() {
    log "Modo HTTP — sem domínio configurado"
    cp "${SETUP_DIR}/http.conf" "${CONF_DIR}/default.conf"
    start_renewal_loop
    exec nginx -g "daemon off;"
}

# ── Sem domínio → HTTP ────────────────────────────────────────────────────────
if [ -z "$DOMAIN" ]; then
    start_http_only
fi

log "Domínio: ${DOMAIN} — configurando HTTPS"

# ── Inicia nginx temporariamente com HTTP para o desafio ACME ─────────────────
cp "${SETUP_DIR}/http.conf" "${CONF_DIR}/default.conf"
nginx &
NGINX_BG=$!
sleep 2   # aguarda nginx aceitar conexões

# ── Obtém certificado se ainda não existir ────────────────────────────────────
if [ ! -f "$CERT_PATH" ]; then
    log "Solicitando certificado para ${DOMAIN}..."

    CERT_ARGS="certonly --webroot -w /var/www/certbot \
        -d ${DOMAIN} --non-interactive --agree-tos"

    if [ -n "$EMAIL" ]; then
        CERT_ARGS="${CERT_ARGS} --email ${EMAIL}"
    else
        CERT_ARGS="${CERT_ARGS} --register-unsafely-without-email"
    fi

    if certbot ${CERT_ARGS}; then
        ok "Certificado obtido com sucesso"
    else
        warn "Falha ao obter certificado — continuando em HTTP"
        wait $NGINX_BG
        start_http_only
    fi
fi

# ── Para nginx temporário ─────────────────────────────────────────────────────
kill $NGINX_BG 2>/dev/null || true
wait $NGINX_BG 2>/dev/null || true

# ── Ativa config HTTPS ────────────────────────────────────────────────────────
if [ -f "$CERT_PATH" ]; then
    log "Ativando HTTPS para ${DOMAIN}..."
    sed "s/DOMAIN_PLACEHOLDER/${DOMAIN}/g" \
        "${SETUP_DIR}/https.conf.template" > "${CONF_DIR}/default.conf"
    ok "HTTPS ativo → https://${DOMAIN}"
else
    warn "Certificado não encontrado — fallback HTTP"
    cp "${SETUP_DIR}/http.conf" "${CONF_DIR}/default.conf"
fi

start_renewal_loop
exec nginx -g "daemon off;"
