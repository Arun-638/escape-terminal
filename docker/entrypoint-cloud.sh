#!/bin/bash
set -e

PORT=${PORT:-8080}
echo "[INIT] Booting Escape The Terminal Unified Cloud Platform on Port $PORT..."

# Normalize postgres:// to postgresql:// for SQLAlchemy compatibility
if [ -n "$DATABASE_URL" ]; then
    export DATABASE_URL="${DATABASE_URL/#postgres:\/\//postgresql:\/\/}"
    echo "[INIT] Supabase PostgreSQL database URL configured."
fi

# Configure Nginx with the dynamic public cloud PORT
echo "[INIT] Configuring Nginx reverse proxy on port $PORT..."
envsubst '${PORT}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

# Start CTFd Platform in background (Internal port 8000)
echo "[INIT] Launching CTFd on 127.0.0.1:8000..."
cd /opt/CTFd
if [ -n "$DATABASE_URL" ]; then
    flask db upgrade || true
fi
python serve.py --port 8000 &

# Start Terminal & Anti-Cheat Proctoring Service in background (Internal port 8081)
echo "[INIT] Launching Terminal Service on 127.0.0.1:8081..."
cd /app
uvicorn app.main:app --host 127.0.0.1 --port 8081 &

# Wait for internal services to be ready
sleep 3

# Launch Nginx in foreground to serve external requests on $PORT
echo "[INIT] Starting Nginx frontend gateway..."
exec nginx -g "daemon off;"
