"""Hardware / environment sanity checks.

``torch`` is an OPTIONAL dependency (not pinned in requirements.txt) and CUDA is
only present on the dev machine. The whole module skips when torch is missing
(``importorskip``), and the GPU-specific checks skip when CUDA is unavailable
(``requires_cuda``) — so this file is safe to collect in CI (CPU, often no
torch) instead of being ignored.
"""
import pytest

torch = pytest.importorskip("torch")

requires_cuda = pytest.mark.skipif(
    not torch.cuda.is_available(),
    reason="CUDA not available (CPU-only environment)",
)


def test_torch_imports():
    assert torch.__version__ is not None


@requires_cuda
def test_cuda_available():
    """RTX 3050 should be visible when CUDA is present (drivers/toolkit OK)."""
    assert torch.cuda.is_available()


@requires_cuda
def test_cuda_device_name():
    name = torch.cuda.get_device_name(0)
    assert isinstance(name, str) and len(name) > 0


@requires_cuda
def test_cuda_memory_allocatable():
    """Allocate a small tensor on GPU to verify VRAM is accessible."""
    t = torch.zeros(1024, 1024, device="cuda")
    assert t.device.type == "cuda"
    del t
    torch.cuda.empty_cache()
