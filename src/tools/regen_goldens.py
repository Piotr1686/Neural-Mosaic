"""Regenerate the locked render hashes in tests/test_golden_shapes.py.

The golden test pins a SHA-256 of `_do_render` output for every shape x border
pair. A deliberate engine change (a matching fix, a geometry fix) moves those
hashes, and they then have to be re-locked -- by hand until now, which is both
tedious and a place to make a silent mistake.

The one rule this script exists to enforce: the hashes must be produced by
EXACTLY what the test measures. So it imports the test module and reuses its
library builder, its target generator and its settings dict rather than
restating any of them here. A second, drifting definition of the fixture would
defeat the whole point of a golden.

Reading the report matters as much as running it. Shapes that come back
BIT-IDENTICAL are the collateral-damage check: after a change that should only
touch shape X, every other shape staying identical is the evidence that it did.
After a change to shared matching or geometry code, nothing staying identical is
the expected result. A shape that stays identical when you MEANT to change it is
the interesting case -- it usually means the code you edited is not the code the
engine runs (see the kites triple-walk episode, 2026-07-26).

    python -m src.tools.regen_goldens --check    # report only, writes nothing
    python -m src.tools.regen_goldens            # rewrite the hashes
"""
import argparse
import hashlib
import os
import re
import sys
import tempfile
import threading
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.engine_smart import SmartEngine                       # noqa: E402
import tests.test_golden_shapes as G                           # noqa: E402

TESTFILE = ROOT / "tests" / "test_golden_shapes.py"


def _fixture_settings():
    """The settings dict the golden fixture builds, read from the test source.

    Parsed rather than imported because the fixture is a pytest fixture: calling
    it outside a session would need a tmp_path_factory. Parsing keeps the test
    the single source of truth for the settings the goldens are locked at.
    """
    src = TESTFILE.read_text(encoding="utf-8")
    m = re.search(r"e\.settings = (\{[^}]*\})", src)
    if not m:
        raise SystemExit("ERROR: no `e.settings = {...}` found in the golden fixture")
    return eval(m.group(1), {"__builtins__": {}}, {})


def _render_all():
    settings = _fixture_settings()
    print(f"settings from fixture: {settings}")

    tmp = Path(tempfile.mkdtemp(prefix="goldens_"))
    paths, feats = G._build_library(tmp)
    e = SmartEngine(index_path="__none__.pkl")
    e.paths = paths
    e.features = feats
    e.settings = settings

    digests = {}
    for (shape, border) in G.GOLDEN:
        # Isolate each render's neighbour cache exactly as the test does, so
        # ordering cannot leak between cases.
        e._neighbors_cache = {}
        e._neighbors_lock = threading.Lock()
        out = e._do_render(G._make_target(), shape, tile_scale=0.5,
                           border_mode=border)
        digests[(shape, border)] = hashlib.sha256(out.tobytes()).hexdigest()
    return digests


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="report what would change, write nothing")
    args = ap.parse_args()

    new = _render_all()
    changed = [k for k in G.GOLDEN if G.GOLDEN[k] != new[k]]
    same = [k for k in G.GOLDEN if G.GOLDEN[k] == new[k]]

    print(f"\nchanged:       {len(changed)} / {len(G.GOLDEN)}")
    print(f"BIT-IDENTICAL: {len(same)} / {len(G.GOLDEN)}")
    for shape, border in same:
        print(f"    unchanged: {shape} border={border}")

    if args.check:
        print("\n--check: nothing written")
        return
    if not changed:
        print("\nnothing to rewrite")
        return

    src = TESTFILE.read_text(encoding="utf-8")
    for (shape, border), digest in new.items():
        pat = re.compile(r'(\("%s", %s\): ")[0-9a-f]{64}(")'
                         % (re.escape(shape), border))
        src, n = pat.subn(r"\g<1>%s\g<2>" % digest, src)
        if n != 1:
            raise SystemExit(
                f"ERROR: key {(shape, border)} matched {n} times, expected 1 "
                f"-- refusing to write a partial update")
    TESTFILE.write_text(src, encoding="utf-8")
    print(f"\nwrote {len(new)} hashes to {TESTFILE}")
    print("Now run: pytest tests/test_golden_shapes.py")


if __name__ == "__main__":
    main()
