"""Typer CLI: apple-health / ahp — receive iPhone health data, query SQLite cache."""

from __future__ import annotations

import json
import platform
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Any, Optional

import typer

from apple_health import import_xml, store
from apple_health.config import ensure_data_dirs
from apple_health.constants import EXIT_CONFIG, EXIT_GENERAL
from apple_health.serve import IngestServer, default_token
from apple_health.watch import default_watch_dir, scan_once, watch_loop

OPT_JSON_OUTPUT = typer.Option(False, "--json-output", help="Emit JSON envelope on stdout")
OPT_JSON_ERRORS = typer.Option(False, "--json-errors", help="Emit JSON errors on stderr")
OPT_START = typer.Option(None, "--start", help="Range start (ISO8601 UTC)")
OPT_END = typer.Option(None, "--end", help="Range end (ISO8601 UTC)")
OPT_DAYS = typer.Option(7, "--days", help="When --start omitted, look back N days")

app = typer.Typer(
    rich_markup_mode=None,
    context_settings={"help_option_names": ["-h", "--help"]},
    help="Receive Apple Watch data via iPhone (AHPSync) and query local SQLite cache.",
    epilog="Run `ahp serve` on Mac and sync from the AHPSync iOS app.",
)


def _emit(body: Any, *, json_output: bool, status: int = 200) -> None:
    if json_output:
        typer.echo(json.dumps({"status": status, "body": body}, ensure_ascii=False, indent=2))
    elif isinstance(body, (dict, list)):
        typer.echo(json.dumps(body, ensure_ascii=False, indent=2))
    else:
        typer.echo(str(body))


def _fail(msg: str, *, json_errors: bool, code: int) -> None:
    if json_errors:
        typer.echo(json.dumps({"error": msg}, ensure_ascii=False), err=True)
    else:
        typer.echo(msg, err=True)
    raise typer.Exit(code)


def _parse_bound(raw: str | None, default: datetime) -> datetime:
    if not raw:
        return default
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    return datetime.fromisoformat(raw)


@app.callback()
def main_callback() -> None:
    """Global options (none yet)."""
    return


@app.command("setup")
def cmd_setup(json_output: bool = OPT_JSON_OUTPUT) -> None:
    """Onboarding: AHPSync + serve + optional import/watch."""
    ensure_data_dirs()
    lines = [
        "Apple Health CLI (ahp)",
        "",
        "1) Mac: export AHP_INGEST_TOKEN=… && ahp serve --host 0.0.0.0",
        "2) iPhone: build AHPSync from tools/apple-health-cli/ios/ (see ios/README.zh.md)",
        "3) Query: ahp steps --days 7 --json-output",
        "",
        "Optional: ahp import export.xml | ahp watch (iCloud folder)",
        "",
        f"Local DB: {store.DB_FILE}",
        f"Docs: tools/apple-health-cli/docs/AHPSYNC_SETUP.zh.md",
    ]
    _emit({"steps": lines, "db_path": str(store.DB_FILE)} if json_output else "\n".join(lines), json_output=json_output)


@app.command("doctor")
def cmd_doctor(json_output: bool = OPT_JSON_OUTPUT) -> None:
    """Which commands apply on this machine."""
    body = {
        "platform": platform.platform(),
        "sync_path": "iPhone AHPSync → ahp serve → SQLite",
        "works_on_mac": [
            "serve",
            "watch",
            "import",
            "status",
            "steps",
            "heart-rate",
            "sleep",
            "workouts",
        ],
        "ios_app": "tools/apple-health-cli/ios/AHPSync.xcodeproj",
    }
    _emit(body, json_output=json_output)


@app.command("serve")
def cmd_serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Listen address; use 0.0.0.0 for iPhone on LAN"),
    port: int = typer.Option(8765, "--port"),
    token: Optional[str] = typer.Option(None, "--token", help="Bearer token (default: AHP_INGEST_TOKEN or random)"),
    json_output: bool = OPT_JSON_OUTPUT,
) -> None:
    """Run ingest HTTP server (AHPSync POST JSON/XML)."""
    tok = (token or default_token()).strip()
    body = {
        "listening": f"http://{host}:{port}",
        "health": f"http://{host}:{port}/v1/health",
        "ahpsync_url": f"http://{host}:{port}/api/ingest",
        "ingest_json": f"http://{host}:{port}/v1/ingest",
        "ingest_xml": f"http://{host}:{port}/v1/import-xml",
        "auth_header": "Bearer <token> | X-AHP-Token | api-key",
        "token": tok,
    }
    if json_output:
        _emit(body, json_output=True)
    else:
        typer.echo("AHP ingest server (Ctrl+C to stop)")
        typer.echo(f"  AHPSync URL: {body['ahpsync_url']}")
        typer.echo(f"  Token: {tok}")
        if host == "127.0.0.1":
            typer.echo("  Tip: iPhone on Wi‑Fi needs --host 0.0.0.0 and Mac firewall allow.")
    server = IngestServer(host, port, tok)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        typer.echo("stopped.", err=True)


@app.command("watch")
def cmd_watch(
    path: Annotated[
        Optional[Path],
        typer.Option("--dir", help="Folder to watch (default: iCloud Drive/AHP)"),
    ] = None,
    interval: float = typer.Option(60.0, "--interval", help="Seconds between scans (daemon mode)"),
    once: bool = typer.Option(False, "--once", help="Scan once and exit"),
    force: bool = typer.Option(False, "--force", help="Re-import all files"),
    json_output: bool = OPT_JSON_OUTPUT,
) -> None:
    """Auto-import new export.xml / ingest.json dropped into a folder."""
    watch_dir = path.expanduser() if path else default_watch_dir()
    if once:
        batch = scan_once(watch_dir, force=force)
        _emit({"dir": str(watch_dir), "imported": batch}, json_output=json_output)
        return
    typer.echo(f"Watching {watch_dir} every {interval}s (Ctrl+C to stop)")
    watch_dir.mkdir(parents=True, exist_ok=True)
    try:
        watch_loop(watch_dir, interval, on_batch=lambda b: typer.echo(f"imported {len(b)} file(s)"))
    except KeyboardInterrupt:
        typer.echo("stopped.", err=True)


@app.command("status")
def cmd_status(json_output: bool = OPT_JSON_OUTPUT) -> None:
    """Local SQLite cache stats."""
    body = {"platform": platform.platform(), "cache": store.db_stats()}
    _emit(body, json_output=json_output)


@app.command("import")
def cmd_import(
    path: Annotated[Path, typer.Argument(help="export.xml from iPhone Health export")],
    force: bool = typer.Option(False, "--force", help="Re-import even if file unchanged"),
    json_output: bool = OPT_JSON_OUTPUT,
    json_errors: bool = OPT_JSON_ERRORS,
) -> None:
    """Import Apple Health export.xml (one-time bulk)."""
    try:
        body = import_xml.import_export_xml(path, force=force)
    except FileNotFoundError:
        _fail(f"File not found: {path}", json_errors=json_errors, code=EXIT_CONFIG)
    except OSError as e:
        _fail(str(e), json_errors=json_errors, code=EXIT_GENERAL)
    _emit(body, json_output=json_output)


def _query_range(start: str | None, end: str | None, days: int) -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    end_dt = _parse_bound(end, now)
    start_dt = _parse_bound(start, end_dt - timedelta(days=days))
    return start_dt.isoformat(), end_dt.isoformat()


@app.command("steps")
def cmd_steps(
    json_output: bool = OPT_JSON_OUTPUT,
    start: Optional[str] = OPT_START,
    end: Optional[str] = OPT_END,
    days: int = OPT_DAYS,
) -> None:
    """Query cached step samples."""
    s, e = _query_range(start, end, days)
    rows = store.query_quantities("steps", s, e)
    _emit({"samples": rows, "total_steps": sum(r["value"] for r in rows)}, json_output=json_output)


@app.command("heart-rate")
def cmd_heart_rate(
    json_output: bool = OPT_JSON_OUTPUT,
    start: Optional[str] = OPT_START,
    end: Optional[str] = OPT_END,
    days: int = OPT_DAYS,
) -> None:
    """Query cached heart rate samples."""
    s, e = _query_range(start, end, days)
    rows = store.query_quantities("heart_rate", s, e)
    _emit({"samples": rows}, json_output=json_output)


@app.command("sleep")
def cmd_sleep(
    json_output: bool = OPT_JSON_OUTPUT,
    start: Optional[str] = OPT_START,
    end: Optional[str] = OPT_END,
    days: int = OPT_DAYS,
) -> None:
    """Query cached sleep segments."""
    s, e = _query_range(start, end, days)
    rows = store.query_categories("sleep", s, e)
    _emit({"segments": rows}, json_output=json_output)


@app.command("workouts")
def cmd_workouts(
    json_output: bool = OPT_JSON_OUTPUT,
    start: Optional[str] = OPT_START,
    end: Optional[str] = OPT_END,
    days: int = OPT_DAYS,
) -> None:
    """Query cached workouts."""
    s, e = _query_range(start, end, days)
    rows = store.query_workouts(s, e)
    _emit({"workouts": rows}, json_output=json_output)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
