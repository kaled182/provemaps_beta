FROM alfg/nginx-rtmp:latest

# Keep the upstream entrypoint happy by providing both the template and the final config
COPY nginx.conf /etc/nginx/nginx.conf.template
COPY nginx.conf /etc/nginx/nginx.conf

ENV RTMP_PORT=1935 \
    HTTP_PORT=8080
