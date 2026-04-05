"""Hardware / environment sanity checks."""
import pytest
import torch


def test_torch_imports():
    assert torch.__version__ is not None


def test_cuda_available():
    """RTX 3050 should be visible. Fails if drivers or CUDA toolkit are broken."""
    assert torch.cuda.is_available(), "CUDA not available — check drivers"


def test_cuda_device_name():
    if not torch.cuda.is_available():
        pytest.skip("CUDA not available")
    name = torch.cuda.get_device_name(0)
    assert isinstance(name, str) and len(name) > 0


def test_cuda_memory_allocatable():
    """Allocate a small tensor on GPU to verify VRAM is accessible."""
    if not torch.cuda.is_available():
        pytest.skip("CUDA not available")
    t = torch.zeros(1024, 1024, device="cuda")
    assert t.device.type == "cuda"
    del t
    torch.cuda.empty_cache()
