#!/usr/bin/env bash
# ==============================================================================
# ESCAPE THE TERMINAL - Container Cleanup Utility
# Safely stops and removes all team sandbox containers (escape-team-*)
# ==============================================================================
set -euo pipefail

PREFIX="escape-team-"
DRY_RUN=false
FORCE=false

for arg in "$@"; do
    case "$arg" in
        --dry-run)
            DRY_RUN=true
            ;;
        --force|-f)
            FORCE=true
            ;;
        --help|-h)
            echo "Usage: $0 [--dry-run] [--force]"
            echo "  --dry-run   List containers that would be removed without touching them"
            echo "  --force     Force stop (SIGKILL) instead of graceful stop"
            exit 0
            ;;
    esac
done

echo "🔍 Searching for sandbox containers matching '${PREFIX}*'..."

CONTAINERS=$(docker ps -a --filter "name=^/${PREFIX}" --format "{{.Names}}" || true)

if [ -z "$CONTAINERS" ]; then
    echo "✅ No active or stopped sandbox containers found."
    exit 0
fi

COUNT=$(echo "$CONTAINERS" | wc -l)
echo "📦 Found $COUNT sandbox container(s):"
echo "$CONTAINERS" | sed 's/^/  - /'

if [ "$DRY_RUN" = true ]; then
    echo "💡 [Dry-run] No containers were modified."
    exit 0
fi

if [ "$FORCE" = true ]; then
    echo "⚡ Force-killing and removing containers..."
    echo "$CONTAINERS" | xargs -r docker rm -f
else
    echo "🛑 Gracefully stopping sandbox containers (timeout 5s)..."
    echo "$CONTAINERS" | xargs -r docker stop -t 5
    echo "🧹 Removing sandbox containers..."
    echo "$CONTAINERS" | xargs -r docker rm
fi

echo "✅ All sandbox containers cleaned up successfully."
