"""Tests for src/config.py — Config dataclass and settings singleton."""
import pytest
from pathlib import Path
from src.config import Config, settings


def test_config_instantiates():
    cfg = Config()
    assert cfg is not None


def test_paths_are_absolute():
    cfg = Config()
    assert cfg.BASE_DIR.is_absolute()
    assert cfg.DATA_DIR.is_absolute()
    assert cfg.OUTPUT_DIR.is_absolute()
    assert cfg.INPUT_DIR.is_absolute()


def test_data_dir_under_base():
    cfg = Config()
    assert cfg.BASE_DIR in cfg.DATA_DIR.parents


def test_default_tile_size():
    cfg = Config()
    assert cfg.TILE_SIZE == 75


def test_default_target_short_side():
    cfg = Config()
    assert cfg.TARGET_SHORT_SIDE == 18000


def test_default_download_size():
    cfg = Config()
    assert cfg.DOWNLOAD_SIZE == 512


def test_download_size_decoupled_from_tile_size():
    cfg = Config()
    # Storage resolution must not collapse to the placement grid (the bug that
    # softened the library): downloads should be larger than TILE_SIZE.
    assert cfg.DOWNLOAD_SIZE > cfg.TILE_SIZE


def test_use_cuda_is_bool():
    cfg = Config()
    assert isinstance(cfg.USE_CUDA, bool)


def test_settings_is_config_instance():
    assert isinstance(settings, Config)


def test_cache_path_includes_tile_size():
    cfg = Config()
    assert str(cfg.TILE_SIZE) in str(cfg.CACHE_PATH)


def test_cache_path_is_under_data_dir():
    cfg = Config()
    assert cfg.DATA_DIR in cfg.CACHE_PATH.parents
