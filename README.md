# AI 红绿灯 🚦

> WorkBuddy 桌面状态小组件——用红绿灯显示你的 AI 助手在干什么。

设计借鉴了 [AI Light](https://github.com/LeoKemp223/ai-light) 的红绿灯状态模型，通过**自动检测工作区文件变更 + 子进程活动**来判断 WorkBuddy 是否正在工作，完全无需手动操作。

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

红绿灯每 0.5 秒检测两个信号，任一命中即判定为「工作中」：

1. **文件变更** — 工作区目录内有文件被修改（3 秒窗口）
2. **子进程活动** — 工作区路径下出现额外的 bash/node 等子进程

两个信号同时失效 1.5 秒后，自动切回就绪状态。覆盖所有操作类型：写代码、搜网页、调 API、跑脚本。

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
