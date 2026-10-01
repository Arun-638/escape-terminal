#!/bin/bash
set -e

PORT=${PORT:-8080}
echo "[INIT] Booting Escape The Terminal Unified Cloud Platform on Port $PORT..."

cd /opt/CTFd

# Normalize postgres:// to postgresql:// for SQLAlchemy compatibility
if [ -n "$DATABASE_URL" ]; then
    export DATABASE_URL="${DATABASE_URL/#postgres:\/\//postgresql:\/\/}"
    echo "[INIT] External DATABASE_URL detected. Testing connection (5s timeout)..."
    if python -c "
import os, sys
from sqlalchemy import create_engine
try:
    url = os.environ['DATABASE_URL']
    engine = create_engine(url, connect_args={'connect_timeout': 5})
    with engine.connect() as conn:
        print('[INIT] Successfully authenticated with external PostgreSQL database!')
except Exception as err:
    print('[WARN] Could not connect to external database:', err)
    sys.exit(1)
"; then
        echo "[INIT] Running database migrations on external database..."
        export FLASK_APP=CTFd
        flask db upgrade || true
    else
        echo "[WARN] External database connection failed. Falling back to built-in SQLite database."
        unset DATABASE_URL
    fi
else
    echo "[INIT] No external database configured. Using built-in SQLite database."
fi

export FLASK_APP=CTFd
export SECRET_KEY=${SECRET_KEY:-escape_ctfd_secret_key_2026}
export REVERSE_PROXY=true

# Configure Nginx with the dynamic public cloud PORT
echo "[INIT] Configuring Nginx reverse proxy on port $PORT..."
envsubst '${PORT}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

# Start CTFd Platform in background (Internal port 8000)
echo "[INIT] Launching CTFd on 127.0.0.1:8000..."
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
    echo "[INIT] Waiting for CTFd startup... ($i/30)"
    sleep 2
done

# Launch Nginx in foreground to serve external requests on public $PORT
echo "[INIT] Starting Nginx frontend gateway on public port $PORT..."
exec nginx -g "daemon off;"
