"""
src/indexer_smart.py
--------------------
Builds the SmartEngine colour index from the tile library.

Each image is reduced to a 5×5 pixel grid and converted to CIELAB colour
space, producing a 75-dimensional feature vector (25 pixels × 3 channels).
The resulting feature matrix and file paths are persisted to a pickle file
so SmartEngine can load them instantly at runtime.
"""
import os
import pickle
import numpy as np
from pathlib import Path
from PIL import Image
from tqdm import tqdm
import skimage.color


LIBRARY_DIRS = [
    Path("data/library_starter/tiles"),
    Path("data/library_public/tiles"),
    Path("data/library_extended/tiles"),
    Path("data/library_private/tiles"),
]


class SmartIndexer:
    """Scans a tile library and builds a CIELAB feature index for SmartEngine.

    Args:
        library_path: Directory containing the tile images (searched recursively).
                      If None, all LIBRARY_DIRS are scanned.
        index_path:   Destination path for the serialised index pickle file.
    """

    def __init__(self, library_path=None, index_path="data/smart_index.pkl"):
        self.library_path = library_path
        self.index_path = index_path

        Path(self.index_path).parent.mkdir(parents=True, exist_ok=True)
        for lib_dir in LIBRARY_DIRS:
            lib_dir.mkdir(parents=True, exist_ok=True)

    def run(self):
        """Scan the library, extract features, and write the index to disk."""
        print("--- SMART INDEXER ---")

        valid_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
        image_paths = []

        if self.library_path:
            scan_dirs = [Path(self.library_path)]
        else:
            scan_dirs = LIBRARY_DIRS

        for lib_dir in scan_dirs:
            count = len(list(lib_dir.glob("*.jpg")) + list(lib_dir.glob("*.jpeg")) +
                        list(lib_dir.glob("*.png")) + list(lib_dir.glob("*.webp")))
            print(f"  {lib_dir}: {count} images")
            for root, _dirs, files in os.walk(lib_dir):
                for file in files:
                    if os.path.splitext(file)[1].lower() in valid_extensions:
                        image_paths.append(os.path.join(root, file))

        if not image_paths:
            print("No images found! Place tile images in one of the LIBRARY_DIRS.")
            return

        print(f"Found {len(image_paths)} images. Extracting features...")

        features = []
        valid_paths = []

        # Feature extraction: 5×5 CIELAB grid → 75-dim vector per image.
        for path in tqdm(image_paths):
            try:
                with Image.open(path) as img:
                    img = img.convert("RGB")

                    # Downscale to 5×5 pixels: 25 pixels × 3 channels = 75 numbers.
                    matrix = img.resize((5, 5), Image.Resampling.BOX)
                    arr = np.array(matrix) / 255.0

                    # Convert RGB → CIELAB for perceptually uniform colour matching.
                    lab = skimage.color.rgb2lab(arr).flatten()

                    # Normalise to [0, 1] — must match engine_smart.py exactly.
                    # L channel: 0..100  → 0..1
                    lab[0::3] /= 100.0
                    # a channel: -128..127 → 0..1
                    lab[1::3] = (lab[1::3] + 128) / 255.0
                    # b channel: -128..127 → 0..1
                    lab[2::3] = (lab[2::3] + 128) / 255.0

                    features.append(lab.astype(np.float32))
                    valid_paths.append(path)

            except Exception as e:
                print(f"Error processing {path}: {e}")

        if features:
            data = {
                "paths": valid_paths,
                "features": np.array(features),
                "schema_version": "5x5",
                "feature_dim": 75,
            }
            with open(self.index_path, "wb") as f:
                pickle.dump(data, f)

            print(f"Successfully indexed {len(valid_paths)} images.")
            print(f"Index saved to: {self.index_path}")
        else:
            print("Indexing failed — no valid features extracted.")


if __name__ == "__main__":
    idx = SmartIndexer()
    idx.run()
