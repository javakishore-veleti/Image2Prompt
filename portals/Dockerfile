# Builds BOTH Angular portals and serves them from a single nginx (one Fargate
# task serves both). CI/ECS build only. Build context = repo root.
#   /         -> customer-portal
#   /admin/   -> admin-portal
FROM node:20-alpine AS build
WORKDIR /build

COPY portals/customer-portal/package.json portals/customer-portal/package-lock.json* portals/customer-portal/
RUN cd portals/customer-portal && npm install
COPY portals/customer-portal portals/customer-portal
RUN cd portals/customer-portal && npm run build

COPY portals/admin-portal/package.json portals/admin-portal/package-lock.json* portals/admin-portal/
RUN cd portals/admin-portal && npm install
COPY portals/admin-portal portals/admin-portal
RUN cd portals/admin-portal && npm run build -- --base-href=/admin/

FROM nginx:alpine
# Served as an envsubst template: the entrypoint renders CSP_* vars into the
# config at container start. Override these in the ECS task def for cross-origin
# API (CSP_CONNECT_SRC) or report-only rollout (CSP_HEADER_NAME).
ENV CSP_HEADER_NAME="Content-Security-Policy" \
    CSP_CONNECT_SRC="'self'" \
    CSP_REPORT_URI="/api/csp-report" \
    HSTS_MAX_AGE="0" \
    NGINX_ENVSUBST_FILTER="^(CSP_|HSTS_)"
COPY portals/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /build/portals/customer-portal/dist/customer-portal/browser /usr/share/nginx/html
COPY --from=build /build/portals/admin-portal/dist/admin-portal/browser /usr/share/nginx/html/admin
EXPOSE 80
