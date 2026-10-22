#!/bin/sh
# Runs when the container starts (nginx image entrypoint hook).
# Writes environment values into config.js so one image works in every environment.
# index.html must load /config.js before the app bundle.
# An empty API_URL means "same address as the app" (Caddy forwards /api/* to the API).
set -eu

cat > /usr/share/nginx/html/config.js <<EOF
window.__CONFIG__ = {
  app: "${APP_NAME}",
  apiUrl: "${API_URL:-}",
  apiMode: "${API_MODE:-real}",
  posthogKey: "${POSTHOG_KEY:-}",
  sentryDsn: "${SENTRY_DSN:-}"
};
EOF
