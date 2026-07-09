#!/usr/bin/env python3
"""AI 红绿灯 — 模仿 AI Light 的 push + timeout 状态模型"""

import tkinter as tk
import json
import os
import time
import threading

STATUS_FILE = os.path.expanduser('~/.workbuddy/ai_status.json')

# WorkBuddy 所有工作区的根目录
WB_ROOT = os.path.expanduser('~/WorkBuddy')
IGNORE_DIRS = {'.git', '__pycache__', 'node_modules'}

STATUS_CONFIG = {
    'waiting': {'color': '#cc0000', 'glow': '#ff4444', 'label': '需要介入'},
    'working': {'color': '#cc9900', 'glow': '#ffcc00', 'label': '工作中'},
    'idle':    {'color': '#00aa00', 'glow': '#44ff44', 'label': '就绪'},
}

# 超时：working 状态持续超过此秒数无新信号 → 自动回退 idle
WORKING_TIMEOUT = 3


class TrafficLight:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('AI 红绿灯')
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.92)
        self.root.geometry('64x176+20+80')
        self.root.configure(bg='#1e1e1e')

        self.canvas = tk.Canvas(self.root, width=64, height=176,
                                bg='#1e1e1e', highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)
        self._draw_rounded_bg()

        self.current_status = 'idle'
        self.light_ids = {}
        self.label_id = None
        self._draw_lights()
        self._draw_label()

        self._offset_x = 0
        self._offset_y = 0
        self.canvas.bind('<Button-1>', self._on_drag_start)
        self.canvas.bind('<B1-Motion>', self._on_drag_move)

        # 上次收到「工作中」信号的时间
        self._last_work_signal = 0

        self._update_display()
        self._start_watcher()

    # ─── UI 绘制 ────────────────────────────────

    def _draw_rounded_bg(self):
        r = 10
        self._create_rounded_rect(2, 2, 62, 174, r,
                                  fill='#2a2a2a', outline='#3a3a3a', width=1)

    def _create_rounded_rect(self, x1, y1, x2, y2, r, **kw):
        pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
               x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
               x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        return self.canvas.create_polygon(pts, smooth=True, **kw)

    def _draw_lights(self):
        cx = 32
        for status, y in [('waiting', 34), ('working', 74), ('idle', 114)]:
            r = 12
            glow = self.canvas.create_oval(
                cx - r - 4, y - r - 4, cx + r + 4, y + r + 4,
                fill='', outline='', tags=(f'glow_{status}',))
            light = self.canvas.create_oval(
                cx - r, y - r, cx + r, y + r,
                fill='#333', outline='#555', width=1, tags=(f'light_{status}',))
            self.light_ids[status] = (light, glow)
            self.canvas.tag_bind(f'light_{status}', '<Button-1>',
                                 lambda e, s=status: self.set_status(s))
            self.canvas.tag_bind(f'glow_{status}', '<Button-1>',
                                 lambda e, s=status: self.set_status(s))

    def _draw_label(self):
        self.label_id = self.canvas.create_text(
            32, 146, text='就绪', fill='#999', font=('Helvetica', 8))

    def _on_drag_start(self, ev): self._offset_x, self._offset_y = ev.x, ev.y
    def _on_drag_move(self, ev):
        self.root.geometry(f'+{self.root.winfo_pointerx() - self._offset_x}'
                           f'+{self.root.winfo_pointery() - self._offset_y}')

    # ─── 状态控制 ──────────────────────────────

    def set_status(self, status):
        if status == self.current_status:
            return
        self.current_status = status
        self.root.after(0, self._update_display)
        self._save_status()

    def _update_display(self):
        cfg = STATUS_CONFIG[self.current_status]
        for s, (light, glow) in self.light_ids.items():
            if s == self.current_status:
                self.canvas.itemconfig(light, fill=STATUS_CONFIG[s]['color'],
                                       outline='#666')
                self.canvas.itemconfig(glow, fill=STATUS_CONFIG[s]['glow'])
            else:
                self.canvas.itemconfig(light, fill='#222', outline='#444')
                self.canvas.itemconfig(glow, fill='')
        self.canvas.itemconfig(self.label_id, text=cfg['label'])

    def _save_status(self):
        try:
            os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
            with open(STATUS_FILE, 'w') as f:
                json.dump({'status': self.current_status,
                           'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S')}, f)
        except Exception:
            pass

    # ─── 检测逻辑（模仿 AI Light：push 优先 + timeout 兜底）────

    def _detect_work_signal(self):
        """检测是否有「工作中」信号：
           1. 状态文件写入了 working（push 信号）
           2. 工作区文件在 3 秒内被修改（被动检测）
        """
        now = time.time()

        # 信号 1：状态文件
        try:
            if os.path.exists(STATUS_FILE):
                with open(STATUS_FILE) as f:
                    data = json.load(f)
                if data.get('status') == 'working':
                    mtime = os.path.getmtime(STATUS_FILE)
                    if now - mtime < WORKING_TIMEOUT:
                        return True
        except Exception:
            pass

        # 信号 2：工作区文件变更
        return self._has_recent_file_changes(now)

    def _has_recent_file_changes(self, now):
        """扫描 ~/WorkBuddy/ 下所有工作区，检测最近 3 秒的文件变更。
           先用目录 mtime 快速过滤，只对近期有变化的工作区深入扫描。"""
        latest = 0
        threshold = now - 3

        def scan_dir(path):
            nonlocal latest
            try:
                for entry in os.scandir(path):
                    if entry.name.startswith('.') or entry.name in IGNORE_DIRS:
                        continue
                    try:
                        if entry.is_file():
                            m = entry.stat().st_mtime
                            if m > latest: latest = m
                        elif entry.is_dir():
                            try:
                                for sub in os.scandir(entry.path):
                                    if sub.name.startswith('.'): continue
                                    try:
                                        if sub.is_file():
                                            m = sub.stat().st_mtime
                                            if m > latest: latest = m
                                    except OSError: pass
                            except OSError: pass
                    except OSError: pass
            except OSError: pass

        try:
            for entry in os.scandir(WB_ROOT):
                if not entry.is_dir() or not entry.name[0].isdigit():
                    continue
                # 快速过滤：目录 mtime 在 3 秒内才深入扫描
                try:
                    if entry.stat().st_mtime < threshold:
                        continue
                except OSError:
                    continue
                scan_dir(entry.path)
        except OSError:
            pass

        try:
            m = os.path.getmtime(STATUS_FILE)
            if m > latest: latest = m
        except OSError: pass

        return (now - latest) < 3

    def _watcher_loop(self):
        while True:
            now = time.time()

            work_signal = self._detect_work_signal()

            if work_signal:
                self._last_work_signal = now
                target = 'working'
            else:
                # 超时：超过 WORKING_TIMEOUT 秒无新信号 → idle
                target = 'idle' if (now - self._last_work_signal) > WORKING_TIMEOUT else self.current_status

            if target != self.current_status:
                self.current_status = target
                self.root.after(0, self._update_display)

            time.sleep(0.5)

    def _start_watcher(self):
        t = threading.Thread(target=self._watcher_loop, daemon=True)
        t.start()

    def run(self):
        self.root.mainloop()


def main():
    TrafficLight().run()


if __name__ == '__main__':
    main()
