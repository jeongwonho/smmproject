"""Backend domain modules for the Instamart panel.

The legacy ``core.PanelStore`` remains the compatibility facade used by
``server.py``. New backend work should live in these domain modules first and
be composed into the facade instead of growing ``core.py``.
"""

from __future__ import annotations

from typing import Any


def panel_store_class() -> Any:
    """Return the compatibility facade lazily to avoid import cycles."""

    try:
        from smm_panel.core import PanelStore
    except ImportError:  # pragma: no cover - top-level script runtime
        from core import PanelStore  # type: ignore
    return PanelStore
