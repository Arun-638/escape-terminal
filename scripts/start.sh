#!/usr/bin/env bash
# ==============================================================================
# ESCAPE THE TERMINAL - Start Competition Services
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$ROOT_DIR/docker"

echo "[+] Starting CTFd, PostgreSQL, Redis, and Nginx reverse proxy..."
docker compose -f "$DOCKER_DIR/docker-compose.yml" up -d

echo "[+] Waiting for services to become healthy..."
sleep 5

docker compose -f "$DOCKER_DIR/docker-compose.yml" ps

echo "======================================================"
echo "🐧 CTFd is now live on http://localhost (Port 80)"
echo "Access via college LAN using: http://<SERVER_IP>"
echo "======================================================"
