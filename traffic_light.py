#!/usr/bin/env python3
"""AI 红绿灯 - 桌面悬浮显示 AI 助手工作状态"""

import tkinter as tk
import json
import os
import time
import threading

STATUS_FILE = os.path.expanduser('~/.workbuddy/ai_status.json')

STATUS_CONFIG = {
    'waiting': {'color': '#cc0000', 'glow': '#ff4444', 'label': '需要介入'},
    'working': {'color': '#cc9900', 'glow': '#ffcc00', 'label': '工作中'},
    'idle':    {'color': '#00aa00', 'glow': '#44ff44', 'label': '就绪'},
}


class TrafficLight:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('AI 红绿灯')
        self.root.overrideredirect(True)  # 无边框
        self.root.attributes('-topmost', True)  # 始终置顶
        self.root.attributes('-alpha', 0.92)  # 半透明背景

        # 窗口大小和位置
        self.root.geometry('64x176+20+80')
        self.root.configure(bg='#1e1e1e')

        # 圆角效果（用 Canvas 画背景）
        self.canvas = tk.Canvas(
            self.root, width=64, height=176,
            bg='#1e1e1e', highlightthickness=0
        )
        self.canvas.pack(fill='both', expand=True)

        # 圆角背景
        self._draw_rounded_bg()

        self.current_status = 'idle'
        self.light_ids = {}
        self.label_id = None

        self._draw_lights()
        self._draw_label()

        # 关闭按钮
        self.canvas.tag_bind('close', '<Button-1>', lambda e: self.root.withdraw())

        # 拖拽移动
        self._offset_x = 0
        self._offset_y = 0
        self.canvas.bind('<Button-1>', self._on_drag_start)
        self.canvas.bind('<B1-Motion>', self._on_drag_move)

        self._update_display()

        # 状态文件轮询
        self._start_watcher()

    def _draw_rounded_bg(self):
        """画圆角矩形背景"""
        r = 10
        self.canvas.create_rounded = self._create_rounded_rect(
            2, 2, 62, 174, r, fill='#2a2a2a', outline='#3a3a3a', width=1
        )

    def _create_rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        """创建圆角矩形"""
        points = [
            x1 + r, y1,
            x2 - r, y1,
            x2, y1,
            x2, y1 + r,
            x2, y2 - r,
            x2, y2,
            x2 - r, y2,
            x1 + r, y2,
            x1, y2,
            x1, y2 - r,
            x1, y1 + r,
            x1, y1,
        ]
        return self.canvas.create_polygon(points, smooth=True, **kwargs)

    def _draw_lights(self):
        """画三个圆灯"""
        cx = 32
        positions = [
            ('waiting', cx, 34, 12),
            ('working', cx, 74, 12),
            ('idle',    cx, 114, 12),
        ]

        for status, x, y, r in positions:
            # 灯光晕（发光效果）
            glow = self.canvas.create_oval(
                x - r - 4, y - r - 4, x + r + 4, y + r + 4,
                fill='', outline='', tags=(f'glow_{status}',)
            )
            # 灯本体
            light = self.canvas.create_oval(
                x - r, y - r, x + r, y + r,
                fill='#333333', outline='#555555', width=1,
                tags=(f'light_{status}',)
            )
            self.light_ids[status] = (light, glow, x, y, r)
            # 点击事件
            self.canvas.tag_bind(
                f'light_{status}', '<Button-1>',
                lambda e, s=status: self.set_status(s)
            )
            self.canvas.tag_bind(
                f'glow_{status}', '<Button-1>',
                lambda e, s=status: self.set_status(s)
            )

    def _draw_label(self):
        """画状态标签"""
        self.label_id = self.canvas.create_text(
            32, 146,
            text='就绪',
            fill='#999999',
            font=('Helvetica', 8)
        )

    def _on_drag_start(self, event):
        self._offset_x = event.x
        self._offset_y = event.y

    def _on_drag_move(self, event):
        x = self.root.winfo_pointerx() - self._offset_x
        y = self.root.winfo_pointery() - self._offset_y
        self.root.geometry(f'+{x}+{y}')

    def set_status(self, status):
        """手动设置状态并写入文件"""
        if status == self.current_status:
            return
        self.current_status = status
        self._update_display()
        self._save_status()

    def _update_display(self):
        """根据当前状态更新灯的显示"""
        cfg = STATUS_CONFIG[self.current_status]

        for s, (light, glow, x, y, r) in self.light_ids.items():
            if s == self.current_status:
                # 亮灯
                self.canvas.itemconfig(light, fill=STATUS_CONFIG[s]['color'], outline='#666666')
                self.canvas.itemconfig(glow, fill=STATUS_CONFIG[s]['glow'])
            else:
                # 灭灯
                self.canvas.itemconfig(light, fill='#222222', outline='#444444')
                self.canvas.itemconfig(glow, fill='')

        self.canvas.itemconfig(self.label_id, text=cfg['label'])

    def _save_status(self):
        """写入状态文件"""
        data = {'status': self.current_status, 'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S')}
        try:
            os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
            with open(STATUS_FILE, 'w') as f:
                json.dump(data, f)
        except Exception:
            pass

    def _read_status_file(self):
        """读取状态文件；超过 2 分钟未更新则自动回退到空闲"""
        try:
            if os.path.exists(STATUS_FILE):
                mtime = os.path.getmtime(STATUS_FILE)
                age = time.time() - mtime

                with open(STATUS_FILE, 'r') as f:
                    data = json.load(f)

                status = data.get('status')

                # 状态文件超过 2 分钟没更新 → 回退到空闲（防止我忘记更新）
                if age > 120 and status != 'idle':
                    status = 'idle'

                if status in STATUS_CONFIG and status != self.current_status:
                    self.current_status = status
                    self.root.after(0, self._update_display)
        except Exception:
            pass

    def _start_watcher(self):
        """启动状态文件轮询"""

        def poll():
            while True:
                self._read_status_file()
                time.sleep(1)

        t = threading.Thread(target=poll, daemon=True)
        t.start()

    def run(self):
        self.root.mainloop()


def main():
    app = TrafficLight()
    app.run()


if __name__ == '__main__':
    main()
