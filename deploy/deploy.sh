#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/home/igordev/apps/gerador-de-apostila"
VENV_DIR="/home/igordev/venvs/gerador-de-apostila"
SERVICE_NAME="gerador-de-apostila.service"
HEALTH_URL="http://127.0.0.1:8006/health"

echo "==> [DEPLOY] Iniciando deploy de gerador-de-apostila..."

cd "$APP_DIR"
git fetch origin main
git reset --hard origin/main

if [ ! -d "$VENV_DIR" ]; then
    echo "==> [DEPLOY] Criando virtualenv em $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

echo "==> [DEPLOY] Atualizando dependências..."
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$APP_DIR/requirements.txt"

echo "==> [DEPLOY] Reiniciando serviço $SERVICE_NAME..."
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
systemctl --user daemon-reload
systemctl --user restart "$SERVICE_NAME"

echo "==> [DEPLOY] Aguardando healthcheck em $HEALTH_URL..."
for i in {1..15}; do
    if curl -fsS "$HEALTH_URL" >/dev/null 2>&1; then
        echo "✅ [DEPLOY] Serviço saudável! Healthcheck OK."
        curl -fsS "$HEALTH_URL"
        echo ""
        exit 0
    fi
    sleep 1
done

echo "❌ [DEPLOY] Falha no healthcheck após 15 segundos."
journalctl --user -u "$SERVICE_NAME" -n 30 --no-pager || true
exit 1
