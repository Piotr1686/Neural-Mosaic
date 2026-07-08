"""
src/engine_smart.py
-------------------
Colour-matched photomosaic engine (SmartEngine).

Supports multiple tile geometries including the per-tile deltoidal kite
grid ("kites") and the chiral aperiodic "spectre" monotile (src/spectre_tiling.py).
Each sector of the target image is matched to the best-fitting tile from
the pre-built CIELAB feature index with spatial anti-repetition enforcement.

Index schema "5x5_edge" (79-dim) enables edge-aware matching: 4 extra
features (mean L of each border strip) are appended to the standard 75-dim
LAB vector and scaled by EDGE_WEIGHT so boundary lightness contributes ~15%
of the total Euclidean distance. With edge_aware=False the engine silently
slices the first 75 dimensions, so old and new indexes are both accepted.
"""
import numpy as np
import pickle
import math
import threading
from dataclasses import dataclass
from PIL import Image, ImageOps, ImageDraw
from tqdm import tqdm
from scipy.spatial import cKDTree
import skimage.color

from .spectre_tiling import generate_spectre_tiling
from .render_control import RenderCancelled
from .grout import classify_edges, draw_grout, scale_widths, sub7

# Shapes whose sub7/block grouping was reviewed and approved (2026-07-05): the
# grout pass draws hierarchical L1/L2/L3 lines for these. Other shapes fall
# back to flat single-level grout (follow-up) or skip the pass.
GROUT_HIERARCHICAL = ("square", "hexagon", "triangle", "kites")

# Must match EDGE_WEIGHT in indexer_smart.py.
EDGE_WEIGHT = 2.0


def _euclid_f32(chunk, feats, feat_sq):
    """Euclidean distances (float32) via the GEMM identity
    ||a||^2 + ||b||^2 - 2 a.b, computed in place to keep a single matrix resident.

    Drop-in for ``scipy.cdist(chunk, feats, 'euclidean')`` but without the float64
    promotion: ``chunk`` and ``feats`` must be float32, ``feat_sq`` the precomputed
    row-wise squared norm of ``feats``. For a 16K render vs ~455k tiles the per-chunk
    matrix drops from ~1.8 GB (cdist float64) to ~0.25 GB. Rankings are identical
    (sqrt is monotonic); the returned values are true euclidean distances, so the
    freq_penalty score downstream stays numerically equivalent (within float32).
    """
    d = chunk @ feats.T                                   # (rows, n_lib) float32
    d *= -2.0
    d += feat_sq[np.newaxis, :]
    d += np.einsum("ij,ij->i", chunk, chunk)[:, np.newaxis]
    np.maximum(d, 0.0, out=d)                             # guard tiny negatives
    np.sqrt(d, out=d)
    return d


class _LazyMask:
    """Deferred polygon mask for kite/spectre sectors.

    Each non-grid sector used to keep a fully rasterised "L" mask resident in
    sectors_data from build time until the composite pass — at 16K that is the
    dominant *resident* RAM cost (grid masks are shared references, so cheap).
    Storing the polygon instead and re-rasterising on demand cuts that to a
    handful of float pairs per sector.

    ``render()`` reproduces the original rasterisation byte-for-byte: kites draw
    at native resolution (``aa == 1``); spectres supersample by ``aa`` then
    downsample with LANCZOS (anti-aliased edge), exactly as the build pass did.
    The same render() output feeds both the feature computation and the final
    putalpha, so matching and pixels are unchanged.
    """

    __slots__ = ("poly", "bw", "bh", "aa")

    def __init__(self, poly, bw, bh, aa=1):
        self.poly = poly      # polygon in mask-local (unscaled) coordinates
        self.bw = bw
        self.bh = bh
        self.aa = aa

    def render(self):
        if self.aa == 1:
            m = Image.new("L", (self.bw, self.bh), 0)
            ImageDraw.Draw(m).polygon(self.poly, fill=255)
            return m
        m = Image.new("L", (self.bw * self.aa, self.bh * self.aa), 0)
        scaled = [(x * self.aa, y * self.aa) for (x, y) in self.poly]
        ImageDraw.Draw(m).polygon(scaled, fill=255)
        return m.resize((self.bw, self.bh), Image.Resampling.LANCZOS)


# ==========================================================================
# SHAPE REGISTRY  (single source of truth for the shape list + geometry)
# ==========================================================================
def _gen_kites(engine, target_w, target_h, base_s):
    """Yield per-kite polygons of the deltoidal trihexagonal grid, in image
    space (y down).

    Each hexagon on the flat-topped grid splits into 6 kites; every kite is its
    own sector. The (q, r, k) iteration order is a pure function of geometry, so
    preview and render stay reproducible (no RNG). The Cartesian kites are built
    y-up, filtered by their (unflipped) centroid, then each vertex is flipped to
    image space here — the y-flip stays inside the generator so `_polygon_sector`
    is orientation-agnostic (see PLAN_SHAPES.md Sprint 2, contract point 2).
    """
    s = base_s
    r3 = math.sqrt(3)
    range_q = int(target_w / (1.5 * s)) + 3
    range_r = int(target_h / (r3 * s)) + 3

    for q in range(-range_q, range_q):
        # centre the r-window on -q/2: cy = r3*s*(r + q/2), so a fixed window
        # scans a cy band displaced by q/2 at large |q| and leaves the far
        # corner without hexagons (black wedge bottom-right, fixed 2026-07-04)
        r_mid = -(q // 2)
        for r in range(r_mid - range_r, r_mid + range_r):
            cx = 1.5 * s * q
            cy = r3 * s * (r + q / 2.0)
            if -2 * s < cx < target_w + 2 * s and -2 * s < cy < target_h + 2 * s:
                for k in range(6):
                    poly = engine._get_kite_poly(cx, cy, s, k)
                    cent_x = sum(p[0] for p in poly) / 4
                    cent_y = sum(p[1] for p in poly) / 4
                    if 0 <= cent_x < target_w and 0 <= cent_y < target_h:
                        yield [(px, target_h - py) for px, py in poly]


def _gen_spectre(engine, target_w, target_h, base_s):
    """Yield the chiral aperiodic spectre monotiles as image-space polygons.

    `generate_spectre_tiling` already emits points in image space (y down), so
    the generator is a thin adaptor over it.
    """
    for spec in generate_spectre_tiling(target_w, target_h, base_s):
        yield list(spec.points)


@dataclass(frozen=True)
class ShapeSpec:
    """Descriptor for one tile shape.

    kind      : "grid"    -> axis-aligned crop + shared mask (grid branch).
                "polygon" -> per-tile polygon via `_polygon_sector`.
    generator : callable(engine, target_w, target_h, base_s) -> iterable[poly],
                each poly a list of (x, y) vertices in image space (y down).
                None for grid shapes.
    aa        : anti-aliasing supersample for the polygon mask (1 = native).
    seeded    : reserved for future variable-cell shapes that need a
                deterministic RNG seed (voronoi/phyllotaxis/poincare, S5).
    """
    kind: str
    generator: object = None
    aa: int = 1
    seeded: bool = False


# Ordered registry — GUI dropdown, CLI --shape choices, make_showcase and the
# benchmark all read the names from `shape_names()` so adding a shape is a
# one-line edit here (the earlier kite->kites rename touched five files).
SHAPE_MODES = {
    "square":        ShapeSpec("grid"),
    "rectangle_3x1": ShapeSpec("grid"),
    "brick_wall":    ShapeSpec("grid"),
    "hexagon":       ShapeSpec("grid"),
    "hexagon_romb":  ShapeSpec("grid"),
    "romb":          ShapeSpec("grid"),
    "triangle":      ShapeSpec("grid"),
    "kites":         ShapeSpec("polygon", _gen_kites, aa=1),
    "spectre":       ShapeSpec("polygon", _gen_spectre, aa=4),
}


def shape_names():
    """Ordered list of registered shape-mode names (single source of truth)."""
    return list(SHAPE_MODES.keys())


class SmartEngine:
    def __init__(self, index_path="data/smart_index.pkl"):
        print(f"Loading Smart Index: {index_path}...")
        try:
            with open(index_path, "rb") as f:
                data = pickle.load(f)

            self.paths = data["paths"]
            self.features = data["features"]

            actual_dim = self.features.shape[1] if self.features.ndim == 2 else 0
            if actual_dim not in (75, 79):
                print(f"ERROR: Index has {actual_dim}-dim features, expected 75 or 79. "
                      f"Rendering DISABLED. Rebuild index: GUI → 'Update / Create Index'")
                self.paths = []
                self.features = []
                return

            schema = data.get("schema_version", "unknown")
            if schema not in ("5x5", "5x5_edge"):
                print(f"WARNING: Index schema '{schema}', expected '5x5' or '5x5_edge'.")

            self.settings = {
                "allow_mirror": True,
                "edge_aware": False,
                "freq_penalty": 30.0,
            }
            self._neighbors_cache: dict = {}
            self._neighbors_lock = threading.Lock()
            print(f"Smart Engine Ready. Images: {len(self.paths)}  "
                  f"schema: {schema}  dim: {actual_dim}")
        except FileNotFoundError:
            print("Error: Smart Index not found. Run 'Update / Create Index' in GUI.")
            self.paths = []
            self.features = []

    def _get_neighbors_map(self, _nkey, points, search_radius):
        """Return the cached neighbour adjacency for this render geometry.

        Concurrent preview renders may run two _do_render calls in parallel
        (the generation token only gates result delivery, not execution), so
        the cache-miss path is serialised with double-checked locking to avoid
        racing mutation of self._neighbors_cache. The fast path is a lock-free
        dict read; the tree is built at most once per key under the lock.
        """
        neighbors_map = self._neighbors_cache.get(_nkey)
        if neighbors_map is not None:
            return neighbors_map
        with self._neighbors_lock:
            # Re-check under lock: another thread may have populated it while
            # we waited, so we don't recompute the tree needlessly.
            neighbors_map = self._neighbors_cache.get(_nkey)
            if neighbors_map is None:
                tree = cKDTree(points)
                neighbors_map = tree.query_ball_tree(tree, r=search_radius)
                if len(self._neighbors_cache) > 8:
                    self._neighbors_cache.pop(next(iter(self._neighbors_cache)))
                self._neighbors_cache[_nkey] = neighbors_map
        return neighbors_map

    # ==========================================
    # FEATURE EXTRACTION HELPER
    # ==========================================
    def _compute_sector_feature(self, s_img, edge_aware):
        """Return a 75-dim or 79-dim LAB feature vector for a tile-sized crop."""
        mat = s_img.resize((5, 5), Image.Resampling.BOX)
        arr = np.array(mat) / 255.0
        lab_5x5 = skimage.color.rgb2lab(arr)  # (5, 5, 3)
        lab = lab_5x5.flatten()
        lab[0::3] /= 100.0
        lab[1::3] = (lab[1::3] + 128) / 255.0
        lab[2::3] = (lab[2::3] + 128) / 255.0
        vec = lab.astype(np.float32)
        if edge_aware:
            edge_feats = np.array([
                lab_5x5[0, :, 0].mean() / 100.0,   # top row
                lab_5x5[:, 4, 0].mean() / 100.0,   # right column
                lab_5x5[4, :, 0].mean() / 100.0,   # bottom row
                lab_5x5[:, 0, 0].mean() / 100.0,   # left column
            ], dtype=np.float32) * EDGE_WEIGHT
            vec = np.concatenate([vec, edge_feats])
        return vec

    # ==========================================
    # KITE GRID MATHEMATICS
    # ==========================================
    def _get_kite_poly(self, cx, cy, s, k):
        """Return the 4 vertices of a single kite on a flat-topped hexagonal grid.

        Args:
            cx, cy: Cartesian centre of the parent hexagon.
            s:      Hexagon side length in pixels.
            k:      Kite index within the hexagon (0–5).

        Returns:
            List of four (x, y) tuples: [hex_centre, edge_mid(k-1), vertex(k), edge_mid(k)].
        """
        r3 = math.sqrt(3)
        def P(idx):
            angle = math.radians(idx * 60)
            return (cx + s * math.cos(angle), cy + s * math.sin(angle))

        def M(idx):
            angle = math.radians(idx * 60 + 30)
            return (cx + s * r3/2 * math.cos(angle), cy + s * r3/2 * math.sin(angle))

        return [(cx, cy), M((k-1) % 6), P(k), M(k)]

    def _transform_kite_index(self, base_q, base_r, base_k, offset_q, offset_r, rot, flip):
        """Apply a topological transformation to kite axial coordinates (q, r, k).

        Args:
            base_q, base_r, base_k: Source kite coordinates.
            offset_q, offset_r:     Translation in axial hex space.
            rot:                    Number of 60-degree counter-clockwise rotations.
            flip:                   Whether to mirror along the horizontal axis first.

        Returns:
            Transformed (q, r, k) tuple.
        """
        q, r, k = base_q, base_r, base_k

        if flip:
            q, r = q, -q - r
            k = (6 - k) % 6

        for _ in range(rot):
            q, r = -r, q + r
            k = (k + 1) % 6

        return (q + offset_q, r + offset_r, k)

    # ==========================================
    # STANDARD SHAPES AND MASKS
    # ==========================================
    def _get_shape_mask(self, shape_type, w, h, flipped=False, padding=1.0):
        scale_aa = 4
        W, H = int(w * scale_aa), int(h * scale_aa)
        mask = Image.new("L", (W, H), 0)
        draw = ImageDraw.Draw(mask)
        cx, cy = W/2, H/2

        pad_w = W * (1 - padding) / 2
        pad_h = H * (1 - padding) / 2

        if shape_type == "square" or shape_type == "rectangle_3x1" or shape_type == "brick_wall":
            draw.rectangle((pad_w, pad_h, W-pad_w, H-pad_h), fill=255)
        elif "hexagon" in shape_type and "romb" not in shape_type:
            pts = [(cx, pad_h), (W-pad_w, H*0.25+pad_h/2), (W-pad_w, H*0.75-pad_h/2),
                   (cx, H-pad_h), (pad_w, H*0.75-pad_h/2), (pad_w, H*0.25+pad_h/2)]
            draw.polygon(pts, fill=255)
        elif "romb" in shape_type and "hexagon" not in shape_type:
            pts = [(cx, pad_h), (W-pad_w, cy), (cx, H-pad_h), (pad_w, cy)]
            draw.polygon(pts, fill=255)
        elif shape_type == "mask_top":
            pts = [(cx, cy), (W - pad_w, H*0.25 + pad_h/2), (cx, 0 + pad_h), (0 + pad_w, H*0.25 + pad_h/2)]
            draw.polygon(pts, fill=255)
        elif shape_type == "mask_left":
            pts = [(cx, cy), (0 + pad_w, H*0.25 + pad_h/2), (0 + pad_w, H*0.75 - pad_h/2), (cx, H - pad_h)]
            draw.polygon(pts, fill=255)
        elif shape_type == "mask_right":
            pts = [(cx, cy), (cx, H - pad_h), (W - pad_w, H*0.75 - pad_h/2), (W - pad_w, H*0.25 + pad_h/2)]
            draw.polygon(pts, fill=255)
        elif shape_type == "triangle":
            if not flipped: pts = [(cx, pad_h), (W-pad_w, H-pad_h), (pad_w, H-pad_h)]
            else: pts = [(pad_w, pad_h), (W-pad_w, pad_h), (cx, H-pad_h)]
            draw.polygon(pts, fill=255)

        return mask.resize((w, h), Image.Resampling.LANCZOS)

    def _smart_crop(self, img, target_w, target_h):
        src_w, src_h = img.size
        src_ratio = src_w / src_h; tgt_ratio = target_w / target_h
        if src_ratio > tgt_ratio:
            new_w = int(src_h * tgt_ratio); offset = (src_w - new_w) // 2
            box = (offset, 0, offset + new_w, src_h)
        else:
            new_h = int(src_w / tgt_ratio); offset = (src_h - new_h) // 2
            box = (0, offset, src_w, offset + new_h)
        return img.crop(box).resize((target_w, target_h), Image.Resampling.LANCZOS)

    def create_mosaic(self, target_path, output_path, resolution_key, shape_mode, tile_scale, border_mode=False, blend_strength=0.0, tint_strength=0.0, grout_preset=None, progress_cb=None, cancel_event=None):
        """Public API — resolves resolution_key and delegates to _do_render.

        ``grout_preset`` (None | "cienki"/"sredni"/"gruby") is an independent
        opt-in border pass: when set, hierarchical grout lines are drawn on the
        finished mosaic (see _do_render). Orthogonal to ``border_mode`` (the
        tile-shrink gap), which is left untouched.
        """
        if not self.paths:
            print("ERROR: Index not loaded.")
            return
        res_map = {"2K": 1920, "4K": 3840, "8K": 7680, "16K": 15360}
        target_long = res_map.get(resolution_key, 3840)
        target = Image.open(target_path).convert("RGB")
        img_w, img_h = target.size
        scale_res = target_long / max(img_w, img_h)
        target = target.resize((int(img_w * scale_res), int(img_h * scale_res)), Image.Resampling.LANCZOS)
        result = self._do_render(target, shape_mode, tile_scale, border_mode, blend_strength, tint_strength, grout_preset=grout_preset, progress_cb=progress_cb, cancel_event=cancel_event)
        result.save(output_path, quality=95)

    def render_preview(self, target_path, short_edge=512, shape_mode="hexagon_romb",
                       tile_scale=1.0, border_mode=False, grout_preset=None):
        """Return a PIL Image preview at ~short_edge px short side — no file I/O."""
        if not self.paths:
            raise RuntimeError("Index not loaded.")
        target = Image.open(target_path).convert("RGB")
        img_w, img_h = target.size
        scale = short_edge / min(img_w, img_h)
        prev_w = max(1, int(img_w * scale))
        prev_h = max(1, int(img_h * scale))
        target = target.resize((prev_w, prev_h), Image.Resampling.LANCZOS)
        return self._do_render(target, shape_mode, tile_scale, border_mode, 0.0, 0.0, grout_preset=grout_preset)

    def _resolve_matching_modes(self):
        """Resolve edge_aware/allow_mirror, degrading on conflicts (warns on stdout).

        Returns (edge_aware, allow_mirror). Two mutually-exclusive degradations:
          * edge_aware requested but index is 75-dim -> edge_aware off
          * edge_aware AND allow_mirror both on -> allow_mirror off (edge_aware wins)

        The second guard backs up the GUI mutex: allow_mirror reshapes tile
        features as 75-dim (5x5x3), which is incompatible with the 79-dim
        edge-aware features. Without this, _do_render would raise a cryptic
        ValueError on reshape when both modes reach the engine (e.g. via CLI).
        """
        edge_aware = self.settings.get("edge_aware", False)
        allow_mirror = self.settings.get("allow_mirror", False)
        has_edge_features = (self.features.ndim == 2 and self.features.shape[1] == 79)

        if edge_aware and not has_edge_features:
            print("WARNING: Edge-Aware requested but index is 75-dim. "
                  "Rebuild index (Update / Create Index). Falling back to standard matching.")
            edge_aware = False

        if edge_aware and allow_mirror:
            print("WARNING: allow_mirror is incompatible with edge_aware (79-dim "
                  "features). Disabling mirror for this render.")
            allow_mirror = False

        return edge_aware, allow_mirror

    @staticmethod
    def _mean_fill_outside_mask(s_img, mask):
        """Replace pixels outside *mask* with the in-mask mean colour.

        A non-convex tile (kite, spectre) carries a lot of neighbouring content
        in its bounding box; filling the outside with the tile's own mean keeps
        that content from polluting the LAB feature match. Returns *s_img*
        unchanged if the mask is empty.
        """
        arr = np.asarray(s_img, dtype=np.float32)
        m = np.asarray(mask, dtype=np.float32)[:, :, None] / 255.0
        m_sum = float(m.sum())
        if m_sum <= 0.0:
            return s_img
        mean_rgb = (arr * m).sum(axis=(0, 1)) / m_sum
        filled = arr * m + mean_rgb * (1.0 - m)
        return Image.fromarray(np.clip(filled, 0, 255).astype(np.uint8))

    def _polygon_sector(self, target, poly, render_padding, aa, edge_aware):
        """Build one non-grid (polygon) sector from a single image-space polygon.

        Shared core of every polygon shape (kites, spectre, and the Sprint 3+
        tilings). `poly` is a list of (x, y) vertices already in image space
        (y down) — any y-flip belongs in the shape generator, not here.

        Steps: shrink toward the polygon centroid by `render_padding`; take the
        bounding box; crop the target to it; `_LazyMask` at supersample `aa`;
        `_mean_fill_outside_mask` so the bbox's neighbouring content does not
        pollute the LAB match; compute the feature.

        Bounding-box strategy is the KITE one (PLAN_SHAPES.md Sprint 2, point 1):
        the paste origin may be negative at the top/left edge, handled by an
        offset repaste (`sb[0] - safe_box[0]`) rather than clamping min to 0.
        This correctly places edge tiles whose polygon spills off-canvas — the
        off-canvas strip stays black and is clipped by the negative-dest
        alpha_composite at assembly time.

        Returns a sector dict {"meta": (0, min_x, min_y, lazy_mask, bw, bh,
        False), "feature": ...} (the caller overwrites the placeholder index 0),
        or None if the sector is degenerate or entirely off-canvas.
        """
        target_w, target_h = target.size
        n = len(poly)
        cx = sum(p[0] for p in poly) / n
        cy = sum(p[1] for p in poly) / n
        padded_poly = [
            (cx + (px - cx) * render_padding, cy + (py - cy) * render_padding)
            for px, py in poly
        ]

        min_x = min(p[0] for p in padded_poly)
        max_x = max(p[0] for p in padded_poly)
        min_y = min(p[1] for p in padded_poly)
        max_y = max(p[1] for p in padded_poly)

        bw, bh = int(max_x - min_x), int(max_y - min_y)
        if bw <= 0 or bh <= 0:
            return None

        safe_box = (int(min_x), int(min_y), int(max_x), int(max_y))
        sb = (max(0, safe_box[0]), max(0, safe_box[1]),
              min(target_w, safe_box[2]), min(target_h, safe_box[3]))
        if sb[2] <= sb[0] or sb[3] <= sb[1]:
            return None

        s_img = target.crop(sb)
        if s_img.size != (bw, bh):
            tmp = Image.new("RGB", (bw, bh), (0, 0, 0))
            tmp.paste(s_img, (sb[0] - safe_box[0], sb[1] - safe_box[1]))
            s_img = tmp

        shifted_poly = [(p[0] - min_x, p[1] - min_y) for p in padded_poly]
        lazy_mask = _LazyMask(shifted_poly, bw, bh, aa=aa)
        mask = lazy_mask.render()
        feat_img = self._mean_fill_outside_mask(s_img, mask)

        return {
            "meta": (0, int(min_x), int(min_y), lazy_mask, bw, bh, False),
            "feature": self._compute_sector_feature(feat_img, edge_aware),
        }

    # ==========================================
    # GROUT CELLS  (hierarchical border-pass geometry)
    # ==========================================
    def _grout_cells(self, shape_mode, target_w, target_h, base_s):
        """Build ``(poly, g2, g3)`` cells for the grout pass, in image space
        (y down). Cells reproduce the NOMINAL tile geometry (the same step
        formulas the composite uses) so grout lines land on the tile seams;
        the composite's integer mask-truncation differs by <1 px, well inside
        the grout line width. Returns None for shapes without an approved
        grouping — the caller then skips the hierarchical pass.
        """
        if shape_mode == "square":
            return self._grout_cells_square(target_w, target_h, base_s)
        if shape_mode == "triangle":
            return self._grout_cells_triangle(target_w, target_h, base_s)
        if shape_mode == "hexagon":
            return self._grout_cells_hexagon(target_w, target_h, base_s)
        if shape_mode == "kites":
            return self._grout_cells_kites(target_w, target_h, base_s)
        if shape_mode == "spectre":
            return self._grout_cells_flat_spectre(target_w, target_h, base_s)
        if shape_mode == "romb":
            return self._grout_cells_flat_romb(target_w, target_h, base_s)
        if shape_mode == "rectangle_3x1":
            th = base_s // 3
            return self._grout_cells_flat_rect(
                target_w, target_h, base_s, th, float(base_s), float(th), 0.0)
        if shape_mode == "brick_wall":
            th = base_s // 2
            return self._grout_cells_flat_rect(
                target_w, target_h, base_s, th, float(base_s), float(th),
                float(base_s // 2))
        return None

    def _grout_cells_square(self, target_w, target_h, base_s):
        s = base_s
        cols = int(target_w / s) + 2
        rows = int(target_h / s) + 2
        cells = []
        for r in range(-1, rows):
            for c in range(-1, cols):
                x, y = c * s, r * s
                poly = [(x, y), (x + s, y), (x + s, y + s), (x, y + s)]
                cells.append((poly, (c // 3, r // 3), (c // 9, r // 9)))
        return cells

    def _grout_cells_triangle(self, target_w, target_h, base_s):
        # Matches the composite's triangle grid exactly (tile_w=base_s,
        # tile_h=int(base_s*0.866), step_x=base_s/2). The vertex lattice and the
        # class-0-corner "owner" grouping are the reviewed proposal geometry.
        w = float(base_s)
        h = float(int(base_s * 0.866))
        cols = int(target_w / (w / 2)) + 2
        rows = int(target_h / h) + 2

        def owner(corners):
            for (a, b) in corners:
                if a % 3 == 0:
                    return (a, b)
            raise AssertionError("triangle grout: no class-0 corner")

        def hex_axial(a, b):
            p = a // 3
            j = (b - ((1 + p) % 2)) // 2
            return (p, j - (p - (p & 1)) // 2)

        cells = []
        for r in range(-1, rows):
            for c in range(-1, cols):
                if (c + r) % 2 == 0:
                    corners = [(c, r + 1), (c + 2, r + 1), (c + 1, r)]
                else:
                    corners = [(c, r), (c + 2, r), (c + 1, r + 1)]
                poly = [(a * w / 2, b * h) for (a, b) in corners]
                own = owner(corners)
                cells.append((poly, own, sub7(*hex_axial(*own))))
        return cells

    def _grout_cells_hexagon(self, target_w, target_h, base_s):
        # Hexes on the composite's offset grid (odd rows shifted +base_s/2).
        # Offset->axial q = c - (r - (r&1))//2 (r_axial = r) so the sub7 flowers
        # are spatially contiguous; see test_grout_engine.
        #
        # th is the FLOAT regular-hexagon height base_s*2/sqrt(3); the composite
        # truncates it to int for the mask, but grout needs th*0.75 == step_y
        # exactly or the diagonal edges of adjacent rows miss each other and
        # classify_edges finds no shared edges (all become frame boundaries ->
        # flat grout with black gaps). The <1 px difference from the composite's
        # int mask is hidden under the line width and the 2% tile overlap.
        hr3 = math.sqrt(3) / 2
        tw = base_s
        th = base_s * 2.0 / math.sqrt(3)
        step_x = float(tw)
        step_y = base_s * hr3
        cols = int(target_w / step_x) + 2
        rows = int(target_h / step_y) + 2
        cells = []
        for r in range(-1, rows):
            pos_y = r * step_y
            for c in range(-1, cols):
                pos_x = c * step_x + (base_s / 2 if r % 2 == 1 else 0.0)
                poly = [
                    (pos_x + tw / 2, pos_y),
                    (pos_x + tw,     pos_y + th * 0.25),
                    (pos_x + tw,     pos_y + th * 0.75),
                    (pos_x + tw / 2, pos_y + th),
                    (pos_x,          pos_y + th * 0.75),
                    (pos_x,          pos_y + th * 0.25),
                ]
                q = c - (r - (r & 1)) // 2
                g2 = sub7(q, r)
                cells.append((poly, g2, sub7(*g2)))
        return cells

    def _grout_cells_kites(self, target_w, target_h, base_s):
        # Mirrors _gen_kites (same q,r,k iteration and y-flip) so lines sit on
        # the composited kite edges; L2 = parent hexagon, L3 = its 7-flower.
        s = base_s
        r3 = math.sqrt(3)
        range_q = int(target_w / (1.5 * s)) + 3
        range_r = int(target_h / (r3 * s)) + 3
        cells = []
        for q in range(-range_q, range_q):
            r_mid = -(q // 2)
            for r in range(r_mid - range_r, r_mid + range_r):
                cx = 1.5 * s * q
                cy = r3 * s * (r + q / 2.0)
                if -2 * s < cx < target_w + 2 * s and -2 * s < cy < target_h + 2 * s:
                    g3 = sub7(q, r)
                    for k in range(6):
                        poly = self._get_kite_poly(cx, cy, s, k)
                        cent_x = sum(p[0] for p in poly) / 4
                        cent_y = sum(p[1] for p in poly) / 4
                        if 0 <= cent_x < target_w and 0 <= cent_y < target_h:
                            img_poly = [(px, target_h - py) for px, py in poly]
                            cells.append((img_poly, (q, r), g3))
        return cells

    def _grout_cells_flat_spectre(self, target_w, target_h, base_s):
        # Flat (non-hierarchical) grout: every spectre monotile shares one group
        # id, so classify_edges keeps the interior seams at L1 and closes the
        # frame-boundary edges at L3. generate_spectre_tiling emits nominal
        # image-space points (the same source _gen_spectre composites from), so
        # the grout lines land on the seams. _apply_grout draws all three levels
        # at one uniform width for flat shapes, so the L1/L3 split only decides
        # which segments exist, not their thickness.
        return [(list(spec.points), 0, 0)
                for spec in generate_spectre_tiling(target_w, target_h, base_s)]

    def _grout_cells_flat_romb(self, target_w, target_h, base_s):
        # Mirrors the composite's romb grid (tile_w=base_s, step_x=base_s,
        # step_y=base_s*0.75, odd rows shifted +base_s/2), same -1 start so the
        # edge wedges are covered. tile_h MUST be the FLOAT base_s*1.5: the
        # composite truncates it to int for the mask, but grout needs the exact
        # value so each diamond's side vertices sit exactly step_y (= tile_h/2)
        # below its top -> adjacent rows share edges. With int() the seam splits
        # by <1 px and classify_edges finds no shared edges (all become frame
        # boundaries) -- the same lesson as the hexagon th. Flat: one group id,
        # so interior seams stay L1 and only the frame boundary is L3.
        tile_w = float(base_s)
        tile_h = base_s * 1.5
        step_x = float(base_s)
        step_y = base_s * 0.75
        offset_odd = base_s / 2.0
        cols = int(target_w / step_x) + 2
        rows = int(target_h / step_y) + 2
        cells = []
        for r in range(-1, rows):
            pos_y = r * step_y
            for c in range(-1, cols):
                pos_x = c * step_x + (offset_odd if r % 2 == 1 else 0.0)
                poly = [
                    (pos_x + tile_w / 2, pos_y),
                    (pos_x + tile_w,     pos_y + tile_h / 2),
                    (pos_x + tile_w / 2, pos_y + tile_h),
                    (pos_x,              pos_y + tile_h / 2),
                ]
                cells.append((poly, 0, 0))
        return cells

    def _grout_cells_flat_rect(self, target_w, target_h,
                               tile_w, tile_h, step_x, step_y, offset_odd):
        # Shared flat-grout geometry for the rectangular grids (rectangle_3x1,
        # brick_wall), same -1 start as the composite so the edge wedges are
        # covered. Rectangles abut EXACTLY, so unlike romb/hexagon the steps
        # stay at the integer canvas size (tile_h passed already //-truncated);
        # a float step here would open the 1-px gaps the composite comment
        # warns about. brick_wall's half-brick offset makes the horizontal
        # mortar meet vertical edges at T-junctions -- harmless for flat grout:
        # every level draws one width and the collinear horizontal segments of
        # adjacent rows paint the same line (no gap, no visible doubling).
        cols = int(target_w / step_x) + 2
        rows = int(target_h / step_y) + 2
        cells = []
        for r in range(-1, rows):
            pos_y = r * step_y
            for c in range(-1, cols):
                pos_x = c * step_x + (offset_odd if r % 2 == 1 else 0.0)
                poly = [
                    (pos_x, pos_y),
                    (pos_x + tile_w, pos_y),
                    (pos_x + tile_w, pos_y + tile_h),
                    (pos_x, pos_y + tile_h),
                ]
                cells.append((poly, 0, 0))
        return cells

    # Shapes with an approved multi-level grouping get graded widths (thin L1 ->
    # thick L3); every other supported shape draws flat single-width grout.
    _HIERARCHICAL_GROUT = ("square", "triangle", "hexagon", "kites")

    def _apply_grout(self, mosaic_rgb, shape_mode, target_w, target_h, base_s, preset):
        """Draw the grout overlay on the finished RGB mosaic.

        Hierarchical shapes (``_HIERARCHICAL_GROUT``) get graded widths from the
        preset (thin L1 -> thick L3). Flat shapes reuse the same classified
        segments but draw every level at one uniform width (the preset's L1),
        including the frame-boundary edges (drawn, not suppressed). A no-op (with
        a note) for shapes still lacking any grouping.
        """
        cells = self._grout_cells(shape_mode, target_w, target_h, base_s)
        if cells is None:
            print(f"Grout: '{shape_mode}' has no grouping yet — grout skipped.")
            return
        widths = scale_widths(preset, base_s)
        if shape_mode in self._HIERARCHICAL_GROUT:
            level_w = widths
            kind = "hierarchical"
        else:
            w = widths[1]
            level_w = {1: w, 2: w, 3: w}
            kind = "flat"
        print(f"Grout: drawing {kind} borders '{preset}' over {len(cells)} cells...")
        by_level = classify_edges(cells)
        draw_grout(ImageDraw.Draw(mosaic_rgb), by_level, level_w, color=(0, 0, 0))

    def _do_render(self, target, shape_mode, tile_scale, border_mode=False, blend_strength=0.0, tint_strength=0.0, grout_preset=None, progress_cb=None, cancel_event=None):
        """Core rendering kernel — accepts a pre-scaled PIL Image, returns PIL Image.

        ``progress_cb``, if given, is called ``progress_cb(done, total)`` after each
        matching chunk during the final assembly loop (the dominant cost), where
        ``total`` is the number of sectors. Used by the GUI to drive a progress bar.

        ``cancel_event`` (``threading.Event``), if given, is polled at loop
        boundaries in both the sector-building and matching passes; when set,
        the render aborts by raising RenderCancelled (no partial output).
        """
        def _check_cancel():
            if cancel_event is not None and cancel_event.is_set():
                raise RenderCancelled("Render cancelled by user.")

        edge_aware, allow_mirror = self._resolve_matching_modes()

        target_w, target_h = target.size
        base_s = int(100 * tile_scale)
        if base_s < 10: base_s = 10
        render_padding = 0.94 if border_mode else 1.02

        final_mosaic = Image.new("RGBA", (target_w, target_h), (0,0,0,255))
        sectors_data = []

        # ==========================================
        # KITE TILING (DELTOIDAL TRIHEXAGONAL, PER-TILE)
        # ==========================================
        if shape_mode == "kites":
            # Each hexagon on the flat-topped grid splits into 6 kites; every
            # kite is its own sector (one photo per kite). The earlier "kite"
            # mode bundled 8 kites into randomly-oriented einstein "hats", which
            # read as chaotic blobs and emphasised the black borders. Per-tile
            # is fully deterministic (no RNG): the (q, r, k) iteration order is a
            # pure function of geometry, so preview and render stay reproducible
            # and the _neighbors_cache entry keyed by _nkey is stable.
            print(f"Mode: Kite tiling (deltoidal, per-tile). Borders: {border_mode}")

            s  = base_s
            r3 = math.sqrt(3)

            range_q = int(target_w / (1.5 * s)) + 3
            range_r = int(target_h / (r3 * s)) + 3

            print("Building kite grid...")
            target_kites = []
            for q in range(-range_q, range_q):
                _check_cancel()
                # centre the r-window on -q/2 (same fix as _gen_kites): the shear
                # term q/2 in cy displaced the scanned band at large |q|, leaving
                # the bottom-right corner without kites (fixed 2026-07-04)
                r_mid = -(q // 2)
                for r in range(r_mid - range_r, r_mid + range_r):
                    cx = 1.5 * s * q
                    cy = r3 * s * (r + q / 2.0)

                    if -2*s < cx < target_w + 2*s and -2*s < cy < target_h + 2*s:
                        for k in range(6):
                            poly   = self._get_kite_poly(cx, cy, s, k)
                            cent_x = sum(p[0] for p in poly) / 4
                            cent_y = sum(p[1] for p in poly) / 4

                            if 0 <= cent_x < target_w and 0 <= cent_y < target_h:
                                target_kites.append((cx, cy, k))

            print(f"Rendering {len(target_kites)} kites...")
            for i_kite, (cx, cy, k) in enumerate(tqdm(target_kites, desc="Sampling kite sectors")):
                if i_kite % 256 == 0:
                    _check_cancel()
                poly = self._get_kite_poly(cx, cy, s, k)
                kite_cx = sum(p[0] for p in poly) / 4
                kite_cy = sum(p[1] for p in poly) / 4

                # Shrink toward the kite's own centroid (not a hat centroid): the
                # black border now outlines every individual kite.
                padded_poly = []
                for px, py in poly:
                    nx = kite_cx + (px - kite_cx) * render_padding
                    ny = kite_cy + (py - kite_cy) * render_padding
                    padded_poly.append((nx, target_h - ny))

                min_x = min(p[0] for p in padded_poly)
                max_x = max(p[0] for p in padded_poly)
                min_y = min(p[1] for p in padded_poly)
                max_y = max(p[1] for p in padded_poly)

                bw, bh = int(max_x - min_x), int(max_y - min_y)
                if bw <= 0 or bh <= 0: continue

                safe_box = (int(min_x), int(min_y), int(max_x), int(max_y))
                sb = (max(0, safe_box[0]), max(0, safe_box[1]), min(target_w, safe_box[2]), min(target_h, safe_box[3]))
                if sb[2] <= sb[0] or sb[3] <= sb[1]: continue

                s_img = target.crop(sb)
                if s_img.size != (bw, bh):
                    tmp = Image.new("RGB", (bw, bh), (0,0,0))
                    tmp.paste(s_img, (sb[0] - safe_box[0], sb[1] - safe_box[1]))
                    s_img = tmp

                shifted_poly = [(p[0] - min_x, p[1] - min_y) for p in padded_poly]
                lazy_mask = _LazyMask(shifted_poly, bw, bh, aa=1)
                mask_kite = lazy_mask.render()

                # Replace outside-mask pixels with the kite's mean colour so the
                # bounding box does not leak neighbouring content into the LAB
                # match (same treatment as the spectre mode).
                feat_img = self._mean_fill_outside_mask(s_img, mask_kite)

                # is_hat=False -> standard spatial anti-repetition across all
                # neighbours (no hat grouping to scope it to). Store the lazy
                # descriptor, not the rasterised mask: it is re-rendered
                # identically at composite time (see putalpha).
                sectors_data.append({
                    "meta": (i_kite, int(min_x), int(min_y), lazy_mask, bw, bh, False),
                    "feature": self._compute_sector_feature(feat_img, edge_aware)
                })

        # ==========================================
        # SPECTRE TILING (CHIRAL APERIODIC MONOTILE)
        # ==========================================
        elif shape_mode == "spectre":
            print(f"Mode: Spectre (chiral aperiodic monotile). Borders: {border_mode}")

            spectres = generate_spectre_tiling(target_w, target_h, base_s)
            print(f"Aperiodic tiling ready: {len(spectres)} spectres")

            scale_aa = 4
            for i_spec, spec in enumerate(tqdm(spectres, desc="Sampling spectre sectors")):
                if i_spec % 256 == 0:
                    _check_cancel()
                spec_cx = sum(p[0] for p in spec.points) / len(spec.points)
                spec_cy = sum(p[1] for p in spec.points) / len(spec.points)
                padded_poly = [
                    (spec_cx + (px - spec_cx) * render_padding,
                     spec_cy + (py - spec_cy) * render_padding)
                    for px, py in spec.points
                ]

                # Clamp the bounding box at the top/left edges so the paste
                # origin stays non-negative (alpha_composite requirement).
                min_x = max(0.0, min(p[0] for p in padded_poly))
                min_y = max(0.0, min(p[1] for p in padded_poly))
                max_x = max(p[0] for p in padded_poly)
                max_y = max(p[1] for p in padded_poly)

                bw, bh = int(max_x - min_x), int(max_y - min_y)
                if bw <= 0 or bh <= 0: continue

                safe_box = (int(min_x), int(min_y),
                            min(target_w, int(max_x)), min(target_h, int(max_y)))
                if safe_box[2] <= safe_box[0] or safe_box[3] <= safe_box[1]: continue

                s_img = target.crop(safe_box)
                if s_img.size != (bw, bh):
                    tmp = Image.new("RGB", (bw, bh), (0,0,0))
                    tmp.paste(s_img, (0, 0))
                    s_img = tmp

                # Anti-aliased polygon mask (supersampled, like _get_shape_mask):
                # store the unscaled polygon; _LazyMask.render() supersamples by
                # scale_aa and downsamples with LANCZOS — identical to the build pass.
                shifted_poly = [(p[0] - min_x, p[1] - min_y) for p in padded_poly]
                lazy_mask = _LazyMask(shifted_poly, bw, bh, aa=scale_aa)
                mask_spec = lazy_mask.render()

                # The spectre is non-convex, so its bounding box contains a
                # lot of neighbouring content; replace outside-mask pixels
                # with the tile's mean colour so they do not pollute the
                # LAB match.
                feat_img = self._mean_fill_outside_mask(s_img, mask_spec)

                # Store the lazy descriptor, not the rasterised mask (re-rendered
                # identically at composite time — see putalpha).
                sectors_data.append({
                    "meta": (i_spec, int(min_x), int(min_y), lazy_mask, bw, bh, False),
                    "feature": self._compute_sector_feature(feat_img, edge_aware)
                })

        # ==========================================
        # STANDARD GRID (HexagonRomb, Square, Triangle, …)
        # ==========================================
        else:
            print(f"Mode: Grid ({shape_mode}). Borders: {border_mode}")
            # Mask canvases (tile_w/tile_h) stay integer. Grid steps are kept
            # as floats ONLY for geometries whose mask overlaps past the step
            # (hexagon, romb) — there the old int() truncation compounded row
            # after row into a ~0.7% vertical squeeze. Shapes that abut
            # exactly (rectangle, brick, triangle rows) must keep the step
            # equal to the integer canvas size or 1-px gaps open up.
            hr3 = math.sqrt(3) / 2
            tile_w, tile_h = base_s, base_s
            step_x, step_y = float(base_s), float(base_s)
            offset_odd_row_x = 0.0

            if shape_mode == "rectangle_3x1": tile_h=base_s//3; step_y=float(tile_h)
            elif shape_mode == "brick_wall": tile_h=base_s//2; step_y=float(tile_h); offset_odd_row_x=base_s//2
            elif "hexagon" in shape_mode or shape_mode == "hexagon_romb":
                tile_w=base_s; tile_h=int(base_s*1.155)
                step_x=float(tile_w); step_y=base_s*hr3; offset_odd_row_x=base_s/2
            elif shape_mode == "triangle": tile_w=base_s; tile_h=int(base_s*0.866); step_x=base_s/2; step_y=float(tile_h)
            elif shape_mode == "romb": tile_w=base_s; tile_h=int(base_s*1.5); step_x=float(tile_w); step_y=base_s*0.75; offset_odd_row_x=base_s/2

            cols = int(target_w / step_x) + 2
            rows = int(target_h / step_y) + 2

            if shape_mode == "hexagon_romb":
                # The composite hexagon is drawn from the three romb masks
                # below; _get_shape_mask has no "hexagon_romb" branch and
                # would silently return a blank mask here.
                mask_norm = mask_flip = None
                mask_left = self._get_shape_mask("mask_left", tile_w, tile_h, padding=render_padding)
                mask_right = self._get_shape_mask("mask_right", tile_w, tile_h, padding=render_padding)
                mask_top = self._get_shape_mask("mask_top", tile_w, tile_h, padding=render_padding)
            else:
                mask_norm = self._get_shape_mask(shape_mode, tile_w, tile_h, False, padding=render_padding)
                mask_flip = self._get_shape_mask(shape_mode, tile_w, tile_h, True, padding=render_padding)

            print("Scanning grid...")
            # Start at -1, not 0: offset/half-step geometries (hexagon,
            # hexagon_romb, romb, brick_wall, triangle) leave a triangular or
            # half-tile gap along the top/left edge because odd rows are pushed
            # right by offset_odd_row_x and rows below the first don't cover the
            # canvas top. The phantom -1 row/column fills those wedges; its
            # tiles land at negative px/py and are clipped by the safe-box +
            # safe[2]<=safe[0] guards below (off-canvas tiles, e.g. square's
            # even-row c=-1, collapse to zero width and are skipped). Pillow
            # 11.1 accepts negative dest in alpha_composite, so the partially
            # visible edge tiles composite correctly.
            for r in range(-1, rows):
                _check_cancel()
                for c in range(-1, cols):
                    pos_x = c * step_x
                    pos_y = r * step_y
                    is_flipped = False

                    if shape_mode in ["brick_wall", "hexagon", "hexagon_romb", "romb"]:
                        if r % 2 == 1: pos_x += offset_odd_row_x
                    elif shape_mode == "triangle":
                        if (c+r)%2==1: is_flipped = True

                    if shape_mode == "hexagon_romb":
                        off_d = tile_w // 4
                        sample_offsets = [(-off_d, off_d), (off_d, off_d), (0, -off_d)]
                        masks = [mask_left, mask_right, mask_top]
                        for k in range(3):
                            spx = int(pos_x + tile_w/2 + sample_offsets[k][0] - tile_w/2)
                            spy = int(pos_y + tile_h/2 + sample_offsets[k][1] - tile_h/2)
                            if spx > target_w or spy > target_h: continue
                            safe = (max(0, spx), max(0, spy), min(target_w, spx+tile_w), min(target_h, spy+tile_h))
                            if safe[2]<=safe[0]: continue
                            s_img = target.crop(safe)
                            if s_img.size != (tile_w, tile_h):
                                tmp = Image.new("RGB", (tile_w, tile_h), (0,0,0)); tmp.paste(s_img, (0,0)); s_img = tmp

                            sectors_data.append({
                                "meta": (r, int(pos_x), int(pos_y), masks[k], tile_w, tile_h, False),
                                "feature": self._compute_sector_feature(s_img, edge_aware)
                            })
                        continue

                    px, py = int(pos_x), int(pos_y)
                    if px > target_w or py > target_h: continue
                    safe = (max(0, px), max(0, py), min(target_w, px+tile_w), min(target_h, py+tile_h))
                    if safe[2]<=safe[0]: continue
                    s_img = target.crop(safe)
                    if s_img.size != (tile_w, tile_h):
                        tmp = Image.new("RGB", (tile_w, tile_h), (0,0,0)); tmp.paste(s_img, (0,0)); s_img = tmp

                    current_mask = mask_flip if is_flipped else mask_norm
                    sectors_data.append({
                        "meta": (r, px, py, current_mask, tile_w, tile_h, False),
                        "feature": self._compute_sector_feature(s_img, edge_aware)
                    })

        # ==========================================
        # PHOTO-TO-TILE MATCHING (SHARED PASS)
        # ==========================================
        if not sectors_data:
            # Returning None here used to surface as a cryptic AttributeError
            # in create_mosaic (result.save on None).
            raise ValueError(
                f"No tiles generated for {target_w}x{target_h} target with "
                f"shape '{shape_mode}' and tile scale {tile_scale} — the "
                f"target is too small for the chosen tile size.")

        # Select which tile features to use for matching.
        # edge_aware/allow_mirror conflict already resolved by _resolve_matching_modes
        # (GUI enforces the mutex; the engine guard backs it up for CLI/programmatic use).
        tile_features = self.features if edge_aware else self.features[:, :75]

        print(f"Building Spatial Tree for {len(sectors_data)} tiles...")
        points = [(s["meta"][1] + s["meta"][4]/2.0, s["meta"][2] + s["meta"][5]/2.0) for s in sectors_data]
        search_radius = base_s * 1.5
        # border_mode changes render_padding (0.94 vs 1.02), which can shift the
        # sector count of edge tiles for kite/spectre. Without it in the key, a
        # second render of the same geometry with the border toggled reuses a
        # stale neighbors_map of the wrong length -> IndexError.
        _nkey = (base_s, shape_mode, target_w, target_h, border_mode)
        neighbors_map = self._get_neighbors_map(_nkey, points, search_radius)

        print("Matching and generating final mosaic...")
        if tint_strength > 0.0:
            print(f"  Tile Tint active: {int(tint_strength * 100)}% (pixel lerp toward sector colour)")
        if blend_strength > 0.0:
            print(f"  Color Blend will be applied at save: {int(blend_strength * 100)}%")
        if edge_aware:
            print("  Edge-Aware Matching active (79-dim features)")

        tgt_features = np.array([x["feature"] for x in sectors_data])
        # int64: used_counts**2 in the frequency penalty (below) overflows int32
        # once a tile is reused >46340 times (huge render + tiny library), which
        # would wrap negative and invert the penalty.
        used_counts = np.zeros(len(self.paths), dtype=np.int64)
        sector_assignments = -1 * np.ones(len(sectors_data), dtype=np.int32)
        failed_tiles = 0

        features_norm = tile_features.astype(np.float32, copy=False)
        features_flip = None
        if allow_mirror:
            # tile_features is guaranteed 75-dim here: _resolve_matching_modes
            # disables allow_mirror whenever edge_aware (79-dim) is active.
            reshaped = features_norm.reshape(-1, 5, 5, 3)
            flipped = reshaped[:, :, ::-1, :]
            features_flip = flipped.reshape(-1, 75)

        # Precompute library squared norms once for the GEMM distance (see
        # _euclid_f32). The flip is a column permutation, so its per-tile norm is
        # identical — but recomputing is O(N) and keeps the call site obvious.
        norms_norm = np.einsum("ij,ij->i", features_norm, features_norm)
        norms_flip = (np.einsum("ij,ij->i", features_flip, features_flip)
                      if allow_mirror else None)
        tgt32 = tgt_features.astype(np.float32, copy=False)

        # Adaptive chunk size: cap the float32 distance matrix (or matrices, when
        # mirroring keeps norm+flip resident together) at ~256 MB. The old fixed
        # chunk_size=500 produced a ~1.8 GB float64 matrix (x2 with mirror) — the
        # dominant peak-RAM spike at 16K.
        n_lib = max(features_norm.shape[0], 1)
        n_matrices = 2 if allow_mirror else 1
        rows_budget = (256 * 1024 * 1024) // (n_lib * 4 * n_matrices)
        chunk_size = int(np.clip(rows_budget, 64, 500))

        top_k = min(len(self.paths), 200)

        for i in tqdm(range(0, len(sectors_data), chunk_size)):
            _check_cancel()
            end = min(i + chunk_size, len(sectors_data))
            chunk_tgt = tgt32[i:end]

            dists_norm = _euclid_f32(chunk_tgt, features_norm, norms_norm)
            if allow_mirror:
                dists_flip = _euclid_f32(chunk_tgt, features_flip, norms_flip)

            top_k_norm = np.argpartition(dists_norm, top_k - 1, axis=1)[:, :top_k]
            if allow_mirror:
                top_k_flip = np.argpartition(dists_flip, top_k - 1, axis=1)[:, :top_k]

            for j in range(len(chunk_tgt)):
                global_idx = i + j
                meta = sectors_data[global_idx]["meta"]

                idx_id, px, py, mask, tw, th, is_hat = meta

                forbidden_indices = set()
                my_neighbors = neighbors_map[global_idx]
                for n_idx in my_neighbors:
                    if n_idx == global_idx: continue
                    if is_hat:
                        if sectors_data[n_idx]["meta"][0] == idx_id:
                            assigned = sector_assignments[n_idx]
                            if assigned != -1: forbidden_indices.add(assigned)
                    else:
                        assigned = sector_assignments[n_idx]
                        if assigned != -1: forbidden_indices.add(assigned)

                candidates = []
                for idx in top_k_norm[j]:
                    score = dists_norm[j, idx] + (used_counts[idx]**2 * self.settings["freq_penalty"] * 0.001)
                    if idx in forbidden_indices: score += 1000000.0
                    candidates.append((score, idx, False))

                if allow_mirror:
                    for idx in top_k_flip[j]:
                        score = dists_flip[j, idx] + (used_counts[idx]**2 * self.settings["freq_penalty"] * 0.001)
                        if idx in forbidden_indices: score += 1000000.0
                        candidates.append((score, idx, True))

                candidates.sort(key=lambda x: x[0])
                best_score, best_idx, should_mirror = candidates[0]

                used_counts[best_idx] += 1
                sector_assignments[global_idx] = best_idx

                try:
                    with Image.open(self.paths[best_idx]) as img:
                        img = img.convert("RGBA")
                        if should_mirror: img = ImageOps.mirror(img)

                        img = self._smart_crop(img, tw, th)

                        if tint_strength > 0.0:
                            sector_box = (
                                max(0, px), max(0, py),
                                min(target_w, px + tw), min(target_h, py + th)
                            )
                            if sector_box[2] > sector_box[0] and sector_box[3] > sector_box[1]:
                                sector_crop = target.crop(sector_box)
                                sector_mean = np.array(
                                    sector_crop.resize((1, 1), Image.Resampling.BOX).getpixel((0, 0)),
                                    dtype=np.float32)[:3]
                                tile_rgb = img.convert("RGB")
                                tile_arr = np.array(tile_rgb, dtype=np.float32)
                                tile_arr = tile_arr * (1.0 - tint_strength) + sector_mean * tint_strength
                                tile_arr = np.clip(tile_arr, 0, 255).astype(np.uint8)
                                img = Image.fromarray(tile_arr).convert("RGBA")

                        # Grid masks are shared PIL images; kite/spectre store a
                        # _LazyMask re-rasterised here (identical to build time).
                        tile_mask = mask.render() if isinstance(mask, _LazyMask) else mask
                        img.putalpha(tile_mask)
                        final_mosaic.alpha_composite(img, (px, py))
                except Exception:
                    # One bad tile must not abort the render, but silent
                    # holes are debugging hell — count and report below.
                    failed_tiles += 1

            if progress_cb is not None:
                progress_cb(end, len(sectors_data))

        if failed_tiles > 0:
            print(f"WARNING: {failed_tiles} of {len(sectors_data)} tiles "
                  f"failed to load/composite and were skipped (holes show "
                  f"the black background).")

        mosaic_rgb = final_mosaic.convert("RGB")
        if blend_strength > 0.0:
            print(f"Applying Color Blend: {int(blend_strength * 100)}%...")
            original_resized = target.resize(mosaic_rgb.size, Image.Resampling.LANCZOS)
            mosaic_rgb = Image.blend(mosaic_rgb, original_resized, blend_strength)

        # Grout is drawn last so it sits on top of the blend as a hard overlay
        # (a colour blend must not wash the lines out).
        if grout_preset is not None:
            _check_cancel()
            self._apply_grout(mosaic_rgb, shape_mode, target_w, target_h, base_s,
                              grout_preset)
        return mosaic_rgb
