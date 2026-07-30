#!/bin/sh
set -eu

node /app/scripts/prepare-prisma-provider.js
npx prisma generate
npx prisma db push --skip-generate --accept-data-loss=false

if [ "${RUN_AS_WORKER:-false}" = "true" ]; then
  exec npx tsx /app/scripts/worker.ts
fi

exec ./node_modules/.bin/next start -H 0.0.0.0 -p "${PORT:-8000}"
