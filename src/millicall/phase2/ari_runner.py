"""Entry point for the ARI listener process."""

import asyncio
import logging

logging.basicConfig(level=logging.INFO)


def main():
    from millicall.phase2.ari_handler import run_ari_listener
    asyncio.run(run_ari_listener())


if __name__ == "__main__":
    main()
