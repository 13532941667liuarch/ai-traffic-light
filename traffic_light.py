#!/usr/bin/env python3
"""AI 红绿灯 - 桌面悬浮显示 WorkBuddy 工作状态（自动检测）"""

import tkinter as tk
import json
import os
import time
import threading
import subprocess

STATUS_FILE = os.path.expanduser('~/.workbuddy/ai_status.json')

# 工作区目录：本脚本所在项目目录的上一级
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.path.dirname(SCRIPT_DIR)

# 忽略的目录
IGNORE_DIRS = {'.git', '__pycache__', 'node_modules'}

STATUS_CONFIG = {
    'waiting': {'color': '#cc0000', 'glow': '#ff4444', 'label': '需要介入'},
    'working': {'color': '#cc9900', 'glow': '#ffcc00', 'label': '工作中'},
    'idle':    {'color': '#00aa00', 'glow': '#44ff44', 'label': '就绪'},
}


class TrafficLight:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('AI 红绿灯')
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.92)

        self.root.geometry('64x176+20+80')
        self.root.configure(bg='#1e1e1e')

        self.canvas = tk.Canvas(
            self.root, width=64, height=176,
            bg='#1e1e1e', highlightthickness=0
        )
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

        self._update_display()

        # 手动状态保持标记：用户点灯后锁定 30 秒，不被自动检测覆盖
        self._manual_lock_until = 0

        # 启动自动检测
        self._start_watcher()

    def _draw_rounded_bg(self):
        r = 10
        self._create_rounded_rect(
            2, 2, 62, 174, r, fill='#2a2a2a', outline='#3a3a3a', width=1
        )

    def _create_rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        points = [
            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
        ]
        return self.canvas.create_polygon(points, smooth=True, **kwargs)

    def _draw_lights(self):
        cx = 32
        positions = [
            ('waiting', cx, 34, 12),
            ('working', cx, 74, 12),
            ('idle',    cx, 114, 12),
        ]

        for status, x, y, r in positions:
            glow = self.canvas.create_oval(
                x - r - 4, y - r - 4, x + r + 4, y + r + 4,
                fill='', outline='', tags=(f'glow_{status}',)
            )
            light = self.canvas.create_oval(
                x - r, y - r, x + r, y + r,
                fill='#333333', outline='#555555', width=1,
                tags=(f'light_{status}',)
            )
            self.light_ids[status] = (light, glow, x, y, r)
            self.canvas.tag_bind(
                f'light_{status}', '<Button-1>',
                lambda e, s=status: self.set_status(s)
            )
            self.canvas.tag_bind(
                f'glow_{status}', '<Button-1>',
                lambda e, s=status: self.set_status(s)
            )

    def _draw_label(self):
        self.label_id = self.canvas.create_text(
            32, 146, text='就绪', fill='#999999', font=('Helvetica', 8)
        )

    def _on_drag_start(self, event):
        self._offset_x = event.x
        self._offset_y = event.y

    def _on_drag_move(self, event):
        x = self.root.winfo_pointerx() - self._offset_x
        y = self.root.winfo_pointery() - self._offset_y
        self.root.geometry(f'+{x}+{y}')

    def set_status(self, status):
        """手动设置状态（点击灯时触发），锁定 30 秒不被自动检测覆盖"""
        if status == self.current_status:
            return
        self.current_status = status
        self._manual_lock_until = time.time() + 30
        self.root.after(0, self._update_display)
        self._save_status()

    def _update_display(self):
        cfg = STATUS_CONFIG[self.current_status]
        for s, (light, glow, x, y, r) in self.light_ids.items():
            if s == self.current_status:
                self.canvas.itemconfig(light, fill=STATUS_CONFIG[s]['color'], outline='#666666')
                self.canvas.itemconfig(glow, fill=STATUS_CONFIG[s]['glow'])
            else:
                self.canvas.itemconfig(light, fill='#222222', outline='#444444')
                self.canvas.itemconfig(glow, fill='')
        self.canvas.itemconfig(self.label_id, text=cfg['label'])

    def _save_status(self):
        data = {'status': self.current_status, 'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S')}
        try:
            os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
            with open(STATUS_FILE, 'w') as f:
                json.dump(data, f)
        except Exception:
            pass

    def _detect_activity(self):
        """综合检测：文件变更 + 活跃进程数"""
        now = time.time()

        # 1. 文件变更检测
        file_active = self._has_recent_file_changes(now)

        # 2. 进程检测（覆盖搜索、API 调用等不写文件的操作）
        proc_active = self._has_active_subprocesses()

        return file_active or proc_active

    def _has_recent_file_changes(self, now):
        """扫描工作区，检测最近 3 秒是否有文件变更"""
        latest_mtime = 0

        def check_dir(path):
            nonlocal latest_mtime
            try:
                for entry in os.scandir(path):
                    if entry.name.startswith('.') or entry.name in IGNORE_DIRS:
                        continue
                    try:
                        if entry.is_file():
                            mtime = entry.stat().st_mtime
                            if mtime > latest_mtime:
                                latest_mtime = mtime
                        elif entry.is_dir():
                            try:
                                for sub in os.scandir(entry.path):
                                    if sub.name.startswith('.'):
                                        continue
                                    try:
                                        if sub.is_file():
                                            mtime = sub.stat().st_mtime
                                            if mtime > latest_mtime:
                                                latest_mtime = mtime
                                    except OSError:
                                        pass
                            except OSError:
                                pass
                    except OSError:
                        pass
            except OSError:
                pass

        check_dir(WORKSPACE_DIR)
        try:
            mtime = os.path.getmtime(STATUS_FILE)
            if mtime > latest_mtime:
                latest_mtime = mtime
        except OSError:
            pass

        return (now - latest_mtime) < 3

    def _has_active_subprocesses(self):
        """检测工作区是否有活跃子进程（WorkBuddy 干活时会启动 bash/python/node）"""
        my_pid = str(os.getpid())
        try:
            # 查工作区路径下的活跃进程，排除红绿灯自身和 grep
            result = subprocess.run(
                ['pgrep', '-f', WORKSPACE_DIR],
                capture_output=True, text=True, timeout=1
            )
            pids = [p.strip() for p in result.stdout.split('\n') if p.strip() and p.strip() != my_pid]
            # 至少有一个其他进程在工作区 → 活跃
            return len(pids) > 0
        except Exception:
            return False

    def _watcher_loop(self):
        """自动检测循环：每 0.5 秒检测一次工作区活动"""
        idle_start = time.time()

        while True:
            # 手动锁定期间跳过自动检测
            if time.time() < self._manual_lock_until:
                time.sleep(0.5)
                continue

            active = self._detect_activity()

            if active:
                idle_start = time.time()
                target = 'working'
            else:
                # 停止活动后延迟 1.5 秒再切回就绪（防止短暂停顿误判）
                target = 'working' if (time.time() - idle_start) < 1.5 else 'idle'

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
    app = TrafficLight()
    app.run()


if __name__ == '__main__':
    main()
