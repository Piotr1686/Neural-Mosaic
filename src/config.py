"""
src/config.py
-------------
Application-wide configuration for Neural-Mosaic.

Loads environment variables from a .env file and exposes them as typed
fields on a frozen dataclass so every module imports from one place.
"""
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    """
    Configuration v4.0 - Neural-Mosaic Architecture.
    Supports dynamic shapes and advanced rendering.
    """
    
    # --- PATHS ---
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    INPUT_DIR: Path = BASE_DIR / "input"
    DATA_DIR: Path = BASE_DIR / "data" / "tiles"
    OUTPUT_DIR: Path = BASE_DIR / "output"
    
    # --- PARAMETERS ---
    TARGET_SHORT_SIDE: int = int(os.getenv("TARGET_SHORT_SIDE", 18000))
    TILE_SIZE: int = int(os.getenv("TILE_SIZE", 75))
    GHOSTING_OPACITY: float = float(os.getenv("GHOSTING_OPACITY", 0.25))
    
    # --- DATA ---
    # Downloader target count only (read by downloader.FastDownloader). NOT a cap
    # on the indexer or engine — both process every tile they find. Env key is
    # NUM_TILES for historical reasons.
    NUM_IMAGES: int = int(os.getenv("NUM_TILES", 300000))
    
    # --- HARDWARE ---
    USE_CUDA: bool = os.getenv("USE_CUDA", "True").lower() == "true"

    def __post_init__(self):
        for directory in [self.DATA_DIR, self.OUTPUT_DIR, self.INPUT_DIR]:
            directory.mkdir(parents=True, exist_ok=True)

    @property
    def CACHE_PATH(self) -> Path:
        """Dynamic cache filename based on tile size."""
        return self.DATA_DIR / f"tiles_cache_size{self.TILE_SIZE}.pkl"

settings = Config()