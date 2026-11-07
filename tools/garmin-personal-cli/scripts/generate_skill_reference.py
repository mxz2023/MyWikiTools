#!/usr/bin/env python3
"""Generate skills/garmin-personal-cli/reference.md from garmin_personal.help_text."""

from __future__ import annotations

import sys
from pathlib import Path

TOOL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = TOOL_ROOT.parents[1]
SRC = TOOL_ROOT / "src"
OUT = REPO_ROOT / "skills" / "garmin-personal-cli" / "reference.md"

sys.path.insert(0, str(SRC))

from garmin_personal import help_text as ht  # noqa: E402

DATA_ORDER: list[str] = [
    "profile-settings",
    "steps",
    "stress",
    "hydration",
    "effective-weight-goals",
    "weight-measurements",
    "food-logs",
    "sleep",
    "sleep-summaries",
    "body-battery",
    "daily-summaries",
    "heart-rate",
    "hrv",
    "hrv-summaries",
    "heart-rate-zones",
    "fitness-age",
    "spo2",
    "menstrual-cycle-summary",
    "menstrual-cycle-day-view",
    "wellness-activity-summaries",
    "activities",
    "activity",
    "activity-workouts",
    "activity-download",
]

DATA_CATEGORY: dict[str, str] = {
    "profile-settings": "用户资料 / profile",
    "steps": "每日步数 / steps",
    "stress": "每日压力 / stress",
    "hydration": "饮水 / hydration",
    "effective-weight-goals": "体重目标 / weight-goals",
    "weight-measurements": "体重记录 / weight",
    "food-logs": "饮食 / nutrition",
    "sleep": "睡眠（单日）/ sleep",
    "sleep-summaries": "睡眠（区间）/ sleep-range",
    "body-battery": "Body Battery / body-battery",
    "daily-summaries": "每日综合摘要 / daily-summary",
    "heart-rate": "心率 / heart-rate",
    "hrv": "HRV（单日）/ hrv",
    "hrv-summaries": "HRV（区间）/ hrv-range",
    "heart-rate-zones": "心率区间 / hr-zones",
    "fitness-age": "体能年龄 / fitness-age",
    "spo2": "血氧 / spo2",
    "menstrual-cycle-summary": "月经周期摘要 / menstrual",
    "menstrual-cycle-day-view": "月经周期日视图 / menstrual-day",
    "wellness-activity-summaries": "按日活动汇总 / wellness-activity",
    "activities": "运动列表 / activities",
    "activity": "单次运动详情 / activity-detail",
    "activity-workouts": "运动训练段 / activity-workouts",
    "activity-download": "运动文件下载 / activity-file",
}

GENERIC_BODY_HINT = (
    "Parse `body` in the stdout envelope after run; do not invent field names before execution. "
    "业务数据在 envelope.body，结构以本次响应为准。"
)

BODY_HINT: dict[str, str] = {
    "profile-settings": "object | null — 用户/资料设置",
    "steps": "array | object | null — 区间内每日步数",
    "stress": "array | object | null — 区间内每日压力",
    "hydration": "array | object | null — 区间内饮水",
    "effective-weight-goals": "object | array | null — 体重目标",
    "weight-measurements": "array | object | null — 体重记录",
    "food-logs": "object | array | null — 单日饮食",
    "sleep": "object | null — 单日睡眠",
    "sleep-summaries": "array | object | null — 睡眠区间",
    "body-battery": "array | object | null — Body Battery",
    "daily-summaries": "array | object | null — 每日综合",
    "heart-rate": "object | array | null — 单日心率",
    "hrv": "object | array | null — 单日 HRV",
    "hrv-summaries": "array | object | null — HRV 区间",
    "heart-rate-zones": "object | array | null — 心率区间配置",
    "fitness-age": "object | null — 体能年龄",
    "spo2": "object | array | null — 血氧",
    "menstrual-cycle-summary": "object | null",
    "menstrual-cycle-day-view": "object | null",
    "wellness-activity-summaries": "array | object | null — 按日活动汇总（非单次列表）",
    "activities": "object | array | null — 运动列表（含 activityId；跑步机/室内跑在列表中筛选）",
    "activity": "object | null — 单次运动详情",
    "activity-workouts": "object | array | null — 分段/训练段",
    "activity-download": "binary written to `-o` path; metadata use `activity` / `activities`",
    "request": GENERIC_BODY_HINT,
}

DEFAULT_RANGE_ARGS = (
    "| `--start-date` | YYYY-MM-DD 起（必填） | |\n"
    "| `--end-date` | YYYY-MM-DD 止（必填） | |\n"
    "| `--json-output` | 见 SKILL.md 契约 | 推荐 |\n"
    "| `--json-errors` | stderr JSON 错误 | 推荐 |"
)
DEFAULT_DATE_ARGS = (
    "| `--date` | YYYY-MM-DD（必填） | |\n"
    "| `--json-output` | 见 SKILL.md 契约 | 推荐 |\n"
    "| `--json-errors` | stderr JSON 错误 | 推荐 |"
)
DEFAULT_JSON_ONLY = (
    "| *(none)* | — | |\n"
    "| `--json-output` | 见 SKILL.md 契约 | 推荐 |\n"
    "| `--json-errors` | stderr JSON 错误 | 推荐 |"
)

CLI_ARGS = {
    "profile-settings": DEFAULT_JSON_ONLY,
    "steps": DEFAULT_RANGE_ARGS,
    "stress": DEFAULT_RANGE_ARGS,
    "hydration": DEFAULT_RANGE_ARGS,
    "effective-weight-goals": DEFAULT_RANGE_ARGS,
    "weight-measurements": DEFAULT_RANGE_ARGS,
    "food-logs": DEFAULT_DATE_ARGS,
    "sleep": DEFAULT_DATE_ARGS,
    "sleep-summaries": DEFAULT_RANGE_ARGS,
    "body-battery": (
        DEFAULT_RANGE_ARGS.replace(
            "| `--end-date` | YYYY-MM-DD 止（必填） | |\n",
            "| `--end-date` | YYYY-MM-DD 止（必填） | |\n"
            "| `--chunks` | 可选分块数量 | 可选 |\n",
        )
    ),
    "daily-summaries": DEFAULT_RANGE_ARGS,
    "heart-rate": DEFAULT_DATE_ARGS,
    "hrv": DEFAULT_DATE_ARGS,
    "hrv-summaries": DEFAULT_RANGE_ARGS,
    "heart-rate-zones": DEFAULT_JSON_ONLY,
    "fitness-age": DEFAULT_DATE_ARGS,
    "spo2": DEFAULT_DATE_ARGS,
    "menstrual-cycle-summary": DEFAULT_DATE_ARGS,
    "menstrual-cycle-day-view": (
        "| `--date` | YYYY-MM-DD（必填） | |\n"
        "| `--today-date` | 当天 YYYY-MM-DD（必填） | |\n"
        "| `--json-output` | 见 SKILL.md 契约 | 推荐 |\n"
        "| `--json-errors` | stderr JSON 错误 | 推荐 |"
    ),
    "wellness-activity-summaries": DEFAULT_RANGE_ARGS,
    "activities": (
        "| `--start` | 分页偏移，默认 0 | 可选 |\n"
        "| `--limit` | 每页条数，默认 20 | 可选 |\n"
        "| `--start-date` | 过滤起始 YYYY-MM-DD | 可选 |\n"
        "| `--end-date` | 过滤结束 YYYY-MM-DD | 可选 |\n"
        "| `--activity-type` | 佳明活动类型码；先列再筛，勿臆造 | 可选 |\n"
        "| `--json-output` | 见 SKILL.md 契约 | 推荐 |\n"
        "| `--json-errors` | stderr JSON 错误 | 推荐 |"
    ),
    "activity": (
        "| `activity_id` | 位置参数，来自 `activities` 列表 | 必填 |\n"
        "| `--json-output` | 见 SKILL.md 契约 | 推荐 |\n"
        "| `--json-errors` | stderr JSON 错误 | 推荐 |"
    ),
    "activity-workouts": (
        "| `activity_id` | 位置参数 | 必填 |\n"
        "| `--json-output` | 见 SKILL.md 契约 | 推荐 |\n"
        "| `--json-errors` | stderr JSON 错误 | 推荐 |"
    ),
    "activity-download": (
        "| `activity_id` | 位置参数 | 必填 |\n"
        "| `-o, --output` | 输出 .zip 路径 | 必填 |\n"
        "| `--force` | 覆盖已存在文件 | 可选 |\n"
        "| `--json-output` | 通常不需要；文件在 `-o` | 可选 |"
    ),
    "request": (
        "| `METHOD` | GET（常用）等 | 必填 |\n"
        "| `path` | 以 `/` 开头的 API 路径 | 必填 |\n"
        "| `--json-output` | 见 SKILL.md 契约 | 推荐 |\n"
        "| `--json-errors` | stderr JSON 错误 | 推荐 |\n"
        "| `-o, --output` | 原始响应写文件 | 可选 |"
    ),
}

NOTES: dict[str, str] = {
    "activities": "昨天/跑步机：同一天设 `--start-date` 与 `--end-date`；室内跑从 `body` 列表筛，勿盲猜 `--activity-type`。分页用 `--start`/`--limit`。",
    "activity-download": "二进制 ZIP；问答用 `activity`/`activities`。",
    "wellness-activity-summaries": "按日汇总，不是「每一次跑步」列表；单次列表用 `activities`。",
}

# Verified against live `gmp ... --json-output` (personal.connectapi.garmin.cn, 2025-11).
# Update this dict after re-running commands when Garmin or CLI changes.
RESP_VERIFIED: dict[str, str] = {
    "profile-settings": (
        "`body` 为 object：`displayName`, `timeZone`, `measurementSystem`, `preferredLocale` 等设置项。"
    ),
    "steps": (
        "`body` 为 **array**；元素含 `calendarDate`, `totalSteps`, `totalDistance`, `stepGoal`。"
    ),
    "activities": (
        "`body` 为 **array**（非外层包裹对象）。每项含 `activityId`, `activityName`, "
        "`startTimeLocal`, `duration`（秒）, `distance`, `calories`, `averageHR`；"
        "`activityType.typeKey` 如 `treadmill_running`（跑步机）、`running`、`lap_swimming`。"
        "列表项已够回答「跑了多久/多远」；不必先调 `activity`。"
    ),
    "activity": (
        "`body` 为 object；**概览指标多在 `summaryDTO`**（`distance`, `duration`, `calories`, "
        "`averageHR`, `startTimeLocal` 等），勿假定与列表相同字段都在顶层。"
    ),
    "sleep": (
        "`body` 为 object：`calendarDate`, `sleepTimeSeconds`, `deepSleepSeconds`, "
        "`lightSleepSeconds`, `remSleepSeconds`, `sleepScores.overall.value` 等。"
    ),
}


def agent_example(cmd: str) -> str:
    if cmd == "profile-settings":
        return "gmp profile-settings --json-output --json-errors"
    if cmd == "heart-rate-zones":
        return "gmp heart-rate-zones --json-output --json-errors"
    if cmd == "activity":
        return "gmp activity 123456789 --json-output --json-errors"
    if cmd == "activity-workouts":
        return "gmp activity-workouts 123456789 --json-output --json-errors"
    if cmd == "activity-download":
        return "gmp activity-download 123456789 -o ./activity.zip"
    base = ht.EXAMPLE.get(cmd, f"gmp {cmd}")
    if "|" in base:
        base = f"gmp {cmd}"
    if "--json-output" in base:
        if "--json-errors" not in base:
            return f"{base} --json-errors"
        return base
    return f"{base} --json-output --json-errors"


def section_data_command(name: str) -> list[str]:
    lines = [
        f"### `{name}`",
        "",
        f"- **类别**: {DATA_CATEGORY.get(name, name)}",
        f"- **HTTP**: `{ht.HTTP.get(name, '—')}`",
        f"- **说明**: {ht.SHORT.get(name, '')}",
    ]
    note = NOTES.get(name)
    if note:
        lines.append(f"- **注意**: {note}")
    lines.extend(
        [
        "",
        "**CLI 参数**",
        "",
        "| 参数 | 含义 | 备注 |",
        "|------|------|------|",
        CLI_ARGS.get(name, DEFAULT_JSON_ONLY),
        "",
        f"**body_hint**: {BODY_HINT.get(name, GENERIC_BODY_HINT)}",
        "",
        ],
    )
    verified = RESP_VERIFIED.get(name)
    if verified:
        lines.extend(
            [
                "**响应（实测 API）**",
                "",
                verified,
                "",
            ]
        )
    lines.extend(
        [
        "**示例**",
        "",
        "```bash",
        agent_example(name),
        "```",
        "",
        ]
    )
    return lines


def main() -> None:
    out: list[str] = [
        "<!-- generated by tools/garmin-personal-cli/scripts/generate_skill_reference.py; do not edit -->",
        "",
        "# gmp command reference (Agent)",
        "",
        "全量 Personal API 数据命令目录。执行前读 [SKILL.md](SKILL.md) 中的 I/O 契约。",
        "不要访问 Garmin 开发者 Swagger/FAQ 猜路径；优先用下表子命令。",
        "",
        "## 数据命令",
        "",
    ]
    for name in DATA_ORDER:
        if name not in ht.HTTP:
            continue
        out.extend(section_data_command(name))

    out.extend(
        [
            "## `request`（兜底）",
            "",
            f"- **说明**: {ht.SHORT['request']}",
            "",
            "**CLI 参数**",
            "",
            "| 参数 | 含义 | 备注 |",
            "|------|------|------|",
            CLI_ARGS["request"],
            "",
            f"**body_hint**: {BODY_HINT['request']}",
            "",
            "```bash",
            "gmp request GET '/userprofile-service/userprofile/settings' --json-output --json-errors",
            "```",
            "",
            "## 配置 / 元命令（非 wellness 数据）",
            "",
            "| 命令 | 用途 |",
            "|------|------|",
            "| `gmp profile list` | 列出配置档 |",
            "| `gmp profile add NAME KEY [--default]` | 写入 API Key |",
            "| `gmp profile remove NAME` | 删除配置档 |",
            "| `gmp profile set-default NAME` | 设默认配置档 |",
            "| `gmp auth print-token [--refresh]` | 调试令牌（勿对用户展示） |",
            "| `gmp setup` | 安装后引导 |",
            "| `gmp version` | 包版本 |",
            "",
        ]
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(out), encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
