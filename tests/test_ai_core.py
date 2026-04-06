"""Tests for src/ai_core.py — AICore singleton and depth-map pipeline.

All tests are fully isolated: MiDaS is never actually downloaded.
torch.hub.load is patched wherever model loading would occur.
"""
import numpy as np
import pytest
import torch
from PIL import Image
from unittest.mock import MagicMock, call, patch


# ---------------------------------------------------------------------------
# Singleton isolation — reset between every test
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_singleton():
    """Wipe the AICore singleton before and after each test."""
    import src.ai_core as _mod
    _mod.AICore._instance = None
    yield
    _mod.AICore._instance = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_transforms():
    """Return a mock object that mimics midas_transforms (has .dpt_transform)."""
    t = MagicMock()
    # dpt_transform is itself callable; return a real 4-D tensor so the rest
    # of the pipeline (interpolate / squeeze) works without further mocks.
    t.dpt_transform = MagicMock(
        return_value=torch.zeros(1, 3, 64, 64)
    )
    return t


def _mock_model(output_h=64, output_w=64):
    """Return a mock MiDaS model that produces a plausible depth tensor."""
    m = MagicMock()
    m.to.return_value = m                          # model.to(device) → model
    m.return_value = torch.rand(1, output_h, output_w) * 200  # depth values
    return m


# ---------------------------------------------------------------------------
# Singleton behaviour
# ---------------------------------------------------------------------------

class TestSingleton:
    def test_two_calls_return_same_object(self):
        from src.ai_core import AICore
        assert AICore() is AICore()

    def test_instance_has_device_attribute(self):
        from src.ai_core import AICore
        assert hasattr(AICore(), "device")

    def test_device_is_torch_device(self):
        from src.ai_core import AICore
        assert isinstance(AICore().device, torch.device)

    def test_device_type_is_cuda_or_cpu(self):
        from src.ai_core import AICore
        assert AICore().device.type in ("cuda", "cpu")

    def test_midas_is_none_before_loading(self):
        from src.ai_core import AICore
        assert AICore().midas is None

    def test_midas_transform_is_none_before_loading(self):
        from src.ai_core import AICore
        assert AICore().midas_transform is None


# ---------------------------------------------------------------------------
# load_midas
# ---------------------------------------------------------------------------

class TestLoadMidas:
    def test_returns_model_and_transform(self):
        from src.ai_core import AICore

        mock_model = _mock_model()
        mock_tf = _mock_transforms()

        with patch("torch.hub.load", side_effect=[mock_model, mock_tf]):
            model, transform = AICore().load_midas()

        assert model is mock_model
        assert transform is mock_tf.dpt_transform

    def test_hub_load_called_twice_on_first_call(self):
        """torch.hub.load must be called once for the model, once for transforms."""
        from src.ai_core import AICore

        with patch("torch.hub.load", side_effect=[_mock_model(), _mock_transforms()]) as hub:
            AICore().load_midas()
        assert hub.call_count == 2

    def test_subsequent_calls_do_not_reload(self):
        """load_midas is idempotent — hub.load must NOT be called again."""
        from src.ai_core import AICore

        with patch("torch.hub.load", side_effect=[_mock_model(), _mock_transforms()]) as hub:
            core = AICore()
            core.load_midas()
            core.load_midas()
            core.load_midas()
        assert hub.call_count == 2  # still only the original two calls

    def test_sets_midas_attribute(self):
        from src.ai_core import AICore

        mock_model = _mock_model()
        with patch("torch.hub.load", side_effect=[mock_model, _mock_transforms()]):
            core = AICore()
            core.load_midas()
        assert core.midas is mock_model

    def test_sets_midas_transform_attribute(self):
        from src.ai_core import AICore

        mock_tf = _mock_transforms()
        with patch("torch.hub.load", side_effect=[_mock_model(), mock_tf]):
            core = AICore()
            core.load_midas()
        assert core.midas_transform is mock_tf.dpt_transform

    def test_model_moved_to_device(self):
        from src.ai_core import AICore

        mock_model = _mock_model()
        with patch("torch.hub.load", side_effect=[mock_model, _mock_transforms()]):
            core = AICore()
            core.load_midas()
        mock_model.to.assert_called_once_with(core.device)

    def test_model_put_in_eval_mode(self):
        from src.ai_core import AICore

        mock_model = _mock_model()
        with patch("torch.hub.load", side_effect=[mock_model, _mock_transforms()]):
            AICore().load_midas()
        mock_model.eval.assert_called_once()


# ---------------------------------------------------------------------------
# get_depth_map — integration (mocked model, real PIL / NumPy pipeline)
# ---------------------------------------------------------------------------

class TestGetDepthMap:
    """get_depth_map with a fully mocked MiDaS but a real interpolation path."""

    @pytest.fixture
    def core_with_mock_midas(self):
        """AICore whose midas & midas_transform are replaced with test doubles."""
        from src.ai_core import AICore
        core = AICore()

        mock_tf = MagicMock()
        # transform(img_np) must return a tensor with a working .to()
        mock_tf.return_value = torch.zeros(1, 3, 64, 64)

        mock_midas = MagicMock()
        # Return a (1, 64, 64) depth tensor so F.interpolate has real data
        mock_midas.return_value = torch.rand(1, 64, 64) * 200

        core.midas = mock_midas
        core.midas_transform = mock_tf
        return core

    def test_returns_pil_image(self, core_with_mock_midas):
        result = core_with_mock_midas.get_depth_map(Image.new("RGB", (64, 64)))
        assert isinstance(result, Image.Image)

    def test_output_mode_is_grayscale(self, core_with_mock_midas):
        result = core_with_mock_midas.get_depth_map(Image.new("RGB", (64, 64)))
        assert result.mode == "L"

    def test_output_size_matches_input(self, core_with_mock_midas):
        img = Image.new("RGB", (80, 60))
        result = core_with_mock_midas.get_depth_map(img)
        assert result.size == (80, 60)

    def test_output_size_square(self, core_with_mock_midas):
        img = Image.new("RGB", (64, 64))
        result = core_with_mock_midas.get_depth_map(img)
        assert result.size == (64, 64)

    def test_pixel_values_in_0_255(self, core_with_mock_midas):
        result = core_with_mock_midas.get_depth_map(Image.new("RGB", (64, 64)))
        arr = np.array(result)
        assert arr.min() >= 0
        assert arr.max() <= 255

    def test_transform_receives_numpy_array(self, core_with_mock_midas):
        """MiDaS transform must be given a NumPy array, not a PIL Image (known bug fix)."""
        img = Image.new("RGB", (64, 64), (100, 150, 200))
        core_with_mock_midas.get_depth_map(img)
        first_arg = core_with_mock_midas.midas_transform.call_args[0][0]
        assert isinstance(first_arg, np.ndarray), (
            "transform must receive np.ndarray — PIL Image is not accepted by MiDaS"
        )

    def test_transform_array_shape_matches_image(self, core_with_mock_midas):
        """NumPy array passed to transform must have the same (H, W, 3) shape."""
        img = Image.new("RGB", (80, 60), (0, 128, 255))
        core_with_mock_midas.get_depth_map(img)
        arr_arg = core_with_mock_midas.midas_transform.call_args[0][0]
        assert arr_arg.shape == (60, 80, 3)

    def test_model_called_once_per_image(self, core_with_mock_midas):
        img = Image.new("RGB", (64, 64))
        core_with_mock_midas.get_depth_map(img)
        assert core_with_mock_midas.midas.call_count == 1


# ---------------------------------------------------------------------------
# Depth normalisation — white-box unit tests (no model required)
# ---------------------------------------------------------------------------

class TestDepthNormalisation:
    """Mirror the normalisation branch from get_depth_map and test it directly."""

    @staticmethod
    def _normalise(depth: np.ndarray) -> np.ndarray:
        d_min, d_max = depth.min(), depth.max()
        if d_max - d_min > 0:
            return (depth - d_min) / (d_max - d_min)
        return np.zeros_like(depth, dtype=float)

    def test_min_of_normalised_is_zero(self):
        depth = np.array([[10.0, 50.0], [100.0, 200.0]])
        assert self._normalise(depth).min() == pytest.approx(0.0)

    def test_max_of_normalised_is_one(self):
        depth = np.array([[10.0, 50.0], [100.0, 200.0]])
        assert self._normalise(depth).max() == pytest.approx(1.0)

    def test_uniform_depth_normalises_to_zero(self):
        """Flat depth map (e.g. solid background) must not produce NaN / divide-by-zero."""
        depth = np.full((10, 10), 42.0)
        result = self._normalise(depth)
        assert np.all(result == 0.0)
        assert not np.any(np.isnan(result))

    def test_negative_depth_values_are_handled(self):
        depth = np.array([[-200.0, -100.0], [0.0, 100.0]])
        norm = self._normalise(depth)
        assert norm.min() == pytest.approx(0.0)
        assert norm.max() == pytest.approx(1.0)

    def test_single_element_array(self):
        depth = np.array([[7.5]])
        assert self._normalise(depth)[0, 0] == pytest.approx(0.0)

    def test_large_range_preserves_relative_order(self):
        depth = np.array([[1.0, 500.0, 1000.0]])
        norm = self._normalise(depth)
        assert norm[0, 0] < norm[0, 1] < norm[0, 2]

    def test_scaled_to_uint8_stays_in_range(self):
        """Simulates the final (norm * 255).astype('uint8') step."""
        depth = np.random.rand(50, 50) * 300 - 50  # values in [-50, 250]
        norm = self._normalise(depth)
        uint8 = (norm * 255).astype("uint8")
        assert uint8.min() >= 0
        assert uint8.max() <= 255
