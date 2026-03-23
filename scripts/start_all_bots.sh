#!/bin/bash
cd /opt/AiComic/scripts
export PYTHONUNBUFFERED=1

nohup python3 -u bot_http_server_v2.py monitor 8001 "状态监控机器人" > /tmp/bot_monitor.log 2>&1 &
nohup python3 -u bot_http_server_v2.py pm 8002 "产品经理机器人" > /tmp/bot_pm.log 2>&1 &
nohup python3 -u bot_http_server_v2.py dev 8003 "研发机器人" > /tmp/bot_dev.log 2>&1 &
nohup python3 -u bot_http_server_v2.py marketing 8004 "营销机器人" > /tmp/bot_marketing.log 2>&1 &

echo "All bots started with unbuffered output"
wait
