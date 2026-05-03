FROM nginx:alpine

# certbot via pip (alpine compatible)
RUN apk add --no-cache python3 py3-pip augeas-libs \
    && pip3 install --no-cache-dir certbot --break-system-packages 2>/dev/null \
    || pip3 install --no-cache-dir certbot

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
