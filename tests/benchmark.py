"""
tests/benchmark.py
------------------
Performance benchmark for NeuroMosaic — generates values for the README table.

Each operation is timed with time.perf_counter(); peak RAM is tracked via psutil.
The script prints a "README-paste" block at the end — copy the values directly
into the Performance section of README.md.

Usage:
    python -m tests.benchmark              # all benchmarks (~30+ min on full library)
    python -m tests.benchmark --quick      # skip 16K kite render
    python -m tests.benchmark --no-typo   # skip Symbol Mosaic (no typo index needed)
    python -m tests.benchmark --quick --no-typo
"""
import argparse
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
import random
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import psutil
from PIL import Image

# Optional CUDA tracking — SmartEngine runs on CPU, but VRAM is reported if available.
try:
    import torch
    _CUDA = torch.cuda.is_available()
except ImportError:
    _CUDA = False

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

LIBRARY_DIRS = [
    PROJECT_ROOT / "data" / "library_starter" / "tiles",
    PROJECT_ROOT / "data" / "library_public" / "tiles",
    PROJECT_ROOT / "data" / "library_public_2" / "tiles",
    PROJECT_ROOT / "data" / "library_extended" / "tiles",
    PROJECT_ROOT / "data" / "library_private" / "tiles",
]
VALID_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

INDEX_PATH      = PROJECT_ROOT / "data" / "smart_index.pkl"
TYPO_INDEX_PATH = PROJECT_ROOT / "data" / "typo_index.pkl"


# ── helpers ──────────────────────────────────────────────────────────────────

def _rss_mb() -> float:
    return psutil.Process().memory_info().rss / 1024**2


def _vram_mb() -> float:
    return torch.cuda.max_memory_allocated() / 1024**2 if _CUDA else 0.0


def _reset_vram():
    if _CUDA:
        torch.cuda.reset_peak_memory_stats()


def _fmt(s: float) -> str:
    return f"{s/60:.1f} min" if s >= 60 else f"{s:.1f} s"


def _scan_library() -> list:
    paths = []
    for lib_dir in LIBRARY_DIRS:
        if not lib_dir.exists():
            continue
        for root, _, files in os.walk(lib_dir):
            for fname in files:
                if Path(fname).suffix.lower() in VALID_EXTS:
                    paths.append(Path(root) / fname)
    return paths


def _make_test_image(path: Path, size=(1024, 768)):
    """Synthetic colour gradient — exercises the full LAB gamut."""
    w, h = size
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    arr[:, :, 0] = np.linspace(0, 255, w, dtype=np.uint8)[np.newaxis, :]
    arr[:, :, 1] = np.linspace(0, 255, h, dtype=np.uint8)[:, np.newaxis]
    arr[:, :, 2] = 128
    Image.fromarray(arr).save(path)


# ── benchmarks ───────────────────────────────────────────────────────────────

def bench_indexing(all_paths: list) -> list:
    """Time the 79-dim feature extraction loop for 10k and 50k tiles."""
    import skimage.color
    EDGE_WEIGHT = 2.0
    results = []

    for n in (10_000, 50_000):
        if len(all_paths) < n:
            print(f"  [skip] Index {n:,} tiles — library too small ({len(all_paths)} files)")
            continue

        sample = random.sample(all_paths, n)
        print(f"  Indexing {n:,} tiles …", flush=True)
        ram0 = _rss_mb()
        t0   = time.perf_counter()
        ok   = 0

        for path in sample:
            try:
                with Image.open(path) as img:
                    arr = np.array(img.convert("RGB").resize((5, 5), Image.Resampling.BOX)) / 255.0
                    lab = skimage.color.rgb2lab(arr)
                    flat = lab.flatten()
                    flat[0::3] /= 100.0
                    flat[1::3] = (flat[1::3] + 128) / 255.0
                    flat[2::3] = (flat[2::3] + 128) / 255.0
                    edge = np.array([
                        lab[0, :, 0].mean() / 100.0,
                        lab[:, 4, 0].mean() / 100.0,
                        lab[4, :, 0].mean() / 100.0,
                        lab[:, 0, 0].mean() / 100.0,
                    ], dtype=np.float32) * EDGE_WEIGHT
                    _ = np.concatenate([flat.astype(np.float32), edge])
                    ok += 1
            except Exception:
                pass

        elapsed = time.perf_counter() - t0
        ram_delta = max(0.0, _rss_mb() - ram0)
        results.append({
            "label": f"Index {n:,} tiles",
            "elapsed_s": elapsed,
            "ram_delta_mb": ram_delta,
            "n_ok": ok,
        })
        print(f"  ✓ {_fmt(elapsed)}  ({ok:,} succeeded)")

    return results


def bench_render(test_img: Path, configs: list) -> list:
    if not INDEX_PATH.exists():
        print(f"  [skip] Smart renders — index not found: {INDEX_PATH}")
        return []

    from src.engine_smart import SmartEngine
    engine = SmartEngine(index_path=str(INDEX_PATH))
    if not engine.paths:
        print("  [skip] Smart renders — index failed to load.")
        return []

    results = []
    with tempfile.TemporaryDirectory() as tmpdir:
        for cfg in configs:
            label = cfg["label"]
            out   = Path(tmpdir) / f"{label.replace(' ', '_')}.jpg"
            print(f"\n  → {label}")
            engine.settings.update({
                "allow_mirror": False,
                "edge_aware": False,
                "freq_penalty": 30.0,
            })
            ram0 = _rss_mb()
            _reset_vram()
            t0 = time.perf_counter()
            engine.create_mosaic(
                target_path=str(test_img),
                output_path=str(out),
                resolution_key=cfg["res"],
                shape_mode=cfg["shape"],
                tile_scale=cfg.get("scale", 1.0),
            )
            elapsed    = time.perf_counter() - t0
            ram_delta  = max(0.0, _rss_mb() - ram0)
            vram       = _vram_mb()
            results.append({
                "label": label,
                "elapsed_s": elapsed,
                "ram_delta_mb": ram_delta,
                "vram_mb": vram,
            })
            print(f"  ✓ {label}: {_fmt(elapsed)}")

    return results


def bench_typo(test_img: Path):
    if not TYPO_INDEX_PATH.exists():
        print(f"  [skip] Symbol Mosaic — typo index not found: {TYPO_INDEX_PATH}")
        return None

    from src.engine_typo import TypoEngine
    engine = TypoEngine(index_path=str(TYPO_INDEX_PATH))
    if not engine.library:
        print("  [skip] Symbol Mosaic — typo index empty.")
        return None

    print("\n  → Symbol mosaic 8K · B&W")
    with tempfile.TemporaryDirectory() as tmpdir:
        out  = Path(tmpdir) / "bench_typo.png"
        ram0 = _rss_mb()
        t0   = time.perf_counter()
        engine.process(
            input_path=str(test_img),
            output_path=str(out),
            res_key="8K",
            mode="black_on_white",
            scale=1.0,
        )
        elapsed   = time.perf_counter() - t0
        ram_delta = max(0.0, _rss_mb() - ram0)

    print(f"  ✓ Symbol mosaic 8K · B&W: {_fmt(elapsed)}")
    return {
        "label": "Symbol mosaic 8K · B&W",
        "elapsed_s": elapsed,
        "ram_delta_mb": ram_delta,
    }


# ── reporting ─────────────────────────────────────────────────────────────────

def print_summary(idx_res: list, rnd_res: list, typ_res):
    W   = 64
    SEP = "═" * W

    print(f"\n{SEP}")
    print("  NEUROMOSAIC BENCHMARK RESULTS")
    cuda_tag = f"  |  CUDA available: {torch.cuda.get_device_name(0)}" if _CUDA else "  |  CUDA: not available"
    print(f"  CPUs: {psutil.cpu_count()}{cuda_tag}")
    print(SEP)
    print(f"  {'Operation':<36}  {'Time':>9}  {'RAM Δ':>8}")
    print(f"  {'─'*36}  {'─'*9}  {'─'*8}")

    for r in idx_res:
        print(f"  {r['label']:<36}  {_fmt(r['elapsed_s']):>9}  {r['ram_delta_mb']:>6.0f} MB")
    for r in rnd_res:
        vram_tag = f"   VRAM: {r['vram_mb']:.0f} MB" if r.get("vram_mb") else ""
        print(f"  {r['label']:<36}  {_fmt(r['elapsed_s']):>9}  {r['ram_delta_mb']:>6.0f} MB{vram_tag}")
    if typ_res:
        print(f"  {typ_res['label']:<36}  {_fmt(typ_res['elapsed_s']):>9}  {typ_res['ram_delta_mb']:>6.0f} MB")

    peak_ram_gb = _rss_mb() / 1024
    peak_vram_gb = _vram_mb() / 1024

    print(f"\n  Peak RAM  : {peak_ram_gb:.2f} GB")
    if _CUDA:
        print(f"  Peak VRAM : {peak_vram_gb:.2f} GB  (engine runs on CPU — VRAM is overhead only)")
    else:
        print("  Peak VRAM : N/A")

    # README-ready paste block
    print(f"\n{SEP}")
    print("  README PASTE — replace '— s' and '— GB' in the Performance table:")
    print(SEP)

    note = "(engine runs on CPU — same for both columns)"

    for r in idx_res:
        t = _fmt(r["elapsed_s"])
        print(f"  | {r['label']:<35} | {t:>7} | {t:>7} |")
    for r in rnd_res:
        t = _fmt(r["elapsed_s"])
        print(f"  | {r['label']:<35} | {t:>7} | {t:>7} |")
    if typ_res:
        t = _fmt(typ_res["elapsed_s"])
        print(f"  | {typ_res['label']:<35} | {t:>7} | {t:>7} |")

    vram_str = f"{peak_vram_gb:.2f} GB" if _CUDA else "N/A"
    print(f"  | {'Peak VRAM':<35} | {vram_str:>7} | {'N/A':>7} |  {note}")
    print(f"  | {'Peak RAM':<35} | {peak_ram_gb:.2f} GB | {peak_ram_gb:.2f} GB |")
    print(f"\n  Note: {note}")
    print(f"{SEP}\n")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="NeuroMosaic performance benchmark — generates README table values.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--quick", action="store_true",
        help="Skip 16K kite render (long — can take 15-30 min)",
    )
    parser.add_argument(
        "--no-typo", action="store_true",
        help="Skip Symbol Mosaic benchmark",
    )
    args = parser.parse_args()

    render_configs = [
        {"label": "Render 4K · square tiles",   "res": "4K",  "shape": "square",  "scale": 1.0},
        {"label": "Render 8K · hexagon tiles",  "res": "8K",  "shape": "hexagon", "scale": 1.0},
    ]
    if not args.quick:
        render_configs.append(
            {"label": "Render 16K · kite tiles", "res": "16K", "shape": "kite",   "scale": 1.0}
        )

    print("=" * 64)
    print("  NeuroMosaic Benchmark")
    if args.quick:
        print("  Mode: --quick  (16K kite skipped)")
    print("=" * 64)

    with tempfile.TemporaryDirectory() as tmpdir:
        test_img = Path(tmpdir) / "test_source.jpg"
        _make_test_image(test_img, size=(1024, 768))
        print(f"\n  Test image: {test_img.name}  (1024×768 synthetic gradient)\n")

        # 1. Indexing
        print("[1] INDEXING BENCHMARK")
        all_paths = _scan_library()
        print(f"  Library: {len(all_paths):,} files found")
        idx_res = bench_indexing(all_paths)

        # 2. Render
        print("\n[2] RENDER BENCHMARK (SmartEngine)")
        rnd_res = bench_render(test_img, render_configs)

        # 3. Symbol Mosaic
        typ_res = None
        if not args.no_typo:
            print("\n[3] SYMBOL MOSAIC BENCHMARK (TypoEngine)")
            typ_res = bench_typo(test_img)

        print_summary(idx_res, rnd_res, typ_res)


if __name__ == "__main__":
    main()
