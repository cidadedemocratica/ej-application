FROM besouro/ej-server:staging as django

FROM nginx:1.13

COPY ./besouro/docker/production/api/default.conf /etc/nginx/conf.d/default.conf

COPY --from=django /app/local/static/ /usr/share/nginx/html/static/
