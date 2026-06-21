#!/usr/bin/env bash
# =============================================================================
#  OctaOS – Video Renderer First-Time Setup
#  Usage: sudo bash setup-renderer.sh
# =============================================================================

set -euo pipefail

# ── Colour helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RENDERER_DIR="$SCRIPT_DIR/video-renderer"

if [[ "$EUID" -ne 0 ]]; then
  error "Please run as root:  sudo bash setup-renderer.sh"
fi

if [[ ! -d "$RENDERER_DIR" ]]; then
  error "video-renderer directory not found at $RENDERER_DIR"
fi

info "Installing global dependencies..."
apt-get update -y
apt-get install -y nodejs npm ffmpeg xvfb libasound2 libgbm-dev libnss3 libatk-bridge2.0-0 libgtk-3-0

cd "$RENDERER_DIR"

info "Installing Node.js dependencies for video-renderer..."
npm install

info "Creating systemd service for octaos-video-renderer..."

cat > /etc/systemd/system/octaos-video-renderer.service <<EOF
[Unit]
Description=OctaOS Remotion Video Renderer
After=network.target

[Service]
User=root
WorkingDirectory=$RENDERER_DIR
ExecStart=/usr/bin/npm run start
Restart=always
Environment=NODE_ENV=production
Environment=PORT=8002

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable octaos-video-renderer
systemctl start octaos-video-renderer

success "octaos-video-renderer installed and started!"
