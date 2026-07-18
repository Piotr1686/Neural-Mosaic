"""Proposal swatches: 10 decorative grout STROKE STYLES (2026-07-18).

PROPOZYCJE, nie wdrozenia. Nie mylic z gen_grout_proposals.py (2026-07-05):
tamto proponowalo POZIOMY hierarchii L1/L2/L3 (wdrozone); to proponuje STYL
samej kreski. Kazdy styl to synteza kreski wzdluz istniejacych,
sklasyfikowanych krawedzi komorek - wpina sie w etap kapsul draw_grout
(src/grout.py); poziomy hierarchiczne i presety grubosci zostaja bez zmian.
Style kolorowe (beads/bevel/neon/kintsugi) wymagaja rozszerzenia presetu o
kolor - dzis grout jest jednobarwny.

UCZCIWY RENDER (lekcja pikselozy groutu e8e0b74): swatche rysowane w
supersamplingu ss=4 i skladane downscalem BOX - dokladnie tak, jak robi to
silnik w draw_grout. Zadnego "ladniej niz bedzie w silniku".

Jitter (kintsugi/brush/stitch) z crc32 indeksu segmentu, BEZ RNG -
reprodukowalny bit-w-bit jak reszta silnika.

Outputs: assets/proposals/grout_<styl>.png + montage_grout_styles.png

Run:
  C:/Users/plazo/miniconda3/envs/mosaic/python.exe -m src.tools.gen_grout_style_proposals
"""
import logging
import math
import zlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

log = logging.getLogger(__name__)

S = 300          # swatch size (3x3 tiles of 100 px)
SS = 4           # engine-grade supersampling
BG = (20, 20, 24)

_TILES = [
    (96, 116, 88), (140, 120, 96), (88, 100, 128),
    (150, 140, 120), (110, 90, 100), (122, 132, 104),
    (100, 88, 76), (84, 112, 116), (134, 106, 90),
]


def _crc(*key):
    return zlib.crc32(repr(key).encode("ascii"))


def _frange(a, b, step):
    t = a
    while t <= b:
        yield t
        t += step


def _base(dark=False):
    img = Image.new("RGB", (S * SS, S * SS), BG)
    dr = ImageDraw.Draw(img)
    f = 0.45 if dark else 1.0
    for j in range(3):
        for i in range(3):
            col = tuple(int(v * f) for v in _TILES[j * 3 + i])
            dr.rectangle([i * 100 * SS, j * 100 * SS,
                          (i + 1) * 100 * SS - 1, (j + 1) * 100 * SS - 1],
                         fill=col)
    return img.convert("RGBA")


def _segs():
    out = []
    for k in (100, 200):
        out.append(((k, 0), (k, S)))
        out.append(((0, k), (S, k)))
    e = 1.5
    out += [((e, e), (S - e, e)), ((S - e, e), (S - e, S - e)),
            ((S - e, S - e), (e, S - e)), ((e, S - e), (e, e))]
    return out


def _unit(seg):
    (x0, y0), (x1, y1) = seg
    L = math.hypot(x1 - x0, y1 - y0)
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    return L, (ux, uy), (-uy, ux)


def _pt(seg, t, off):
    (x0, y0), _ = seg
    L, (ux, uy), (nx, ny) = _unit(seg)
    return ((x0 + t * ux + off * nx) * SS, (y0 + t * uy + off * ny) * SS)


def _over():
    return Image.new("RGBA", (S * SS, S * SS), (0, 0, 0, 0))


# --------------------------------------------------------------------------
# styles
# --------------------------------------------------------------------------
def style_zigzag(base):
    ov = _over()
    dr = ImageDraw.Draw(ov)
    for seg in _segs():
        L, _, _ = _unit(seg)
        pts, side = [], 1
        for t in _frange(0.0, L, 6.0):
            pts.append(_pt(seg, t, 4.0 * side))
            side = -side
        dr.line(pts, fill=(28, 24, 22, 255), width=2 * SS, joint="curve")
    base.alpha_composite(ov)
    return base


def style_squiggle(base):
    ov = _over()
    dr = ImageDraw.Draw(ov)
    for seg in _segs():
        L, _, _ = _unit(seg)
        pts = [_pt(seg, t, 3.5 * math.sin(2 * math.pi * t / 18.0))
               for t in _frange(0.0, L, 2.0)]
        dr.line(pts, fill=(28, 24, 22, 255), width=2 * SS, joint="curve")
    base.alpha_composite(ov)
    return base


def style_double(base):
    ov = _over()
    dr = ImageDraw.Draw(ov)
    for seg in _segs():
        L, _, _ = _unit(seg)
        for off in (-3.0, 3.0):
            dr.line([_pt(seg, 0, off), _pt(seg, L, off)],
                    fill=(28, 24, 22, 255), width=int(1.6 * SS))
    base.alpha_composite(ov)
    return base


def style_stitch(base):
    ov = _over()
    dr = ImageDraw.Draw(ov)
    for seg in _segs():
        L, _, _ = _unit(seg)
        k = 0
        for t in _frange(8.0, L - 6.0, 12.0):
            tilt = 1.4 if k % 2 == 0 else -1.4
            dr.line([_pt(seg, t, -tilt), _pt(seg, t + 6.0, tilt)],
                    fill=(45, 38, 60, 255), width=2 * SS)
            k += 1
    base.alpha_composite(ov)
    return base


def style_beads(base):
    ov = _over()
    dr = ImageDraw.Draw(ov)
    for seg in _segs():
        L, _, _ = _unit(seg)
        for t in _frange(4.0, L, 7.5):
            x, y = _pt(seg, t, 0)
            r = 2.6 * SS
            dr.ellipse([x - r, y - r, x + r, y + r],
                       fill=(235, 225, 205, 255),
                       outline=(60, 50, 40, 255), width=SS)
    base.alpha_composite(ov)
    return base


def style_rope(base):
    ov = _over()
    dr = ImageDraw.Draw(ov)
    for seg in _segs():
        L, (ux, uy), _ = _unit(seg)
        horizontal = abs(ux) >= abs(uy)
        k = 0
        for t in _frange(0.0, L - 9.0, 9.0):
            x0, y0 = _pt(seg, t, -4.5)
            x1, y1 = _pt(seg, t + 9.0, 4.5)
            bbox = [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)]
            if horizontal:
                start, end = (180, 360) if k % 2 == 0 else (0, 180)
            else:
                start, end = (90, 270) if k % 2 == 0 else (270, 90)
            dr.arc(bbox, start, end, fill=(30, 26, 24, 255), width=2 * SS)
            k += 1
    base.alpha_composite(ov)
    return base


def style_bevel(base):
    for off, col in ((-1.6, (255, 255, 255, 115)), (1.6, (0, 0, 0, 150))):
        ov = _over()
        dr = ImageDraw.Draw(ov)
        for seg in _segs():
            L, _, (nx, ny) = _unit(seg)
            side = 1.0 if (nx + ny) < 0 else -1.0   # light towards top-left
            dr.line([_pt(seg, 0, off * side), _pt(seg, L, off * side)],
                    fill=col, width=2 * SS)
        base.alpha_composite(ov)
    return base


def style_neon(base):
    ov = _over()
    dr = ImageDraw.Draw(ov)
    layers = [(9, (0, 190, 235, 46)), (5, (40, 220, 250, 95)),
              (3, (130, 245, 255, 160)), (1, (245, 255, 255, 255))]
    for w, col in layers:
        for seg in _segs():
            L, _, _ = _unit(seg)
            dr.line([_pt(seg, 0, 0), _pt(seg, L, 0)], fill=col, width=w * SS)
    base.alpha_composite(ov)
    return base


def style_kintsugi(base):
    ov = _over()
    dr = ImageDraw.Draw(ov)
    for si, seg in enumerate(_segs()):
        L, _, _ = _unit(seg)
        pts = [_pt(seg, 0, 0)]
        for i, t in enumerate(_frange(9.0, L - 4.0, 9.0)):
            off = ((_crc(si, i) & 255) / 255.0 - 0.5) * 5.6
            pts.append(_pt(seg, t, off))
        pts.append(_pt(seg, L, 0))
        dr.line(pts, fill=(198, 161, 54, 255), width=3 * SS, joint="curve")
        dr.line(pts, fill=(255, 229, 148, 220), width=1 * SS, joint="curve")
    base.alpha_composite(ov)
    return base


def style_brush(base):
    ov = _over()
    dr = ImageDraw.Draw(ov)
    for si, seg in enumerate(_segs()):
        L, _, _ = _unit(seg)
        ph = ((_crc(si) & 255) / 255.0) * 2 * math.pi
        for t in _frange(0.0, L, 2.0):
            r = (0.9 + 1.5 * (0.5 + 0.5 * math.sin(t / 21.0 + ph))) * SS
            x, y = _pt(seg, t, 0)
            dr.ellipse([x - r, y - r, x + r, y + r], fill=(24, 20, 18, 255))
    base.alpha_composite(ov)
    return base


STYLES = [
    ("grout_zigzag", style_zigzag, False),
    ("grout_squiggle", style_squiggle, False),
    ("grout_double", style_double, False),
    ("grout_stitch", style_stitch, False),
    ("grout_beads", style_beads, False),
    ("grout_rope", style_rope, False),
    ("grout_bevel", style_bevel, False),
    ("grout_neon", style_neon, True),
    ("grout_kintsugi", style_kintsugi, False),
    ("grout_brush", style_brush, False),
]


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    out_dir = Path(__file__).resolve().parents[2] / "assets" / "proposals"
    out_dir.mkdir(parents=True, exist_ok=True)
    panels = []
    for name, fn, dark in STYLES:
        img = fn(_base(dark)).convert("RGB").resize((S, S), Image.BOX)
        img.save(out_dir / f"{name}.png")
        panels.append((name, img))
        log.info("Saved: %s", out_dir / f"{name}.png")

    pad, label_h, cols, cell = 12, 26, 2, 300
    rows = (len(panels) + cols - 1) // cols
    W = cols * cell + (cols + 1) * pad
    H = rows * (cell + label_h) + (rows + 1) * pad
    m = Image.new("RGB", (W, H), BG)
    dr = ImageDraw.Draw(m)
    font = ImageFont.load_default()
    for i, (name, img) in enumerate(panels):
        c, r = i % cols, i // cols
        x = pad + c * (cell + pad)
        y = pad + r * (cell + label_h + pad)
        m.paste(img, (x, y))
        dr.text((x + 6, y + cell + 7), name, fill=(225, 225, 225), font=font)
    m.save(out_dir / "montage_grout_styles.png")
    log.info("Saved: %s", out_dir / "montage_grout_styles.png")


if __name__ == "__main__":
    main()
