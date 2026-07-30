# syntax=docker/dockerfile:1

FROM node:22-bookworm-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-bookworm-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
ENV DATABASE_URL="file:./prisma/build.db"
RUN node scripts/prepare-prisma-provider.js \
  && npx prisma generate \
  && npm run build \
  && npm prune --omit=dev

FROM node:22-bookworm-slim AS runner
WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=8000 \
    HOSTNAME=0.0.0.0

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    ca-certificates \
    cups-client \
    curl \
    tini \
  && rm -rf /var/lib/apt/lists/* \
  && groupadd --system --gid 10001 printdrop \
  && useradd --system --uid 10001 --gid 10001 --home-dir /app --shell /usr/sbin/nologin printdrop \
  && mkdir -p /app /data/uploads /data/tmp \
  && chown -R printdrop:printdrop /app /data

COPY --from=builder --chown=printdrop:printdrop /app/package.json /app/package-lock.json ./
COPY --from=builder --chown=printdrop:printdrop /app/node_modules ./node_modules
COPY --from=builder --chown=printdrop:printdrop /app/.next ./.next
COPY --from=builder --chown=printdrop:printdrop /app/public ./public
COPY --from=builder --chown=printdrop:printdrop /app/prisma ./prisma
COPY --from=builder --chown=printdrop:printdrop /app/scripts ./scripts
COPY --from=builder --chown=printdrop:printdrop /app/next.config.ts ./next.config.ts
COPY --from=builder --chown=printdrop:printdrop /app/tsconfig.json ./tsconfig.json
COPY --from=builder --chown=printdrop:printdrop /app/src/lib ./src/lib
COPY --from=builder --chown=printdrop:printdrop /app/src/instrumentation.ts ./src/instrumentation.ts

# tsx is needed for the optional worker entrypoint
USER root
RUN npm install --no-save tsx prisma@6.19.0 \
  && chown -R printdrop:printdrop /app \
  && chmod +x /app/scripts/docker-entrypoint.sh
USER printdrop

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT:-8000}/healthz" || exit 1

ENTRYPOINT ["tini", "--"]
CMD ["/app/scripts/docker-entrypoint.sh"]
