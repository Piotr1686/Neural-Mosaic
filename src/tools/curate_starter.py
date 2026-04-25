"""
src/tools/curate_starter.py
---------------------------
Farthest-point sampling in CIELAB colour space.

Selects N images from a source library that maximally cover the colour space,
then copies them to a destination directory (default: data/library_starter/tiles/).

Usage:
    python -m src.tools.curate_starter
    python -m src.tools.curate_starter --src data/library_public_2/tiles --n 500
"""
import argparse
import logging
import shutil
from pathlib import Path

import numpy as np
from PIL import Image
from tqdm import tqdm
import skimage.color

logger = logging.getLogger(__name__)

DEFAULT_SRC = Path("data/library_public_2/tiles")
DEFAULT_DST = Path("data/library_starter/tiles")
DEFAULT_N = 500
VALID_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def extract_lab_feature(path: Path) -> "np.ndarray | None":
    """5×5 CIELAB grid → 75-dim float32 vector (identical to indexer_smart schema)."""
    try:
        with Image.open(path) as img:
            img = img.convert("RGB")
            matrix = img.resize((5, 5), Image.Resampling.BOX)
            arr = np.array(matrix) / 255.0
            lab = skimage.color.rgb2lab(arr).flatten()
            lab[0::3] /= 100.0
            lab[1::3] = (lab[1::3] + 128) / 255.0
            lab[2::3] = (lab[2::3] + 128) / 255.0
            return lab.astype(np.float32)
    except Exception as exc:
        logger.warning("Skipped %s: %s", path.name, exc)
        return None


def farthest_point_sample(features: np.ndarray, n: int) -> list:
    """Return indices of n points that maximally cover the feature space.

    Greedy FPS: each step picks the candidate whose minimum distance to any
    already-selected point is largest.
    """
    m = len(features)
    if n >= m:
        return list(range(m))

    selected = [int(np.random.randint(m))]
    min_dists = np.full(m, np.inf)

    for _ in tqdm(range(n - 1), desc="Sampling", unit="tile"):
        last = features[selected[-1]]
        dists = np.sum((features - last) ** 2, axis=1)
        np.minimum(min_dists, dists, out=min_dists)
        selected.append(int(np.argmax(min_dists)))

    return selected


def curate(src: Path, dst: Path, n: int) -> int:
    """Extract LAB features, run FPS, copy selected files to dst.

    Returns the number of files copied.
    """
    src = Path(src)
    dst = Path(dst)
    dst.mkdir(parents=True, exist_ok=True)

    paths = sorted(p for p in src.iterdir() if p.suffix.lower() in VALID_EXT)
    if not paths:
        print(f"No images found in {src}")
        return 0

    print(f"Found {len(paths)} images in {src}. Extracting LAB features...")
    features, valid_paths = [], []
    for p in tqdm(paths, desc="Features", unit="img"):
        feat = extract_lab_feature(p)
        if feat is not None:
            features.append(feat)
            valid_paths.append(p)

    if not features:
        print("No valid images — nothing to sample.")
        return 0

    features_arr = np.array(features)
    n = min(n, len(valid_paths))
    print(f"Running farthest-point sampling: selecting {n} from {len(valid_paths)}...")

    indices = farthest_point_sample(features_arr, n)
    selected = [valid_paths[i] for i in indices]

    print(f"Copying {len(selected)} files → {dst} ...")
    for p in tqdm(selected, desc="Copying", unit="file"):
        shutil.copy2(p, dst / p.name)

    print(f"Done. {len(selected)} tiles saved to {dst}")
    return len(selected)


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(
        description="Curate a starter tile set via farthest-point LAB sampling."
    )
    parser.add_argument(
        "--src", default=str(DEFAULT_SRC),
        help=f"Source tile directory (default: {DEFAULT_SRC})",
    )
    parser.add_argument(
        "--dst", default=str(DEFAULT_DST),
        help=f"Destination directory (default: {DEFAULT_DST})",
    )
    parser.add_argument(
        "--n", type=int, default=DEFAULT_N,
        help=f"Number of tiles to select (default: {DEFAULT_N})",
    )
    args = parser.parse_args()

    curate(Path(args.src), Path(args.dst), args.n)
