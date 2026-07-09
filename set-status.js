#!/usr/bin/env node
// AI 红绿灯状态写入工具
// 用法: node set-status.js [waiting|working|idle]

const fs = require('fs');
const path = require('path');
const os = require('os');

const STATUS_FILE = path.join(os.homedir(), '.workbuddy', 'ai_status.json');
const PID_FILE = path.join(os.homedir(), '.workbuddy', 'ai_traffic_light.pid');
const status = process.argv[2];

// 启动红绿灯
if (status === 'start') {
  const { spawn } = require('child_process');
  const scriptDir = __dirname;
  const child = spawn('/Users/xiaoxin/.workbuddy/binaries/python/versions/3.13.12/bin/python3',
    [path.join(scriptDir, 'traffic_light.py')],
    { detached: true, stdio: 'ignore' }
  );
  child.unref();
  const dir = path.dirname(PID_FILE);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(PID_FILE, String(child.pid));
  console.log(`AI 红绿灯已启动 (PID: ${child.pid})`);
  process.exit(0);
}

// 停止
if (status === 'stop') {
  try {
    const pid = parseInt(fs.readFileSync(PID_FILE, 'utf-8').trim());
    process.kill(pid, 'SIGTERM');
    console.log(`AI 红绿灯已停止 (PID: ${pid})`);
  } catch (e) {
    // 尝试用 pkill
    const { execSync } = require('child_process');
    try { execSync('pkill -f traffic_light.py'); console.log('已停止'); }
    catch { console.log('未找到运行中的红绿灯'); }
  }
  process.exit(0);
}

if (!status || !['waiting', 'working', 'idle'].includes(status)) {
  console.error('用法: node set-status.js [waiting|working|idle|start|stop]');
  process.exit(1);
}

const dir = path.dirname(STATUS_FILE);
if (!fs.existsSync(dir)) {
  fs.mkdirSync(dir, { recursive: true });
}

fs.writeFileSync(STATUS_FILE, JSON.stringify({
  status,
  timestamp: new Date().toISOString(),
}, null, 2));

console.log(`状态已更新: ${status}`);
