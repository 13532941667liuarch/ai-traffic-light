#!/bin/bash
# AI 红绿灯启动脚本
cd "$(dirname "$0")"
/Users/xiaoxin/.workbuddy/binaries/python/versions/3.13.12/bin/python3 traffic_light.py &
echo "AI 红绿灯已启动 (PID: $!)"
