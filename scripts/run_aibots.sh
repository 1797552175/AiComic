#!/bin/bash
cd /opt/AiComic/scripts
export PYTHONUNBUFFERED=1

setsid python3 -u bot_http_server_v2.py monitor 8001 "状态监控机器人" </dev/null >/tmp/bot_8001.log 2>&1 &
setsid python3 -u bot_http_server_v2.py pm 8002 "产品经理机器人" </dev/null >/tmp/bot_8002.log 2>&1 &
setsid python3 -u bot_http_server_v2.py dev 8003 "研发机器人" </dev/null >/tmp/bot_8003.log 2>&1 &
setsid python3 -u bot_http_server_v2.py marketing 8004 "营销机器人" </dev/null >/tmp/bot_8004.log 2>&1 &

wait
