"""
src/preview.py
--------------
Debounced preview pipeline for the GUI.

PreviewRenderer schedules a low-resolution render 300 ms after the last
request.  Rapid slider/setting changes cancel the pending render so only
the final state triggers actual engine work.
"""
import threading
from typing import Callable


class PreviewRenderer:
    """Fires engine.render_preview() 300 ms after the last request."""

    DEBOUNCE_S = 0.30

    def __init__(self):
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def request(
        self,
        engine,
        input_path: str,
        short_edge: int,
        params: dict,
        on_done: Callable,   # on_done(pil_image)
        on_error: Callable,  # on_error(message: str)
    ):
        """Schedule a preview render, cancelling any pending one."""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(
                self.DEBOUNCE_S,
                self._run,
                args=(engine, input_path, short_edge, params, on_done, on_error),
            )
            self._timer.daemon = True
            self._timer.start()

    def cancel(self):
        """Cancel any pending render immediately."""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None

    def _run(self, engine, input_path, short_edge, params, on_done, on_error):
        try:
            img = engine.render_preview(input_path, short_edge=short_edge, **params)
            on_done(img)
        except Exception as exc:
            on_error(str(exc))
