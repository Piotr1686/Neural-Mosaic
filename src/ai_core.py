import torch
from PIL import Image
import numpy as np

class AICore:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AICore, cls).__new__(cls)
            cls._instance.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            cls._instance.midas = None
            cls._instance.midas_transform = None
        return cls._instance

    def load_midas(self):
        """Ładuje model MiDaS do estymacji głębi."""
        if self.midas is None:
            print(f"Loading MiDaS (Depth) on {self.device}...")
            # Używamy mniejszego modelu 'DPT_Hybrid' dla balansu jakość/szybkość
            self.midas = torch.hub.load("intel-isl/MiDaS", "DPT_Hybrid")
            self.midas.to(self.device)
            self.midas.eval()
            
            midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
            self.midas_transform = midas_transforms.dpt_transform
        return self.midas, self.midas_transform

    def get_depth_map(self, img_pil):
        """Zwraca mapę głębi (PIL Image, Grayscale) dla danego zdjęcia."""
        midas, transform = self.load_midas()
        
        # FIX: MiDaS transform wymaga tablicy NumPy, a nie obiektu PIL.
        # Konwertujemy obraz na tablicę NumPy przed przekazaniem do transformacji.
        img_np = np.array(img_pil)
        
        input_batch = transform(img_np).to(self.device)
        
        with torch.no_grad():
            prediction = midas(input_batch)
            
            # Skalowanie wyniku z powrotem do oryginalnego rozmiaru
            prediction = torch.nn.functional.interpolate(
                prediction.unsqueeze(1),
                size=img_pil.size[::-1], # (Height, Width)
                mode="bicubic",
                align_corners=False,
            ).squeeze()

        depth = prediction.cpu().numpy()
        
        # Normalizacja do 0-255
        depth_min = depth.min()
        depth_max = depth.max()
        
        # Zabezpieczenie przed dzieleniem przez zero (gdyby obraz był jednokolorowy)
        if depth_max - depth_min > 0:
            depth_norm = (depth - depth_min) / (depth_max - depth_min)
        else:
            depth_norm = np.zeros_like(depth)
            
        depth_img = Image.fromarray((depth_norm * 255).astype("uint8"))
        return depth_img