# One recipe for both frontend apps. Build from the repo root so workspace packages are included:
#   docker build -f infra/web/Dockerfile --build-arg APP=console -t booking-core/console .
#   docker build -f infra/web/Dockerfile --build-arg APP=member  -t booking-core/member .
# Pin the Node and nginx versions the team standardises on.

FROM node:24-alpine AS build
ARG APP
WORKDIR /repo
RUN corepack enable
COPY . .
RUN pnpm install --frozen-lockfile
RUN pnpm --filter "${APP}..." build

FROM nginx:1.27-alpine
ARG APP
ENV APP_NAME=${APP}
COPY infra/web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --chmod=755 infra/web/40-runtime-config.sh /docker-entrypoint.d/40-runtime-config.sh
COPY --from=build /repo/apps/${APP}/dist /usr/share/nginx/html
