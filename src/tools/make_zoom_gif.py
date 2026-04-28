"""
src/tools/make_zoom_gif.py
--------------------------
Generates a zoom-in GIF from a mosaic image (16K JPG or PNG).
Zooms from full image to tile-level detail with sinusoidal easing.

Optimization: crop-first -- extracts ROI from full-res image before
resizing to output size. Never resizes the full 16K image per frame.

Usage:
    python -m src.tools.make_zoom_gif <input> <output.gif>
    python -m src.tools.make_zoom_gif <input> <output.gif> --frames 40
    python -m src.tools.make_zoom_gif <input> <output.gif> --cx 0.3 --cy 0.4
"""
import argparse
import math
import sys
from pathlib import Path

from PIL import Image

OUTPUT_W = 640
OUTPUT_H = 360
N_FRAMES = 40
FRAME_MS = 70
PAUSE_MS = 800
GIF_COLORS = 128
MIN_CROP_FRACTION = 0.05   # at max zoom, crop = 5% of image short edge


def _easing(t: float) -> float:
    return 0.5 - 0.5 * math.cos(math.pi * t)


def _crop_box(
    img_w: int, img_h: int, t: float,
    cx_frac: float = 0.5, cy_frac: float = 0.5,
) -> tuple:
    """
    Return (x0, y0, x1, y1) for zoom level t (0=full, 1=max zoom).
    Maintains OUTPUT_W:OUTPUT_H aspect ratio. Center of zoom at (cx_frac, cy_frac).
    """
    out_ratio = OUTPUT_W / OUTPUT_H

    # Starting crop: largest rect with correct aspect ratio that fits in image
    if img_w / img_h >= out_ratio:
        start_h = img_h
        start_w = int(img_h * out_ratio)
    else:
        start_w = img_w
        start_h = int(img_w / out_ratio)

    # Minimum crop size (maximum zoom level)
    min_side = min(img_w, img_h) * MIN_CROP_FRACTION
    if out_ratio >= 1.0:
        min_w = max(2, int(min_side * out_ratio))
        min_h = max(2, int(min_side))
    else:
        min_w = max(2, int(min_side))
        min_h = max(2, int(min_side / out_ratio))

    ease_t = _easing(t)
    crop_w = int(start_w + (min_w - start_w) * ease_t)
    crop_h = int(start_h + (min_h - start_h) * ease_t)

    # Center of zoom
    cx = int(img_w * cx_frac)
    cy = int(img_h * cy_frac)

    x0 = max(0, cx - crop_w // 2)
    y0 = max(0, cy - crop_h // 2)
    x1 = min(img_w, x0 + crop_w)
    y1 = min(img_h, y0 + crop_h)

    # Clamp: if we hit the edge, shift the opposite side
    if x1 - x0 < crop_w:
        x0 = max(0, x1 - crop_w)
    if y1 - y0 < crop_h:
        y0 = max(0, y1 - crop_h)

    return (x0, y0, x1, y1)


def make_zoom_gif(
    input_path: Path,
    output_path: Path,
    n_frames: int = N_FRAMES,
    cx_frac: float = 0.5,
    cy_frac: float = 0.5,
):
    print(f"Loading {input_path.name} ...")
    Image.MAX_IMAGE_PIXELS = None  # allow 16K images

    with Image.open(input_path) as src:
        src_rgb = src.convert("RGB")

    img_w, img_h = src_rgb.size
    print(f"  Source: {img_w}x{img_h} px")
    print(f"  Zoom center: ({cx_frac:.2f}, {cy_frac:.2f})")

    frames = []
    durations = []

    for i in range(n_frames):
        t = i / max(n_frames - 1, 1)
        box = _crop_box(img_w, img_h, t, cx_frac, cy_frac)
        cropped = src_rgb.crop(box)
        frame = cropped.resize((OUTPUT_W, OUTPUT_H), Image.Resampling.LANCZOS)
        frames.append(frame.quantize(colors=GIF_COLORS, method=Image.Quantize.MEDIANCUT, dither=1))

        if i == 0 or i == n_frames - 1:
            durations.append(PAUSE_MS)
        else:
            durations.append(FRAME_MS)

        if i % 10 == 0 or i == n_frames - 1:
            print(f"  Frame {i + 1}/{n_frames}  box={box}", flush=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        loop=0,
        duration=durations,
        optimize=False,
    )
    size_kb = output_path.stat().st_size / 1024
    print(f"  Saved: {output_path}  ({size_kb:.0f} KB)")


def main():
    parser = argparse.ArgumentParser(
        description="Generate zoom-in GIF from a mosaic image.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", type=Path, help="Source image (JPG or PNG)")
    parser.add_argument("output", type=Path, help="Output GIF path")
    parser.add_argument(
        "--frames", type=int, default=N_FRAMES,
        help=f"Number of frames (default: {N_FRAMES})",
    )
    parser.add_argument(
        "--cx", type=float, default=0.5, metavar="FRAC",
        help="Horizontal zoom center as fraction 0-1 (default: 0.5)",
    )
    parser.add_argument(
        "--cy", type=float, default=0.5, metavar="FRAC",
        help="Vertical zoom center as fraction 0-1 (default: 0.5)",
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"ERROR: input not found: {args.input}")
        sys.exit(1)

    make_zoom_gif(args.input, args.output, n_frames=args.frames, cx_frac=args.cx, cy_frac=args.cy)


if __name__ == "__main__":
    main()
