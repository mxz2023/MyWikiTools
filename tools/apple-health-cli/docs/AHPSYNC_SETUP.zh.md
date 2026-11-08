# 用 AHPSync 代替 Health Auto Export（方案 1 免费版）

## Mac

```bash
export AHP_INGEST_TOKEN='长随机密码'
ahp serve --host 0.0.0.0 --port 8765
```

## iPhone：编译安装 AHPSync

见 [ios/README.zh.md](../ios/README.zh.md)（Xcode + 真机一次安装）。

## App 配置

- URL：`http://<Mac-IP>:8765/api/ingest`  
- Token：与 `AHP_INGEST_TOKEN` 一致  

点 **立即同步到 Mac** 后，在 Mac 执行 `ahp status --json-output` 检查样本数。

## 定时

在 App 中打开 **后台定时同步**；并偶尔前台打开 App 点一次同步（iOS 后台限制）。
