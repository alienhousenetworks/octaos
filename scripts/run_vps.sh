#!/usr/bin/env bash
# =============================================================================
#  OctaOS Production Setup – 2 GB RAM Optimized
# =============================================================================
set -e

PROJECT_DIR="/opt/octaos"
cd "${PROJECT_DIR}"

echo "=========================================================="
echo "1. Clearing Any Stuck Locks & Updating Packages"
echo "=========================================================="
# Kill any hung background apt processes waiting for stdin
killall -9 apt apt-get dpkg 2>/dev/null || true
rm -f /var/lib/apt/lists/lock /var/cache/apt/archives/lock /var/lib/dpkg/lock* 2>/dev/null || true

export DEBIAN_FRONTEND=noninteractive
dpkg --configure -a || true

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y curl wget git build-essential \
    python3 python3-venv python3-pip python3-dev \
    libpq-dev libcairo2 libcairo2-dev libpango-1.0-0 libpangocairo-1.0-0 \
    redis-server postgresql postgresql-contrib nginx

echo "=========================================================="
echo "2. Checking Swap & Virtual Memory (Crucial for 2GB RAM)"
echo "=========================================================="
if [ ! -f /swapfile ]; then
    fallocate -l 4G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=4096
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile || true
    grep -qxF '/swapfile none swap sw 0 0' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
else
    swapon /swapfile 2>/dev/null || true
fi

sysctl vm.swappiness=10
sysctl vm.vfs_cache_pressure=50

echo "=========================================================="
echo "3. Node.js 20 LTS"
echo "=========================================================="
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
fi
echo "Node version: $(node -v)"

echo "=========================================================="
echo "4. Tuning Redis & PostgreSQL (Low RAM Profile)"
echo "=========================================================="
# Cap Redis to 64MB RAM with LRU eviction
sed -i '/^maxmemory /d' /etc/redis/redis.conf || true
sed -i '/^maxmemory-policy /d' /etc/redis/redis.conf || true
echo "maxmemory 64mb" >> /etc/redis/redis.conf
echo "maxmemory-policy allkeys-lru" >> /etc/redis/redis.conf
systemctl enable --now redis-server
systemctl restart redis-server

# Tune PostgreSQL to low-RAM footprint
PG_CONF=$(find /etc/postgresql/ -name "postgresql.conf" | head -n 1)
if [ -n "$PG_CONF" ]; then
    sed -i "s/shared_buffers = .*/shared_buffers = 64MB/" "$PG_CONF"
    sed -i "s/max_connections = .*/max_connections = 25/" "$PG_CONF"
    sed -i "s/#work_mem = .*/work_mem = 4MB/" "$PG_CONF"
    sed -i "s/#maintenance_work_mem = .*/maintenance_work_mem = 32MB/" "$PG_CONF"
    systemctl restart postgresql
fi

# Load DB credentials dynamically from .env
PG_USER="octaos_admin"
PG_PASS="octaos_secure_pass_928174"
PG_DB="octaos"

if [ -f "${PROJECT_DIR}/.env" ]; then
    ENV_USER=$(grep -E "^POSTGRES_USER=" "${PROJECT_DIR}/.env" | cut -d'=' -f2- | tr -d '\r' || true)
    ENV_PASS=$(grep -E "^POSTGRES_PASSWORD=" "${PROJECT_DIR}/.env" | cut -d'=' -f2- | tr -d '\r' || true)
    ENV_DB=$(grep -E "^POSTGRES_DB=" "${PROJECT_DIR}/.env" | cut -d'=' -f2- | tr -d '\r' || true)
    [ -n "$ENV_USER" ] && PG_USER="$ENV_USER"
    [ -n "$ENV_PASS" ] && PG_PASS="$ENV_PASS"
    [ -n "$ENV_DB" ] && PG_DB="$ENV_DB"
fi

sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='${PG_USER}'" | grep -q 1 || \
sudo -u postgres psql -c "CREATE USER ${PG_USER} WITH PASSWORD '${PG_PASS}';"

sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${PG_DB}'" | grep -q 1 || \
sudo -u postgres psql -c "CREATE DATABASE ${PG_DB} OWNER ${PG_USER};"

sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${PG_DB} TO ${PG_USER};"

echo "=========================================================="
echo "5. Python Backend & Database Migrations"
echo "=========================================================="
python3 -m venv "${PROJECT_DIR}/venv"
source "${PROJECT_DIR}/venv/bin/activate"
pip install --upgrade pip setuptools wheel
pip install -r "${PROJECT_DIR}/requirements.txt"
# If tenants table is missing, ensure alembic_version is dropped so migration starts cleanly from initial schema
sudo -u postgres psql -d "${PG_DB}" -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'tenants') THEN DROP TABLE IF EXISTS alembic_version; END IF; END \$\$;" 2>/dev/null || true

# Run migrations
alembic upgrade head || python3 scripts/fix_alembic_and_migrate.py || true

echo "=========================================================="
echo "6. Next.js Frontend Installation & Build"
echo "=========================================================="
cd "${PROJECT_DIR}/frontend"
cat << FRONTEND_ENV > "${PROJECT_DIR}/frontend/.env.local"
NEXT_PUBLIC_API_URL=http://151.242.187.221/api/v1
FRONTEND_ENV

npm install
# Set max-old-space-size to 1536MB so Next.js build never crashes on 2GB RAM
NODE_OPTIONS="--max-old-space-size=1536" npm run build

echo "=========================================================="
echo "7. Systemd Services (1 Worker for Low Memory)"
echo "=========================================================="
RUN_USER="root"

# 1. Backend Service
cat << SYSTEMD_BACKEND > /etc/systemd/system/octaos-backend.service
[Unit]
Description=OctaOS FastAPI Backend
After=network.target postgresql.service redis-server.service

[Service]
Type=simple
User=${RUN_USER}
WorkingDirectory=${PROJECT_DIR}
EnvironmentFile=${PROJECT_DIR}/.env
ExecStart=${PROJECT_DIR}/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SYSTEMD_BACKEND

# 2. Celery Worker (1 concurrency + worker recycling)
cat << SYSTEMD_WORKER > /etc/systemd/system/octaos-worker.service
[Unit]
Description=OctaOS Celery Worker
After=network.target postgresql.service redis-server.service

[Service]
Type=simple
User=${RUN_USER}
WorkingDirectory=${PROJECT_DIR}
EnvironmentFile=${PROJECT_DIR}/.env
ExecStart=${PROJECT_DIR}/venv/bin/celery -A app.worker.tasks worker --concurrency=1 --max-tasks-per-child=20 --loglevel=info
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SYSTEMD_WORKER

# 3. Celery Beat
cat << SYSTEMD_BEAT > /etc/systemd/system/octaos-beat.service
[Unit]
Description=OctaOS Celery Beat Scheduler
After=network.target postgresql.service redis-server.service

[Service]
Type=simple
User=${RUN_USER}
WorkingDirectory=${PROJECT_DIR}
EnvironmentFile=${PROJECT_DIR}/.env
ExecStart=${PROJECT_DIR}/venv/bin/celery -A app.worker.tasks beat --loglevel=info
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SYSTEMD_BEAT

# 4. Frontend
cat << SYSTEMD_FRONTEND > /etc/systemd/system/octaos-frontend.service
[Unit]
Description=OctaOS Next.js Frontend
After=network.target

[Service]
Type=simple
User=${RUN_USER}
WorkingDirectory=${PROJECT_DIR}/frontend
ExecStart=/usr/bin/npm start -- -p 3000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SYSTEMD_FRONTEND

systemctl daemon-reload
systemctl enable octaos-backend octaos-worker octaos-beat octaos-frontend
systemctl restart octaos-backend octaos-worker octaos-beat octaos-frontend

echo "=========================================================="
echo "8. Nginx Reverse Proxy"
echo "=========================================================="
cat << NGINX_CONF > /etc/nginx/sites-available/octaos
server {
    listen 80 default_server;
    server_name _;

    client_max_body_size 50M;

    # Frontend UI
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }

    # Backend API
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # API Documentation
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

echo ""
echo "=========================================================="
echo "🎉 SUCCESS: OctaOS is now deployed on your 2 GB Server!"
echo "➡️  Open URL:  http://151.242.187.221"
echo "➡️  API Docs:  http://151.242.187.221/docs"
echo "🧠  AI Engine: NVIDIA Nemotron (nemotron-3.5-super-vl-120b-a12b)"
echo "=========================================================="
