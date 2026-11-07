"""Bilingual CLI help strings (EN / 中文)."""

ROOT_HELP = """
Garmin Connect Personal API CLI. / 佳明 Connect 个人 API 命令行工具。

Commands: gmp | garmin-personal (short: gm + p from Garmin + personal).

Workflow / 流程:
  1. gmp profile add NAME --default "<api-key>"
  2. gmp profile-settings          # verify key / 验证 Key
  3. gmp steps --start-date ... --end-date ...

Defaults / 默认:
  API base https://personal.connectapi.garmin.cn (override: --api-base, GARMIN_API_BASE)
  Config ~/.config/garmin-personal/config.toml

Exit codes / 退出码: 0 ok; 3 no credentials; 4 HTTP 4xx; 5 HTTP 5xx

Agent output: add --json-output on request or data commands.
""".strip()

OPT_JSON_OUTPUT = (
    'Emit {"status","headers","body"} JSON / 输出含 status、headers、body 的 JSON（便于 Agent 解析）'
)
OPT_JSON_ERRORS = "Write errors as JSON on stderr / 错误信息以 JSON 输出到 stderr"
OPT_START_DATE = "Start date YYYY-MM-DD (inclusive) / 开始日期 YYYY-MM-DD"
OPT_END_DATE = "End date YYYY-MM-DD (inclusive) / 结束日期 YYYY-MM-DD"
OPT_DATE = "Calendar date YYYY-MM-DD / 日历日期 YYYY-MM-DD"
OPT_QUIET = "Suppress extra stderr / 减少 stderr 输出"

SHORT: dict[str, str] = {
    "request": "Raw HTTP to API paths / 通用 HTTP 请求（相对 API 根路径）",
    "steps": "Daily steps / 每日步数",
    "stress": "Daily stress / 每日压力",
    "hydration": "Daily hydration / 每日饮水",
    "effective-weight-goals": "Weight goals / 有效体重目标",
    "weight-measurements": "Weight measurements / 体重记录",
    "food-logs": "Food logs for one day / 单日饮食",
    "profile-settings": "User profile settings — verify API key / 用户资料（验证 Key）",
    "sleep": "Sleep for one day / 单日睡眠",
    "sleep-summaries": "Sleep summaries in range / 睡眠摘要区间",
    "body-battery": "Body Battery reports / Body Battery",
    "daily-summaries": "Daily wellness summaries / 每日综合摘要",
    "heart-rate": "Daily heart rate / 每日心率",
    "hrv": "HRV for one day / 单日 HRV",
    "hrv-summaries": "HRV range / HRV 区间",
    "heart-rate-zones": "Heart rate zones / 心率区间",
    "menstrual-cycle-summary": "Menstrual cycle summary / 月经周期摘要",
    "menstrual-cycle-day-view": "Menstrual cycle day view / 月经周期日视图",
    "fitness-age": "Fitness Age / 体能年龄",
    "spo2": "SpO2 for one day / 单日血氧",
    "wellness-activity-summaries": "Wellness activity summaries / 活动摘要",
    "activities": "Search activities / 搜索活动列表",
    "activity": "Activity detail / 活动详情",
    "activity-workouts": "Workouts in activity / 活动训练段",
    "activity-download": "Download activity ZIP / 下载活动 ZIP",
    "setup": "Post-install: API key URL + profile add / 安装后引导",
    "version": "Print package version / 打印版本号",
}

HTTP: dict[str, str] = {
    "steps": "GET /usersummary-service/stats/steps/daily/{start_date}/{end_date}",
    "stress": "GET /usersummary-service/stats/stress/daily/{start_date}/{end_date}",
    "hydration": "GET /usersummary-service/stats/hydration/daily/{start_date}/{end_date}",
    "effective-weight-goals": "GET /goal-service/goal/user/effective/weightgoal/{start_date}/{end_date}",
    "weight-measurements": "GET /weight-service/weight/range/{start_date}/{end_date}?includeAll=true",
    "food-logs": "GET /nutrition-service/food/logs/{date}",
    "profile-settings": "GET /userprofile-service/userprofile/settings",
    "sleep": "GET /sleep-service/sleep/dailySleep?date={date}",
    "sleep-summaries": "GET /sleep-service/sleep/dailySleepSummariesByDate?startDate=…&endDate=…",
    "body-battery": "GET /wellness-service/wellness/bodyBattery/reports/daily?startDate=…&endDate=…",
    "daily-summaries": "GET /usersummary-service/v2/dailysummaries?startDate=…&endDate=…",
    "heart-rate": "GET /wellness-service/wellness/dailyHeartRate?date={date}",
    "hrv": "GET /hrv-service/hrv/{date}",
    "hrv-summaries": "GET /hrv-service/hrv/daily/{start_date}/{end_date}",
    "heart-rate-zones": "GET /biometric-service/heartRateZones/v2",
    "menstrual-cycle-summary": "GET /periodichealth-service/menstrualcycle/summary/{date}",
    "menstrual-cycle-day-view": "GET /periodichealth-service/menstrualcycle/dayview/{date}?todayDate=…",
    "fitness-age": "GET /fitnessage-service/fitnessage/v2/{date}",
    "spo2": "GET /wellness-service/wellness/daily/spo2acclimation/{date}",
    "wellness-activity-summaries": "GET /wellnessactivity-service/activity/summary/range/{start_date}/{end_date}",
    "activities": "GET /activitylist-service/activities/search/activities?start&limit&…",
    "activity": "GET /activity-service/activity/{activity_id}",
    "activity-workouts": "GET /activity-service/activity/{activity_id}/workouts",
    "activity-download": "GET /download-service/files/activity/{activity_id} (binary ZIP)",
}

EXAMPLE: dict[str, str] = {
    "steps": 'gmp steps --start-date 2025-11-01 --end-date 2025-11-07 [--json-output]',
    "stress": 'gmp stress --start-date 2025-11-01 --end-date 2025-11-07',
    "hydration": 'gmp hydration --start-date 2025-11-01 --end-date 2025-11-07',
    "effective-weight-goals": "gmp effective-weight-goals --start-date 2025-11-01 --end-date 2025-11-30",
    "weight-measurements": "gmp weight-measurements --start-date 2025-11-01 --end-date 2025-11-30",
    "food-logs": "gmp food-logs --date 2025-11-06",
    "profile-settings": "gmp profile-settings  |  gmp profile-settings --json-output",
    "sleep": "gmp sleep --date 2025-11-06",
    "sleep-summaries": "gmp sleep-summaries --start-date 2025-11-01 --end-date 2025-11-07",
    "body-battery": "gmp body-battery --start-date 2025-11-01 --end-date 2025-11-07",
    "daily-summaries": "gmp daily-summaries --start-date 2025-11-01 --end-date 2025-11-07",
    "heart-rate": "gmp heart-rate --date 2025-11-06",
    "hrv": "gmp hrv --date 2025-11-06",
    "hrv-summaries": "gmp hrv-summaries --start-date 2025-11-01 --end-date 2025-11-07",
    "heart-rate-zones": "gmp heart-rate-zones",
    "menstrual-cycle-summary": "gmp menstrual-cycle-summary --date 2025-11-06",
    "menstrual-cycle-day-view": "gmp menstrual-cycle-day-view --date 2025-11-06 --today-date 2025-11-06",
    "fitness-age": "gmp fitness-age --date 2025-11-06",
    "spo2": "gmp spo2 --date 2025-11-06",
    "wellness-activity-summaries": "gmp wellness-activity-summaries --start-date 2025-11-01 --end-date 2025-11-07",
    "activities": "gmp activities --limit 10 --start-date 2025-11-01 --end-date 2025-11-07",
    "activity": "gmp activity 123456789",
    "activity-workouts": "gmp activity-workouts 123456789",
    "activity-download": "gmp activity-download 123456789 -o ~/Downloads/act.zip",
}


def long_doc(name: str, http: str, example: str, note: str = "") -> str:
    extra = f"\n\n{note}" if note else ""
    return f"""{SHORT.get(name, name)}

HTTP: {http}

Example / 示例:
  {example}

Requires Personal API key (profile or GARMIN_API_KEY). Empty body may mean HTTP 204 (no data).
需要已配置 Personal API Key。无数据时可能返回 204。{extra}"""
