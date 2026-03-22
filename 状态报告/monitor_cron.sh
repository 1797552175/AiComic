#!/bin/bash
# AiComic 项目监控定时任务
# 功能：轮询目录变化、检测Bot活跃状态、检查任务板

LOG_FILE="/opt/AiComic/状态报告/monitor_$(date +%Y%m%d).log"
MAX_LOG_SIZE=$((10 * 1024 * 1024))  # 10MB

# 日志滚动
if [ -f "$LOG_FILE" ] && [ $(stat -c%s "$LOG_FILE" 2>/dev/null || echo 0) -gt $MAX_LOG_SIZE ]; then
    mv "$LOG_FILE" "${LOG_FILE}.old"
fi

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

check_dirs() {
    # 检测 docs/, 代码/, 营销方案/, 原型/ 目录变化
    for dir in docs 代码 营销方案 原型; do
        if [ -d "/opt/AiComic/$dir" ]; then
            count=$(find "/opt/AiComic/$dir" -type f -name "*.md" -mmin -5 2>/dev/null | wc -l)
            if [ "$count" -gt 0 ]; then
                log "[发现新文件] $dir/ 目录有 $count 个新文件"
            fi
        fi
    done
}

check_git() {
    # 检查git push状态
    cd /opt/AiComic && git fetch origin 2>/dev/null
    local_status=$(cd /opt/AiComic && git status -s 2>/dev/null)
    if [ -n "$local_status" ]; then
        log "[Git] 有未提交的更改"
    fi
}

main() {
    log "=== 监控任务开始 ==="
    check_dirs
    check_git
    log "=== 监控任务结束 ==="
}

main "$@"
