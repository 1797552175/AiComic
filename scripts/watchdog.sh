#!/bin/bash
# Bot Watchdog - 自动检查并重启挂掉的 Bot

BOT_SCRIPT="/opt/AiComic/scripts/bot_http_server_v2.py"
LOG_DIR="/opt/AiComic/状态报告"
PORTS=(8001 8002 8003 8004)
NAMES=("monitor" "pm" "dev" "marketing")

check_and_restart() {
    local port=$1
    local name=$2
    
    # 检查健康状态
    if ! curl -s --max-time 3 "http://localhost:$port/health" > /dev/null 2>&1; then
        echo "[$(date)] $name (port $port) DOWN - 重启中..."
        
        # 杀掉旧进程
        pkill -f "bot_http_server_v2.py.*$port" 2>/dev/null
        sleep 1
        
        # 重启
        cd /opt/AiComic/scripts
        nohup python3 bot_http_server_v2.py $name $port > "$LOG_DIR/${name}.log" 2>&1 &
        
        sleep 3
        
        if curl -s --max-time 3 "http://localhost:$port/health" > /dev/null 2>&1; then
            echo "[$(date)] $name 重启成功"
        else
            echo "[$(date)] $name 重启失败"
        fi
    fi
}

# 检查所有 Bot
for i in "${!PORTS[@]}"; do
    check_and_restart ${PORTS[$i]} ${NAMES[$i]}
done
