"""
src/tools/make_zoom_gif.py
--------------------------
Generates a zoom-in (optionally bounce-back zoom-out) GIF from a mosaic image.
Sinusoidal easing, crop-first optimization (never resizes the full source per frame).

Usage:
    # Defaults: 250% zoom, 5s in / 2s hold / 5s out, 20 fps, centered.
    python -m src.tools.make_zoom_gif <input> <output.gif>

    # Override timing / zoom / framerate:
    python -m src.tools.make_zoom_gif <input> <output.gif> \
        --zoom 2.5 --zoom-in 5 --hold 2 --zoom-out 5 --fps 20

    # Off-center zoom (fraction of image, 0-1):
    python -m src.tools.make_zoom_gif <input> <output.gif> --cx 0.3 --cy 0.4

    # Disable bounce (one-way zoom-in only):
    python -m src.tools.make_zoom_gif <input> <output.gif> --zoom-out 0
"""
import argparse
import math
import sys
from pathlib import Path

from PIL import Image

# Output dimensions tuned for README embedding: 720x405 (16:9) keeps
# file size comfortable while staying sharp on GitHub's ~720px column.
OUTPUT_W = 640
OUTPUT_H = 360

DEFAULT_FPS = 14              # 70ms/frame, matching original mosaic_zoom.gif
DEFAULT_ZOOM = 20.0           # ~5% crop at max zoom, matching MIN_CROP_FRACTION=0.05
DEFAULT_ZOOM_IN_SEC = 2.8     # 40 frames at 14fps
DEFAULT_HOLD_SEC = 0.8        # pause at max zoom
DEFAULT_ZOOM_OUT_SEC = 0.0    # no bounce
GIF_COLORS = 128


def _easing(t: float) -> float:
    return 0.5 - 0.5 * math.cos(math.pi * t)


def _crop_box(
    img_w: int, img_h: int, t: float,
    cx_frac: float = 0.5, cy_frac: float = 0.5,
    zoom: float = DEFAULT_ZOOM,
) -> tuple:
    """
    Return (x0, y0, x1, y1) for zoom level t in [0, 1].
    t=0 -> largest crop with OUTPUT aspect that fits in image.
    t=1 -> crop scaled down by `zoom` (so crop_w = start_w / zoom).
    Center of zoom at (cx_frac, cy_frac).
    """
    out_ratio = OUTPUT_W / OUTPUT_H

    if img_w / img_h >= out_ratio:
        start_h = img_h
        start_w = int(img_h * out_ratio)
    else:
        start_w = img_w
        start_h = int(img_w / out_ratio)

    min_w = max(2, int(start_w / zoom))
    min_h = max(2, int(start_h / zoom))

    ease_t = _easing(t)
    crop_w = int(start_w + (min_w - start_w) * ease_t)
    crop_h = int(start_h + (min_h - start_h) * ease_t)

    cx = int(img_w * cx_frac)
    cy = int(img_h * cy_frac)

    x0 = max(0, cx - crop_w // 2)
    y0 = max(0, cy - crop_h // 2)
    x1 = min(img_w, x0 + crop_w)
    y1 = min(img_h, y0 + crop_h)

    # Clamp: if we hit the edge, shift the opposite side back
    if x1 - x0 < crop_w:
        x0 = max(0, x1 - crop_w)
    if y1 - y0 < crop_h:
        y0 = max(0, y1 - crop_h)

    return (x0, y0, x1, y1)


def _render_frame(src_rgb: Image.Image, box: tuple) -> Image.Image:
    cropped = src_rgb.crop(box)
    frame = cropped.resize((OUTPUT_W, OUTPUT_H), Image.Resampling.LANCZOS)
    return frame.quantize(
        colors=GIF_COLORS, method=Image.Quantize.MEDIANCUT, dither=1
    )


def make_zoom_gif(
    input_path: Path,
    output_path: Path,
    cx_frac: float = 0.5,
    cy_frac: float = 0.5,
    zoom: float = DEFAULT_ZOOM,
    zoom_in_sec: float = DEFAULT_ZOOM_IN_SEC,
    hold_sec: float = DEFAULT_HOLD_SEC,
    zoom_out_sec: float = DEFAULT_ZOOM_OUT_SEC,
    fps: int = DEFAULT_FPS,
):
    print(f"Loading {input_path.name} ...")
    Image.MAX_IMAGE_PIXELS = None  # allow 16K images

    with Image.open(input_path) as src:
        src_rgb = src.convert("RGB")

    img_w, img_h = src_rgb.size
    print(f"  Source: {img_w}x{img_h} px")
    print(f"  Output: {OUTPUT_W}x{OUTPUT_H} @ {fps} fps, {GIF_COLORS} colors")
    print(f"  Zoom center: ({cx_frac:.2f}, {cy_frac:.2f})  factor: {zoom:.2f}x")
    print(f"  Timing: zoom-in {zoom_in_sec}s | hold {hold_sec}s | zoom-out {zoom_out_sec}s")

    frame_ms = int(round(1000.0 / fps))
    n_zoom_in = max(1, int(round(zoom_in_sec * fps)))
    n_zoom_out = max(0, int(round(zoom_out_sec * fps)))

    frames = []
    durations = []

    # --- zoom-in: t goes 0 -> 1 ---
    for i in range(n_zoom_in):
        t = i / max(n_zoom_in - 1, 1)
        box = _crop_box(img_w, img_h, t, cx_frac, cy_frac, zoom)
        frames.append(_render_frame(src_rgb, box))
        durations.append(frame_ms)
        if i % 20 == 0 or i == n_zoom_in - 1:
            print(f"  zoom-in  {i + 1}/{n_zoom_in}  box={box}", flush=True)

    # --- hold at max zoom: single frame with extended duration ---
    if hold_sec > 0:
        box = _crop_box(img_w, img_h, 1.0, cx_frac, cy_frac, zoom)
        frames.append(_render_frame(src_rgb, box))
        durations.append(int(round(hold_sec * 1000)))
        print(f"  hold     {hold_sec}s on box={box}", flush=True)

    # --- zoom-out: t goes 1 -> 0 ---
    for i in range(n_zoom_out):
        t = 1.0 - (i + 1) / n_zoom_out
        box = _crop_box(img_w, img_h, t, cx_frac, cy_frac, zoom)
        frames.append(_render_frame(src_rgb, box))
        durations.append(frame_ms)
        if i % 20 == 0 or i == n_zoom_out - 1:
            print(f"  zoom-out {i + 1}/{n_zoom_out}  box={box}", flush=True)

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
    print(f"  Saved: {output_path}  ({size_kb:.0f} KB, {len(frames)} frames)")


def main():
    parser = argparse.ArgumentParser(
        description="Generate zoom-in/out GIF from a mosaic image.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", type=Path, help="Source image (JPG or PNG)")
    parser.add_argument("output", type=Path, help="Output GIF path")
    parser.add_argument(
        "--cx", type=float, default=0.5, metavar="FRAC",
        help="Horizontal zoom center as fraction 0-1 (default: 0.5)",
    )
    parser.add_argument(
        "--cy", type=float, default=0.5, metavar="FRAC",
        help="Vertical zoom center as fraction 0-1 (default: 0.5)",
    )
    parser.add_argument(
        "--zoom", type=float, default=DEFAULT_ZOOM,
        help=f"Zoom factor at max (default: {DEFAULT_ZOOM} = 250%%)",
    )
    parser.add_argument(
        "--zoom-in", dest="zoom_in", type=float, default=DEFAULT_ZOOM_IN_SEC,
        help=f"Zoom-in duration in seconds (default: {DEFAULT_ZOOM_IN_SEC})",
    )
    parser.add_argument(
        "--hold", type=float, default=DEFAULT_HOLD_SEC,
        help=f"Hold duration at max zoom in seconds (default: {DEFAULT_HOLD_SEC})",
    )
    parser.add_argument(
        "--zoom-out", dest="zoom_out", type=float, default=DEFAULT_ZOOM_OUT_SEC,
        help=f"Zoom-out duration in seconds, 0 to disable bounce (default: {DEFAULT_ZOOM_OUT_SEC})",
    )
    parser.add_argument(
        "--fps", type=int, default=DEFAULT_FPS,
        help=f"Frames per second (default: {DEFAULT_FPS})",
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"ERROR: input not found: {args.input}")
        sys.exit(1)

    make_zoom_gif(
        args.input,
        args.output,
        cx_frac=args.cx,
        cy_frac=args.cy,
        zoom=args.zoom,
        zoom_in_sec=args.zoom_in,
        hold_sec=args.hold,
        zoom_out_sec=args.zoom_out,
        fps=args.fps,
    )


if __name__ == "__main__":
    main()
