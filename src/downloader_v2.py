"""
src/downloader_v2.py
--------------------
PoliteDownloader — multi-source CC0/PD tile downloader.

Sources: Openverse (primary), Met Museum, Art Institute Chicago,
         NASA, Cleveland Museum of Art, Wikimedia Commons.
No Flickr (paid API), no Library of Congress (no stable endpoint).
"""
import os
import json
import time
import random
import logging
import threading
import shutil
from pathlib import Path
from io import BytesIO
from typing import Callable, Optional

import requests
from PIL import Image, ImageFilter
import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_OUTPUT_DIR = Path("data/library_public_2/tiles")
STATE_FILE = Path("data/download_state.json")

DOWNLOAD_PLANS = {
    "starter":  {"openverse": 200, "met": 100, "artic": 80,
                 "nasa": 60, "cleveland": 30, "wikimedia": 30},
    "public":   {"openverse": 2000, "met": 1000, "artic": 700,
                 "nasa": 500, "cleveland": 400, "wikimedia": 400},
    "extended": {"openverse": 14000, "met": 5000, "artic": 4000,
                 "nasa": 3000, "cleveland": 2000, "wikimedia": 2000},
}

OPENVERSE_TAGS = [
    "nature", "landscape", "architecture", "animals", "food",
    "people", "travel", "abstract", "flowers", "ocean",
    "forest", "city", "art", "texture", "sky",
    "mountains", "beach", "street", "vintage", "colorful",
    "patterns", "birds", "cats", "dogs", "cars",
    "water", "sunset", "winter", "autumn", "summer",
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
]

WIKIMEDIA_UA = (
    "Neural-Mosaic/1.0 "
    "(https://github.com/Piotr1686/neural-mosaic; p.lazowski.1986@gmail.com)"
)


# ---------------------------------------------------------------------------
# PoliteDownloader
# ---------------------------------------------------------------------------

class PoliteDownloader:
    """
    Downloads CC0/PD images from multiple museum and open-content APIs
    with rate limiting, deduplication, and quality filtering.
    """

    def __init__(self, output_dir: str | Path = DEFAULT_OUTPUT_DIR):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.session = requests.Session()
        self._openverse_token: Optional[str] = None

        self._request_count = 0
        self._tag_index = 0
        self._tags = list(OPENVERSE_TAGS)  # mutable per-instance copy, shuffled each epoch

        self.on_progress: Optional[Callable[[str], None]] = None

        self._stop_event = threading.Event()

        # phash index: loaded from state or built from existing files
        self._hashes: list = []
        self._downloaded_ids: set = set()
        self._state_path = STATE_FILE

        self._load_state()

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def stop(self):
        """Request graceful stop. Saves state immediately."""
        self._stop_event.set()
        self._save_state()

    def download(self, plan: str = "starter") -> int:
        """Run a named download plan. Returns number of saved images."""
        if plan not in DOWNLOAD_PLANS:
            raise ValueError(f"Unknown plan '{plan}'. Choose from: {list(DOWNLOAD_PLANS)}")

        self._stop_event.clear()

        if plan == "extended":
            free_gb = shutil.disk_usage(".").free / (1024 ** 3)
            if free_gb < 5:
                self._log(f"WARNING: Only {free_gb:.1f} GB free. Extended needs ~2.5 GB.")

        targets = DOWNLOAD_PLANS[plan]
        total_saved = 0

        for source, count in targets.items():
            if self._stop_event.is_set():
                self._log("Download stopped by user.")
                break
            self._log(f"[{source.upper()}] target={count}")
            fetcher = getattr(self, f"_fetch_{source}_ids")
            saved = self._run_source(fetcher, count, source)
            total_saved += saved
            self._log(f"[{source.upper()}] saved={saved}")

        self._save_state()
        return total_saved

    def test_download(self, dest: str | Path = "data/test_download") -> int:
        """Download 10 images to a test directory. Used for smoke-testing."""
        dest = Path(dest)
        dest.mkdir(parents=True, exist_ok=True)
        orig_dir = self.output_dir
        self.output_dir = dest
        try:
            ids = list(self._fetch_openverse_ids(10))
            saved = 0
            for url, img_id in ids:
                if self._download_and_save(url, img_id):
                    saved += 1
            return saved
        finally:
            self.output_dir = orig_dir

    # -----------------------------------------------------------------------
    # Source fetchers — yield (url, unique_id) tuples
    # -----------------------------------------------------------------------

    def _fetch_openverse_ids(self, limit: int):
        token = self._get_openverse_token()
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        page_size = 20
        fetched = 0
        auth_failures = 0  # consecutive 401s; bail if re-auth keeps failing

        while fetched < limit:
            if self._stop_event.is_set():
                return
            n = len(self._tags)
            tag = self._tags[self._tag_index % n]
            self._tag_index += 1
            if self._tag_index % n == 0:
                random.shuffle(self._tags)  # new epoch — reshuffle for variety

            params = {
                "q": tag,
                "license": "cc0,pdm",
                "page_size": page_size,
                "page": random.randint(1, 10),
                "size": "medium,large",
                "min_width": 200,
                "min_height": 200,
            }
            resp = self._get("https://api.openverse.org/v1/images/",
                             params=params, headers=headers)
            if resp is None:
                break
            if resp.status_code == 401:
                auth_failures += 1
                if auth_failures >= 3:
                    self._log("Openverse: repeated 401 after re-auth — giving up.")
                    break
                self._openverse_token = None
                token = self._get_openverse_token()
                headers = {"Authorization": f"Bearer {token}"} if token else {}
                continue
            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", 60))
                self._log(f"Openverse 429 — sleeping {wait}s")
                time.sleep(wait)
                continue
            if not resp.ok:
                break
            auth_failures = 0  # successful response — reset the 401 counter

            results = resp.json().get("results", [])
            for item in results:
                w = item.get("width") or 0
                h = item.get("height") or 0
                if w and h and min(w, h) < 200:
                    continue
                url = item.get("thumbnail") or item.get("url")
                img_id = f"openverse_{item.get('id', '')}"
                if url and img_id not in self._downloaded_ids:
                    yield url, img_id
                    fetched += 1
                    if fetched >= limit:
                        return

    def _fetch_met_ids(self, limit: int):
        # Public domain objects with images, random departments
        dept_ids = [1, 3, 4, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 17, 18, 19, 21]
        fetched = 0
        for dept in random.sample(dept_ids, min(len(dept_ids), 6)):
            if fetched >= limit or self._stop_event.is_set():
                break
            resp = self._get(
                "https://collectionapi.metmuseum.org/public/collection/v1/objects",
                params={"departmentIds": dept, "hasImages": True, "isPublicDomain": True},
            )
            if resp is None or not resp.ok:
                continue
            obj_ids = resp.json().get("objectIDs") or []
            random.shuffle(obj_ids)
            for obj_id in obj_ids:
                if fetched >= limit or self._stop_event.is_set():
                    return
                img_id = f"met_{obj_id}"
                if img_id in self._downloaded_ids:
                    continue
                detail = self._get(
                    f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{obj_id}"
                )
                if detail is None or not detail.ok:
                    continue
                url = detail.json().get("primaryImageSmall") or detail.json().get("primaryImage")
                if url:
                    yield url, img_id
                    fetched += 1

    def _fetch_artic_ids(self, limit: int):
        fetched = 0
        page = 1
        while fetched < limit:
            if self._stop_event.is_set():
                return
            resp = self._get(
                "https://api.artic.edu/api/v1/artworks",
                params={
                    "fields": "id,image_id,is_public_domain",
                    "limit": 100,
                    "page": page,
                    "query[term][is_public_domain]": "true",
                },
            )
            page += 1
            if resp is None or not resp.ok:
                break
            items = resp.json().get("data", [])
            if not items:
                break
            base = "https://www.artic.edu/iiif/2"
            for item in items:
                if fetched >= limit:
                    return
                img_id_raw = item.get("image_id")
                if not img_id_raw:
                    continue
                img_id = f"artic_{item['id']}"
                if img_id in self._downloaded_ids:
                    continue
                url = f"{base}/{img_id_raw}/full/843,/0/default.jpg"
                yield url, img_id
                fetched += 1

    def _fetch_nasa_ids(self, limit: int):
        queries = ["earth", "nebula", "galaxy", "moon", "mars",
                   "astronaut", "rocket", "space", "planet", "aurora"]
        fetched = 0
        for q in random.sample(queries, min(len(queries), limit // 5 + 1)):
            if fetched >= limit or self._stop_event.is_set():
                break
            resp = self._get(
                "https://images-api.nasa.gov/search",
                params={"q": q, "media_type": "image"},
            )
            if resp is None or not resp.ok:
                continue
            items = resp.json().get("collection", {}).get("items", [])
            for item in items:
                if fetched >= limit:
                    return
                links = item.get("links", [])
                href = next((l["href"] for l in links if l.get("rel") == "preview"), None)
                nasa_id = (item.get("data") or [{}])[0].get("nasa_id", "")
                img_id = f"nasa_{nasa_id}"
                if href and nasa_id and img_id not in self._downloaded_ids:
                    yield href, img_id
                    fetched += 1

    def _fetch_cleveland_ids(self, limit: int):
        fetched = 0
        skip = 0
        while fetched < limit:
            if self._stop_event.is_set():
                return
            resp = self._get(
                "https://openaccess-api.clevelandart.org/api/artworks/",
                params={"has_image": 1, "cc0": 1, "limit": 100, "skip": skip},
            )
            skip += 100
            if resp is None or not resp.ok:
                break
            items = resp.json().get("data", [])
            if not items:
                break
            for item in items:
                if fetched >= limit:
                    return
                img_id = f"cleveland_{item.get('id', '')}"
                if img_id in self._downloaded_ids:
                    continue
                images = item.get("images", {})
                url = (images.get("web", {}).get("url")
                       or images.get("print", {}).get("url")
                       or images.get("full", {}).get("url"))
                if url:
                    yield url, img_id
                    fetched += 1

    def _fetch_wikimedia_ids(self, limit: int):
        categories = [
            "Category:CC0 photographs", "Category:Public domain photographs",
            "Category:Public domain paintings", "Category:Public domain drawings",
        ]
        fetched = 0
        for cat in random.sample(categories, min(len(categories), 4)):
            if fetched >= limit or self._stop_event.is_set():
                break
            resp = self._get(
                "https://commons.wikimedia.org/w/api.php",
                params={
                    "action": "query", "list": "categorymembers",
                    "cmtitle": cat, "cmtype": "file",
                    "cmlimit": 100, "format": "json",
                },
                headers={"User-Agent": WIKIMEDIA_UA},
            )
            if resp is None or not resp.ok:
                continue
            members = resp.json().get("query", {}).get("categorymembers", [])
            for m in members:
                if fetched >= limit:
                    return
                title = m.get("title", "")
                img_id = f"wiki_{m.get('pageid', '')}"
                if img_id in self._downloaded_ids:
                    continue
                thumb = self._wikimedia_thumbnail(title)
                if thumb:
                    yield thumb, img_id
                    fetched += 1

    def _wikimedia_thumbnail(self, title: str) -> Optional[str]:
        resp = self._get(
            "https://commons.wikimedia.org/w/api.php",
            params={
                "action": "query", "titles": title,
                "prop": "imageinfo", "iiprop": "url|extmetadata",
                "iiurlwidth": 800, "format": "json",
            },
            headers={"User-Agent": WIKIMEDIA_UA},
        )
        if resp is None or not resp.ok:
            return None
        pages = resp.json().get("query", {}).get("pages", {})
        for page in pages.values():
            info = (page.get("imageinfo") or [{}])[0]
            meta = info.get("extmetadata", {})
            license_id = meta.get("LicenseShortName", {}).get("value", "")
            # Only CC0 and PD — reject CC-BY, CC-BY-SA etc.
            if license_id.upper() not in ("CC0", "PDM", "PUBLIC DOMAIN"):
                return None
            return info.get("thumburl")
        return None

    # -----------------------------------------------------------------------
    # Openverse OAuth2
    # -----------------------------------------------------------------------

    def _get_openverse_token(self) -> Optional[str]:
        if self._openverse_token:
            return self._openverse_token
        client_id = os.environ.get("OPENVERSE_CLIENT_ID")
        client_secret = os.environ.get("OPENVERSE_CLIENT_SECRET")
        if not client_id or not client_secret:
            return None
        try:
            resp = requests.post(
                "https://api.openverse.org/v1/auth_tokens/token/",
                data={"grant_type": "client_credentials",
                      "client_id": client_id,
                      "client_secret": client_secret},
                timeout=15,
            )
            if resp.ok:
                self._openverse_token = resp.json().get("access_token")
                return self._openverse_token
        except Exception as exc:
            logger.warning("Openverse token fetch failed: %s", exc)
        return None

    # -----------------------------------------------------------------------
    # Download + quality pipeline
    # -----------------------------------------------------------------------

    def _run_source(self, fetcher, count: int, source_name: str) -> int:
        saved = 0
        attempted = 0
        stats = {"fetch_fail": 0, "decode": 0, "small": 0, "quality": 0, "dup": 0}

        for url, img_id in fetcher(count * 3):  # overfetch to allow rejects
            if self._stop_event.is_set():
                self._log(f"[{source_name}] Download stopped by user.")
                break
            if saved >= count:
                break
            if img_id in self._downloaded_ids:
                continue

            result = self._download_and_save(url, img_id)
            attempted += 1
            if result is True:
                saved += 1
                if saved % 10 == 0:
                    self._log(f"[{source_name}] {saved}/{count} saved")
                    self._save_state()
            elif result in stats:
                stats[result] += 1

            if attempted % 50 == 0:
                self._log(
                    f"[{source_name}] tried={attempted} saved={saved} | "
                    f"fetch_fail={stats['fetch_fail']} small={stats['small']} "
                    f"quality={stats['quality']} dup={stats['dup']}"
                )

        return saved

    def _download_and_save(self, url: str, img_id: str):
        """Returns True on success, or a rejection-reason string on failure."""
        raw = self._fetch_bytes(url)
        if raw is None:
            return "fetch_fail"
        try:
            img = Image.open(BytesIO(raw))
            img = img.convert("RGB")
        except Exception:
            return "decode"

        w, h = img.size
        shortest = min(w, h)
        if shortest < 100:
            return "small"
        if shortest > 600:
            scale = 600 / shortest
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

        if self._is_low_quality(img):
            return "quality"

        from imagehash import phash as compute_phash
        h_val = compute_phash(img)
        for existing in self._hashes:
            if (h_val - existing) < 5:
                return "dup"
        self._hashes.append(h_val)

        out_path = self.output_dir / f"{img_id}.jpg"
        img.save(out_path, "JPEG", quality=85)
        self._downloaded_ids.add(img_id)
        return True

    def _is_low_quality(self, img: Image.Image) -> bool:
        arr = np.array(img.convert("L"), dtype=np.float32)
        if arr.std() < 8:
            return True
        if int(arr.max()) - int(arr.min()) < 20:
            return True
        return False

    # -----------------------------------------------------------------------
    # HTTP helpers
    # -----------------------------------------------------------------------

    def _get(self, url: str, params=None, headers=None) -> Optional[requests.Response]:
        self._polite_wait()
        if self._stop_event.is_set():
            return None
        merged_headers = {"User-Agent": random.choice(USER_AGENTS)}
        if headers:
            merged_headers.update(headers)
        for attempt in range(4):
            try:
                resp = self.session.get(url, params=params, headers=merged_headers,
                                        timeout=20)
                if resp.status_code in (429, 500, 502, 503, 504):
                    wait = int(resp.headers.get("Retry-After", 10 * (2 ** attempt)))
                    time.sleep(wait)
                    continue
                return resp
            except Exception as exc:
                logger.debug("GET %s failed (attempt %d): %s", url, attempt, exc)
                time.sleep(5 * (attempt + 1))
        return None

    def _fetch_bytes(self, url: str) -> Optional[bytes]:
        resp = self._get(url)
        if resp is None or not resp.ok:
            return None
        return resp.content

    def _polite_wait(self):
        self._request_count += 1
        base = random.uniform(2.0, 3.0)
        jitter = base * random.uniform(-0.3, 0.3)
        delay = base + jitter

        if self._request_count % 200 == 0:
            delay = random.uniform(60, 120)
            self._log(f"Long pause ({delay:.0f}s) after {self._request_count} requests")
        elif self._request_count % 50 == 0:
            delay = random.uniform(10, 20)
            self._log(f"Micro-pause ({delay:.0f}s) after {self._request_count} requests")

        # Sleep in small chunks so stop() takes effect quickly
        deadline = time.time() + delay
        while time.time() < deadline:
            if self._stop_event.is_set():
                return
            time.sleep(0.5)

    # -----------------------------------------------------------------------
    # State persistence
    # -----------------------------------------------------------------------

    def _load_state(self):
        if self._state_path.exists():
            try:
                state = json.loads(self._state_path.read_text())
                self._downloaded_ids = set(state.get("downloaded_ids", []))
                self._tag_index = state.get("tag_index", 0)
                hash_ints = state.get("phashes", [])
                try:
                    import numpy as _np
                    from imagehash import ImageHash
                    self._hashes = [ImageHash(_np.array(h, dtype=bool).reshape(8, 8))
                                    for h in hash_ints]
                except Exception:
                    self._hashes = []
                self._log(f"Resumed: {len(self._downloaded_ids)} IDs, "
                          f"{len(self._hashes)} hashes loaded, "
                          f"tag_index={self._tag_index}")
            except Exception as exc:
                logger.warning("Could not load state: %s", exc)

    def _save_state(self):
        try:
            from imagehash import ImageHash
            hash_data = [h.hash.flatten().tolist() for h in self._hashes]
            state = {
                "downloaded_ids": list(self._downloaded_ids),
                "phashes": hash_data,
                "tag_index": self._tag_index,
            }
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            self._state_path.write_text(json.dumps(state))
        except Exception as exc:
            logger.warning("Could not save state: %s", exc)

    def _log(self, msg: str):
        logger.info(msg)
        if self.on_progress:
            self.on_progress(msg)
        else:
            print(msg)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Neural-Mosaic tile downloader")
    parser.add_argument("plan", nargs="?", default="starter",
                        choices=["starter", "public", "extended", "test"],
                        help="Download plan (default: starter)")
    parser.add_argument("--out", default=str(DEFAULT_OUTPUT_DIR),
                        help="Output directory")
    args = parser.parse_args()

    dl = PoliteDownloader(args.out)
    if args.plan == "test":
        n = dl.test_download()
        print(f"Test complete: {n} images saved to data/test_download/")
    else:
        n = dl.download(args.plan)
        print(f"Done: {n} images saved to {args.out}")
