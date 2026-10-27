#!/usr/bin/env bash
set -e

PROJECT_DIR="/opt/octaos"
cd "${PROJECT_DIR}"

echo "=========================================================="
echo "🚀 1. Updating System & Installing Core Dependencies"
echo "=========================================================="
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update -y && sudo apt-get upgrade -y
sudo apt-get install -y curl wget git build-essential \
    python3 python3-venv python3-pip python3-dev \
    libpq-dev libcairo2 libcairo2-dev libpango-1.0-0 libpangocairo-1.0-0 \
    redis-server postgresql postgresql-contrib nginx

echo "=========================================================="
echo "💾 2. Creating 4 GB Swap File (Critical for 2 GB VPS)"
echo "=========================================================="
if [ ! -f /swapfile ]; then
    sudo fallocate -l 4G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    sudo sysctl vm.swappiness=10
    sudo sysctl vm.vfs_cache_pressure=50
    echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
    echo 'vm.vfs_cache_pressure=50' | sudo tee -a /etc/sysctl.conf
fi

echo "=========================================================="
echo "⚡ 3. Installing Node.js 20 LTS"
echo "=========================================================="
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

echo "=========================================================="
echo "🗄️ 4. Configuring PostgreSQL & Redis (Low-Memory Profiles)"
echo "=========================================================="
# Cap Redis to 64MB RAM
sudo sed -i '/^maxmemory /d' /etc/redis/redis.conf
sudo sed -i '/^maxmemory-policy /d' /etc/redis/redis.conf
echo "maxmemory 64mb" | sudo tee -a /etc/redis/redis.conf
echo "maxmemory-policy allkeys-lru" | sudo tee -a /etc/redis/redis.conf
sudo systemctl restart redis-server
sudo systemctl enable redis-server

# Tune PostgreSQL to light footprint
PG_CONF=$(sudo find /etc/postgresql/ -name "postgresql.conf" | head -n 1)
if [ -n "$PG_CONF" ]; then
    sudo sed -i "s/shared_buffers = .*/shared_buffers = 64MB/" "$PG_CONF"
    sudo sed -i "s/max_connections = .*/max_connections = 25/" "$PG_CONF"
    sudo sed -i "s/#work_mem = .*/work_mem = 4MB/" "$PG_CONF"
    sudo sed -i "s/#maintenance_work_mem = .*/maintenance_work_mem = 32MB/" "$PG_CONF"
    sudo systemctl restart postgresql
fi

SERVER_IP=$(curl -s ifconfig.me || hostname -I | awk '{print $1}')
echo "Detected Server Public IP: ${SERVER_IP}"

PG_USER="octaos_admin"
PG_PASS="octaos_pwd_$(openssl rand -hex 6)"
PG_DB="octaos"

sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='${PG_USER}'" | grep -q 1 || \
sudo -u postgres psql -c "CREATE USER ${PG_USER} WITH PASSWORD '${PG_PASS}';"

sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${PG_DB}'" | grep -q 1 || \
sudo -u postgres psql -c "CREATE DATABASE ${PG_DB} OWNER ${PG_USER};"

sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${PG_DB} TO ${PG_USER};"

echo "=========================================================="
echo "🔑 5. Generating Production .env (NVIDIA Nemotron Default)"
echo "=========================================================="
cat << ENV_EOF > "${PROJECT_DIR}/.env"
# Database
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_USER=${PG_USER}
POSTGRES_PASSWORD=${PG_PASS}
POSTGRES_DB=${PG_DB}

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Environment
DEV=false
ENVIRONMENT=production
SECRET_KEY=${SECRET_KEY:-$(openssl rand -hex 32)}
ACCESS_TOKEN_EXPIRE_MINUTES=10080
REFRESH_TOKEN_EXPIRE_DAYS=30

# URLs
CORS_ORIGINS=http://${SERVER_IP},http://${SERVER_IP}:3000,http://localhost:3000
NEXT_PUBLIC_API_URL=http://${SERVER_IP}/api/v1
PUBLIC_BASE_URL=http://${SERVER_IP}

# Disable in-app video to protect 2GB RAM
ENABLE_IN_APP_VIDEO=false
TENANT_API_RATE_LIMIT_PER_MINUTE=300
MFA_REQUIRED=false
RAZORPAY_REQUIRE_PAYMENT=false
RAZORPAY_CURRENCY=INR

# Base AI Model: NVIDIA Nemotron
DEFAULT_AI_PROVIDER=nvidia
DEFAULT_AI_MODEL=nvidia/nemotron-3.5-super-vl-120b-a12b
DEFAULT_AI_MODE=inbuilt

# API Keys — export these before running the script. They are not stored in git.
NVIDIA_API_KEY=${NVIDIA_API_KEY:-}
OPENROUTER_API_KEY=${OPENROUTER_API_KEY:-}
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}
GROQ_API_KEY=${GROQ_API_KEY:-}
FIRECRAWL_API_KEY=${FIRECRAWL_API_KEY:-}
HF_TOKEN=${HF_TOKEN:-}

# OAuth & Connectors
GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID:-}
GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET:-}
GITHUB_CLIENT_ID=${GITHUB_CLIENT_ID:-}
GITHUB_CLIENT_SECRET=${GITHUB_CLIENT_SECRET:-}
LINKEDIN_CLIENT_ID=${LINKEDIN_CLIENT_ID:-}
LINKEDIN_CLIENT_SECRET=${LINKEDIN_CLIENT_SECRET:-}
LINKEDIN_VERSION=${LINKEDIN_VERSION:-202610}
LINKEDIN_ORGANIZATION_ID=${LINKEDIN_ORGANIZATION_ID:-}
LINKEDIN_ORGANIZATION_URN=${LINKEDIN_ORGANIZATION_URN:-}

# SMTP / Mail
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
EMAIL_USE_TLS=true
ENV_EOF

echo "=========================================================="
echo "🐍 6. Python Virtualenv & Migrations"
echo "=========================================================="
python3 -m venv "${PROJECT_DIR}/venv"
source "${PROJECT_DIR}/venv/bin/activate"
pip install --upgrade pip setuptools wheel
pip install -r "${PROJECT_DIR}/requirements.txt"
alembic upgrade head

echo "=========================================================="
echo "⚛️ 7. Next.js Frontend Build"
echo "=========================================================="
cd "${PROJECT_DIR}/frontend"
cat << FRONTEND_ENV > "${PROJECT_DIR}/frontend/.env.local"
NEXT_PUBLIC_API_URL=http://${SERVER_IP}/api/v1
FRONTEND_ENV

npm install
# Prevent Node from exceeding memory during build
NODE_OPTIONS="--max-old-space-size=1536" npm run build

echo "=========================================================="
echo "⚙️ 8. Setting up Systemd Auto-Restart Services"
echo "=========================================================="

# 1. Backend Service (1 Worker to save memory)
sudo tee /etc/systemd/system/octaos-backend.service > /dev/null << SYSTEMD_BACKEND
[Unit]
Description=OctaOS Backend
After=network.target postgresql.service redis-server.service

[Service]
Type=simple
User=${USER}
WorkingDirectory=${PROJECT_DIR}
EnvironmentFile=${PROJECT_DIR}/.env
ExecStart=${PROJECT_DIR}/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SYSTEMD_BACKEND

# 2. Celery Worker Service (1 Concurrency + Task recycling)
sudo tee /etc/systemd/system/octaos-worker.service > /dev/null << SYSTEMD_WORKER
[Unit]
Description=OctaOS Celery Worker
After=network.target postgresql.service redis-server.service

[Service]
Type=simple
User=${USER}
WorkingDirectory=${PROJECT_DIR}
EnvironmentFile=${PROJECT_DIR}/.env
ExecStart=${PROJECT_DIR}/venv/bin/celery -A app.worker.tasks worker --concurrency=1 --max-tasks-per-child=20 --loglevel=info
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SYSTEMD_WORKER

# 3. Celery Beat Service
sudo tee /etc/systemd/system/octaos-beat.service > /dev/null << SYSTEMD_BEAT
[Unit]
Description=OctaOS Celery Beat Scheduler
After=network.target postgresql.service redis-server.service

[Service]
Type=simple
User=${USER}
WorkingDirectory=${PROJECT_DIR}
EnvironmentFile=${PROJECT_DIR}/.env
ExecStart=${PROJECT_DIR}/venv/bin/celery -A app.worker.tasks beat --loglevel=info
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SYSTEMD_BEAT

# 4. Frontend Service
sudo tee /etc/systemd/system/octaos-frontend.service > /dev/null << SYSTEMD_FRONTEND
[Unit]
Description=OctaOS Next.js Frontend
After=network.target

[Service]
Type=simple
User=${USER}
WorkingDirectory=${PROJECT_DIR}/frontend
ExecStart=/usr/bin/npm start -- -p 3000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SYSTEMD_FRONTEND

sudo systemctl daemon-reload
sudo systemctl enable --now octaos-backend octaos-worker octaos-beat octaos-frontend

echo "=========================================================="
echo "🌐 9. Configuring Nginx Reverse Proxy"
echo "=========================================================="
sudo tee /etc/nginx/sites-available/octaos > /dev/null << NGINX_CONF
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

sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/octaos /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl restart nginx

echo ""
echo "=========================================================="
echo "🎉 SUCCESS: OctaOS is running on your 2 GB Server!"
echo "➡️  Open URL:  http://${SERVER_IP}"
echo "➡️  API Docs:  http://${SERVER_IP}/docs"
echo "🧠  AI Engine: NVIDIA Nemotron (nemotron-3.5-super-vl-120b-a12b)"
echo "=========================================================="
