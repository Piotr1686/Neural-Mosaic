"""
src/preview.py
--------------
Debounced preview pipeline for the GUI.

PreviewRenderer schedules a low-resolution render 300 ms after the last
request.  Rapid slider/setting changes cancel the pending render so only
the final state triggers actual engine work.

Każde żądanie dostaje rosnący numer generacji.  Render trwający już na
wątku Timera nie da się anulować przez ``Timer.cancel()`` (debounce chroni
tylko oczekujący timer), więc po jego zakończeniu sprawdzamy, czy nasza
generacja jest wciąż aktualna.  Jeśli w międzyczasie pojawiło się nowsze
żądanie, wynik jest odrzucany — to zapobiega nadpisaniu podglądu starszym,
nieaktualnym obrazem (stale-result race).
"""
import logging
import threading
from typing import Callable

logger = logging.getLogger(__name__)


class PreviewRenderer:
    """Fires engine.render_preview() 300 ms after the last request."""

    DEBOUNCE_S = 0.30

    def __init__(self):
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()
        self._generation = 0

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
            self._generation += 1
            gen = self._generation
            self._timer = threading.Timer(
                self.DEBOUNCE_S,
                self._run,
                args=(gen, engine, input_path, short_edge, params, on_done, on_error),
            )
            self._timer.daemon = True
            self._timer.start()

    def cancel(self):
        """Cancel any pending render immediately."""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
            # Bump generacji unieważnia też render już trwający na wątku Timera.
            self._generation += 1

    def _is_current(self, gen: int) -> bool:
        """True tylko gdy ``gen`` to wciąż najnowsza wystawiona generacja."""
        with self._lock:
            return gen == self._generation

    def _run(self, gen, engine, input_path, short_edge, params, on_done, on_error):
        try:
            img = engine.render_preview(input_path, short_edge=short_edge, **params)
        except Exception as exc:
            if self._is_current(gen):
                on_error(str(exc))
            else:
                logger.debug("Odrzucono stale on_error (gen=%s): %s", gen, exc)
            return

        if self._is_current(gen):
            on_done(img)
        else:
            logger.debug("Odrzucono stale on_done (gen=%s)", gen)
