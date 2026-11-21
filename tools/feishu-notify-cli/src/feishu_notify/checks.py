from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from feishu_notify.config import CONFIG_FILE, load_config
from feishu_notify.lark_status import fetch_auth_status, identity_summary, lark_cli_path


@dataclass
class CheckItem:
    id: str
    title: str
    ok: bool
    detail: str
    fix: str = ""


@dataclass
class DoctorReport:
    ok: bool
    items: list[CheckItem] = field(default_factory=list)
    config_path: str = str(CONFIG_FILE)
    lark_auth: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "config_path": self.config_path,
            "items": [
                {"id": i.id, "title": i.title, "ok": i.ok, "detail": i.detail, "fix": i.fix}
                for i in self.items
            ],
            "lark": self.lark_auth,
        }


def run_doctor() -> DoctorReport:
    items: list[CheckItem] = []

    path = lark_cli_path()
    if not path:
        items.append(
            CheckItem(
                id="lark_cli",
                title="lark-cli 已安装",
                ok=False,
                detail="未在 PATH 中找到 lark-cli",
                fix="安装 lark-cli 并确保在 shell 的 PATH 中",
            )
        )
        return DoctorReport(ok=False, items=items)

    items.append(
        CheckItem(
            id="lark_cli",
            title="lark-cli 已安装",
            ok=True,
            detail=path,
            fix="",
        )
    )

    status, err = fetch_auth_status()
    if err or not status:
        items.append(
            CheckItem(
                id="lark_auth",
                title="lark-cli 已配置应用凭证",
                ok=False,
                detail=err or "unknown",
                fix="运行: lark-cli config init（首次）并按文档完成应用配置",
            )
        )
        return DoctorReport(ok=False, items=items, lark_auth=None)

    info = identity_summary(status)
    items.append(
        CheckItem(
            id="lark_app",
            title="飞书应用已绑定到 lark-cli",
            ok=bool(info.get("app_id")),
            detail=f"appId={info.get('app_id')} app={info.get('app_name') or '—'}",
            fix="lark-cli config init",
        )
    )

    bot_ok = bool(info.get("bot_ready"))
    items.append(
        CheckItem(
            id="lark_bot",
            title="Bot 身份可用（fnotify 默认用 Bot 发消息）",
            ok=bot_ok,
            detail=info.get("bot_message") or "—",
            fix="在飞书开发者后台确保应用已发布/可用；Bot 租户 token 由 lark-cli 管理，勿对 bot 执行 auth login",
        ),
    )

    user_ok = bool(info.get("user_ready"))
    ou = info.get("user_open_id") or ""
    items.append(
        CheckItem(
            id="lark_user",
            title="用户身份可用（用来获取你的 open_id）",
            ok=user_ok,
            detail=(
                f"{info.get('user_name') or '—'} {ou}".strip()
                if user_ok
                else (info.get("user_message") or "未登录")
            ),
            fix="lark-cli auth login --domain im --no-wait --json  # 扫码授权用户身份",
        ),
    )

    cfg = load_config()
    route = (cfg.get("routes") or {}).get("dm_self") or {}
    uid = (route.get("user_id") or "").strip()
    uid_ok = uid.startswith("ou_")
    items.append(
        CheckItem(
            id="fnotify_recipient",
            title="fnotify 收件人 user_id（你的 open_id）",
            ok=uid_ok,
            detail=uid or "未配置",
            fix="fnotify install  # 或编辑 config.yaml 中 routes.dm_self.user_id",
        ),
    )

    all_ok = all(i.ok for i in items)
    return DoctorReport(ok=all_ok, items=items, lark_auth=info)