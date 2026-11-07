"""Post-install / first-run guidance (stdout)."""

from __future__ import annotations

ONBOARDING_LINES = """
==============================================
  garmin-personal-cli installed / 安装完成
==============================================

Next / 请按顺序完成：

1) Create a Garmin Personal API key / 在佳明网站申请个人 API 密钥
   https://connect.garmin.com/app/settings/personalApiToken
   (Key is shown only once — save it securely / 密钥只显示一次，请妥善保存)

2) Configure this machine / 在本机写入配置档：
   gmp profile add default --default "<your-api-key>"

3) Verify / 验证连接：
   gmp profile-settings
   gmp --help

Docs: README.zh.md or README.md in the repo.
""".strip()


def onboarding_text() -> str:
    return ONBOARDING_LINES
