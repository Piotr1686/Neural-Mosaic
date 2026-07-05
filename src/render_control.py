"""Shared render-control primitives for both mosaic engines.

Lives in its own module so SmartEngine, TypoEngine and the GUI can all import
the same exception without the engines importing each other.
"""


class RenderCancelled(Exception):
    """Raised inside a render loop when the caller's cancel_event is set.

    The engines poll the optional ``cancel_event`` (a ``threading.Event``) at
    loop boundaries and raise this to abort. ``create_mosaic``/``process``
    never reach their save step, so a cancelled render writes no output file.
    """
