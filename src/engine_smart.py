"""
src/engine_smart.py
-------------------
Colour-matched photomosaic engine (SmartEngine).

Supports multiple tile geometries including the kite (diamond) shape and
the chiral aperiodic "spectre" monotile (src/spectre_tiling.py).
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
import random
import math
import threading
from collections import defaultdict
from PIL import Image, ImageOps, ImageDraw
from tqdm import tqdm
from scipy.spatial.distance import cdist
from scipy.spatial import cKDTree
import skimage.color

from .spectre_tiling import generate_spectre_tiling

# Must match EDGE_WEIGHT in indexer_smart.py.
EDGE_WEIGHT = 2.0


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

    def create_mosaic(self, target_path, output_path, resolution_key, shape_mode, tile_scale, border_mode=False, blend_strength=0.0, tint_strength=0.0, progress_cb=None):
        """Public API — resolves resolution_key and delegates to _do_render."""
        if not self.paths:
            print("ERROR: Index not loaded.")
            return
        res_map = {"2K": 1920, "4K": 3840, "8K": 7680, "16K": 15360}
        target_long = res_map.get(resolution_key, 3840)
        target = Image.open(target_path).convert("RGB")
        img_w, img_h = target.size
        scale_res = target_long / max(img_w, img_h)
        target = target.resize((int(img_w * scale_res), int(img_h * scale_res)), Image.Resampling.LANCZOS)
        result = self._do_render(target, shape_mode, tile_scale, border_mode, blend_strength, tint_strength, progress_cb=progress_cb)
        result.save(output_path, quality=95)

    def render_preview(self, target_path, short_edge=512, shape_mode="hexagon_romb",
                       tile_scale=1.0, border_mode=False):
        """Return a PIL Image preview at ~short_edge px short side — no file I/O."""
        if not self.paths:
            raise RuntimeError("Index not loaded.")
        target = Image.open(target_path).convert("RGB")
        img_w, img_h = target.size
        scale = short_edge / min(img_w, img_h)
        prev_w = max(1, int(img_w * scale))
        prev_h = max(1, int(img_h * scale))
        target = target.resize((prev_w, prev_h), Image.Resampling.LANCZOS)
        return self._do_render(target, shape_mode, tile_scale, border_mode, 0.0, 0.0)

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

    def _do_render(self, target, shape_mode, tile_scale, border_mode=False, blend_strength=0.0, tint_strength=0.0, progress_cb=None):
        """Core rendering kernel — accepts a pre-scaled PIL Image, returns PIL Image.

        ``progress_cb``, if given, is called ``progress_cb(done, total)`` after each
        matching chunk during the final assembly loop (the dominant cost), where
        ``total`` is the number of sectors. Used by the GUI to drive a progress bar.
        """
        edge_aware, allow_mirror = self._resolve_matching_modes()

        target_w, target_h = target.size
        base_s = int(100 * tile_scale)
        if base_s < 10: base_s = 10
        render_padding = 0.94 if border_mode else 1.02

        final_mosaic = Image.new("RGBA", (target_w, target_h), (0,0,0,255))
        sectors_data = []

        # ==========================================
        # KITE TILING (DIAMOND GEOMETRY)
        # ==========================================
        if shape_mode == "kite":
            print(f"Mode: Kite tiling. Borders: {border_mode}")

            s  = base_s
            r3 = math.sqrt(3)

            BASE_HAT = [
                (0, 0, 0), (0, 0, 1), (0, 0, 2), (0, 0, 3), (0, 0, 5),
                (0, 1, 4), (0, 1, 5),
                (1, 0, 3),
            ]

            target_kites  = set()
            kite_centroids = {}

            range_q = int(target_w / (1.5 * s)) + 3
            range_r = int(target_h / (r3 * s)) + 3

            print("Building kite grid...")
            for q in range(-range_q, range_q):
                for r in range(-range_r, range_r):
                    cx = 1.5 * s * q
                    cy = r3 * s * (r + q / 2.0)

                    if -2*s < cx < target_w + 2*s and -2*s < cy < target_h + 2*s:
                        for k in range(6):
                            poly   = self._get_kite_poly(cx, cy, s, k)
                            cent_x = sum(p[0] for p in poly) / 4
                            cent_y = sum(p[1] for p in poly) / 4

                            if 0 <= cent_x < target_w and 0 <= cent_y < target_h:
                                target_kites.add((q, r, k))
                            kite_centroids[(q, r, k)] = (cent_x, cent_y)

            uncovered_targets = list(target_kites)
            uncovered_targets.sort(
                key=lambda k: (kite_centroids[k][0] - target_w/2)**2
                              + (kite_centroids[k][1] - target_h/2)**2
            )

            occupied   = set()
            placed_hats = []

            # Deterministic per render geometry: an unseeded RNG produced a
            # different hat layout (and sector count) every run, which both
            # broke preview/render reproducibility and poisoned the
            # _neighbors_cache entry shared by renders with the same _nkey
            # (stale adjacency, possible IndexError on the second render).
            rng = random.Random(f"kite_{base_s}_{target_w}_{target_h}")

            kite_to_hats = defaultdict(list)
            for target_k in target_kites:
                t_q, t_r, t_k = target_k
                for rot in range(6):
                    for flip in [False, True]:
                        for b_idx in range(8):
                            bq, br, bk = BASE_HAT[b_idx]
                            trans_q, trans_r, trans_k = self._transform_kite_index(
                                bq, br, bk, 0, 0, rot, flip
                            )
                            if trans_k == t_k:
                                dq = t_q - trans_q
                                dr = t_r - trans_r
                                hat = tuple(
                                    self._transform_kite_index(x, y, z, dq, dr, rot, flip)
                                    for x, y, z in BASE_HAT
                                )
                                if hat not in kite_to_hats[target_k]:
                                    kite_to_hats[target_k].append(hat)

            for k_target in tqdm(uncovered_targets, desc="Assembling hats edge-to-edge"):
                if k_target in occupied:
                    continue

                valid_hats = [
                    hat for hat in kite_to_hats[k_target]
                    if not any(k in occupied for k in hat)
                ]

                if valid_hats:
                    chosen_hat = rng.choice(valid_hats)
                    placed_hats.append(chosen_hat)
                    for k in chosen_hat:
                        occupied.add(k)
                else:
                    placed_hats.append((k_target,))
                    occupied.add(k_target)

            print("Rendering 8-kite hats...")
            for i_hat, hat_kites in enumerate(placed_hats):
                hat_polys = []
                for q, r, k in hat_kites:
                    cx   = 1.5 * s * q
                    cy   = r3 * s * (r + q / 2.0)
                    poly = self._get_kite_poly(cx, cy, s, k)
                    hat_polys.append(poly)

                all_pts = [p for poly in hat_polys for p in poly]
                hat_cx  = sum(p[0] for p in all_pts) / len(all_pts)
                hat_cy  = sum(p[1] for p in all_pts) / len(all_pts)

                for k_idx, poly in enumerate(hat_polys):
                    padded_poly = []
                    for px, py in poly:
                        nx = hat_cx + (px - hat_cx) * render_padding
                        ny = hat_cy + (py - hat_cy) * render_padding
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

                    mask_kite = Image.new("L", (bw, bh), 0)
                    draw_k = ImageDraw.Draw(mask_kite)
                    shifted_poly = [(p[0] - min_x, p[1] - min_y) for p in padded_poly]
                    draw_k.polygon(shifted_poly, fill=255)

                    # Replace outside-mask pixels with the kite's mean colour
                    # so the bounding box does not leak neighbouring content
                    # into the LAB match (same treatment as the spectre mode).
                    feat_img = self._mean_fill_outside_mask(s_img, mask_kite)

                    sectors_data.append({
                        "meta": (i_hat, int(min_x), int(min_y), mask_kite, bw, bh, len(hat_kites) > 1),
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

                # Anti-aliased polygon mask (supersampled, like _get_shape_mask).
                mask_spec = Image.new("L", (bw * scale_aa, bh * scale_aa), 0)
                draw_s = ImageDraw.Draw(mask_spec)
                shifted_poly = [((p[0] - min_x) * scale_aa, (p[1] - min_y) * scale_aa)
                                for p in padded_poly]
                draw_s.polygon(shifted_poly, fill=255)
                mask_spec = mask_spec.resize((bw, bh), Image.Resampling.LANCZOS)

                # The spectre is non-convex, so its bounding box contains a
                # lot of neighbouring content; replace outside-mask pixels
                # with the tile's mean colour so they do not pollute the
                # LAB match.
                feat_img = self._mean_fill_outside_mask(s_img, mask_spec)

                sectors_data.append({
                    "meta": (i_spec, int(min_x), int(min_y), mask_spec, bw, bh, False),
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

        chunk_size = 500

        features_norm = tile_features
        features_flip = None
        if allow_mirror:
            # tile_features is guaranteed 75-dim here: _resolve_matching_modes
            # disables allow_mirror whenever edge_aware (79-dim) is active.
            reshaped = tile_features.reshape(-1, 5, 5, 3)
            flipped = reshaped[:, :, ::-1, :]
            features_flip = flipped.reshape(-1, 75)

        top_k = min(len(self.paths), 200)

        for i in tqdm(range(0, len(sectors_data), chunk_size)):
            end = min(i + chunk_size, len(sectors_data))
            chunk_tgt = tgt_features[i:end]

            dists_norm = cdist(chunk_tgt, features_norm, 'euclidean')
            if allow_mirror:
                dists_flip = cdist(chunk_tgt, features_flip, 'euclidean')

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

                        img.putalpha(mask)
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
        return mosaic_rgb
