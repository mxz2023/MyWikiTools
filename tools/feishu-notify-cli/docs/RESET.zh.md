# 从零重配 lark-cli + fnotify

用于验证 `fnotify install` 或换应用/换机。

## 一、清除本机状态

```bash
fnotify uninstall        # 分步询问：配置 / lark-cli 凭证 / pipx 卸 fnotify
fnotify uninstall --yes  # 只删 ~/.config/fnotify
```

若要同时清 **lark-cli** 本机凭证（与 fnotify 无关，需手动）：

```bash
lark-cli auth logout --json
lark-cli config remove
```

可选：若残留异常，可查看并手动清理（**一般不需要**）：

- `~/.lark-cli/config.json`
- `~/Library/Application Support/lark-cli/`

## 二、重新配置

```bash
fnotify install
```

一条命令内会按需执行 lark-cli 应用绑定与用户扫码登录，并写入 fnotify 配置。

## 三、预期 install 行为

| 状态 | `fnotify install` |
|------|----------------|
| 未 `config init` | 步骤 2 失败，提示 `lark-cli config init --new` |
| 无用户登录 | 提示 `lark-cli auth login --domain im` |
| Bot + 用户就绪 | 自动写 `ou_`，`doctor` 全绿，可选测试消息 |