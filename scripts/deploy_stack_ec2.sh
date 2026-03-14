#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 user@host [remote_dir]" >&2
  exit 1
fi

REMOTE_HOST="$1"
REMOTE_DIR="${2:-/opt/trading}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

rsync -az --delete \
  --exclude '.git/' \
  --exclude '.venv/' \
  --exclude '__pycache__/' \
  --exclude 'data/' \
  "${PROJECT_DIR}/" "${REMOTE_HOST}:${REMOTE_DIR}/"

ssh "${REMOTE_HOST}" "cd ${REMOTE_DIR} && docker compose -f docker-compose.aws.yml build"
ssh "${REMOTE_HOST}" "sudo cp ${REMOTE_DIR}/deploy/systemd/trading-stack.service /etc/systemd/system/trading-stack.service && sudo systemctl daemon-reload && sudo systemctl enable --now trading-stack && sudo systemctl restart trading-stack && sudo systemctl status trading-stack --no-pager"

