# 自动同步

## 推荐：AHPSync + `ahp serve`

详见 [AHPSYNC_SETUP.zh.md](AHPSYNC_SETUP.zh.md)。

## 备选：iCloud 目录

```bash
mkdir -p ~/Library/Mobile\ Documents/com~apple~CloudDocs/AHP
ahp watch
```

将 `export.xml` 或 ingest JSON 放入该目录即可自动导入。

## 备选：一次性 bulk

```bash
ahp import /path/to/export.xml
```
