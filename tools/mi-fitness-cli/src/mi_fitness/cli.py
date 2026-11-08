"""Typer CLI: mi-fitness / mfp."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Optional

import typer

from mi_fitness import help_text as ht
from mi_fitness import store
from mi_fitness import sync
from mi_fitness.auth import LoginError, login_with_pass_token, login_with_qr
from mi_fitness.client import open_mifit, ping_cloud, request_raw
from mi_fitness.config import (
    ensure_config_dir,
    ensure_data_dir,
    env_pass_token_login,
    import_session_file,
    load_local_session,
    logout_local,
)
from mi_fitness.constants import (
    DB_FILE,
    EXIT_AUTH,
    EXIT_CONFIG,
    EXIT_GENERAL,
    SESSION_FILE,
    SYNC_TYPES,
)
from mi_fitness.onboarding import setup_lines

OPT_JSON_OUTPUT = typer.Option(False, "--json-output", help=ht.OPT_JSON_OUTPUT)
OPT_JSON_ERRORS = typer.Option(False, "--json-errors", help=ht.OPT_JSON_ERRORS)
OPT_DAYS = typer.Option(7, "--days", help="Look back N days when --start-date omitted")

app = typer.Typer(
    rich_markup_mode=None,
    context_settings={"help_option_names": ["-h", "--help"]},
    help=ht.ROOT_HELP,
)

login_app = typer.Typer(help="Log in to Xiaomi Mi Fitness cloud.")
app.add_typer(login_app, name="login")


def _emit(body: Any, *, json_output: bool, status: int = 200, headers: dict | None = None) -> None:
    if json_output:
        typer.echo(
            json.dumps(
                {"status": status, "headers": headers or {}, "body": body},
                ensure_ascii=False,
                indent=2,
            )
        )
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


def _parse_date(raw: str) -> date:
    return date.fromisoformat(raw)


@app.command("setup")
def cmd_setup(json_output: bool = OPT_JSON_OUTPUT) -> None:
    """Onboarding steps."""
    ensure_config_dir()
    ensure_data_dir()
    lines = setup_lines()
    body = {"steps": lines, "session": str(SESSION_FILE), "db": str(DB_FILE)}
    if json_output:
        _emit(body, json_output=True)
    else:
        typer.echo("\n".join(lines))


@app.command("doctor")
def cmd_doctor(json_output: bool = OPT_JSON_OUTPUT) -> None:
    """Check session file and cloud reachability."""
    sess = load_local_session()
    session_ok = sess is not None and sess.is_valid()
    body: dict[str, Any] = {
        "session_path": str(SESSION_FILE),
        "session_ok": session_ok,
        "user_id": sess.user_id if sess else None,
        "region": sess.region if sess else None,
        "can_renew": sess.can_renew() if sess else False,
        "db": store.db_status(),
    }
    if session_ok:
        body["cloud"] = ping_cloud(sess)
    _emit(body, json_output=json_output)


@app.command("status")
def cmd_status(json_output: bool = OPT_JSON_OUTPUT) -> None:
    """Session + database stats."""
    sess = load_local_session()
    body = {
        "logged_in": bool(sess and sess.is_valid()),
        "session_path": str(SESSION_FILE),
        "db": store.db_status(),
    }
    if sess:
        body["user_id"] = sess.user_id
        body["region"] = sess.region
    _emit(body, json_output=json_output)


@app.command("logout")
def cmd_logout(json_output: bool = OPT_JSON_OUTPUT) -> None:
    """Remove local session file."""
    removed = logout_local()
    _emit({"logged_out": removed}, json_output=json_output)


@login_app.callback(invoke_without_command=True)
def login_default(
    ctx: typer.Context,
    pass_token: Optional[str] = typer.Option(None, "--pass-token", help="Cookie passToken"),
    user_id: Optional[str] = typer.Option(None, "--user-id", help="Xiaomi userId"),
    c_user_id: Optional[str] = typer.Option(None, "--c-user-id"),
    region: str = typer.Option("cn", "--region"),
    json_output: bool = OPT_JSON_OUTPUT,
    json_errors: bool = OPT_JSON_ERRORS,
) -> None:
    if ctx.invoked_subcommand is not None:
        return
    try:
        if pass_token and user_id:
            sess = login_with_pass_token(
                user_id=user_id,
                pass_token=pass_token,
                c_user_id=c_user_id or "",
                region=region,
            )
        else:
            env = env_pass_token_login()
            if env and not pass_token:
                sess = login_with_pass_token(
                    user_id=env[0],
                    pass_token=env[1],
                    region=region,
                )
            else:
                sess = login_with_qr()
    except LoginError as exc:
        _fail(str(exc), json_errors=json_errors, code=EXIT_AUTH)
    body = {"ok": True, "user_id": sess.user_id, "region": sess.region}
    _emit(body, json_output=json_output)


@login_app.command("import")
def login_import(
    path: Path,
    json_output: bool = OPT_JSON_OUTPUT,
    json_errors: bool = OPT_JSON_ERRORS,
) -> None:
    """Import session JSON from PATH."""
    try:
        sess = import_session_file(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        _fail(str(exc), json_errors=json_errors, code=EXIT_CONFIG)
    body = {"ok": True, "user_id": sess.user_id, "region": sess.region}
    _emit(body, json_output=json_output)


@app.command("sync")
def cmd_sync(
    start_date: Optional[str] = typer.Option(None, "--start-date", help="YYYY-MM-DD"),
    end_date: Optional[str] = typer.Option(None, "--end-date", help="YYYY-MM-DD"),
    days: int = OPT_DAYS,
    sync_type: Optional[list[str]] = typer.Option(
        None, "--type", help=f"Repeatable: {', '.join(SYNC_TYPES)}"
    ),
    json_output: bool = OPT_JSON_OUTPUT,
    json_errors: bool = OPT_JSON_ERRORS,
) -> None:
    """Pull cloud data into local SQLite."""
    try:
        start = _parse_date(start_date) if start_date else None
        end = _parse_date(end_date) if end_date else None
        s, e = sync.parse_dates(start_date=start, end_date=end, days=days)
        result = sync.sync_range(s, e, list(sync_type) if sync_type else None)
    except Exception as exc:
        _fail(str(exc), json_errors=json_errors, code=EXIT_GENERAL)
    _emit(result, json_output=json_output)


def _query_range(days: int, start: str | None, end: str | None) -> tuple[date, date]:
    end_d = _parse_date(end) if end else date.today()
    if start:
        start_d = _parse_date(start)
    else:
        start_d = end_d - timedelta(days=max(days - 1, 0))
    return start_d, end_d


@app.command("steps")
def cmd_steps(
    days: int = OPT_DAYS,
    start: Optional[str] = typer.Option(None, "--start"),
    end: Optional[str] = typer.Option(None, "--end"),
    json_output: bool = OPT_JSON_OUTPUT,
) -> None:
    since, until = _query_range(days, start, end)
    rows = store.query_steps(since, until)
    _emit({"items": rows, "count": len(rows)}, json_output=json_output)


@app.command("sleep")
def cmd_sleep(
    days: int = OPT_DAYS,
    start: Optional[str] = typer.Option(None, "--start"),
    end: Optional[str] = typer.Option(None, "--end"),
    json_output: bool = OPT_JSON_OUTPUT,
) -> None:
    since, until = _query_range(days, start, end)
    rows = store.query_sleep(since, until)
    _emit({"items": rows, "count": len(rows)}, json_output=json_output)


@app.command("heart-rate")
def cmd_heart_rate(
    days: int = OPT_DAYS,
    start: Optional[str] = typer.Option(None, "--start"),
    end: Optional[str] = typer.Option(None, "--end"),
    json_output: bool = OPT_JSON_OUTPUT,
) -> None:
    since, until = _query_range(days, start, end)
    rows = store.query_heart_rate(since, until)
    _emit({"items": rows, "count": len(rows)}, json_output=json_output)


@app.command("workouts")
def cmd_workouts(
    days: int = OPT_DAYS,
    start: Optional[str] = typer.Option(None, "--start"),
    end: Optional[str] = typer.Option(None, "--end"),
    json_output: bool = OPT_JSON_OUTPUT,
) -> None:
    since, until = _query_range(days, start, end)
    rows = store.query_workouts(since, until)
    _emit({"items": rows, "count": len(rows)}, json_output=json_output)


@app.command("weight")
def cmd_weight(
    days: int = OPT_DAYS,
    start: Optional[str] = typer.Option(None, "--start"),
    end: Optional[str] = typer.Option(None, "--end"),
    full: bool = typer.Option(False, "--full", help="Include body composition fields"),
    json_output: bool = OPT_JSON_OUTPUT,
) -> None:
    since, until = _query_range(days, start, end)
    rows = store.query_weight(since, until, full=full or json_output)
    _emit({"items": rows, "count": len(rows)}, json_output=json_output)


@app.command("request")
def cmd_request(
    path: str = typer.Argument(..., help="API path under app/v1, e.g. data/get_fitness_data_by_time"),
    data_json: str = typer.Option("{}", "--data", help="JSON body object"),
    json_output: bool = OPT_JSON_OUTPUT,
    json_errors: bool = OPT_JSON_ERRORS,
) -> None:
    """Signed GET to Mi Fitness API (debug)."""
    sess = load_local_session()
    if not sess or not sess.is_valid():
        _fail("Not logged in.", json_errors=json_errors, code=EXIT_AUTH)
    try:
        payload = json.loads(data_json)
        if not isinstance(payload, dict):
            raise ValueError("--data must be a JSON object")
        result = request_raw(sess, path, payload)
    except Exception as exc:
        _fail(str(exc), json_errors=json_errors, code=EXIT_GENERAL)
    _emit(result, json_output=json_output)


if __name__ == "__main__":
    app()
