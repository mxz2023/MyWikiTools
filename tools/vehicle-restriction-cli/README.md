# 汽车尾号限行 CLI

vehicle-restriction 用官方来源维护北京、天津的尾号轮换政策，并允许离线查询指定日期的轮换组。项目是 MyWikiTools 的独立 Python CLI 包。

## 安装

在 MyWikiTools 仓库根目录执行：

```sh
python3 -m pip install --user pipx
python3 -m pipx ensurepath
pipx install ./tools/vehicle-restriction-cli
```

重新打开终端后确认命令可用：

```sh
vehicle-restriction --help
```

## 政策更新

按城市分别调用更新命令：

```sh
vehicle-restriction refresh --city beijing
vehicle-restriction refresh --city tianjin
```

refresh（手动运行或由 launchd 调用）均先检查该城本地 next_check_date。未到日期时返回 not_due，不访问网站；到期后才请求该城官方 HTTPS 来源。初次尚无政策时立即尝试一次，失败后 7 天重试。已有政策通常在有效期结束前一个月开始检查；失败后每 7 天重试，失效前三天进行最后一次提前检查，若仍未发现新政策，则在有效期最后一天之后的到期日再查。旧政策到期后仍未找到新的有效官网政策时，每 7 天重试，直至找到新政策。此期间提醒因本地没有覆盖当日的有效政策而返回 policy_status=unconfirmed，应报告“无法确认当日限行规则”。各城市分别维护检查日期；单城失败不会阻止其他到期城市的检查。

刷新结果为 JSON 对象，城市结果是 published、not_due 或 unconfirmed。当前已确认：北京适配器从官方交管专题及其官方通告解析轮换周期；天津目前只识别到历史通告，刷新会安全返回未确认，不会把过期规则当作现行政策。

## 离线查询

remind 只读取本地状态，不联网、不刷新政策：

```sh
vehicle-restriction remind beijing --plate-region 津 --tail 7 --date 2026-11-11
vehicle-restriction remind tianjin --plate-region 津 --tail 7 --date 2026-11-11
```

只传号牌地区简称和尾号，不向命令传完整车牌。可省略 --date，默认使用运行机器当前日期。全局参数必须放在子命令之前：

```sh
vehicle-restriction --state /path/to/state.json remind beijing --plate-region 津 --tail 7 --date 2026-11-11
```

提醒结果刻意不判断车辆是否可以通行。输出的 policy_status 表示本地是否有该日有效的已确认政策；tail_rotation_match 只表示尾号是否属于普通周一至周五轮换组。travel_status 始终是 unknown，applicability_status 始终是 unconfirmed，因为工具不核验节假日或调休安排、车辆和号牌类别、区域、时段或临时措施。不能将轮换组匹配解释成整城禁行或允许通行。缺少有效本地政策时 tail_rotation_match 为 null。

## macOS 按到期日刷新（可选）

安装 CLI 后可运行：

```sh
./tools/vehicle-restriction-cli/launchd/install.sh
```

vehicle-restriction cities 以顶层 JSON 数组列出 CLI 注册的城市 ID。LaunchAgent 登录后启动一个轻量等待进程，通过该命令读取列表，逐城读取 next_check_date，只等待到期城市的检查日当天 06:00（Asia/Shanghai）并调用 refresh；更新状态后重新计算下次检查日。注册城市列表无法读取或格式无效时，它只记录错误并等待重试，不回退到硬编码城市。新增城市后，更新 CLI 注册表并重新安装/启动 LaunchAgent，以重新加载城市列表。它不会每天执行检查，也不会每天访问官网。到期日仍未发现新政策时，按 7 天间隔重新预约；到期后无有效政策期间，离线提醒仍返回无法确认。初次安装且尚无任何政策或检查记录时会立即尝试首次官方查询。机器睡眠或用户退出登录会延迟运行，到重新唤醒或登录后补做已到期检查。日志在状态目录的 refresh.stdout.log 与 refresh.stderr.log。

停止并移除 LaunchAgent：

```sh
./tools/vehicle-restriction-cli/launchd/uninstall.sh
```

wrapper 和 plist 安装到用户目录，安装后可移动工具仓库。卸载不会删除政策状态或日志。不希望启用自动刷新时，不运行安装脚本。

## 开发验证

```sh
cd tools/vehicle-restriction-cli
python3 -m pytest -q
cd ../..
./scripts/test-all.sh
```
