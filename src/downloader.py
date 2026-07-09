"""
src/downloader.py
-----------------
Asynchronous tile downloader for NeuroMosaic.

Fetches tile images from Picsum and LoremFlickr using rotating keywords
and resumable downloads.  Designed to handle large datasets (100 000+
images) without saturating RAM or leaving broken files on disk.
"""
import asyncio
import logging
import os
import sys
import random
import aiohttp
import aiofiles
from tqdm.asyncio import tqdm
from src.config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("FastDownloader")

class FastDownloader:
    """Async tile downloader with keyword rotation and duplicate-skip logic.

    Uses two image sources in alternation:
      - Picsum Photos  (stable, high quality, deterministic seeds)
      - LoremFlickr    (high variety via keyword rotation)
    """

    # Safe keyword list — always returns real photos, never error placeholders.
    KEYWORDS = [
        "nature", "water", "fire", "sky", "grass", "mountain", "beach",
        "city", "architecture", "building", "road", "bridge",
        "animal", "cat", "dog", "bird", "fish",
        "abstract", "texture", "pattern", "light", "bokeh", "color",
        "food", "coffee", "fruit", "vegetable",
        "people", "portrait", "woman", "man", "crowd",
        "tech", "computer", "space", "galaxy"
    ]

    def __init__(self, target_count: int = 100000):
        self.target_count = target_count
        # High concurrency limit — 100 k images needs throughput.
        self.semaphore = asyncio.Semaphore(60)
        self.session = None

    async def download_image(self, idx: int, pbar: tqdm):
        filename = settings.DATA_DIR / f"tile_{idx:06d}.jpg"
        if filename.exists():
            # Skip files that are already complete (non-zero size).
            if filename.stat().st_size > 0:
                pbar.update(1)
                return

        # Source rotation strategy:
        #   Even indices  → Picsum (deterministic seed for reproducibility)
        #   Odd indices   → LoremFlickr with a random keyword (variety)
        # DOWNLOAD_SIZE (default 512), NOT TILE_SIZE (75): tiles are stored at
        # fetch resolution and must stay sharp when a mosaic cell is larger than
        # the placement grid. See config.Config.DOWNLOAD_SIZE.
        size = settings.DOWNLOAD_SIZE
        if idx % 2 == 0:
            url = f"https://picsum.photos/seed/{idx}/{size}"
        else:
            keyword = random.choice(self.KEYWORDS)
            # random={idx} forces a fresh image for each index.
            url = f"https://loremflickr.com/{size}/{size}/{keyword}?random={idx}"

        try:
            async with self.semaphore:
                async with self.session.get(url, timeout=15) as response:
                    if response.status == 200:
                        content = await response.read()
                        # Reject suspiciously small responses — likely error pages.
                        if len(content) > 1000:
                            # Write to a temp file then atomically rename, so an
                            # interrupted write never leaves a truncated .jpg that
                            # the size>0 skip-check would treat as complete.
                            tmp = filename.with_suffix(".part")
                            async with aiofiles.open(tmp, mode='wb') as f:
                                await f.write(content)
                            os.replace(tmp, filename)
                    pbar.update(1)
        except Exception:
            # At 100 k downloads, transient failures are expected — skip silently.
            pass

    async def run(self):
        settings.DATA_DIR.mkdir(parents=True, exist_ok=True)

        logger.info(f"Starting download of {self.target_count} tiles ({settings.DOWNLOAD_SIZE}px)...")
        logger.info("Strategy: Picsum + LoremFlickr (Filtered Keywords)")

        async with aiohttp.ClientSession() as session:
            self.session = session
            pbar = tqdm(total=self.target_count, desc="Downloading Massive Dataset")

            tasks = [self.download_image(i, pbar) for i in range(self.target_count)]
            await asyncio.gather(*tasks)

            pbar.close()
        logger.info("Download complete. You can now run the indexer.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    downloader = FastDownloader(target_count=settings.NUM_IMAGES)
    asyncio.run(downloader.run())
