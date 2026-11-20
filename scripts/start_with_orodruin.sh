#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Starting Orodruin OSINT Backend on :8001..."
(cd "$ROOT_DIR/orodruin/backend" && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001) &

echo "Starting Orodruin 3D Globe Frontend on :5174..."
(cd "$ROOT_DIR/orodruin/frontend" && npm run dev) &

echo "Starting OctaOS Enterprise API on :8000..."
(cd "$ROOT_DIR" && ORODRUIN_API_URL="http://127.0.0.1:8001" uvicorn app.main:app --host 0.0.0.0 --port 8000) &

echo "Starting OctaOS Next.js Frontend on :3000..."
(cd "$ROOT_DIR/frontend" && NEXT_PUBLIC_ORODRUIN_URL="http://localhost:5174" npm run dev) &

wait
