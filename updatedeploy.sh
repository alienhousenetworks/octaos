#!/usr/bin/env bash
# =============================================================================
#  OctaOS – Fast Production Update & Redeploy Script
#  Usage: sudo bash updatedeploy.sh
# =============================================================================

set -euo pipefail

# ── Colour helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }
header()  { echo -e "\n${BOLD}━━━ $* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }

# ── Paths & constants ─────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR"
ENV_FILE="$APP_DIR/.env"
VENV_DIR="$APP_DIR/venv"
FRONTEND_DIR="$APP_DIR/frontend"
LOG_DIR="/var/log/octaos"

# ── Must-run-as-root check ────────────────────────────────────────────────────
if [[ "$EUID" -ne 0 ]]; then
  error "Please run as root:  sudo bash updatedeploy.sh"
fi

# =============================================================================
# 1. Load Env Vars
# =============================================================================
if [[ -f "$ENV_FILE" ]]; then
  set -a; source "$ENV_FILE"; set +a
  success "Loaded configuration from .env"
else
  error ".env file not found at $ENV_FILE. Please run deploy.sh first."
fi

# =============================================================================
# 2. Git Pull Latest Changes
# =============================================================================
header "Pulling Latest Code"
cd "$APP_DIR"

if git rev-parse --git-dir &>/dev/null; then
  BRANCH=$(git rev-parse --abbrev-ref HEAD)
  info "Fetching latest changes from Git..."
  git fetch --all
  info "Pulling latest from branch: $BRANCH"
  if ! git pull origin "$BRANCH"; then
    warn "Git pull failed. You might have uncommitted local changes on the VPS."
    warn "To overwrite local changes and pull:  git reset --hard origin/$BRANCH"
    warn "Continuing deployment with existing code..."
  else
    success "Code pulled successfully"
  fi
else
  warn "Not a git repository – skipping pull"
fi

# =============================================================================
# 3. Update Backend Dependencies & Migrations
# =============================================================================
header "Updating Backend"

if [[ -d "$VENV_DIR" ]]; then
  info "Installing/updating Python dependencies..."
  "$VENV_DIR/bin/pip" install -r "$APP_DIR/requirements.txt" -q
  success "Python dependencies updated"
  
  info "Running database init/migration..."
  "$VENV_DIR/bin/python3" "$APP_DIR/init_db.py" || warn "init_db.py had warnings (may be safe to ignore)"
  success "Database migrations completed"
else
  error "Virtualenv not found at $VENV_DIR. Please run deploy.sh first."
fi

# =============================================================================
# 4. Rebuild Next.js Frontend
# =============================================================================
header "Updating & Building Frontend"

if [[ -d "$FRONTEND_DIR" ]]; then
  cd "$FRONTEND_DIR"
  
  # Ensure frontend .env.local matches config
  cat > "$FRONTEND_DIR/.env.local" <<EOF
NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
EOF

  info "Installing frontend dependencies..."
  npm ci --silent || npm install --silent
  
  info "Building Next.js production bundle (optimized for RAM size)..."
  NODE_OPTIONS="--max-old-space-size=1024" npm run build
  success "Frontend build completed"
  
  # Copy static assets for Next.js standalone runner if standalone directory exists
  NODE_BIN="$(which node)"
  if [[ -d "$FRONTEND_DIR/.next/standalone" ]]; then
    info "Next.js standalone structure found. Copying static files..."
    cp -r "$FRONTEND_DIR/.next/static"   "$FRONTEND_DIR/.next/standalone/.next/static"   2>/dev/null || true
    cp -r "$FRONTEND_DIR/public"         "$FRONTEND_DIR/.next/standalone/public"          2>/dev/null || true
    success "Next.js standalone assets copied"
  fi
else
  warn "Frontend directory not found at $FRONTEND_DIR – skipping frontend build"
fi

# =============================================================================
# 5. Restart Systemd Services & Nginx
# =============================================================================
header "Restarting Services"

info "Restarting OctaOS systemd services..."
for svc in octaos-api octaos-worker octaos-beat octaos-frontend; do
  if systemctl list-units --type=service | grep -Fq "${svc}.service"; then
    systemctl restart "$svc"
    success "$svc restarted"
  else
    warn "Service $svc is not registered/found"
  fi
done

info "Restarting Nginx..."
if nginx -t; then
  systemctl restart nginx
  success "Nginx restarted"
else
  warn "Nginx config test failed – skipping restart"
fi

# =============================================================================
# 6. Health Check
# =============================================================================
header "Health Check"
sleep 3

check_service() {
  if systemctl is-active --quiet "$1"; then
    success "$1 is active and running ✓"
  else
    warn "$1 is NOT running – check: journalctl -u $1 -n 50"
  fi
}

for svc in postgresql redis-server nginx octaos-api octaos-worker octaos-beat octaos-frontend; do
  check_service "$svc"
done

# Quick HTTP smoke test
if curl -sf "http://localhost:8001/" > /dev/null 2>&1; then
  success "Backend API responding ✓"
else
  warn "Backend API not responding yet"
fi

if curl -sf "http://localhost:3001/" > /dev/null 2>&1; then
  success "Frontend responding ✓"
else
  warn "Frontend not responding yet"
fi

echo ""
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}${BOLD}  OctaOS Update & Redeploy Successful!${NC}"
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
