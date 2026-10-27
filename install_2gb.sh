#!/usr/bin/env bash
set -e
PROJECT_DIR="/opt/octaos"
cd "${PROJECT_DIR}"

echo "=== 1. Swap & Virtual Memory (Crucial for 2GB RAM) ==="
if [ ! -f /swapfile ]; then
    fallocate -l 4G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=4096
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    grep -qxF '/swapfile none swap sw 0 0' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi
sysctl vm.swappiness=10
sysctl vm.vfs_cache_pressure=50

echo "=== 2. Packages & Node.js 20 LTS ==="
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y curl wget git build-essential \
    python3 python3-venv python3-pip python3-dev \
    libpq-dev libcairo2 libcairo2-dev libpango-1.0-0 libpangocairo-1.0-0 \
    redis-server postgresql postgresql-contrib nginx

if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
fi

echo "=== 3. Low-Memory Redis & PostgreSQL Setup ==="
# Redis 64MB cap
sed -i '/^maxmemory /d' /etc/redis/redis.conf || true
echo "maxmemory 64mb" >> /etc/redis/redis.conf
echo "maxmemory-policy allkeys-lru" >> /etc/redis/redis.conf
systemctl enable --now redis-server
systemctl restart redis-server

# Tune PostgreSQL for 2GB RAM
PG_CONF=$(find /etc/postgresql/ -name "postgresql.conf" | head -n 1)
if [ -n "$PG_CONF" ]; then
    sed -i "s/shared_buffers = .*/shared_buffers = 64MB/" "$PG_CONF"
    sed -i "s/max_connections = .*/max_connections = 25/" "$PG_CONF"
    systemctl restart postgresql
fi

# Load DB info from .env
PG_USER="octaos_admin"
PG_PASS="${PG_PASS:-octaos_pwd_$(openssl rand -hex 6)}"
PG_DB="octaos"

sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='${PG_USER}'" | grep -q 1 || \
sudo -u postgres psql -c "CREATE USER ${PG_USER} WITH PASSWORD '${PG_PASS}';"

sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${PG_DB}'" | grep -q 1 || \
sudo -u postgres psql -c "CREATE DATABASE ${PG_DB} OWNER ${PG_USER};"

sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${PG_DB} TO ${PG_USER};"

echo "=== 4. Backend Dependencies & Database Migrations ==="
python3 -m venv "${PROJECT_DIR}/venv"
source "${PROJECT_DIR}/venv/bin/activate"
pip install --upgrade pip setuptools wheel
pip install -r "${PROJECT_DIR}/requirements.txt"
alembic upgrade head

echo "=== 5. Frontend Build (Memory-Guarded) ==="
cd "${PROJECT_DIR}/frontend"
echo "NEXT_PUBLIC_API_URL=http://151.242.187.221/api/v1" > "${PROJECT_DIR}/frontend/.env.local"
npm install
NODE_OPTIONS="--max-old-space-size=1536" npm run build

echo "=== 6. Systemd Auto-Restart Services ==="
cat << S1 > /etc/systemd/system/octaos-backend.service
[Unit]
Description=OctaOS Backend
After=network.target postgresql.service redis-server.service

[Service]
Type=simple
User=root
WorkingDirectory=${PROJECT_DIR}
EnvironmentFile=${PROJECT_DIR}/.env
ExecStart=${PROJECT_DIR}/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
S1

cat << S2 > /etc/systemd/system/octaos-worker.service
[Unit]
Description=OctaOS Celery Worker
After=network.target postgresql.service redis-server.service

[Service]
Type=simple
User=root
WorkingDirectory=${PROJECT_DIR}
EnvironmentFile=${PROJECT_DIR}/.env
ExecStart=${PROJECT_DIR}/venv/bin/celery -A app.worker.tasks worker --concurrency=1 --max-tasks-per-child=20 --loglevel=info
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
S2

cat << S3 > /etc/systemd/system/octaos-beat.service
[Unit]
Description=OctaOS Celery Beat Scheduler
After=network.target postgresql.service redis-server.service

[Service]
Type=simple
User=root
WorkingDirectory=${PROJECT_DIR}
EnvironmentFile=${PROJECT_DIR}/.env
ExecStart=${PROJECT_DIR}/venv/bin/celery -A app.worker.tasks beat --loglevel=info
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
S3

cat << S4 > /etc/systemd/system/octaos-frontend.service
[Unit]
Description=OctaOS Next.js Frontend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${PROJECT_DIR}/frontend
ExecStart=/usr/bin/npm start -- -p 3000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
S4

systemctl daemon-reload
systemctl enable --now octaos-backend octaos-worker octaos-beat octaos-frontend

echo "=== 7. Nginx Setup ==="
cat << NGINX_CONF > /etc/nginx/sites-available/octaos
server {
    listen 80 default_server;
    server_name _;
    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /docs {
        proxy_pass http://127.0.0.1:8000/docs;
        proxy_set_header Host \$host;
    }

    location /openapi.json {
        proxy_pass http://127.0.0.1:8000/openapi.json;
        proxy_set_header Host \$host;
    }
}
NGINX_CONF

rm -f /etc/nginx/sites-enabled/default || true
ln -sf /etc/nginx/sites-available/octaos /etc/nginx/sites-enabled/
nginx -t && systemctl restart nginx

echo "=========================================================="
echo "🎉 DEPLOYMENT COMPLETE!"
echo "Open: http://151.242.187.221"
echo "API:  http://151.242.187.221/docs"
echo "AI:   NVIDIA Nemotron (nvidia/nemotron-3.5-super-vl-120b-a12b)"
echo "=========================================================="
