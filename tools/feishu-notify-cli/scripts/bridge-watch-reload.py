#!/usr/bin/env python3
"""Watch feishu-notify-cli sources and kickstart the launchd bridge after saves."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_WATCH = (
    _REPO_ROOT / "src" / "feishu_notify",
    _REPO_ROOT / "tests",
)
_LABEL = "com.fnotify.bridge"

# Runtime files under ~/.config/fnotify must not trigger reload (runs.json updates every card patch).
_RUNTIME_SKIP_NAMES = frozenset(
    {
        "runs.json",
        "dispatched_messages.json",
    }
)


def _iter_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    if not root.is_dir():
        return []
    out: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.name in _RUNTIME_SKIP_NAMES:
            continue
        if path.parent.name == "logs":
            continue
        if path.suffix in {".py", ".yaml", ".yml", ".j2", ".json", ".gif"}:
            out.append(path)
    return out


def snapshot(roots: tuple[Path, ...]) -> dict[str, float]:
    mtimes: dict[str, float] = {}
    for root in roots:
        for path in _iter_files(root):
            try:
                mtimes[str(path)] = path.stat().st_mtime
            except OSError:
                continue
    return mtimes


def kickstart_bridge(*, dry_run: bool = False) -> int:
    target = f"gui/{os.getuid()}/{_LABEL}"
    if dry_run:
        print(f"[bridge-watch] dry-run: launchctl kickstart -k {target}", flush=True)
        return 0
    proc = subprocess.run(
        ["launchctl", "kickstart", "-k", target],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        print(f"[bridge-watch] kickstart failed ({proc.returncode}): {err}", file=sys.stderr)
        return proc.returncode
    print(f"[bridge-watch] reloaded {target}", flush=True)
    return 0


def run_loop(
    roots: tuple[Path, ...],
    *,
    poll_sec: float,
    debounce_sec: float,
    dry_run: bool,
) -> int:
    roots = tuple(p.resolve() for p in roots)
    missing = [p for p in roots if not p.exists()]
    if missing:
        for p in missing:
            print(f"[bridge-watch] skip missing path: {p}", file=sys.stderr)
    roots = tuple(p for p in roots if p.exists())
    if not roots:
        print("[bridge-watch] nothing to watch", file=sys.stderr)
        return 1

    print(
        "[bridge-watch] watching (Ctrl+C to stop); "
        f"poll={poll_sec}s debounce={debounce_sec}s",
        flush=True,
    )
    for p in roots:
        print(f"  - {p}", flush=True)

    last = snapshot(roots)
    changed_at: float | None = None
    while True:
        time.sleep(poll_sec)
        cur = snapshot(roots)
        if cur != last:
            last = cur
            changed_at = time.monotonic()
            continue
        if changed_at is not None and (time.monotonic() - changed_at) >= debounce_sec:
            kickstart_bridge(dry_run=dry_run)
            changed_at = None
            last = snapshot(roots)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Reload com.fnotify.bridge launchd job when feishu-notify-cli sources change.",
    )
    parser.add_argument(
        "--poll",
        type=float,
        default=0.6,
        help="Seconds between mtime scans (default: 0.6)",
    )
    parser.add_argument(
        "--debounce",
        type=float,
        default=1.5,
        help="Wait after last change before kickstart (default: 1.5)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print kickstart only, do not reload daemon",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Extra directories to watch (default: src/feishu_notify, tests)",
    )
    args = parser.parse_args(argv)
    roots = _DEFAULT_WATCH + tuple(args.paths)
    try:
        run_loop(
            roots,
            poll_sec=max(0.2, args.poll),
            debounce_sec=max(0.3, args.debounce),
            dry_run=args.dry_run,
        )
    except KeyboardInterrupt:
        print("\n[bridge-watch] stopped", flush=True)
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())