"""Optional desktop GUI launcher for Agent Kit."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Sequence

from .bridge import GuiBridge


def static_path() -> Path:
    return Path(__file__).with_name("static") / "index.html"


def run_gui() -> int:
    os.environ.setdefault("WEBKIT_DISABLE_DMABUF_RENDERER", "1")
    try:
        import webview  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("The GUI requires pywebview. Install the optional extra: pip install 'cli-ai-agent-starter-kit[gui]'") from exc

    webview.create_window(
        "Agent Kit",
        static_path().as_uri(),
        js_api=GuiBridge(),
        width=1040,
        height=760,
        min_size=(860, 620),
    )
    webview.start()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
