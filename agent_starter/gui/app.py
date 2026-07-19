"""Optional desktop GUI launcher for Agent Kit."""

from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Sequence


def static_path() -> Path:
    return Path(__file__).with_name("static") / "index.html"


def run_gui() -> int:
    os.environ.setdefault("WEBKIT_DISABLE_DMABUF_RENDERER", "1")
    try:
        import webview  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("The GUI requires pywebview. Install the optional extra: pip install 'cli-ai-agent-starter-kit[gui]'") from exc

    from ..diagnostics import get_diagnostic_log
    from .bridge import GuiBridge

    webview.create_window(
        "Agent Kit",
        static_path().as_uri(),
        js_api=GuiBridge(diagnostic_logger=get_diagnostic_log()),
        width=1040,
        height=760,
        min_size=(860, 620),
    )
    webview.start()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args in (["-h"], ["--help"]):
        print("usage: agent-starter-gui [-h|--help]")
        print("Open the optional local AgentKit desktop wizard.")
        return 0
    if args:
        print(f"agent-starter-gui: unrecognized argument: {args[0]}", file=sys.stderr)
        return 2
    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
