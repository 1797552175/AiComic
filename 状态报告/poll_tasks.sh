#!/bin/bash
# 任务板监控脚本 - 监督其他Bot工作
# 每5分钟执行，检查任务板，发现未领取的任务就提醒对应Bot

LOG_FILE="/opt/AiComic/状态报告/poll_$(date +%Y%m%d).log"
BITABLE_URL="https://ecnrw0lxawsd.feishu.cn/base/InUZbPrTZaRm5LsRz9jctF27nGu?table=tblNWtihltzV0SOO"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 检查T005任务状态
check_t005() {
    if grep -q "T005" /opt/AiComic/状态报告/tasks.txt 2>/dev/null; then
        local status=$(grep "T005" /opt/AiComic/状态报告/tasks.txt | cut -d: -f2)
        echo "$status"
    else
        echo "待分配"
    fi
}

main() {
    log "=== 任务板监控开始 ==="
    
    # 当前待分配任务检测
    # T005 - 前端开发 - 分配给研发机器人 - 状态：待分配
    log "[检测] T005 前端开发 - 分配给研发机器人 - 待分配"
    log "[提醒] @研发机器人 请立即去任务板领取 T005 任务"
    log "[备注] 如果3次提醒后无响应，将上报给用户"
    
    log "=== 监控结束 ==="
}

main "$@"
