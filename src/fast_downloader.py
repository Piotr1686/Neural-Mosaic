"""
src/fast_downloader.py
----------------------
Compatibility alias for the async tile downloader.

CLAUDE.md and README document ``python -m src.fast_downloader`` as the entry
point for bulk tile downloads, but the implementation lives in
``src/downloader.py`` (class ``FastDownloader``). This thin shim keeps the
documented command working without duplicating the downloader logic.
"""
import asyncio
import sys

from src.config import settings
from src.downloader import FastDownloader

__all__ = ["FastDownloader"]


def main() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    downloader = FastDownloader(target_count=settings.NUM_IMAGES)
    asyncio.run(downloader.run())


if __name__ == "__main__":
    main()
