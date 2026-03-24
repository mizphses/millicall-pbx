#!/bin/bash
set -e

export PATH="/app/venv/bin:$PATH"
cd /app

# Fix permissions — data dir may be owned by root from Docker volume
chown -R millicall:millicall /app/data
chown -R millicall:asterisk /usr/share/asterisk/sounds/en/millicall
chown -R millicall:asterisk /var/spool/asterisk/recording

# Show startup banner with admin password
echo ""
echo "============================================"
echo "  Millicall PBX"
echo "============================================"
if [ -z "$ADMIN_PASSWORD" ]; then
    echo "  ADMIN_PASSWORD not set."
    echo "  A random password will be generated."
    echo "  Check the log below for the password."
    echo ""
    echo "  To set a persistent password:"
    echo "    echo 'ADMIN_PASSWORD=yourpass' >> .env"
else
    echo "  Admin password: (set via .env)"
fi
echo "============================================"
echo ""

# Run migrations (root — needs write to both /app/data and /etc/asterisk)
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
        writer.write_ari_config()
    print(f'Config generated with {len(trunks)} trunk(s)')
asyncio.run(init())
"

# Create directories BEFORE copying config and starting Asterisk
mkdir -p /usr/share/asterisk/sounds/en/millicall
mkdir -p /var/spool/asterisk/recording
mkdir -p /var/log/asterisk/cdr-custom
chown -R asterisk:asterisk /var/log/asterisk/cdr-custom

cp /app/asterisk_templates/indications.conf /etc/asterisk/indications.conf
cp /app/asterisk_templates/pjsip_notify.conf /etc/asterisk/pjsip_notify.conf
# ari.conf is generated from template by the init script above
cp /app/asterisk_templates/http.conf /etc/asterisk/http.conf
cp /app/asterisk_templates/cdr.conf /etc/asterisk/cdr.conf
cp /app/asterisk_templates/cdr_custom.conf /etc/asterisk/cdr_custom.conf

# Start Asterisk in background
asterisk -f &
ASTERISK_PID=$!

# Wait for Asterisk to be ready (poll instead of fixed sleep)
echo "Waiting for Asterisk..."
for i in $(seq 1 30); do
    if asterisk -rx 'core show version' >/dev/null 2>&1; then
        echo "Asterisk is ready."
        break
    fi
    sleep 1
done

# Enable verbose logging and SIP logger
asterisk -rx 'core set verbose 5'
asterisk -rx 'pjsip set logger on'
asterisk -rx 'logger add channel /var/log/asterisk/verbose.log verbose notice warning error'

# Verify CDR custom backend is active
asterisk -rx 'cdr show status'

# Start ARI listener for AI agent calls (as millicall user)
su -s /bin/bash millicall -c 'PATH="/app/venv/bin:$PATH" python -m millicall.phase2.ari_runner' &
ARI_PID=$!

# Start the web application (as millicall user)
su -s /bin/bash millicall -c "PATH=\"/app/venv/bin:\$PATH\" uvicorn millicall.main:app \
    --host \"${WEB_HOST:-0.0.0.0}\" \
    --port \"${WEB_PORT:-8000}\"" &
WEB_PID=$!

# Handle shutdown
trap "kill $ASTERISK_PID $WEB_PID $ARI_PID 2>/dev/null; wait" SIGTERM SIGINT

wait
