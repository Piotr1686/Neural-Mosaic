import os
import pickle
import numpy as np
from pathlib import Path
from PIL import Image
from tqdm import tqdm
import skimage.color

class SmartIndexer:
    def __init__(self, library_path="data/tiles", index_path="data/smart_index.pkl"):
        self.library_path = library_path
        self.index_path = index_path

        Path(self.index_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.library_path).mkdir(parents=True, exist_ok=True)

    def run(self):
        print(f"--- SMART INDEXER ---")
        print(f"Scanning library: {self.library_path}")
        
        valid_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
        image_paths = []
        
        # 1. Zbieranie plików
        for root, dirs, files in os.walk(self.library_path):
            for file in files:
                if os.path.splitext(file)[1].lower() in valid_extensions:
                    image_paths.append(os.path.join(root, file))
        
        if not image_paths:
            print("No images found! Please put images in 'data/library' folder.")
            return

        print(f"Found {len(image_paths)} images. Processing features...")
        
        features = []
        valid_paths = []
        
        # 2. Przetwarzanie (Feature Extraction 3x3 Grid)
        for path in tqdm(image_paths):
            try:
                with Image.open(path) as img:
                    img = img.convert("RGB")
                    
                    # Skalujemy do 3x3 pikseli (to daje 9 pikseli)
                    # Każdy piksel ma 3 kanały (R, G, B) -> razem 27 liczb
                    matrix = img.resize((3, 3), Image.Resampling.BOX)
                    arr = np.array(matrix) / 255.0
                    
                    # Konwersja RGB -> LAB (lepsze dopasowanie kolorów)
                    lab = skimage.color.rgb2lab(arr).flatten()
                    
                    # Normalizacja (taka sama jak w engine_smart.py)
                    # L (0..100) -> 0..1
                    lab[0::3] /= 100.0
                    # A (-128..127) -> 0..1
                    lab[1::3] = (lab[1::3] + 128) / 255.0
                    # B (-128..127) -> 0..1
                    lab[2::3] = (lab[2::3] + 128) / 255.0
                    
                    # Zapisujemy jako float32 dla oszczędności pamięci
                    features.append(lab.astype(np.float32))
                    valid_paths.append(path)
                    
            except Exception as e:
                print(f"Error processing {path}: {e}")

        # 3. Zapis do pliku
        if features:
            data = {
                "paths": valid_paths,
                "features": np.array(features)
            }
            
            with open(self.index_path, "wb") as f:
                pickle.dump(data, f)
            
            print(f"Successfully indexed {len(valid_paths)} images.")
            print(f"Index saved to: {self.index_path}")
        else:
            print("Indexing failed. No valid features extracted.")

if __name__ == "__main__":
    idx = SmartIndexer()
    idx.run()