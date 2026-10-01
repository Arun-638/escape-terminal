#!/bin/bash
set -e

# ==============================================================================
# ESCAPE THE TERMINAL — Team Container Entrypoint
# ==============================================================================

TEAM_ID="${TEAM_ID:-1}"
SERVER_SECRET="${SERVER_SECRET:-escape_master_secret_lan}"
COMPETITION_ID="${COMPETITION_ID:-escape2026}"

# Ensure secure answers directory exists (root access only)
mkdir -p /var/run/escape
chmod 700 /var/run/escape

# Generate deterministic challenge filesystem if not already present
if [ ! -f /var/run/escape/answers.json ]; then
    echo "[*] Generating isolated challenge environment for Team ${TEAM_ID}..."
    python3 /opt/scripts/generate_challenges.py \
        --team-id "${TEAM_ID}" \
        --secret "${SERVER_SECRET}" \
        --answers-file /var/run/escape/answers.json
fi

# Ensure correct file permissions
chown -R player:player /home/player
chmod 750 /home/player

# Protect escape challenge files (readable by player, writable only by root)
chown -R root:root /escape
chmod -R 755 /escape
chmod 700 /var/run/escape
chmod 600 /var/run/escape/answers.json

# If running as root, switch to player user for default shell
if [ "$(id -u)" = "0" ]; then
    if [ "$#" -eq 0 ]; then
        exec su - player
    else
        exec "$@"
    fi
else
    exec "$@"
fi
