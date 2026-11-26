from __future__ import annotations

import shutil
from pathlib import Path


def build_cursor_argv(*, prompt: str, workspace: Path) -> list[str]:
    exe = shutil.which("cursor") or "cursor"
    return [
        exe,
        "agent",
        "--print",
        "--output-format",
        "text",
        "--force",
        "--workspace",
        str(workspace),
        prompt,
    ]