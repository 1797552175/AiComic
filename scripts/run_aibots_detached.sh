#!/bin/bash
# 使用 nohup + setsid 确保进程完全脱离控制终端
cd /opt/AiComic/scripts
export PYTHONUNBUFFERED=1

for bot_info in "monitor:8001:状态监控机器人" "pm:8002:产品经理机器人" "dev:8003:研发机器人" "marketing:8004:营销机器人"; do
    IFS=':' read -r bot port name <<< "$bot_info"
    nohup setsid python3 -u bot_http_server_v2.py $bot $port "$name" </dev/null >/tmp/bot_$port.log 2>&1 &
    echo "Started $name pid=$!"
done

echo "All detached. PIDs: $(jobs -p)"
