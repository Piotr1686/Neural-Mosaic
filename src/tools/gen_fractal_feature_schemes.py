"""Generate schematic previews for the FRACTAL FEATURE proposals (Sprint 3).

Adversarial design process 2026-07-05 (Wizjoner -> Inzynier + Esteta -> Arbiter
-> owner verdict). Finalists visualised here:
  A. quadtree_detail   - adaptive tile density (quadtree by local detail)
  B. zoom_movie        - dolly-zoom storyboard (tile becomes the next mosaic)
  C. fractal_crossfade - two mosaics stitched by an fBm threshold front
  D. hilbert_flow      - tile pick order along a Hilbert curve (always-on)

PROPOSAL previews (720x720), NOT engine implementations. Mock mosaics are
grids of colour cells sampled from synthetic targets (no tile library needed).
Pure PIL + numpy, deterministic (seeded RNG only). ASCII-only prints (CP1250).

Outputs:
  output/fractal_proposals/<name>.png                   (4 panels)
  output/fractal_proposals/proposals_fractal_features.png  (2x2 montage)

Run:
  C:/Users/plazo/miniconda3/envs/mosaic/python.exe -m src.tools.gen_fractal_feature_schemes
"""
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT_DIR = Path("output/fractal_proposals")
SIZE = 720
BG = (16, 16, 20)
OUTLINE = (20, 20, 24)


def vary(rng, base, amount=12):
    return tuple(int(np.clip(c + rng.integers(-amount, amount + 1), 0, 255)) for c in base)


def hsv_rgb(h, s, v):
    import colorsys
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return (int(r * 255), int(g * 255), int(b * 255))


def _font(size):
    try:
        return ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _label(draw, xy, txt, size=15):
    f = _font(size)
    x, y = xy
    draw.text((x + 1, y + 1), txt, fill=(0, 0, 0), font=f)
    draw.text((x, y), txt, fill=(240, 240, 240), font=f)


# ==========================================
# SYNTHETIC TARGETS (continuous colour functions on [0,1]^2)
# ==========================================
def target_portrait(u, v):
    """Warm 'portrait': hair / face ellipse / shoulders on a dark ground."""
    if ((u - 0.5) / 0.23) ** 2 + ((v - 0.42) / 0.29) ** 2 < 1:
        if v < 0.585 - 0.35 * abs(u - 0.5):
            return (74, 50, 42)                    # hair
        return (223, 177, 146)                     # face
    if v > 0.80 and abs(u - 0.5) < 0.34:
        return (142, 62, 60)                       # shoulders
    return (40, 42, 58)                            # background


def target_landscape(u, v):
    """Cool 'landscape': sky gradient, sun disc, sea below the horizon."""
    if math.hypot(u - 0.70, v - 0.24) < 0.11:
        return (250, 212, 122)                     # sun
    if v < 0.60:
        t = v / 0.60
        return (int(96 + 90 * t), int(140 + 60 * t), int(196 + 20 * t))
    t = (v - 0.60) / 0.40
    return (int(40 - 14 * t + 14), int(84 - 30 * t + 10), int(120 - 40 * t))


# ==========================================
# A. QUADTREE DETAIL
# ==========================================
def gen_quadtree_detail():
    """Adaptive-density mosaic: quadtree splits while local detail (std of
    luminance) exceeds a threshold - big cells on smooth sky, tiny cells on
    texture. The cell-density map IS the motif, so it survives photo
    substitution by construction (Sprint 2, Esteta lesson a)."""
    n = 768                                        # power-of-2 friendly (768 = 2^8 * 3)
    rng = np.random.default_rng(101)
    yy, xx = np.mgrid[0:n, 0:n].astype(float) / n

    img = np.zeros((n, n, 3))
    sky_t = np.clip(yy / 0.66, 0, 1)               # smooth sky gradient
    img[..., 0] = 92 + 112 * sky_t
    img[..., 1] = 136 + 56 * sky_t
    img[..., 2] = 198 - 40 * sky_t
    d_sun = np.hypot(xx - 0.74, yy - 0.18)         # smooth sun disc, soft edge
    sun = np.clip((0.10 - d_sun) / 0.025, 0, 1)
    for c, val in enumerate((252, 214, 122)):
        img[..., c] = img[..., c] * (1 - sun) + val * sun
    ground = yy > 0.70                             # smooth warm ground
    for c, val in enumerate((150, 118, 84)):
        img[..., c][ground] = val - 26 * ((yy[ground] - 0.70) / 0.30) * (val / 150)

    noise = rng.random((n, n))                     # high-frequency texture source
    crown = np.hypot((xx - 0.30) / 1.0, (yy - 0.42) / 0.85) < 0.17
    trunk = (np.abs(xx - 0.30) < 0.016) & (yy > 0.42) & (yy < 0.72)
    hedge = (yy > 0.62) & (yy < 0.70) & (np.abs(np.sin(xx * 60) * 0.5 + noise) > 0.55)
    for mask, base in ((crown, (52, 96, 46)), (trunk, (86, 60, 40)), (hedge, (74, 104, 52))):
        tex = 0.55 + 0.45 * noise[mask]
        for c, val in enumerate(base):
            img[..., c][mask] = val * tex
    gray = img.mean(axis=2)

    leaves = []

    def split(x, y, s, depth):
        if depth >= 6 or s <= 12 or gray[y:y + s, x:x + s].std() < 6.5:
            leaves.append((x, y, s))
            return
        h = s // 2
        for dy in (0, h):
            for dx in (0, h):
                split(x + dx, y + dy, h, depth + 1)

    split(0, 0, n, 0)

    out = Image.new("RGB", (n, n), BG)
    d = ImageDraw.Draw(out)
    for x, y, s in leaves:
        base = tuple(int(c) for c in img[y:y + s, x:x + s].reshape(-1, 3).mean(axis=0))
        d.rectangle([x, y, x + s - 1, y + s - 1], fill=vary(rng, base, 9), outline=OUTLINE)
    out = out.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
    print(f"      quadtree: {len(leaves)} leaves "
          f"(min {min(s for _, _, s in leaves)} px, max {max(s for _, _, s in leaves)} px)")
    return out


# ==========================================
# helpers for mock mosaics (B, C)
# ==========================================
def _mock_mosaic(target, size, cell, seed, window=(0.0, 0.0, 1.0)):
    """Grid of colour cells sampled from a continuous target function with a
    per-cell variation - reads as a photomosaic stand-in. `window` = (u0, v0,
    span) view into target space (for zoom frames)."""
    rng = np.random.default_rng(seed)
    u0, v0, span = window
    img = Image.new("RGB", (size, size), BG)
    d = ImageDraw.Draw(img)
    for y in range(0, size, cell):
        for x in range(0, size, cell):
            u = u0 + span * (x + cell / 2) / size
            v = v0 + span * (y + cell / 2) / size
            d.rectangle([x, y, x + cell - 1, y + cell - 1],
                        fill=vary(rng, target(u, v), 13), outline=OUTLINE)
    return img


# ==========================================
# B. ZOOM MOVIE (storyboard)
# ==========================================
def gen_zoom_movie():
    """Dolly-zoom storyboard in 4 frames: full mosaic A -> 4x zoom (the target
    tile marked) -> the tile fills the frame and the NEXT mosaic bleeds
    through -> full mosaic B. The rendered feature is a looping GIF; a static
    schematic can only show the keyframes."""
    F = 351
    G = 6
    u0, v0, spanz = 0.54, 0.28, 0.25               # zoom window (eye/cheek area)
    canvas = Image.new("RGB", (SIZE, SIZE), BG)

    f1 = _mock_mosaic(target_portrait, F, 13, 201)
    d = ImageDraw.Draw(f1)
    d.rectangle([u0 * F, v0 * F, (u0 + spanz) * F, (v0 + spanz) * F],
                outline=(240, 70, 60), width=3)
    _label(d, (8, 6), "1. mozaika A")

    f2 = _mock_mosaic(target_portrait, F, 52, 202, window=(u0, v0, spanz))
    d = ImageDraw.Draw(f2)
    d.rectangle([156, 156, 156 + 52, 156 + 52], outline=(240, 70, 60), width=3)
    _label(d, (8, 6), "2. zoom x4 -> kafelek")

    f3 = _mock_mosaic(target_landscape, F, 13, 203)
    tile_col = target_portrait(u0 + spanz * 0.52, v0 + spanz * 0.52)
    overlay = Image.new("RGB", (F, F), tile_col)
    f3 = Image.blend(f3, overlay, 0.45)
    d = ImageDraw.Draw(f3)
    d.rectangle([0, 0, F - 1, F - 1], outline=(240, 70, 60), width=3)
    _label(d, (8, 6), "3. kafelek = mozaika B")

    f4 = _mock_mosaic(target_landscape, F, 13, 204)
    d = ImageDraw.Draw(f4)
    _label(d, (8, 6), "4. mozaika B (petla...)")

    for img, (cx, cy) in zip((f1, f2, f3, f4),
                             ((G, G), (2 * G + F, G), (G, 2 * G + F), (2 * G + F, 2 * G + F))):
        canvas.paste(img, (cx, cy))
    return canvas


# ==========================================
# C. FRACTAL CROSSFADE
# ==========================================
def _fbm(n, seed):
    """Multi-octave value noise (fBm) on an n x n grid, range ~[0, 2)."""
    rng = np.random.default_rng(seed)
    acc = np.zeros((n, n))
    amp = 1.0
    for g in (6, 12, 24, 48):
        grid = (rng.random((g + 1, g + 1)) * 255).astype(np.uint8)
        up = Image.fromarray(grid, "L").resize((n, n), Image.Resampling.BILINEAR)
        acc += amp * (np.asarray(up, dtype=float) / 255.0)
        amp *= 0.5
    return acc


def gen_fractal_crossfade():
    """MVP frame at threshold t = median: cell takes mosaic A below t, B above,
    and a narrow |field - t| band blends 50/50. The self-similar fBm front is
    jagged at every scale - the 'frost on glass' seam between two mosaics."""
    ncell = 48
    cell = SIZE // ncell
    field = _fbm(ncell, 301)
    t = float(np.median(field))
    eps = 0.035 * (field.max() - field.min())
    rng = np.random.default_rng(302)
    img = Image.new("RGB", (SIZE, SIZE), BG)
    d = ImageDraw.Draw(img)
    nb = 0
    for j in range(ncell):
        for i in range(ncell):
            u = (i + 0.5) / ncell
            v = (j + 0.5) / ncell
            ca = target_portrait(u, v)
            cb = target_landscape(u, v)
            f = field[j, i]
            if abs(f - t) < eps:
                col = tuple((a + b) // 2 for a, b in zip(ca, cb))
                nb += 1
            elif f < t:
                col = ca
            else:
                col = cb
            d.rectangle([i * cell, j * cell, (i + 1) * cell - 1, (j + 1) * cell - 1],
                        fill=vary(rng, col, 13), outline=OUTLINE)
    print(f"      crossfade: t={t:.3f}, {nb} blended border cells")
    return img


# ==========================================
# D. HILBERT FLOW
# ==========================================
def _hilbert_xy(idx, order):
    """Index along the Hilbert curve -> (x, y) on the 2^order grid."""
    n = 1 << order
    x = y = 0
    t = idx
    s = 1
    while s < n:
        rx = 1 & (t // 2)
        ry = 1 & (t ^ rx)
        if ry == 0:
            if rx == 1:
                x, y = s - 1 - x, s - 1 - y
            x, y = y, x
        x += s * rx
        y += s * ry
        t //= 4
        s *= 2
    return x, y


def gen_hilbert_flow():
    """Left: the same colour multiset assigned in seeded-random order
    (confetti = today's independent picks). Right: colours assigned along the
    Hilbert curve - neighbours on the curve are neighbours in 2D, so the flow
    is silky at every scale. Bottom: the order-3 curve itself."""
    rng = np.random.default_rng(401)
    order = 5
    ng = 1 << order
    P = 352
    cell = P // ng
    cols_flow = [hsv_rgb(0.02 + 0.96 * i / (ng * ng), 0.55, 0.78) for i in range(ng * ng)]

    def grid_panel(assign):
        img = Image.new("RGB", (P, P), BG)
        d = ImageDraw.Draw(img)
        for i in range(ng * ng):
            x, y = assign(i)
            d.rectangle([x * cell, y * cell, (x + 1) * cell - 1, (y + 1) * cell - 1],
                        fill=vary(rng, cols_flow[i], 10), outline=OUTLINE)
        return img

    perm = rng.permutation(ng * ng)
    left = grid_panel(lambda i: (int(perm[i]) % ng, int(perm[i]) // ng))
    right = grid_panel(lambda i: _hilbert_xy(i, order))

    canvas = Image.new("RGB", (SIZE, SIZE), BG)
    d = ImageDraw.Draw(canvas)
    canvas.paste(left, (4, 40))
    canvas.paste(right, (SIZE - P - 4, 40))
    _label(d, (4 + 92, 12), "kolejnosc losowa", 17)
    _label(d, (SIZE - P - 4 + 74, 12), "kolejnosc Hilberta", 17)

    o3 = 3
    n3 = 1 << o3
    sc = 22
    x0 = (SIZE - (n3 - 1) * sc) // 2
    y0 = 40 + P + 62
    pts = [_hilbert_xy(i, o3) for i in range(n3 * n3)]
    d.line([(x0 + x * sc, y0 + y * sc) for x, y in pts], fill=(190, 190, 200), width=5)
    _label(d, (x0 + 6, y0 + (n3 - 1) * sc + 16), "krzywa Hilberta (rzad 3) = trasa doboru kafelkow", 15)
    return canvas


# ==========================================
# MONTAGE
# ==========================================
PANELS = [
    ("quadtree_detail", gen_quadtree_detail, "A. QUADTREE DETAIL",
     "gestosc kafli = mapa detalu zdjecia; motyw odporny na substytucje"),
    ("zoom_movie", gen_zoom_movie, "B. ZOOM MOVIE (storyboard)",
     "GIF: nurkowanie w kafelek, ktory okazuje sie kolejna mozaika"),
    ("fractal_crossfade", gen_fractal_crossfade, "C. FRACTAL CROSSFADE",
     "dwie mozaiki zszyte frontem fBm (klatka t=0.5, print hybrydowy)"),
    ("hilbert_flow", gen_hilbert_flow, "D. HILBERT FLOW (always-on)",
     "dobor wzdluz krzywej Hilberta: plynnosc zamiast losowego szumu"),
]


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    panels = {}
    for name, fn, t1, t2 in PANELS:
        print(f"[gen] {name} ...")
        img = fn()
        img.save(OUT_DIR / f"{name}.png")
        panels[name] = img
        print(f"      -> {OUT_DIR / (name + '.png')}")

    PW, TH = 475, 60
    mont = Image.new("RGB", (PW * 2, (PW + TH) * 2), (10, 10, 12))
    draw = ImageDraw.Draw(mont)
    f_bold = _font(17)
    f_reg = _font(14)
    for idx, (name, fn, t1, t2) in enumerate(PANELS):
        r, c = divmod(idx, 2)
        x0, y0 = c * PW, r * (PW + TH)
        img = panels[name].resize((PW - 24, PW - 24), Image.Resampling.LANCZOS)
        for txt, font, dy in [(t1, f_bold, 10), (t2, f_reg, 34)]:
            tw = draw.textlength(txt, font=font)
            draw.text((x0 + (PW - tw) / 2, y0 + dy), txt, fill=(235, 235, 235), font=font)
        mont.paste(img, (x0 + 12, y0 + TH))
    out = OUT_DIR / "proposals_fractal_features.png"
    mont.save(out)
    print(f"[gen] montage -> {out}")


if __name__ == "__main__":
    main()
