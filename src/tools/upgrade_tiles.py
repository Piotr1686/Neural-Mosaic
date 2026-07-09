"""
src/tools/upgrade_tiles.py
--------------------------
Selective hi-res re-fetch for the tile library (Sprint 3, PLAN_HIRES.md).

The library was crushed to 250 px short-side in-place by src/optimizer.py, so
tiles soften once tile_scale pushes a mosaic cell past ~250 px. This tool
re-downloads the SAME source images at full resolution into the paste-time
overlay data/tiles_hires/ (engine_smart.HIRES_DIR), keyed by filename, so the
render pastes the sharp copy without re-indexing anything.

Input is one or more <stem>_used_tiles.json reports produced by create_mosaic,
so only tiles actually placed in a mosaic get fetched.

Recoverable per source (router in classify_tile):
  coco_train_<id>.jpg -> images.cocodataset.org/train2017/<id>.jpg   (per-file)
  coco_<id>.jpg       -> images.cocodataset.org/unlabeled2017/<id>.jpg
  tile_<idx>.jpg      -> picsum.photos/seed/<idx>/<size>             (per-file)
  food_/places_/dog_/flower_ -> only available inside a multi-GB archive
                                 (etap B, not implemented here) -> "archive"
  everything else (loremflickr keyword tiles) -> "skip"

Every fetched file is checked against the library original with a 5x5 CIELAB
delta-E gate (verify_identity): a wrong id, a changed remote, or a name
collision between two library dirs is caught and the download discarded.

EMPIRICAL (2026-07-09): picsum's seed->photo mapping has DRIFTED since the
library was built — picsum.photos/seed/0/512 no longer returns the photo saved
as tile_000000.jpg (measured mean delta-E ~49). So picsum re-fetch is NOT a
reliable recovery path: every re-fetch is LAB-rejected. picsum is therefore
NOT fetched by default; pass --include-picsum to try anyway (still LAB-gated,
so wrong images are still discarded). COCO IS verified-recoverable per file and
is the sole default fetch source (57% of the library).

Usage:
    python -m src.tools.upgrade_tiles --used-json output/foo_used_tiles.json
    python -m src.tools.upgrade_tiles --used-json a.json --used-json b.json --dry-run
    python -m src.tools.upgrade_tiles --used-json foo.json --limit 200 --size 512
"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image
import skimage.color

try:
    import aiohttp
    import aiofiles
    _HAVE_ASYNC = True
except ImportError:  # network deps optional; router/verify still importable + testable
    _HAVE_ASYNC = False

# --- CONFIGURATION ---
DEFAULT_DEST = Path("data/tiles_hires")
DEFAULT_SIZE = 512
DEFAULT_CONCURRENCY = 16
DEFAULT_MAX_DELTA_E = 8.0

COCO_TRAIN_URL = "http://images.cocodataset.org/train2017/{fname}"
COCO_UNLABELED_URL = "http://images.cocodataset.org/unlabeled2017/{fname}"
PICSUM_URL = "https://picsum.photos/seed/{idx}/{size}"

ARCHIVE_PREFIXES = ("food_", "places_", "dog_", "flower_")
VALID_EXT = (".jpg", ".jpeg", ".png")


# ===========================================================================
# Router (pure) — filename -> (source, url or None)
# ===========================================================================

def _is_coco_id(fname: str) -> bool:
    """True when fname is a bare numeric COCO image name like 000000000009.jpg."""
    stem = fname.rsplit(".", 1)[0]
    return stem.isdigit() and len(stem) >= 6


def _picsum_index(name: str):
    """Return the integer seed from tile_<idx>.<ext>, or None if malformed."""
    stem = name.rsplit(".", 1)[0]
    part = stem[len("tile_"):]
    return int(part) if part.isdigit() else None


def classify_tile(name: str, size: int = DEFAULT_SIZE):
    """Map a library tile filename to (source, url).

    source is one of: "coco", "picsum", "archive", "skip".
    url is None for "archive" (no per-file endpoint) and "skip".

    INVARIANT: coco_train_ MUST be tested before coco_ — otherwise every
    train2017 tile (28% of the library) is misrouted to unlabeled2017.
    """
    if not name.lower().endswith(VALID_EXT):
        return ("skip", None)

    if name.startswith("coco_train_"):
        fname = name[len("coco_train_"):]
        if _is_coco_id(fname):
            return ("coco", COCO_TRAIN_URL.format(fname=fname))
        return ("skip", None)

    if name.startswith("coco_"):
        fname = name[len("coco_"):]
        if _is_coco_id(fname):
            return ("coco", COCO_UNLABELED_URL.format(fname=fname))
        return ("skip", None)

    if name.startswith("tile_"):
        idx = _picsum_index(name)
        if idx is not None:
            # Note: odd idx were loremflickr in downloader.py (not picsum), so
            # this URL yields a different photo -> verify_identity rejects it.
            return ("picsum", PICSUM_URL.format(idx=idx, size=size))
        return ("skip", None)

    if name.startswith(ARCHIVE_PREFIXES):
        return ("archive", None)

    return ("skip", None)


# ===========================================================================
# Identity gate — 5x5 CIELAB delta-E between fetched file and library original
# ===========================================================================

def _lab_grid(path) -> np.ndarray:
    """5x5 real CIELAB grid (L in 0..100, a/b in ~-128..127) — matcher schema."""
    with Image.open(path) as img:
        small = img.convert("RGB").resize((5, 5), Image.Resampling.BOX)
        arr = np.asarray(small, dtype=np.float64) / 255.0
    return skimage.color.rgb2lab(arr)


def mean_delta_e(path_a, path_b) -> float:
    """Mean per-cell CIE76 delta-E over the 5x5 grid of two images."""
    la, lb = _lab_grid(path_a), _lab_grid(path_b)
    return float(np.sqrt(((la - lb) ** 2).sum(axis=2)).mean())


def verify_identity(fetched, lib_path, max_delta_e: float) -> str:
    """Return "ok", "reject", or "unverified".

    "unverified" when the library original is unavailable (can't compare) —
    the download is kept but flagged. "reject" when the colour signature drifts
    beyond max_delta_e (wrong image).
    """
    if lib_path is None or not Path(lib_path).exists():
        return "unverified"
    try:
        return "ok" if mean_delta_e(fetched, lib_path) <= max_delta_e else "reject"
    except Exception:
        # Unreadable library original -> can't gate; keep but flag.
        return "unverified"


# ===========================================================================
# Planning (pure-ish) — merge reports, classify, drop already-present
# ===========================================================================

def collect_used(json_paths):
    """Merge <stem>_used_tiles.json reports into [(name, lib_path, count)].

    Counts for the same filename are summed across reports; the entry list is
    sorted by total count descending (so --limit keeps the most-used tiles).
    """
    merged = {}
    for jp in json_paths:
        data = json.loads(Path(jp).read_text(encoding="utf-8"))
        for t in data.get("tiles", []):
            name = t["name"]
            path = t.get("path", name)
            count = int(t.get("count", 1))
            if name in merged:
                merged[name][1] += count
            else:
                merged[name] = [path, count]
    entries = [(name, pc[0], pc[1]) for name, pc in merged.items()]
    entries.sort(key=lambda e: (-e[2], e[0]))
    return entries


def plan(entries, dest_dir: Path, size: int, include_picsum: bool = False):
    """Classify entries and split into fetchable vs already-present vs other.

    By default only "coco" is queued for fetching (the sole verified-recoverable
    per-file source). "picsum" is queued only when include_picsum is True — its
    seed mapping has drifted, so those fetches are LAB-rejected in practice (see
    module docstring). Returns a dict with per-source breakdown, the to_fetch
    task list [(name, url, lib_path, count)], and the already-present count.
    """
    fetch_sources = {"coco"}
    if include_picsum:
        fetch_sources.add("picsum")

    breakdown = {"coco": 0, "picsum": 0, "archive": 0, "skip": 0}
    to_fetch = []
    skipped_exists = 0
    for name, lib_path, count in entries:
        source, url = classify_tile(name, size)
        breakdown[source] += 1
        if source in fetch_sources:
            dest = dest_dir / name
            if dest.exists() and dest.stat().st_size > 0:
                skipped_exists += 1
                continue
            to_fetch.append((name, url, lib_path, count))
    return {"breakdown": breakdown, "to_fetch": to_fetch,
            "skipped_exists": skipped_exists}


# ===========================================================================
# Async fetch
# ===========================================================================

async def _fetch_one(session, sem, task, dest_dir, max_delta_e, counters):
    name, url, lib_path, _count = task
    dest = dest_dir / name
    tmp = dest_dir / (name + ".part")

    for attempt in range(2):
        try:
            async with sem:
                async with session.get(
                    url, timeout=aiohttp.ClientTimeout(total=25)
                ) as resp:
                    if resp.status != 200:
                        continue
                    content = await resp.read()
            if len(content) < 1000:
                continue

            async with aiofiles.open(tmp, "wb") as fh:
                await fh.write(content)

            verdict = verify_identity(tmp, lib_path, max_delta_e)
            if verdict == "reject":
                _safe_unlink(tmp)
                counters["rejected_lab"] += 1
                return
            os.replace(tmp, dest)
            counters["fetched"] += 1
            if verdict == "unverified":
                counters["unverified"] += 1
            return
        except Exception:
            _safe_unlink(tmp)
            continue

    _safe_unlink(tmp)
    counters["failed_net"] += 1


def _safe_unlink(path: Path):
    try:
        path.unlink()
    except OSError:
        pass


async def run_upgrade(to_fetch, dest_dir: Path, concurrency: int, max_delta_e: float):
    """Fetch every task concurrently; return a counters dict."""
    counters = {"fetched": 0, "rejected_lab": 0, "failed_net": 0, "unverified": 0}
    sem = asyncio.Semaphore(concurrency)
    async with aiohttp.ClientSession() as session:
        tasks = [
            _fetch_one(session, sem, t, dest_dir, max_delta_e, counters)
            for t in to_fetch
        ]
        # Progress without tqdm dependency noise: dots every 200 completions.
        done = 0
        for coro in asyncio.as_completed(tasks):
            await coro
            done += 1
            if done % 200 == 0:
                print(f"  ...{done}/{len(tasks)} processed")
    return counters


# ===========================================================================
# CLI
# ===========================================================================

def _print_breakdown(entries, plan_result, limit, include_picsum):
    b = plan_result["breakdown"]
    to_fetch = plan_result["to_fetch"]
    n_fetch = min(limit, len(to_fetch)) if limit else len(to_fetch)
    print("--- UPGRADE TILES: PLAN ---")
    print(f"  Unique tiles in reports : {len(entries)}")
    print(f"  Per-source breakdown:")
    print(f"    coco (per-file)   : {b['coco']}")
    print(f"    picsum (drifted)  : {b['picsum']}   "
          f"[{'included' if include_picsum else 'not fetched; use --include-picsum'}]")
    print(f"    archive (etap B)  : {b['archive']}   [not fetched here]")
    print(f"    skip (loremflickr): {b['skip']}")
    print(f"  Already in overlay      : {plan_result['skipped_exists']}")
    print(f"  Would fetch now         : {n_fetch}"
          + (f"  (limited from {len(to_fetch)})" if limit and limit < len(to_fetch) else ""))


def _print_report(counters, dest_dir):
    print("--- UPGRADE TILES: RESULT ---")
    print(f"  Fetched   : {counters['fetched']}  (unverified: {counters['unverified']})")
    print(f"  Rejected  : {counters['rejected_lab']}  (LAB delta-E over threshold)")
    print(f"  Failed    : {counters['failed_net']}  (network / non-200)")
    print(f"  Overlay dir: {dest_dir}")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Selective hi-res re-fetch into the tiles_hires overlay."
    )
    parser.add_argument(
        "--used-json", action="append", default=[], metavar="PATH",
        help="A <stem>_used_tiles.json report (repeatable).",
    )
    parser.add_argument("--dest", default=str(DEFAULT_DEST),
                        help=f"Overlay dir (default: {DEFAULT_DEST}).")
    parser.add_argument("--size", type=int, default=DEFAULT_SIZE,
                        help=f"Picsum fetch size (default: {DEFAULT_SIZE}).")
    parser.add_argument("--limit", type=int, default=0,
                        help="Fetch at most N tiles (most-used first). 0 = no cap.")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY,
                        help=f"Concurrent requests (default: {DEFAULT_CONCURRENCY}).")
    parser.add_argument("--max-delta-e", type=float, default=DEFAULT_MAX_DELTA_E,
                        help=f"LAB identity threshold (default: {DEFAULT_MAX_DELTA_E}).")
    parser.add_argument("--include-picsum", action="store_true",
                        help="Also try tile_* picsum re-fetch (seed drifted; "
                             "almost always LAB-rejected). Off by default.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the plan and exit (no network).")
    args = parser.parse_args(argv)

    if not args.used_json:
        parser.error("at least one --used-json report is required")

    entries = collect_used(args.used_json)
    dest_dir = Path(args.dest)
    plan_result = plan(entries, dest_dir, args.size, include_picsum=args.include_picsum)
    _print_breakdown(entries, plan_result, args.limit, args.include_picsum)

    if args.dry_run:
        print("Dry run: nothing fetched.")
        return 0

    to_fetch = plan_result["to_fetch"]
    if args.limit:
        to_fetch = to_fetch[:args.limit]
    if not to_fetch:
        print("Nothing to fetch.")
        return 0

    if not _HAVE_ASYNC:
        print("ERROR: aiohttp/aiofiles not installed; cannot fetch. "
              "Install them or use --dry-run.")
        return 1

    dest_dir.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    counters = asyncio.run(
        run_upgrade(to_fetch, dest_dir, args.concurrency, args.max_delta_e)
    )
    _print_report(counters, dest_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
