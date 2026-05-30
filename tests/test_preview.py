"""Regression tests for src/preview.py (PreviewRenderer generation token).

Covers the stale-result race fixed on 2026-05-30: a render already running
on the Timer thread cannot be stopped by Timer.cancel(), so its result must
be discarded once a newer request has superseded it.
"""
import threading

import pytest

from src.preview import PreviewRenderer


class _ImmediateEngine:
    """render_preview returns at once, tagging the result with short_edge."""

    def render_preview(self, path, short_edge=0, **kw):
        return f"img(edge={short_edge})"


class _BlockingEngine:
    """render_preview blocks until released, signalling when it has started.

    Lets a test deterministically interleave two renders: start the slow one,
    fire a superseding request, then release the slow one and assert its
    result is dropped.
    """

    def __init__(self):
        self.started = threading.Event()
        self.release = threading.Event()

    def render_preview(self, path, short_edge=0, **kw):
        self.started.set()
        if not self.release.wait(timeout=5.0):
            raise TimeoutError("release event never set")
        return f"img(edge={short_edge})"


class _RaisingEngine:
    def render_preview(self, path, short_edge=0, **kw):
        raise ValueError("boom")


def _fast_renderer():
    r = PreviewRenderer()
    r.DEBOUNCE_S = 0.01
    return r


def test_basic_render_delivers():
    """A single request delivers the rendered image via on_done."""
    done = threading.Event()
    out = {}

    def on_done(img):
        out["img"] = img
        done.set()

    r = _fast_renderer()
    r.request(_ImmediateEngine(), "p", short_edge=450, params={},
              on_done=on_done, on_error=lambda m: None)

    assert done.wait(timeout=5.0), "on_done was never called"
    assert out["img"] == "img(edge=450)"


def test_stale_render_dropped():
    """A slow render superseded by a newer request must not call on_done."""
    slow = _BlockingEngine()
    results = []
    fast_done = threading.Event()

    def slow_done(img):
        results.append(("slow", img))

    def fast_done_cb(img):
        results.append(("fast", img))
        fast_done.set()

    r = _fast_renderer()
    # Request 1: slow render. Wait until it is actually running on its thread.
    r.request(slow, "p", short_edge=1800, params={},
              on_done=slow_done, on_error=lambda m: None)
    assert slow.started.wait(timeout=5.0), "slow render never started"

    # Request 2 supersedes request 1 while the latter is still in flight.
    r.request(_ImmediateEngine(), "p", short_edge=450, params={},
              on_done=fast_done_cb, on_error=lambda m: None)
    assert fast_done.wait(timeout=5.0), "fast render never delivered"

    # Now let the stale slow render finish; its result must be discarded.
    slow.release.set()
    # Give the slow thread a moment to attempt (and fail) delivery.
    threading.Event().wait(0.2)

    assert ("slow", "img(edge=1800)") not in results, "stale render leaked"
    assert ("fast", "img(edge=450)") in results


def test_error_propagated_when_current():
    """An engine exception on the current generation reaches on_error."""
    err = threading.Event()
    out = {}

    def on_error(msg):
        out["msg"] = msg
        err.set()

    r = _fast_renderer()
    r.request(_RaisingEngine(), "p", short_edge=450, params={},
              on_done=lambda i: None, on_error=on_error)

    assert err.wait(timeout=5.0), "on_error was never called"
    assert "boom" in out["msg"]


def test_cancel_invalidates_inflight_render():
    """cancel() bumps the generation so an in-flight render is discarded."""
    slow = _BlockingEngine()
    results = []

    r = _fast_renderer()
    r.request(slow, "p", short_edge=1800, params={},
              on_done=lambda img: results.append(img), on_error=lambda m: None)
    assert slow.started.wait(timeout=5.0), "slow render never started"

    r.cancel()
    slow.release.set()
    threading.Event().wait(0.2)

    assert results == [], "cancelled render should not deliver a result"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
