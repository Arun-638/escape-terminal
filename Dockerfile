FROM python:3.11-slim-bookworm

WORKDIR /app

# Install system dependencies, Nginx, and gettext (for envsubst)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libssl-dev \
    curl \
    git \
    nginx \
    gettext-base \
    && rm -rf /var/lib/apt/lists/*

# Install CTFd and Terminal Service Python dependencies
COPY ctfd/requirements.txt /tmp/ctfd-requirements.txt
RUN pip install --no-cache-dir -r /tmp/ctfd-requirements.txt \
    psycopg2-binary \
    fastapi \
    uvicorn \
    websockets \
    pydantic \
    requests \
    docker

# Copy CTFd application code
COPY ctfd /opt/CTFd

# Install the custom Escape Terminal plugin into CTFd
COPY ctfd/custom-plugin /opt/CTFd/CTFd/plugins/escape_theme

# Copy Terminal Service code
COPY terminal-service/app /app/app

# Copy cloud Nginx configuration and entrypoint
COPY docker/nginx/render-nginx.conf /etc/nginx/nginx.conf.template
COPY docker/entrypoint-cloud.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8080

ENTRYPOINT ["/entrypoint.sh"]
