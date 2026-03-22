#!/bin/bash
set -e

export PATH="/app/venv/bin:$PATH"
cd /app

# Run migrations
alembic upgrade head

# Generate Asterisk config BEFORE starting Asterisk
python -m millicall.cli generate-config
cp /app/asterisk_templates/indications.conf /etc/asterisk/indications.conf
cp /app/asterisk_templates/pjsip_notify.conf /etc/asterisk/pjsip_notify.conf

# Start Asterisk in background
asterisk -f &
ASTERISK_PID=$!

# Wait for Asterisk to be ready
sleep 3

# Start the web application
uvicorn millicall.main:app \
    --host "${WEB_HOST:-0.0.0.0}" \
    --port "${WEB_PORT:-8000}" &
WEB_PID=$!

# Handle shutdown
trap "kill $ASTERISK_PID $WEB_PID 2>/dev/null; wait" SIGTERM SIGINT

wait
