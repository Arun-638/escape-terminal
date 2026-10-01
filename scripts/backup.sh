#!/usr/bin/env bash
# ==============================================================================
# ESCAPE THE TERMINAL - PostgreSQL Database Backup Script
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$ROOT_DIR/backups"
TIMESTAMP="$(date +'%Y%m%d_%H%M%S')"
BACKUP_FILE="$BACKUP_DIR/ctfd_backup_$TIMESTAMP.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "[+] Creating PostgreSQL backup: $BACKUP_FILE..."
docker compose -f "$ROOT_DIR/docker/docker-compose.yml" exec -T db pg_dump -U ctfd ctfd | gzip > "$BACKUP_FILE"

echo "[+] Backup successfully saved to $BACKUP_FILE"
