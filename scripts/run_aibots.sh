#!/bin/bash
# AiBots watchdog - 被 systemd 调用
cd /opt/AiComic/scripts
export PYTHONUNBUFFERED=1

LOG="/tmp/bot_watchdog.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG"; }

cleanup() {
    log "Stopping..."
    pkill -f "bot_http_server_v2.py" 2>/dev/null
    exit 0
}
trap cleanup SIGTERM SIGINT

log "=== AiBots watchdog starting ==="

start_bot() {
    local bot=$1 port=$2 name=$3
    log "Starting $name (port $port)..."
    nohup setsid python3 -u bot_http_server_v2.py $bot $port "$name" </dev/null >/tmp/bot_$port.log 2>&1 &
}

# 启动所有 bot
for info in "monitor:8001:状态监控机器人" "pm:8002:产品经理机器人" "dev:8003:研发机器人" "marketing:8004:营销机器人"; do
    IFS=':' read -r bot port name <<< "$info"
    start_bot $bot $port "$name"
done

log "All bots started. Monitoring..."

# 监控循环：用 curl 健康检查，比 pgrep 更可靠
while true; do
    sleep 30
    for info in "monitor:8001:状态监控机器人" "pm:8002:产品经理机器人" "dev:8003:研发机器人" "marketing:8004:营销机器人"; do
        IFS=':' read -r bot port name <<< "$info"
        if curl -s --max-time 3 "http://127.0.0.1:$port/health" 2>/dev/null | grep -q "bot"; then
            log "OK: $name (port $port)"
        else
            log "DOWN: $name (port $port) - restarting..."
            pkill -f "bot_http_server_v2.py $bot $port" 2>/dev/null
            sleep 1
            start_bot $bot $port "$name"
        fi
    done
done
