#!/bin/bash
set -e

export PATH="/app/venv/bin:$PATH"
cd /app

# Run migrations
alembic upgrade head

# Generate Asterisk config BEFORE starting Asterisk (uses DB for trunk/peer data)
python -c "
import asyncio
from millicall.infrastructure.database import async_session, engine
from millicall.infrastructure.orm import metadata
from millicall.infrastructure.asterisk.config_writer import AsteriskConfigWriter
from millicall.infrastructure.repositories.extension_repo import ExtensionRepository
from millicall.infrastructure.repositories.peer_repo import PeerRepository
from millicall.infrastructure.repositories.trunk_repo import TrunkRepository
from millicall.infrastructure.repositories.settings_repo import SettingsRepository
async def init():
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    async with async_session() as session:
        repo = SettingsRepository(session)
        await repo.ensure_defaults()
    async with async_session() as session:
        ext_repo = ExtensionRepository(session)
        peer_repo = PeerRepository(session)
        trunk_repo = TrunkRepository(session)
        extensions = await ext_repo.get_all()
        peers = await peer_repo.get_all()
        trunks = await trunk_repo.get_all_enabled()
        peer_map = {p.id: p for p in peers if p.id is not None}
        writer = AsteriskConfigWriter()
        writer.write_pjsip_config(peers, trunks=trunks)
        writer.write_extensions_config(extensions, peer_map, trunks=trunks)
    print(f'Config generated with {len(trunks)} trunk(s)')
asyncio.run(init())
"
# Create directories BEFORE copying config and starting Asterisk
mkdir -p /usr/share/asterisk/sounds/en/millicall
mkdir -p /var/spool/asterisk/recording
mkdir -p /var/log/asterisk/cdr-csv
chown -R asterisk:asterisk /var/log/asterisk/cdr-csv

cp /app/asterisk_templates/indications.conf /etc/asterisk/indications.conf
cp /app/asterisk_templates/pjsip_notify.conf /etc/asterisk/pjsip_notify.conf
cp /app/asterisk_templates/ari.conf /etc/asterisk/ari.conf
cp /app/asterisk_templates/http.conf /etc/asterisk/http.conf
cp /app/asterisk_templates/cdr.conf /etc/asterisk/cdr.conf
cp /app/asterisk_templates/cdr_csv.conf /etc/asterisk/cdr_csv.conf
cp /app/asterisk_templates/modules.conf /etc/asterisk/modules.conf

# Start Asterisk in background
asterisk -f &
ASTERISK_PID=$!

# Wait for Asterisk to be ready
sleep 3

# Enable verbose logging and SIP logger
asterisk -rx 'core set verbose 5'
asterisk -rx 'pjsip set logger on'
asterisk -rx 'logger add channel /var/log/asterisk/verbose.log verbose notice warning error'

# Verify CDR module is loaded
asterisk -rx 'module show like cdr_csv'

# Start ARI listener for AI agent calls
python -m millicall.phase2.ari_runner &
ARI_PID=$!

# Start the web application
uvicorn millicall.main:app \
    --host "${WEB_HOST:-0.0.0.0}" \
    --port "${WEB_PORT:-8000}" &
WEB_PID=$!

# Handle shutdown
trap "kill $ASTERISK_PID $WEB_PID $ARI_PID 2>/dev/null; wait" SIGTERM SIGINT

wait
