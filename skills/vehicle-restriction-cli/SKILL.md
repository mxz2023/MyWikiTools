---
name: vehicle-restriction-cli
description: 查询北京或天津指定日期的汽车尾号轮换组；提醒只读本地政策，不能联网刷新或推断车辆通行结论。
---

# 汽车尾号限行 CLI

## 提醒规则

- 仅在用户明确起床，或明确表示将前往北京/天津时查询；普通提及城市不触发。
- 使用用户明确的城市和事件日期。晨起地点按 MyWiki 的晨间地点规则；行程日期不明确且无法可靠解析时先询问。
- 只运行离线提醒命令：

  ```sh
  vehicle-restriction remind CITY --plate-region 津 --tail 7 --date YYYY-MM-DD
  ```

- CITY 必须是 CLI 注册的城市。当前项目流程涉及 beijing 和 tianjin。只传地区简称“津”和尾号“7”，不传完整车牌。
- 提醒流程不得运行 refresh、联网搜索或调用其他来源。
- 按 policy_status 判断本地是否有覆盖查询日期的政策。仅当 policy_status 为 confirmed 时，才可报告 tail_rotation_match 所表示的“尾号与普通工作日轮换组匹配/不匹配”。
- travel_status 为 unknown 且 applicability_status 为 unconfirmed；不得把轮换组匹配说成车辆实际受限、整城禁行或可通行。工具未核验节假日/调休、车辆及号牌类别、具体区域时段和临时措施。
- policy_status 为 unconfirmed、CLI 失败或输出不可解析时，报告“无法确认当日限行规则”，不得将缺失或过期政策说成不限行。旧政策到期后、刷新尚未找到新有效政策的间隔期间，也始终按无法确认处理。
- 限行查询分支失败时继续处理其他独立晨间事项。

## 政策维护

刷新与提醒分离。只有用户明确要求政策维护或刷新时，才按城市分别调用：

```sh
vehicle-restriction refresh --city beijing
vehicle-restriction refresh --city tianjin
```

手动 refresh 与 launchd 自动调用都遵守该城市的本地 next_check_date，未到期时不联网。城市维护与调度列表通过 vehicle-restriction cities 返回的顶层 JSON 数组确定；launchd 不硬编码城市。注册列表命令失败或输出无效时，等待器记录错误并停止刷新，绝不回退为固定城市列表。新增城市注册后需重新加载 LaunchAgent。首次没有任何政策或检查记录时会立即尝试；失败后等待 7 天重试。已有政策在失效前三天做最后一次提前检查，到期日再确认；到期后仍无新政策时每 7 天重试，直到找到有效官网政策。提醒期间只能读取旧状态，政策到期且新政策未确认时报告无法确认。不要在每次提醒前刷新。默认状态路径是 ~/.local/share/vehicle-restriction-cli/state.json；全局参数 --state PATH 必须放在子命令之前。
