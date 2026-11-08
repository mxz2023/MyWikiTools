# Apple Health CLI（`ahp`）

在 Mac 上通过免费 **AHPSync**（iPhone）接收手表/健康数据，写入 SQLite，CLI 查询。

命令名：**`ahp`** 或 **`apple-health`**。

## 数据流

Apple 手表 → iPhone 健康 → **AHPSync** → Wi‑Fi → **`ahp serve`** → 本地库

## 安装

```bash
./tools/apple-health-cli/scripts/install.sh
ahp setup
```

详见 [docs/AHPSYNC_SETUP.zh.md](docs/AHPSYNC_SETUP.zh.md)、[ios/README.zh.md](ios/README.zh.md)

## Mac 接收

```bash
export AHP_INGEST_TOKEN='令牌'
ahp serve --host 0.0.0.0 --port 8765
```

## 查询

```bash
ahp status --json-output
ahp steps --days 7 --json-output
```

## 可选

- 一次性导入：`ahp import export.xml`
- 目录监听：`ahp watch`
