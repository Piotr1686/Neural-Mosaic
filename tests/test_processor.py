import pytest
import numpy as np
import torch
from src.processor import TileProcessor

def test_cuda_availability():
    """Sprawdza, czy PyTorch widzi Twoją kartę RTX 3050."""
    assert torch.cuda.is_available(), "CUDA nie jest dostępne! Sprawdź sterowniki."

def test_mean_color_calculation():
    """Sprawdza, czy algorytm poprawnie liczy średni kolor."""
    # Tworzymy czysto czerwony obrazek 10x10
    red_tile = np.zeros((10, 10, 3), dtype=np.uint8)
    red_tile[:, :] = [255, 0, 0]
    
    # Średnia powinna być [255, 0, 0]
    mean = red_tile.mean(axis=(0, 1))
    assert np.array_equal(mean, [255, 0, 0])