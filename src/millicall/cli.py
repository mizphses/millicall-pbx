"""CLI utility for generating Asterisk config outside of the web server."""

import asyncio
import logging
import sys

from millicall.infrastructure.asterisk.config_writer import AsteriskConfigWriter
from millicall.infrastructure.database import async_session, engine
from millicall.infrastructure.orm import metadata
from millicall.infrastructure.repositories.ai_agent_repo import AIAgentRepository
from millicall.infrastructure.repositories.extension_repo import ExtensionRepository
from millicall.infrastructure.repositories.peer_repo import PeerRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def generate_config() -> None:
    """Generate Asterisk config files from database."""
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)

    async with async_session() as session:
        ext_repo = ExtensionRepository(session)
        peer_repo = PeerRepository(session)
        ai_repo = AIAgentRepository(session)

        extensions = await ext_repo.get_all()
        peers = await peer_repo.get_all()
        ai_agents = await ai_repo.get_all()

    peer_map = {p.id: p for p in peers if p.id is not None}
    writer = AsteriskConfigWriter()
    writer.write_pjsip_config(peers)
    writer.write_extensions_config(extensions, peer_map, ai_agents)
    logger.info("Asterisk config files generated successfully")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m millicall.cli <command>")
        print("Commands: generate-config")
        sys.exit(1)

    command = sys.argv[1]
    if command == "generate-config":
        asyncio.run(generate_config())
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
