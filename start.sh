#!/bin/bash
# AI 红绿灯启动脚本
cd "$(dirname "$0")"
python3 traffic_light.py &
echo "AI 红绿灯已启动 (PID: $!)"
