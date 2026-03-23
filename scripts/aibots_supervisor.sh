#!/bin/bash
# 超级监控进程：启动后等待10秒检查子进程，崩溃则重启
cd /opt/AiComic/scripts

pids=()
names=("monitor:8001" "pm:8002" "dev:8003" "marketing:8004")

start_bot() {
    local bot_type=$1
    local port=$2
    local name=$3
    nohup python3 bot_http_server_v2.py $bot_type $port "$name" > /tmp/bot_${port}.log 2>&1 &
    echo $!
}

echo "[AibotsSupervisor] 启动中..."
for info in "${names[@]}"; do
    IFS=':' read -r bot port name <<< "$info"
    pid=$(start_bot $bot $port "$name")
    pids+=($pid)
    echo "[AibotsSupervisor] 启动 $name (pid=$pid)"
done

echo "[AibotsSupervisor] 所有 Bot 已启动，PID=${pids[*]}，进入监控循环"

# 监控循环：检查子进程，死了就重启
while true; do
    sleep 10
    for i in "${!names[@]}"; do
        info=${names[$i]}
        IFS=':' read -r bot port name <<< "$info"
        pid=${pids[$i]}
        if ! kill -0 $pid 2>/dev/null; then
            echo "[AibotsSupervisor] $name (pid=$pid) 挂了，重启中..."
            new_pid=$(start_bot $bot $port "$name")
            pids[$i]=$new_pid
            echo "[AibotsSupervisor] $name 重启，新 pid=$new_pid"
        fi
    done
done
