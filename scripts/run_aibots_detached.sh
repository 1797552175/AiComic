#!/bin/bash
# AiBots 启动脚本 - 带看门狗守护
cd /opt/AiComic/scripts
export PYTHONUNBUFFERED=1

BOT_PIDS=""

start_bot() {
    local bot=$1
    local port=$2
    local name=$3
    nohup setsid python3 -u bot_http_server_v2.py $bot $port "$name" </dev/null >/tmp/bot_$port.log 2>&1 &
    echo "Started $name pid=$!"
}

# 启动4个bot
for bot_info in "monitor:8001:状态监控机器人" "pm:8002:产品经理机器人" "dev:8003:研发机器人" "marketing:8004:营销机器人"; do
    IFS=':' read -r bot port name <<< "$bot_info"
    start_bot $bot $port "$name"
done

# 看门狗：每30秒检查bot是否存活，崩溃则重启
while true; do
    sleep 30
    for bot_info in "monitor:8001:状态监控机器人" "pm:8002:产品经理机器人" "dev:8003:研发机器人" "marketing:8004:营销机器人"; do
        IFS=':' read -r bot port name <<< "$bot_info"
        if ! curl -s --max-time 2 http://127.0.0.1:$port/health >/dev/null 2>&1; then
            echo "[Watchdog] $name died, restarting..."
            start_bot $bot $port "$name"
        fi
    done
done
