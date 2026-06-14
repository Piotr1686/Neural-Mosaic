"""
src/tools/sanity_check.py
--------------------------
Validates the smart tile index against the on-disk library.

Checks:
  1. Metadata — schema_version, feature_dim consistency
  2. Path integrity — orphans (in index, gone from disk) + untracked (on disk, not indexed)
  3. LAB colour coverage — mean-L histogram across 10 luminance buckets
  4. File integrity — Pillow.verify() on a random sample of disk tiles

Usage:
    python -m src.tools.sanity_check
    python -m src.tools.sanity_check --json data/sanity_report.json
    python -m src.tools.sanity_check --no-integrity
    python -m src.tools.sanity_check --index data/smart_index.pkl --sample 200
"""
import argparse
import json
import os
import pickle
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from tqdm import tqdm

from src.library_dirs import LIBRARY_DIRS as _LIBRARY_DIRS

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
INDEX_PATH = PROJECT_ROOT / "data" / "smart_index.pkl"

# Resolve the shared (relative) library dirs against the project root so the
# tool works regardless of the current working directory.
LIBRARY_DIRS = [PROJECT_ROOT / d for d in _LIBRARY_DIRS]

VALID_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
INTEGRITY_SAMPLE_SIZE = 500
LAB_BUCKETS = 10
COVERAGE_WARN_THRESHOLD = 0.30
COVERAGE_MIN_POPULATED = 0.01


def _load_index(index_path: Path) -> dict:
    with open(index_path, "rb") as f:
        return pickle.load(f)


def _scan_library(lib_dirs: list) -> set:
    paths = set()
    for lib_dir in lib_dirs:
        if not lib_dir.exists():
            continue
        for root, _, files in os.walk(lib_dir):
            for fname in files:
                if Path(fname).suffix.lower() in VALID_EXTS:
                    paths.add(Path(root, fname).resolve())
    return paths


def _normalize_index_paths(raw_paths: list, project_root: Path) -> list:
    result = []
    for p in raw_paths:
        p = Path(p)
        if not p.is_absolute():
            p = (project_root / p).resolve()
        else:
            p = p.resolve()
        result.append(p)
    return result


def _check_metadata(data: dict) -> dict:
    features = data["features"]
    stored_header_dim = data.get("feature_dim", features.shape[1])
    return {
        "schema_version": data.get("schema_version", "unknown"),
        "feature_dim": stored_header_dim,
        "actual_dim": features.shape[1],
        "tile_count": features.shape[0],
        "dim_match": stored_header_dim == features.shape[1],
    }


def _check_paths(index_paths: list, disk_paths: set) -> dict:
    index_set = set(index_paths)
    orphans = index_set - disk_paths
    untracked_count = len(disk_paths - index_set)
    return {
        "orphan_count": len(orphans),
        "orphans": sorted(str(p) for p in orphans),
        "untracked_count": untracked_count,
    }


def _check_lab_coverage(features: np.ndarray) -> dict:
    # Mean L across the 5x5 grid per tile; L is every 3rd element from index 0.
    # Slice the first 75 dims first: the index is written as 79-dim (5x5_edge),
    # and the 4 trailing edge features (scaled by EDGE_WEIGHT) would otherwise
    # be picked up by [::3] and contaminate the luminance histogram.
    L_vals = features[:, :75][:, 0::3].mean(axis=1)
    hist, edges = np.histogram(L_vals, bins=LAB_BUCKETS, range=(0.0, 1.0))
    total = len(L_vals)
    fractions = hist / total
    populated = int((fractions > COVERAGE_MIN_POPULATED).sum())
    max_frac = float(fractions.max())
    max_idx = int(fractions.argmax())
    return {
        "buckets": [
            {
                "range": f"{edges[i]*100:.0f}-{edges[i+1]*100:.0f}",
                "count": int(hist[i]),
                "fraction": round(float(fractions[i]), 4),
            }
            for i in range(LAB_BUCKETS)
        ],
        "populated_buckets": populated,
        "max_fraction": round(max_frac, 4),
        "max_bucket_range": f"{edges[max_idx]*100:.0f}-{edges[max_idx+1]*100:.0f}",
        "warn_imbalance": max_frac > COVERAGE_WARN_THRESHOLD,
    }


def _check_integrity(disk_paths: set, sample_size: int) -> dict:
    sample = random.sample(sorted(disk_paths), min(sample_size, len(disk_paths)))
    corrupt = []
    for p in tqdm(sample, desc="  Integrity sample", unit="img", leave=False):
        try:
            with Image.open(p) as img:
                img.verify()
        except Exception as e:
            corrupt.append({"path": str(p), "error": str(e)})
    return {
        "sampled": len(sample),
        "corrupt_count": len(corrupt),
        "corrupt": corrupt,
    }


def _bar(fraction: float, width: int = 20) -> str:
    filled = round(fraction * width)
    return "█" * filled + "░" * (width - filled)


def _print_report(
    meta: dict,
    path_check: dict,
    lab: dict,
    integrity: dict,
    index_path: Path,
) -> None:
    W = 58
    SEP = "═" * W

    print(f"\n{SEP}")
    print("  SMART INDEX SANITY CHECK")
    print(f"  {index_path}")
    print(SEP)

    # 1. Metadata
    print("\n[1] INDEX METADATA")
    print(f"    schema_version : {meta['schema_version']}")
    print(f"    feature_dim    : {meta['feature_dim']}  (actual: {meta['actual_dim']})")
    print(f"    tile_count     : {meta['tile_count']:,}")
    if meta["dim_match"]:
        print(f"    ✓  Dimensions consistent ({meta['actual_dim']})")
    else:
        print(f"    ⚠  MISMATCH: header={meta['feature_dim']}, matrix={meta['actual_dim']}")

    # 2. Path integrity
    print("\n[2] PATH INTEGRITY")
    print(f"    Orphan tiles    : {path_check['orphan_count']:,}  (in index, missing on disk)")
    print(f"    Untracked tiles : {path_check['untracked_count']:,}  (on disk, not in index)")
    if path_check["orphan_count"] == 0:
        print("    ✓  All indexed paths exist on disk.")
    else:
        print(f"    ⚠  {path_check['orphan_count']} orphan(s) — re-index to clean up.")
        for p in path_check["orphans"][:5]:
            print(f"       {p}")
        if path_check["orphan_count"] > 5:
            print(f"       … and {path_check['orphan_count'] - 5} more")
    if path_check["untracked_count"] > 0:
        print(f"    ℹ  Run indexer to include {path_check['untracked_count']:,} untracked file(s).")

    # 3. LAB coverage
    print(f"\n[3] COLOUR COVERAGE  (mean L per tile, {LAB_BUCKETS} buckets)")
    for b in lab["buckets"]:
        flag = " ⚠" if b["fraction"] > COVERAGE_WARN_THRESHOLD else ""
        label = f"L {b['range']:>6}%"
        print(f"    {label}  {_bar(b['fraction'])}  {b['fraction']*100:5.1f}%{flag}")
    print(f"    Populated buckets : {lab['populated_buckets']}/{LAB_BUCKETS}")
    if lab["warn_imbalance"]:
        print(
            f"    ⚠  Bucket L {lab['max_bucket_range']}% holds {lab['max_fraction']*100:.1f}%"
            " of tiles — consider diversifying library."
        )
    else:
        print(f"    ✓  No bucket exceeds {COVERAGE_WARN_THRESHOLD*100:.0f}%.")

    # 4. File integrity
    print(f"\n[4] FILE INTEGRITY SAMPLE  (N={integrity['sampled']})")
    if integrity["corrupt_count"] == 0:
        print("    ✓  All sampled files readable.")
    else:
        print(f"    ⚠  {integrity['corrupt_count']} corrupt file(s):")
        for c in integrity["corrupt"][:5]:
            print(f"       {c['path']}: {c['error']}")
        if integrity["corrupt_count"] > 5:
            print(f"       … and {integrity['corrupt_count'] - 5} more")

    # Summary
    issues = (
        path_check["orphan_count"]
        + (1 if lab["warn_imbalance"] else 0)
        + integrity["corrupt_count"]
    )
    print(f"\n{SEP}")
    if issues == 0:
        print("  ✓  All checks passed.")
    else:
        print(f"  ⚠  {issues} issue group(s) found — see above.")
    print(f"{SEP}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate the NeuroMosaic smart tile index.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--index", type=Path, default=INDEX_PATH, metavar="PATH",
        help="Path to smart_index.pkl (default: data/smart_index.pkl)",
    )
    parser.add_argument(
        "--json", dest="json_out", type=Path, default=None, metavar="PATH",
        help="Write JSON report to this file",
    )
    parser.add_argument(
        "--no-integrity", action="store_true",
        help="Skip the file integrity sample (faster)",
    )
    parser.add_argument(
        "--sample", type=int, default=INTEGRITY_SAMPLE_SIZE, metavar="N",
        help=f"Number of files to sample for integrity check (default: {INTEGRITY_SAMPLE_SIZE})",
    )
    args = parser.parse_args()

    if not args.index.exists():
        print(f"ERROR: index not found: {args.index}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading index … {args.index}")
    data = _load_index(args.index)

    print("Scanning library dirs …")
    disk_paths = _scan_library(LIBRARY_DIRS)
    print(f"  Found {len(disk_paths):,} files on disk.")

    index_paths = _normalize_index_paths(data["paths"], PROJECT_ROOT)

    meta = _check_metadata(data)
    path_check = _check_paths(index_paths, disk_paths)
    lab = _check_lab_coverage(data["features"])
    integrity = (
        {"sampled": 0, "corrupt_count": 0, "corrupt": []}
        if args.no_integrity
        else _check_integrity(disk_paths, args.sample)
    )

    _print_report(meta, path_check, lab, integrity, args.index)

    if args.json_out:
        report = {
            "metadata": meta,
            "path_integrity": path_check,
            "lab_coverage": lab,
            "file_integrity": {
                "sampled": integrity["sampled"],
                "corrupt_count": integrity["corrupt_count"],
                "corrupt": integrity["corrupt"],
            },
        }
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"JSON report written to {args.json_out}")


if __name__ == "__main__":
    main()
