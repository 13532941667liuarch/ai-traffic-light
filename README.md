# AI 红绿灯 🚦

> WorkBuddy 桌面状态小组件——用红绿灯显示你的 AI 助手在干什么。

设计借鉴了 [AI Light](https://github.com/LeoKemp223/ai-light) 的红绿灯状态模型，但实现方式完全不同：它是一个轻量 Python 脚本，通过读取 JSON 状态文件来更新显示。

## 效果

半透明悬浮窗，三盏灯：

| 🟢 绿灯 | 🟡 黄灯 | 🔴 红灯 |
|---------|---------|---------|
| 就绪 | 正在干活 | 需要你介入 |

## 当前能力范围

**已实现：** 搭配 WorkBuddy 使用。WorkBuddy 会在干活时自动写入状态文件，红绿灯实时响应。

**需要自行配置：** 如果你想搭配其他 AI 工具（Claude Code、Codex 等），需要在对应工具的 hook 脚本中写入同样的 JSON 文件。本项目不提供这些 hook 配置。

## 安装和运行

依赖 Python 3（macOS 自带，无需安装任何第三方包）。

```bash
./start.sh
# 或者
python3 traffic_light.py
```

启动后在屏幕左上角显示，可拖拽移动。点击灯可手动切换状态。

## 工作原理

```
WorkBuddy 干活 → 写入 ~/.workbuddy/ai_status.json → 红绿灯轮询读取 → 更新显示
```

状态文件格式：

```json
{"status": "working", "timestamp": "2026-07-09T12:00:00"}
```

可选值：`idle` / `working` / `waiting`。超过 2 分钟未更新的 `working` 状态自动回退到 `idle`。

## 命令行控制

```bash
node set-status.js working   # 黄灯
node set-status.js waiting   # 红灯
node set-status.js idle      # 绿灯
node set-status.js start     # 启动
node set-status.js stop      # 停止
```

## 如何接入其他 AI 工具

在其他 AI 工具的 hook 配置中，写入同一个状态文件即可：

```bash
# Claude Code hooks 示例（需自行配置）
echo '{"status": "working"}' > ~/.workbuddy/ai_status.json
```

## 文件说明

```
├── traffic_light.py   # 主程序（Python tkinter，零依赖）
├── set-status.js      # 状态控制脚本
├── start.sh           # 启动脚本
└── README.md
```

## 致谢

红绿灯三色状态模型参考了 [AI Light](https://github.com/LeoKemp223/ai-light)。本项目使用 Python 原生 GUI 实现，无需 Electron。

## License

MIT
