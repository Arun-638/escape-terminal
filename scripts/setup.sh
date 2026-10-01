#!/usr/bin/env bash
# ==============================================================================
# ESCAPE THE TERMINAL - College LAN Setup Script (Milestone 1)
# Zero-Cost, Self-Hosted Linux Escape-Room Competition Platform
# ==============================================================================
set -euo pipefail

echo "======================================================"
echo "🐧 ESCAPE THE TERMINAL - Initializing Server Setup"
echo "======================================================"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$ROOT_DIR/docker"

# Check Docker and Docker Compose availability
if ! command -v docker >/dev/null 2>&1; then
    echo "[-] Error: Docker is not installed. Please install Docker first."
    exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
    echo "[-] Error: Docker Compose is not installed or not in PATH."
    exit 1
fi

# Ensure .env exists
if [ ! -f "$DOCKER_DIR/.env" ]; then
    echo "[+] Creating docker/.env from .env.example..."
    cp "$DOCKER_DIR/.env.example" "$DOCKER_DIR/.env"
    # Generate random secret key for production security
    RAND_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || openssl rand -hex 32 2>/dev/null || echo "escape_secret_key_$(date +%s)")
    sed -i "s/generate_a_random_32_byte_hex_string_for_production/$RAND_SECRET/" "$DOCKER_DIR/.env"
fi

# Build Docker images
echo "[+] Building CTFd with PostgreSQL support..."
docker compose -f "$DOCKER_DIR/docker-compose.yml" build

echo "[+] Milestone 1 Setup Complete!"
echo "Run './scripts/start.sh' to launch services."
