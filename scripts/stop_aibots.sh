#!/bin/bash
# 停止 aibots 服务
pkill -f "bot_http_server_v2.py" 2>/dev/null
echo "All bot processes stopped."
