import asyncio
import logging

from bot import main as run_bot

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except RuntimeError as exc:
        logger.error("Startup failed: %s", exc)
        raise SystemExit(1)
