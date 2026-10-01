#!/bin/bash
set -e

PORT=${PORT:-8080}
echo "[INIT] Booting Escape The Terminal Unified Cloud Platform on Port $PORT..."

# Normalize postgres:// to postgresql:// for SQLAlchemy compatibility
if [ -n "$DATABASE_URL" ]; then
    export DATABASE_URL="${DATABASE_URL/#postgres:\/\//postgresql:\/\/}"
    echo "[INIT] Supabase PostgreSQL database URL configured."
fi

export FLASK_APP=CTFd
export SECRET_KEY=${SECRET_KEY:-escape_ctfd_secret_key_2026}
export REVERSE_PROXY=true

# Configure Nginx with the dynamic public cloud PORT
echo "[INIT] Configuring Nginx reverse proxy on port $PORT..."
envsubst '${PORT}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

# Start CTFd Platform in background (Internal port 8000)
echo "[INIT] Launching CTFd on 127.0.0.1:8000..."
cd /opt/CTFd

if [ -n "$DATABASE_URL" ]; then
    echo "[INIT] Running database migrations on Supabase..."
    flask db upgrade || true
fi

# Run CTFd using production Gunicorn sync worker
gunicorn 'CTFd:create_app()' \
    --bind '127.0.0.1:8000' \
    --workers 1 \
    --worker-class sync \
    --access-logfile - \
    --error-logfile - &

# Start Terminal & Anti-Cheat Proctoring Service in background (Internal port 8081)
echo "[INIT] Launching Terminal Service on 127.0.0.1:8081..."
cd /app
uvicorn app.main:app --host 127.0.0.1 --port 8081 --access-log &

# Wait for CTFd to finish connecting and become healthy
echo "[INIT] Waiting for CTFd service to become ready..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:8000/ > /dev/null 2>&1; then
        echo "[INIT] CTFd is healthy and ready to serve!"
        break
    fi
    echo "[INIT] Waiting for CTFd database / initialization... ($i/30)"
    sleep 2
done

# Launch Nginx in foreground to serve external requests on public $PORT
echo "[INIT] Starting Nginx frontend gateway on public port $PORT..."
exec nginx -g "daemon off;"
