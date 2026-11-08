"""Setup instructions."""


def setup_lines() -> list[str]:
    return [
        "Mi Fitness CLI (mfp)",
        "",
        "1) pipx install ./tools/mi-fitness-cli",
        "2) mfp login          # 小米账号扫一扫（预览窗口里的码）",
        "   or: mfp login --pass-token … --user-id …",
        "3) mfp sync --days 30",
        "4) mfp steps --days 7 --json-output",
        "",
        "Session: ~/.config/mi-fitness/session.json",
        "Database: ~/.local/share/mi-fitness/health.db",
        "",
        "Unofficial tool — not affiliated with Xiaomi.",
    ]
