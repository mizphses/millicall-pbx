#!/bin/bash
# Deploy Millicall PBX to the server
# Run from the project root on your local machine
set -e

SERVER="192.168.1.2"
SSH_KEY="$HOME/.ssh/id_ed25519_kintosup"
REMOTE_DIR="/opt/millicall"
SSH_CMD="ssh -i $SSH_KEY $SERVER"

echo "=== Deploying Millicall PBX to $SERVER ==="

# 1. Sync project files
echo "[1/3] Syncing files..."
rsync -avz --delete \
    --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.venv' \
    --exclude '*.db' \
    --exclude '.env' \
    --exclude '.ruff_cache' \
    -e "ssh -i $SSH_KEY" \
    ./ "$SERVER:$REMOTE_DIR/"

# 2. Ensure .env exists on server
echo "[2/3] Checking .env..."
$SSH_CMD "test -f $REMOTE_DIR/.env || cp $REMOTE_DIR/.env.example $REMOTE_DIR/.env"

# 3. Build and start
echo "[3/3] Building and starting containers..."
$SSH_CMD "cd $REMOTE_DIR && docker compose up -d --build"

echo ""
echo "=== Deployment complete ==="
echo "Web UI: http://$SERVER:8000"
