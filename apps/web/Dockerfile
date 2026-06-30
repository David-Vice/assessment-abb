FROM node:24-slim AS builder
WORKDIR /app
RUN corepack enable

# Workspace manifests first — layer-cached as long as lock file doesn't change.
COPY apps/web/package.json apps/web/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# Source
COPY apps/web/ ./

# Vite bakes these at build time (browser talks directly to published host ports).
ARG VITE_CHAT_URL=http://localhost:8002
ARG VITE_INGESTION_URL=http://localhost:8001
ARG VITE_ANALYTICS_URL=http://localhost:8003
ENV VITE_CHAT_URL=$VITE_CHAT_URL \
    VITE_INGESTION_URL=$VITE_INGESTION_URL \
    VITE_ANALYTICS_URL=$VITE_ANALYTICS_URL

RUN pnpm build

FROM nginx:1.27-alpine AS runtime
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
