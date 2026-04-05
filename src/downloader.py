# src/fast_downloader.py
import asyncio
import logging
import sys
import random
import aiohttp
import aiofiles
from tqdm.asyncio import tqdm
from src.config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("FastDownloader")

class FastDownloader:
    """
    Downloader v2.0 - Obsługa 100k zdjęć i unikanie 'broken images'.
    Wykorzystuje rotację słów kluczowych.
    """
    
    # Lista bezpiecznych kategorii, które zawsze zwracają zdjęcia (bez napisów błędów)
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
        # Zwiększamy limit połączeń, bo 100k to sporo roboty
        self.semaphore = asyncio.Semaphore(60) 
        self.session = None

    async def download_image(self, idx: int, pbar: tqdm):
        filename = settings.DATA_DIR / f"tile_{idx:06d}.jpg"
        if filename.exists():
            # Jeśli plik jest pusty lub uszkodzony (0 bajtów), pobierz ponownie
            if filename.stat().st_size > 0:
                pbar.update(1)
                return

        # Strategia rotacji źródeł
        # 1. Picsum (Stabilne, wysoka jakość, ale mało unikalnych seedów)
        # 2. LoremFlickr z losowym słowem kluczowym (Duża różnorodność)
        
        if idx % 2 == 0:
            # Używamy konkretnego seeda, żeby mieć determinizm
            url = f"https://picsum.photos/seed/{idx}/{settings.TILE_SIZE}"
        else:
            # Losujemy kategorię, żeby uniknąć "Image Not Found"
            keyword = random.choice(self.KEYWORDS)
            # random={idx} wymusza nowe zdjęcie
            url = f"https://loremflickr.com/{settings.TILE_SIZE}/{settings.TILE_SIZE}/{keyword}?random={idx}"

        try:
            async with self.semaphore:
                async with self.session.get(url, timeout=15) as response:
                    if response.status == 200:
                        content = await response.read()
                        # Prosta walidacja: jeśli obrazek jest za mały (<1KB), to pewnie błąd
                        if len(content) > 1000:
                            async with aiofiles.open(filename, mode='wb') as f:
                                await f.write(content)
                        pbar.update(1)
        except Exception:
            # Przy 100k zdjęciach błędy się zdarzą - ignorujemy pojedyncze sztuki
            pass

    async def run(self):
        settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Start pobierania {self.target_count} kafelków (100x100px)...")
        logger.info("Strategia: Picsum + LoremFlickr (Filtered Keywords)")

        async with aiohttp.ClientSession() as session:
            self.session = session
            pbar = tqdm(total=self.target_count, desc="Downloading Massive Dataset")
            
            # Tworzymy zadania
            tasks = [self.download_image(i, pbar) for i in range(self.target_count)]
            
            # Uruchamiamy
            await asyncio.gather(*tasks)
            
            pbar.close()
        logger.info("Pobieranie zakończone. Możesz uruchamiać main.py.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    downloader = FastDownloader(target_count=settings.NUM_IMAGES)
    asyncio.run(downloader.run())