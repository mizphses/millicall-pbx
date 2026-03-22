#!/bin/bash
set -e

export PATH="/app/venv/bin:$PATH"
cd /app

# Run migrations
alembic upgrade head

# Generate Asterisk config BEFORE starting Asterisk (uses DB for trunk settings)
python -c "
import asyncio
from millicall.infrastructure.database import async_session, engine
from millicall.infrastructure.orm import metadata
from millicall.infrastructure.asterisk.config_writer import AsteriskConfigWriter, TrunkConfig
from millicall.infrastructure.repositories.ai_agent_repo import AIAgentRepository
from millicall.infrastructure.repositories.extension_repo import ExtensionRepository
from millicall.infrastructure.repositories.peer_repo import PeerRepository
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
        ai_repo = AIAgentRepository(session)
        settings_repo = SettingsRepository(session)
        extensions = await ext_repo.get_all()
        peers = await peer_repo.get_all()
        ai_agents = await ai_repo.get_all()
        s = await settings_repo.get_all()
        trunk = TrunkConfig(
            enabled=s.get('trunk_enabled','N').upper() in ('Y','YES','TRUE','1'),
            host=s.get('trunk_host','192.168.1.1'),
            username=s.get('trunk_username',''),
            password=s.get('trunk_password',''),
            did_number=s.get('trunk_did_number',''),
            caller_id=s.get('trunk_caller_id',''),
            incoming_dest=s.get('trunk_incoming_dest',''),
        )
        peer_map = {p.id: p for p in peers if p.id is not None}
        writer = AsteriskConfigWriter()
        writer.write_pjsip_config(peers, trunk=trunk)
        writer.write_extensions_config(extensions, peer_map, ai_agents, trunk)
    print('Config generated with trunk' if trunk.enabled else 'Config generated (no trunk)')
asyncio.run(init())
"
cp /app/asterisk_templates/indications.conf /etc/asterisk/indications.conf
cp /app/asterisk_templates/pjsip_notify.conf /etc/asterisk/pjsip_notify.conf
cp /app/asterisk_templates/ari.conf /etc/asterisk/ari.conf
cp /app/asterisk_templates/http.conf /etc/asterisk/http.conf

# Create directory for AI agent audio files
mkdir -p /usr/share/asterisk/sounds/en/millicall
mkdir -p /var/spool/asterisk/recording

# Start Asterisk in background
asterisk -f &
ASTERISK_PID=$!

# Wait for Asterisk to be ready
sleep 3

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
