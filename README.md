# AI 红绿灯 🚦

> WorkBuddy 桌面状态小组件——用红绿灯显示你的 AI 助手在干什么。

设计借鉴了 [AI Light](https://github.com/LeoKemp223/ai-light) 的 push + timeout 状态模型：WorkBuddy 干活时主动推送状态信号，红绿灯响应后 3 秒无新信号自动回绿，绝不卡死。

## 效果

半透明悬浮窗，三盏灯：

| 🟢 绿灯 | 🟡 黄灯 | 🔴 红灯 |
|---------|---------|---------|
| 就绪 | 正在干活 | 需要你介入 |

## 当前能力范围

**已实现：** 搭配 WorkBuddy 使用，**完全自动检测**——WorkBuddy 干活时自动亮黄灯，干完自动回绿，无需任何手动操作。

**需要自行配置：** 想搭配其他 AI 工具（Claude Code、Codex 等），需在对应工具的 hook 里写入状态文件 `~/.workbuddy/ai_status.json`。

## 安装和运行

依赖 Python 3（macOS 自带，无需安装任何第三方包）。

```bash
./start.sh
# 或者
python3 traffic_light.py
```

启动后在屏幕左上角显示，可拖拽移动。点击灯可手动切换状态。

## 工作原理

模仿 AI Light 的 push + timeout 模型：

1. **Push 信号** — WorkBuddy 干活时写入 `~/.workbuddy/ai_status.json`（`"status": "working"`）
2. **文件变更兜底** — 工作区目录内有文件被修改时也能触发（3 秒窗口）
3. **Timeout 回退** — 3 秒无新信号自动切回就绪，杜绝黄灯卡死

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
