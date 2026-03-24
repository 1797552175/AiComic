#!/bin/bash
# Bot Watchdog - 稳定版
# - 用 PID 文件追踪进程，不依赖模糊 pattern 杀进程
# - 端口残留用 python 检测，不依赖 lsof/ss
# - 连续2次检查失败才重启，避免瞬时抖动

BOT_SCRIPT="/opt/AiComic/scripts/bot_http_server_v2.py"
LOG_DIR="/opt/AiComic/状态报告"
PORTS=(8001 8002 8003 8004)
NAMES=("monitor" "pm" "dev" "marketing")
PID_DIR="/var/run/aicomic-bots"

mkdir -p "$PID_DIR"

# 用 python 检测端口是否被 bot 进程占用
is_port_free() {
    local port=$1
    python3 -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(1)
try:
    s.connect(('127.0.0.1', $port))
    s.close()
    print('IN_USE')
except:
    print('')
" 2>/dev/null | grep -q "IN_USE" && return 1 || return 0
}

check_and_restart() {
    local port=$1
    local name=$2
    local pidfile="$PID_DIR/${name}.pid"

    # 连续2次检查失败才认定 DOWN（避免瞬时抖动）
    local fail_count=0
    for i in 1 2; do
        if curl -s --max-time 3 "http://localhost:$port/health" > /dev/null 2>&1; then
            fail_count=0
            break
        fi
        fail_count=$((fail_count + 1))
        [ $i -eq 1 ] && sleep 2
    done

    [ $fail_count -lt 2 ] && return 0  # 健康

    echo "[$(date)] $name (port $port) DOWN - restarting..."

    # 读取旧 PID
    local old_pid=""
    [ -f "$pidfile" ] && old_pid=$(cat "$pidfile" 2>/dev/null)

    # 精准杀旧进程
    if [ -n "$old_pid" ] && kill -0 "$old_pid" 2>/dev/null; then
        local old_cmdline
        old_cmdline=$(cat /proc/$old_pid/cmdline 2>/dev/null | tr '\0' ' ')
        if echo "$old_cmdline" | grep -q "bot_http_server_v2.py"; then
            kill "$old_pid" 2>/dev/null
            sleep 2
            kill -0 "$old_pid" 2>/dev/null && kill -9 "$old_pid" 2>/dev/null
        fi
    fi

    # 清理端口残留（找所有相关进程，比 lsof 更可靠）
    python3 -c "
import os, signal
port = $port
for pid in os.listdir('/proc'):
    if not pid.isdigit():
        continue
    try:
        cmdline = open(f'/proc/{pid}/cmdline', 'rb').read().decode('utf-8', errors='ignore')
        if 'bot_http_server_v2.py' in cmdline and str(port) in cmdline:
            os.kill(int(pid), signal.SIGKILL)
    except:
        pass
" 2>/dev/null

    sleep 5  # 等待旧进程完全退出 + 端口释放（修复 Address already in use）

    # 启动新进程（最多重试3次，防止端口未释放导致 Address already in use）
    cd /opt/AiComic/scripts
    local new_pid=""
    for attempt in 1 2 3; do
        if [ $attempt -gt 1 ]; then
            echo "[$(date)] $name 第${attempt}次启动尝试，等待5秒..."
            sleep 5
        fi
        python3 -u bot_http_server_v2.py $name $port >> "$LOG_DIR/${name}.log" 2>&1 &
        new_pid=$!
        # 检查进程是否立即退出（通常是因为端口被占用）
        sleep 2
        if kill -0 "$new_pid" 2>/dev/null; then
            break  # 进程存活，启动成功
        fi
        echo "[$(date)] $name 尝试${attempt}失败，进程立即退出（端口可能被占用）"
    done
    echo "$new_pid" > "$pidfile"

    # 等待端口就绪（最多20秒）
    echo "[$(date)] $name waiting for port $port (PID=$new_pid)..."
    local started=0
    for i in $(seq 1 20); do
        if curl -s --max-time 2 "http://localhost:$port/health" > /dev/null 2>&1; then
            started=1
            break
        fi
        sleep 1
    done

    if [ $started -eq 1 ]; then
        echo "[$(date)] $name restart OK (PID=$new_pid)"
    else
        echo "[$(date)] $name restart FAILED - port $port not responding"
        rm -f "$pidfile"
    fi
}

for i in "${!PORTS[@]}"; do
    check_and_restart ${PORTS[$i]} ${NAMES[$i]}
done
