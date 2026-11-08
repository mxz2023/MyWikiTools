# AHPSync（免费 iOS 伴侣 App）

替代付费 **Health Auto Export**：在 iPhone 上读 **HealthKit**（含 Apple Watch 数据），通过 Wi‑Fi 推到 Mac 上的 **`ahp serve`**。

## 功能

- 读取：步数、心率、睡眠、活动能量、步行跑步距离、体能训练  
- 推送格式：与 `ahp serve` 的 **`/api/ingest`**（HAE 兼容 JSON）  
- 支持：立即同步、后台刷新（需打开开关）  
- **不开订阅、不走第三方云端**

## 1. Mac 端

```bash
export AHP_INGEST_TOKEN='你的随机令牌'
ahp serve --host 0.0.0.0 --port 8765
ipconfig getifaddr en0   # 记下 IP，例如 192.168.3.3
```

## 2. 生成 Xcode 工程

```bash
brew install xcodegen   # 首次
./tools/apple-health-cli/ios/scripts/generate-xcodeproj.sh
open tools/apple-health-cli/ios/AHPSync.xcodeproj
```

若不用 XcodeGen：Xcode → **New iOS App** → 命名为 AHPSync → 把 `ios/AHPSync/AHPSync/*.swift` 拖进工程 → 替换 Info.plist / entitlements。

## 3. Xcode 配置

1. **Signing & Capabilities** → Team 选你的 Apple 账号  
2. **+ Capability** → **HealthKit**  
3. Bundle ID 建议：`com.mywikitools.ahpsync`（与 `project.yml` 一致）  
4. [developer.apple.com](https://developer.apple.com) → Identifiers → 为该 App ID 启用 **HealthKit**（若真机安装失败）

## 4. 安装到 iPhone

1. 用数据线或无线调试连接 iPhone  
2. 选真机 → **Run (⌘R)**  
3. 首次：设置 → 通用 → VPN与设备管理 → 信任开发者  

## 5. App 内设置

| 项 | 示例 |
|----|------|
| 服务器 URL | `http://192.168.3.3:8765/api/ingest` |
| Token | 与 Mac 上 `AHP_INGEST_TOKEN` 相同 |
| 同步天数 | 7 |

顺序：**请求健康数据权限** → **立即同步到 Mac**

## 6. 验证

```bash
ahp status --json-output
ahp steps --days 7 --json-output
```

## 目录

```
ios/
  project.yml
  AHPSync.xcodeproj      # xcodegen 生成
  AHPSync/AHPSync/       # Swift 源码
  scripts/generate-xcodeproj.sh
```

## 限制

- 需 **同 Wi‑Fi**；Mac 防火墙放行 8765  
- 后台同步频率由 iOS 调度，不如前台点「立即同步」稳定  
- 未上架 App Store，需自行用 Xcode 装到手机  
