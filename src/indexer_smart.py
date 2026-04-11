"""
src/indexer_smart.py
--------------------
Builds the SmartEngine colour index from the tile library.

Each image is reduced to a 3×3 pixel grid and converted to CIELAB colour
space, producing a 27-dimensional feature vector (9 pixels × 3 channels).
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


class SmartIndexer:
    """Scans a tile library and builds a CIELAB feature index for SmartEngine.

    Args:
        library_path: Directory containing the tile images (searched recursively).
        index_path:   Destination path for the serialised index pickle file.
    """

    def __init__(self, library_path="data/tiles", index_path="data/smart_index.pkl"):
        self.library_path = library_path
        self.index_path = index_path

        Path(self.index_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.library_path).mkdir(parents=True, exist_ok=True)

    def run(self):
        """Scan the library, extract features, and write the index to disk."""
        print("--- SMART INDEXER ---")
        print(f"Scanning library: {self.library_path}")

        valid_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
        image_paths = []

        # 1. Collect all image file paths recursively.
        for root, _dirs, files in os.walk(self.library_path):
            for file in files:
                if os.path.splitext(file)[1].lower() in valid_extensions:
                    image_paths.append(os.path.join(root, file))

        if not image_paths:
            print("No images found! Please place tile images in the 'data/tiles' folder.")
            return

        print(f"Found {len(image_paths)} images. Extracting features...")

        features = []
        valid_paths = []

        # 2. Feature extraction: 3×3 CIELAB grid → 27-dim vector per image.
        for path in tqdm(image_paths):
            try:
                with Image.open(path) as img:
                    img = img.convert("RGB")

                    # Downscale to 3×3 pixels: 9 pixels × 3 channels = 27 numbers.
                    matrix = img.resize((3, 3), Image.Resampling.BOX)
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

                    # Store as float32 to minimise memory usage.
                    features.append(lab.astype(np.float32))
                    valid_paths.append(path)

            except Exception as e:
                print(f"Error processing {path}: {e}")

        # 3. Persist the index to disk.
        if features:
            data = {
                "paths": valid_paths,
                "features": np.array(features),
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