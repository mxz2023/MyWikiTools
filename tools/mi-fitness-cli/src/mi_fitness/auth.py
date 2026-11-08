"""Login: QR, passToken, session import."""

from __future__ import annotations

import io
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

import qrcode.constants as qr_constants
import requests
from mifit.auth.qr import (
    exchange_sts,
    new_device_id,
    poll_qr_login,
    request_qr_login,
)
from mifit.auth.renew import renew_session
from mifit.auth.session import Session
from mifit.errors import NotificationRequiredError
from mifit.region import SID
from qrcode.main import QRCode

from mi_fitness.config import save_local_session

_SCAN_INSTRUCTIONS = """
这是小米账号登录二维码（sid=miothealth），不是手环/体脂秤配对码。

请用以下任一方式扫码（不要用「小米运动健康」App 里的扫码，否则会提示「暂不支持」）：
  • 小米手机：设置 → 小米账号 → 扫一扫
  • 或安装「小米账号」/「小米穿戴」类账号 App 的扫一扫
  • 或手机系统相机对准 Mac「预览」里弹出的二维码

等待手机上点「确认登录」…
""".strip()


class LoginError(Exception):
    """User-facing login failure."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _render_qr_ascii(content: str) -> str:
    """Fallback terminal QR when PNG preview is unavailable."""
    code = QRCode(error_correction=qr_constants.ERROR_CORRECT_M, border=2)
    code.add_data(content)
    code.make(fit=True)
    blocks = io.StringIO()
    code.print_ascii(out=blocks, invert=True)
    text = blocks.getvalue()
    try:
        text.encode(getattr(sys.stdout, "encoding", None) or "utf-8")
    except (UnicodeEncodeError, LookupError):
        text = "".join(
            "".join("  " if cell else "##" for cell in row) + "\n"
            for row in code.get_matrix()
        )
    return text


def _display_qr(http: requests.Session, login_url: str, qr_image_url: str) -> None:
    login_url = (login_url or "").strip()
    qr_image_url = (qr_image_url or "").strip()
    if not login_url or not qr_image_url:
        raise LoginError("Xiaomi login returned incomplete QR data; retry `mfp login`.")

    print(_SCAN_INSTRUCTIONS, file=sys.stderr)
    print(file=sys.stderr)

    resp = http.get(qr_image_url, timeout=30)
    resp.raise_for_status()
    fd, png_path = tempfile.mkstemp(prefix="mfp-qr-", suffix=".png")
    try:
        os.write(fd, resp.content)
    finally:
        os.close(fd)
    os.chmod(png_path, stat.S_IRUSR | stat.S_IWUSR)

    displayed = False
    if sys.platform == "darwin":
        subprocess.run(["open", png_path], check=False)
        print(f"已用「预览」打开官方二维码: {png_path}", file=sys.stderr)
        displayed = True
    imgcat = shutil.which("imgcat")
    if imgcat and os.environ.get("TERM_PROGRAM") == "iTerm.app":
        subprocess.run([imgcat, png_path], check=False)
        displayed = True
    chafa = shutil.which("chafa")
    if chafa:
        subprocess.run([chafa, "-s", "50x25", png_path], check=False)
        displayed = True

    if not displayed:
        print("（终端内 ASCII 二维码，若无法识别请改用 passToken 登录）", file=sys.stderr)
        sys.stdout.write(_render_qr_ascii(login_url))
        sys.stdout.write("\n")
        sys.stdout.flush()

    print(file=sys.stderr)
    print(
        "备用：浏览器打开 account.xiaomi.com 登录后，用 "
        "`mfp login --pass-token … --user-id …`",
        file=sys.stderr,
    )


def login_with_qr() -> Session:
    http = requests.Session()
    device_id = new_device_id()
    try:
        challenge = request_qr_login(http, SID, device_id=device_id)
        _display_qr(http, challenge.login_url, challenge.qr_payload)
        result = poll_qr_login(challenge, http, device_id=device_id)
        session = exchange_sts(result, SID, http, device_id=device_id)
    except NotificationRequiredError as exc:
        raise LoginError(
            f"Xiaomi requires security confirmation. Open: {exc.notification_url}"
        ) from exc
    except Exception as exc:
        raise LoginError(str(exc)) from exc
    save_local_session(session)
    return session


def login_with_pass_token(
    *,
    user_id: str,
    pass_token: str,
    c_user_id: str = "",
    region: str = "cn",
) -> Session:
    device_id = new_device_id()
    seed = Session(
        user_id=user_id.strip(),
        c_user_id=(c_user_id or user_id).strip(),
        service_token="x",
        ssecurity="x",
        region=region,
        created_at=_utc_now(),
        pass_token=pass_token.strip(),
        device_id=device_id,
    )
    http = requests.Session()
    try:
        session = renew_session(seed, http)
    except Exception as exc:
        raise LoginError(f"passToken login failed: {exc}") from exc
    save_local_session(session)
    return session
