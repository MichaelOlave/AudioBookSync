"""Main entry point for AudioBookSync."""

import asyncio

from .core.logging_config import configure_logging
from .operations.library_sync import sync_library


async def main():
    """Main async entry point."""
    await sync_library()


if __name__ == "__main__":
    configure_logging()
    asyncio.run(main())
