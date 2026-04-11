"""
src/ai_core.py
--------------
Singleton wrapper around the MiDaS depth-estimation model.

Provides lazy loading so the model is only downloaded and moved to the GPU
once, regardless of how many times AICore() is constructed.
"""
import torch
from PIL import Image
import numpy as np


class AICore:
    """Singleton AI core providing depth-estimation via MiDaS DPT_Hybrid.

    Usage:
        core = AICore()
        depth_img = core.get_depth_map(pil_image)
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AICore, cls).__new__(cls)
            cls._instance.device = torch.device(
                "cuda" if torch.cuda.is_available() else "cpu"
            )
            cls._instance.midas = None
            cls._instance.midas_transform = None
        return cls._instance

    def load_midas(self):
        """Lazy-load the MiDaS depth estimation model on first call.

        Returns:
            Tuple of (model, transform) ready for inference.
        """
        if self.midas is None:
            print(f"Loading MiDaS (Depth) on {self.device}...")
            # DPT_Hybrid offers the best quality/speed balance within 4 GB VRAM.
            self.midas = torch.hub.load("intel-isl/MiDaS", "DPT_Hybrid")
            self.midas.to(self.device)
            self.midas.eval()

            midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
            self.midas_transform = midas_transforms.dpt_transform
        return self.midas, self.midas_transform

    def get_depth_map(self, img_pil):
        """Return a grayscale depth map for the given PIL image.

        Args:
            img_pil: Input image as a PIL Image (RGB).

        Returns:
            Depth map as a grayscale PIL Image with values 0-255
            (brighter = farther from camera).
        """
        midas, transform = self.load_midas()

        # MiDaS transform expects a NumPy array, not a PIL Image.
        img_np = np.array(img_pil)

        input_batch = transform(img_np).to(self.device)

        with torch.no_grad():
            prediction = midas(input_batch)

            # Resize prediction back to original image dimensions.
            prediction = torch.nn.functional.interpolate(
                prediction.unsqueeze(1),
                size=img_pil.size[::-1],  # (height, width)
                mode="bicubic",
                align_corners=False,
            ).squeeze()

        depth = prediction.cpu().numpy()

        # Normalise depth values to the 0-255 range.
        depth_min = depth.min()
        depth_max = depth.max()

        # Guard against division by zero for uniform-colour images.
        if depth_max - depth_min > 0:
            depth_norm = (depth - depth_min) / (depth_max - depth_min)
        else:
            depth_norm = np.zeros_like(depth)

        return Image.fromarray((depth_norm * 255).astype("uint8"))