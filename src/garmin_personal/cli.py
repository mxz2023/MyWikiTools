"""Typer CLI: garmin-personal / gmp."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Annotated, Any, Optional

import httpx
import typer

from garmin_personal import config as cfg_mod
from garmin_personal.auth import api_key_fingerprint
from garmin_personal.client import GarminClient, decode_body, http_exit_code
from garmin_personal.constants import (
    DEFAULT_API_BASE,
    EXIT_CONFIG,
    EXIT_GENERAL,
    EXIT_HTTP_4XX,
    EXIT_HTTP_5XX,
    EXIT_OK,
)
from garmin_personal import help_text as ht

OPT_JSON_OUTPUT = typer.Option(False, "--json-output", help=ht.OPT_JSON_OUTPUT)
OPT_JSON_ERRORS = typer.Option(False, "--json-errors", help=ht.OPT_JSON_ERRORS)
OPT_START_DATE = typer.Option(..., "--start-date", help=ht.OPT_START_DATE)
OPT_END_DATE = typer.Option(..., "--end-date", help=ht.OPT_END_DATE)
OPT_DATE = typer.Option(..., "--date", help=ht.OPT_DATE)

app = typer.Typer(
    rich_markup_mode=None,
    context_settings={"help_option_names": ["-h", "--help"]},
    help=ht.ROOT_HELP,
    epilog="After `pipx install` only: run `gmp setup` for API key steps / 仅用 pipx 安装后请执行 `gmp setup` 查看密钥配置引导。",
)


def _ctx_timeout(ctx: typer.Context) -> float:
    return float(ctx.obj.get("timeout") or 30.0)


def _ctx_profile(ctx: typer.Context) -> str:
    return cfg_mod.resolve_profile(ctx.obj.get("profile"))


def _resolve_api_key(ctx: typer.Context, profile_name: str) -> str:
    if ctx.obj.get("api_key"):
        return str(ctx.obj["api_key"])
    env = os.environ.get("GARMIN_API_KEY")
    if env:
        return env
    prof = cfg_mod.get_profile_config(profile_name)
    key = prof.get("api_key")
    if isinstance(key, str) and key.strip():
        return key.strip()
    typer.echo(
        "No API key: set GARMIN_API_KEY, use --api-key, or `profile add`. / "
        "未配置 API 密钥：请设置 GARMIN_API_KEY、`--api-key` 或使用 `profile add`。",
        err=True,
    )
    raise typer.Exit(EXIT_CONFIG)


def _client_from_ctx(ctx: typer.Context) -> GarminClient:
    name = _ctx_profile(ctx)
    api_key = _resolve_api_key(ctx, name)
    base = cfg_mod.api_base_for_profile(name)
    token_url = cfg_mod.token_url_for_profile(name)
    return GarminClient(
        api_base=base,
        token_url=token_url,
        api_key=api_key,
        profile=name,
        timeout=_ctx_timeout(ctx),
    )


def _print_response(
    resp: httpx.Response,
    *,
    json_output: bool,
    json_errors: bool,
    quiet: bool,
) -> int:
    body = decode_body(resp)
    if json_output:
        out = {
            "status": resp.status_code,
            "headers": dict(resp.headers),
            "body": body,
        }
        typer.echo(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        if body is None:
            if not quiet:
                typer.echo("", nl=False)
        elif isinstance(body, (dict, list)):
            typer.echo(json.dumps(body, ensure_ascii=False, indent=2))
        else:
            typer.echo(str(body))
    if not resp.is_success:
        msg = f"HTTP {resp.status_code} {resp.reason_phrase}"
        if json_errors:
            typer.echo(json.dumps({"error": msg, "text": resp.text[:2000]}), err=True)
        else:
            typer.echo(msg, err=True)
        if 400 <= resp.status_code < 500:
            return EXIT_HTTP_4XX
        if 500 <= resp.status_code < 600:
            return EXIT_HTTP_5XX
        return EXIT_GENERAL
    return EXIT_OK


@app.callback()
def main_callback(
    ctx: typer.Context,
    profile: Annotated[
        Optional[str],
        typer.Option(
            "--profile",
            "-p",
            help="Profile name / 配置档名称 (default from config or 'default').",
        ),
    ] = None,
    api_key: Annotated[
        Optional[str],
        typer.Option(
            "--api-key",
            help="Personal API key (overrides profile). / 个人 API 密钥（覆盖配置档）.",
        ),
    ] = None,
    timeout: Annotated[
        float,
        typer.Option(
            "--timeout",
            "-t",
            help="HTTP timeout seconds / HTTP 超时秒数.",
        ),
    ] = 30.0,
    lang: Annotated[
        str,
        typer.Option(
            "--lang",
            help="Help text language: both | en | zh / help 语言.",
        ),
    ] = "both",
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            "-q",
            help="Less stderr / 减少 stderr 日志.",
        ),
    ] = False,
) -> None:
    """Global options / 全局选项."""
    import garmin_personal.i18n as i18n

    if lang in ("en", "zh", "both"):
        i18n.LANG = lang
    ctx.ensure_object(dict)
    ctx.obj["profile"] = profile
    ctx.obj["api_key"] = api_key
    ctx.obj["timeout"] = timeout
    ctx.obj["quiet"] = quiet


profile_app = typer.Typer(
    help="Manage API key profiles (multi-user) / 管理多用户 API Key（~/.config/garmin-personal）。",
)
app.add_typer(profile_app, name="profile")


@profile_app.command("list")
def profile_list(ctx: typer.Context) -> None:
    """List profile names / 列出配置档."""
    names = cfg_mod.get_profile_names()
    default = cfg_mod.get_default_profile_name()
    for n in names:
        mark = " *" if n == default else ""
        typer.echo(f"{n}{mark}")
    if not names:
        typer.echo("(no profiles) / （无配置档）")


@profile_app.command("add")
def profile_add(
    ctx: typer.Context,
    name: str,
    api_key: str = typer.Argument(..., help="Personal API key / 个人 API 密钥"),
    default: bool = typer.Option(False, "--default", "-d", help="Set as default / 设为默认"),
    api_base: Optional[str] = typer.Option(
        None,
        "--api-base",
        help=f"API base URL (default {DEFAULT_API_BASE}) / API 根地址.",
    ),
    token_url: Optional[str] = typer.Option(
        None,
        "--token-url",
        help="Token endpoint URL (optional) / 换 token 完整 URL（可选）.",
    ),
) -> None:
    """Add or update a profile / 添加或更新配置档."""
    cfg_mod.set_profile(name, api_key, api_base=api_base, token_url=token_url)
    if default:
        cfg_mod.set_default_profile(name)
    if not ctx.obj.get("quiet"):
        typer.echo(f"Saved profile / 已保存配置档: {name}")


@profile_app.command("remove")
def profile_remove(name: str) -> None:
    """Remove a profile / 删除配置档."""
    cfg_mod.remove_profile(name)
    typer.echo(f"Removed / 已删除: {name}")


@profile_app.command("set-default")
def profile_set_default(name: str) -> None:
    """Set default profile / 设置默认配置档."""
    try:
        cfg_mod.set_default_profile(name)
    except KeyError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(EXIT_CONFIG) from e
    typer.echo(f"Default profile / 默认配置档: {name}")


auth_app = typer.Typer(help="Token helpers / 令牌相关.")
app.add_typer(auth_app, name="auth")


@auth_app.command("print-token")
def auth_print_token(
    ctx: typer.Context,
    refresh: bool = typer.Option(False, "--refresh", help="Force new token / 强制刷新令牌"),
) -> None:
    """Print cached or new bearer token (debug) / 打印访问令牌（调试）."""
    name = _ctx_profile(ctx)
    c = _client_from_ctx(ctx)
    try:
        typer.echo(c.access_token(refresh=refresh))
    finally:
        c.close()


@app.command("request", help=ht.SHORT["request"])
def request_cmd(
    ctx: typer.Context,
    method: str = typer.Argument(..., help="HTTP method GET|POST|PUT|DELETE / HTTP 方法"),
    path: str = typer.Argument(
        ...,
        help="Path under API base, e.g. /userprofile-service/... / 相对 API 根的路径",
    ),
    json_output: bool = OPT_JSON_OUTPUT,
    json_errors: bool = OPT_JSON_ERRORS,
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Write raw body to file (binary OK) / 将原始响应写入文件.",
    ),
) -> None:
    """Call any Personal API path (method + path). / 任意 API 路径。

    HTTP: METHOD {api_base}/path (see --profile / GARMIN_API_BASE for host)

    Example / 示例:
      gmp request GET /userprofile-service/userprofile/settings
      gmp request GET /usersummary-service/stats/steps/daily/2025-11-01/2025-11-07 --json-output
    """
    path = path.strip()
    if not path.startswith("/") and not path.startswith("?"):
        path = "/" + path
    client = _client_from_ctx(ctx)
    try:
        resp = client.request(method, path)
        if output is not None:
            output.write_bytes(resp.content)
            if not ctx.obj.get("quiet"):
                typer.echo(str(output))
            code = EXIT_OK if resp.is_success else http_exit_code(resp.status_code)
            raise typer.Exit(code)
        code = _print_response(
            resp,
            json_output=json_output,
            json_errors=json_errors,
            quiet=bool(ctx.obj.get("quiet")),
        )
        raise typer.Exit(code)
    finally:
        client.close()


def _conv_request(
    ctx: typer.Context,
    path: str,
    params: dict[str, Any] | None,
    json_output: bool,
    json_errors: bool,
    output: Optional[Path],
) -> None:
    client = _client_from_ctx(ctx)
    try:
        q = ""
        if params:
            from urllib.parse import urlencode

            q = "?" + urlencode({k: v for k, v in params.items() if v is not None})
        resp = client.request("GET", path + q)
        if output is not None:
            output.write_bytes(resp.content)
            if not ctx.obj.get("quiet"):
                typer.echo(str(output))
            code = EXIT_OK if resp.is_success else http_exit_code(resp.status_code)
            raise typer.Exit(code)
        code = _print_response(
            resp,
            json_output=json_output,
            json_errors=json_errors,
            quiet=bool(ctx.obj.get("quiet")),
        )
        raise typer.Exit(code)
    finally:
        client.close()


def data_command(name: str):
    """Register a convenience GET command with bilingual help."""

    def outer(fn):
        http = ht.HTTP.get(name, "GET (see source)")
        ex = ht.EXAMPLE.get(name, f"gmp {name} --help")
        fn.__doc__ = ht.long_doc(name, http, ex)
        return app.command(name)(fn)

    return outer


# --- Convenience commands (names match official gc-personal where applicable) ---


@data_command("steps")
def cmd_steps(
    ctx: typer.Context,
    start_date: str = OPT_START_DATE,
    end_date: str = OPT_END_DATE,
    json_output: bool = OPT_JSON_OUTPUT,
    json_errors: bool = OPT_JSON_ERRORS,
) -> None:
    p = f"/usersummary-service/stats/steps/daily/{start_date}/{end_date}"
    _conv_request(ctx, p, None, json_output, json_errors, None)


@data_command("stress")
def cmd_stress(
    ctx: typer.Context,
    start_date: str = OPT_START_DATE,
    end_date: str = OPT_END_DATE,
    json_output: bool = OPT_JSON_OUTPUT,
    json_errors: bool = OPT_JSON_ERRORS,
) -> None:
    p = f"/usersummary-service/stats/stress/daily/{start_date}/{end_date}"
    _conv_request(ctx, p, None, json_output, json_errors, None)


@data_command("hydration")
def cmd_hydration(
    ctx: typer.Context,
    start_date: str = OPT_START_DATE,
    end_date: str = OPT_END_DATE,
    json_output: bool = OPT_JSON_OUTPUT,
    json_errors: bool = OPT_JSON_ERRORS,
) -> None:
    p = f"/usersummary-service/stats/hydration/daily/{start_date}/{end_date}"
    _conv_request(ctx, p, None, json_output, json_errors, None)


@data_command("effective-weight-goals")
def cmd_ewg(
    ctx: typer.Context,
    start_date: str = OPT_START_DATE,
    end_date: str = OPT_END_DATE,
    json_output: bool = OPT_JSON_OUTPUT,
    json_errors: bool = OPT_JSON_ERRORS,
) -> None:
    p = f"/goal-service/goal/user/effective/weightgoal/{start_date}/{end_date}"
    _conv_request(ctx, p, None, json_output, json_errors, None)


@data_command("weight-measurements")
def cmd_wm(
    ctx: typer.Context,
    start_date: str = OPT_START_DATE,
    end_date: str = OPT_END_DATE,
    json_output: bool = OPT_JSON_OUTPUT,
    json_errors: bool = OPT_JSON_ERRORS,
) -> None:
    p = f"/weight-service/weight/range/{start_date}/{end_date}?includeAll=true"
    _conv_request(ctx, p, None, json_output, json_errors, None)


@data_command("food-logs")
def cmd_food(
    ctx: typer.Context,
    date: str = OPT_DATE,
    json_output: bool = OPT_JSON_OUTPUT,
    json_errors: bool = OPT_JSON_ERRORS,
) -> None:
    p = f"/nutrition-service/food/logs/{date}"
    _conv_request(ctx, p, None, json_output, json_errors, None)


@data_command("profile-settings")
def cmd_ps(
    ctx: typer.Context,
    json_output: bool = OPT_JSON_OUTPUT,
    json_errors: bool = OPT_JSON_ERRORS,
) -> None:
    _conv_request(ctx, "/userprofile-service/userprofile/settings", None, json_output, json_errors, None)


@data_command("sleep")
def cmd_sleep(
    ctx: typer.Context,
    date: str = OPT_DATE,
    json_output: bool = OPT_JSON_OUTPUT,
    json_errors: bool = OPT_JSON_ERRORS,
) -> None:
    p = f"/sleep-service/sleep/dailySleep?date={date}"
    _conv_request(ctx, p, None, json_output, json_errors, None)


@data_command("sleep-summaries")
def cmd_sleep_sum(
    ctx: typer.Context,
    start_date: str = OPT_START_DATE,
    end_date: str = OPT_END_DATE,
    json_output: bool = OPT_JSON_OUTPUT,
    json_errors: bool = OPT_JSON_ERRORS,
) -> None:
    p = f"/sleep-service/sleep/dailySleepSummariesByDate?startDate={start_date}&endDate={end_date}"
    _conv_request(ctx, p, None, json_output, json_errors, None)


@data_command("body-battery")
def cmd_bb(
    ctx: typer.Context,
    start_date: str = OPT_START_DATE,
    end_date: str = OPT_END_DATE,
    chunks: Optional[int] = typer.Option(
        None, "--chunks", help="Optional chunk count / 可选分块数量"
    ),
    json_output: bool = OPT_JSON_OUTPUT,
    json_errors: bool = OPT_JSON_ERRORS,
) -> None:
    params = {"startDate": start_date, "endDate": end_date}
    if chunks is not None:
        params["chunks"] = str(chunks)
    from urllib.parse import urlencode

    q = "?" + urlencode(params)
    _conv_request(ctx, "/wellness-service/wellness/bodyBattery/reports/daily" + q, None, json_output, json_errors, None)


@data_command("daily-summaries")
def cmd_ds(
    ctx: typer.Context,
    start_date: str = OPT_START_DATE,
    end_date: str = OPT_END_DATE,
    json_output: bool = OPT_JSON_OUTPUT,
    json_errors: bool = OPT_JSON_ERRORS,
) -> None:
    p = f"/usersummary-service/v2/dailysummaries?startDate={start_date}&endDate={end_date}"
    _conv_request(ctx, p, None, json_output, json_errors, None)


@data_command("heart-rate")
def cmd_hr(
    ctx: typer.Context,
    date: str = OPT_DATE,
    json_output: bool = OPT_JSON_OUTPUT,
    json_errors: bool = OPT_JSON_ERRORS,
) -> None:
    p = f"/wellness-service/wellness/dailyHeartRate?date={date}"
    _conv_request(ctx, p, None, json_output, json_errors, None)


@data_command("hrv")
def cmd_hrv(
    ctx: typer.Context,
    date: str = OPT_DATE,
    json_output: bool = OPT_JSON_OUTPUT,
    json_errors: bool = OPT_JSON_ERRORS,
) -> None:
    p = f"/hrv-service/hrv/{date}"
    _conv_request(ctx, p, None, json_output, json_errors, None)


@data_command("hrv-summaries")
def cmd_hrvs(
    ctx: typer.Context,
    start_date: str = OPT_START_DATE,
    end_date: str = OPT_END_DATE,
    json_output: bool = OPT_JSON_OUTPUT,
    json_errors: bool = OPT_JSON_ERRORS,
) -> None:
    p = f"/hrv-service/hrv/daily/{start_date}/{end_date}"
    _conv_request(ctx, p, None, json_output, json_errors, None)


@data_command("heart-rate-zones")
def cmd_hrz(
    ctx: typer.Context,
    json_output: bool = OPT_JSON_OUTPUT,
    json_errors: bool = OPT_JSON_ERRORS,
) -> None:
    _conv_request(ctx, "/biometric-service/heartRateZones/v2", None, json_output, json_errors, None)


@data_command("menstrual-cycle-summary")
def cmd_mcs(
    ctx: typer.Context,
    date: str = OPT_DATE,
    json_output: bool = OPT_JSON_OUTPUT,
    json_errors: bool = OPT_JSON_ERRORS,
) -> None:
    p = f"/periodichealth-service/menstrualcycle/summary/{date}"
    _conv_request(ctx, p, None, json_output, json_errors, None)


@data_command("menstrual-cycle-day-view")
def cmd_mcd(
    ctx: typer.Context,
    date: str = OPT_DATE,
    today_date: str = typer.Option(..., "--today-date", help="Today YYYY-MM-DD / 当天日期"),
    json_output: bool = OPT_JSON_OUTPUT,
    json_errors: bool = OPT_JSON_ERRORS,
) -> None:
    p = f"/periodichealth-service/menstrualcycle/dayview/{date}?todayDate={today_date}"
    _conv_request(ctx, p, None, json_output, json_errors, None)


@data_command("fitness-age")
def cmd_fa(
    ctx: typer.Context,
    date: str = OPT_DATE,
    json_output: bool = OPT_JSON_OUTPUT,
    json_errors: bool = OPT_JSON_ERRORS,
) -> None:
    p = f"/fitnessage-service/fitnessage/v2/{date}"
    _conv_request(ctx, p, None, json_output, json_errors, None)


@data_command("spo2")
def cmd_spo2(
    ctx: typer.Context,
    date: str = OPT_DATE,
    json_output: bool = OPT_JSON_OUTPUT,
    json_errors: bool = OPT_JSON_ERRORS,
) -> None:
    p = f"/wellness-service/wellness/daily/spo2acclimation/{date}"
    _conv_request(ctx, p, None, json_output, json_errors, None)


@data_command("wellness-activity-summaries")
def cmd_was(
    ctx: typer.Context,
    start_date: str = OPT_START_DATE,
    end_date: str = OPT_END_DATE,
    json_output: bool = OPT_JSON_OUTPUT,
    json_errors: bool = OPT_JSON_ERRORS,
) -> None:
    p = f"/wellnessactivity-service/activity/summary/range/{start_date}/{end_date}"
    _conv_request(ctx, p, None, json_output, json_errors, None)


@data_command("activities")
def cmd_activities(
    ctx: typer.Context,
    start: int = typer.Option(0, "--start", help="Offset for pagination / 分页起始偏移"),
    limit: int = typer.Option(20, "--limit", help="Page size / 每页条数"),
    start_date: Optional[str] = typer.Option(None, "--start-date", help=ht.OPT_START_DATE),
    end_date: Optional[str] = typer.Option(None, "--end-date", help=ht.OPT_END_DATE),
    activity_type: Optional[str] = typer.Option(
        None, "--activity-type", help="Garmin activity type filter / 活动类型筛选"
    ),
    json_output: bool = OPT_JSON_OUTPUT,
    json_errors: bool = OPT_JSON_ERRORS,
) -> None:
    params = {
        "start": str(start),
        "limit": str(limit),
        "startDate": start_date,
        "endDate": end_date,
        "activityType": activity_type,
    }
    from urllib.parse import urlencode

    q = "?" + urlencode({k: v for k, v in params.items() if v is not None})
    _conv_request(ctx, "/activitylist-service/activities/search/activities" + q, None, json_output, json_errors, None)


@data_command("activity")
def cmd_activity(
    ctx: typer.Context,
    activity_id: int = typer.Argument(..., help="Garmin activity ID / 活动 ID"),
    json_output: bool = OPT_JSON_OUTPUT,
    json_errors: bool = OPT_JSON_ERRORS,
) -> None:
    p = f"/activity-service/activity/{activity_id}"
    _conv_request(ctx, p, None, json_output, json_errors, None)


@data_command("activity-workouts")
def cmd_aw(
    ctx: typer.Context,
    activity_id: int = typer.Argument(..., help="Garmin activity ID / 活动 ID"),
    json_output: bool = OPT_JSON_OUTPUT,
    json_errors: bool = OPT_JSON_ERRORS,
) -> None:
    p = f"/activity-service/activity/{activity_id}/workouts"
    _conv_request(ctx, p, None, json_output, json_errors, None)


@data_command("activity-download")
def cmd_ad(
    ctx: typer.Context,
    activity_id: int = typer.Argument(..., help="Garmin activity ID / 活动 ID"),
    output: Path = typer.Option(
        ...,
        "--output",
        "-o",
        help="Output .zip path / 输出 zip 路径",
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite / 覆盖已存在文件"),
    json_output: bool = OPT_JSON_OUTPUT,
    json_errors: bool = OPT_JSON_ERRORS,
) -> None:
    if output.exists() and not force:
        typer.echo(f"Refusing to overwrite (use --force): {output}", err=True)
        raise typer.Exit(EXIT_GENERAL)
    _conv_request(
        ctx, f"/download-service/files/activity/{activity_id}", None, json_output, json_errors, output
    )


@app.command("setup", help=ht.SHORT["setup"])
def cmd_setup() -> None:
    """Post-install: Personal API key URL and `gmp profile add` / 安装后申请 Key 并写入 profile。

    Run after `pipx install` (install.sh runs this automatically).
    pipx 安装后请执行（install.sh 会自动调用）。
    """
    from garmin_personal.onboarding import onboarding_text

    typer.echo(onboarding_text())


@app.command("version", help=ht.SHORT["version"])
def cmd_version() -> None:
    """Show garmin-personal-cli package version / 显示包版本号。"""
    from garmin_personal import __version__

    typer.echo(__version__)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
