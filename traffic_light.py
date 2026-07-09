#!/usr/bin/env python3
"""AI 红绿灯 — 监控 WorkBuddy 工作区创建 + 状态文件 push"""

import tkinter as tk
import json
import os
import time
import threading

STATUS_FILE = os.path.expanduser('~/.workbuddy/ai_status.json')
WB_ROOT = os.path.expanduser('~/WorkBuddy')

STATUS_CONFIG = {
    'waiting': {'color': '#cc0000', 'glow': '#ff4444', 'label': '需要介入'},
    'working': {'color': '#cc9900', 'glow': '#ffcc00', 'label': '工作中'},
    'idle':    {'color': '#00aa00', 'glow': '#44ff44', 'label': '就绪'},
}

WORKING_TIMEOUT = 3
STARTUP_LOOKBACK = 300  # 启动时回溯窗口（秒）


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
        self._draw_lights()
        self._draw_label()

        self._offset_x = self._offset_y = 0
        self.canvas.bind('<Button-1>', self._on_drag_start)
        self.canvas.bind('<B1-Motion>', self._on_drag_move)

        self._last_work_signal = time.time()
        self._startup_time = time.time()
        self._latest_workspace_birth = 0  # 最新工作区创建时间

        self._update_display()
        self._start_watcher()

    # ─── UI ───────────────────────────────────

    def _draw_rounded_bg(self):
        r = 10
        pts = [2+r, 2, 62-r, 2, 62, 2, 62, 2+r,
               62, 174-r, 62, 174, 62-r, 174, 2+r, 174,
               2, 174, 2, 174-r, 2, 2+r, 2, 2]
        self.canvas.create_polygon(pts, smooth=True,
                                    fill='#2a2a2a', outline='#3a3a3a', width=1)

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

    # ─── 状态控制 ─────────────────────────────

    def set_status(self, status):
        if status == self.current_status:
            return
        self.current_status = status
        self.root.after(0, self._update_display)
        self._save_status()

    def _update_display(self):
        for s, (light, glow) in self.light_ids.items():
            if s == self.current_status:
                self.canvas.itemconfig(light, fill=STATUS_CONFIG[s]['color'], outline='#666')
                self.canvas.itemconfig(glow, fill=STATUS_CONFIG[s]['glow'])
            else:
                self.canvas.itemconfig(light, fill='#222', outline='#444')
                self.canvas.itemconfig(glow, fill='')
        self.canvas.itemconfig(self.label_id, text=STATUS_CONFIG[self.current_status]['label'])

    def _save_status(self):
        try:
            os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
            with open(STATUS_FILE, 'w') as f:
                json.dump({'status': self.current_status,
                           'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S')}, f)
        except Exception:
            pass

    # ─── 检测逻辑 ─────────────────────────────

    def _detect_work_signal(self):
        now = time.time()
        since_start = now - self._startup_time
        # 启动后前 10 秒用宽窗口（覆盖崩溃重启场景）
        lookback = STARTUP_LOOKBACK if since_start < 10 else 3

        # 信号 1：状态文件 push
        try:
            if os.path.exists(STATUS_FILE):
                with open(STATUS_FILE) as f:
                    data = json.load(f)
                if data.get('status') == 'working':
                    if now - os.path.getmtime(STATUS_FILE) < WORKING_TIMEOUT:
                        return True
        except Exception:
            pass

        # 信号 2：新工作区创建
        self._scan_workspaces(now)
        if self._latest_workspace_birth > 0 and (now - self._latest_workspace_birth) < 3:
            return True

        return False

    def _scan_workspaces(self, now):
        """扫描今天的工作区，记录最新创建时间"""
        today = time.strftime('%Y-%m-%d')
        latest = 0
        try:
            for entry in os.scandir(WB_ROOT):
                if not entry.is_dir() or not entry.name.startswith(today):
                    continue
                try:
                    bt = entry.stat().st_birthtime
                    if bt > latest:
                        latest = bt
                except OSError:
                    pass
        except OSError:
            pass
        self._latest_workspace_birth = latest

    # ─── 主循环（带自愈）─────────────────────

    def _watcher_loop(self):
        while True:
            try:
                now = time.time()
                work_signal = self._detect_work_signal()

                if work_signal:
                    self._last_work_signal = now
                    target = 'working'
                else:
                    target = 'idle' if (now - self._last_work_signal) > WORKING_TIMEOUT else self.current_status

                if target != self.current_status:
                    self.current_status = target
                    self.root.after(0, self._update_display)

                time.sleep(0.5)
            except Exception:
                time.sleep(1)

    def _start_watcher(self):
        t = threading.Thread(target=self._watcher_loop, daemon=True)
        t.start()

    def run(self):
        self.root.mainloop()


def main():
    TrafficLight().run()


if __name__ == '__main__':
    main()
