#!/usr/bin/env bash
# ==============================================================================
# ESCAPE THE TERMINAL - PostgreSQL Database Restore Script
# ==============================================================================
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <path_to_backup.sql.gz>"
    exit 1
fi

BACKUP_FILE="$1"
if [ ! -f "$BACKUP_FILE" ]; then
    echo "[-] Error: Backup file $BACKUP_FILE not found."
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "[!] WARNING: Restoring will overwrite existing CTFd database data!"
read -p "Are you sure you want to proceed? (y/N): " -r
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "[-] Restore aborted."
    exit 1
fi

echo "[+] Restoring database from $BACKUP_FILE..."
gunzip -c "$BACKUP_FILE" | docker compose -f "$ROOT_DIR/docker/docker-compose.yml" exec -T db psql -U ctfd -d ctfd

echo "[+] Database restore complete!"
