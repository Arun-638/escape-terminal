#!/usr/bin/env bash
# ==============================================================================
# ESCAPE THE TERMINAL - Stop Competition Services
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$ROOT_DIR/docker"

echo "[+] Stopping CTFd and supporting services..."
docker compose -f "$DOCKER_DIR/docker-compose.yml" down

echo "[+] All competition services stopped."
