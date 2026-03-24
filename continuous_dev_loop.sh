#!/bin/bash
# 持续执行原型研发任务
LOG_FILE="/opt/AiComic/continuous_dev.log"
BOT_TYPE="dev"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

log "🚀 启动持续研发任务循环"

while true; do
    # 获取待研发原型任务
    PROTOS=$(ls /opt/AiComic/原型/*.md 2>/dev/null | head -5)
    
    for proto in $PROTOS; do
        proto_name=$(basename "$proto")
        log "📋 开始处理: $proto_name"
        
        # 调用研发Bot执行任务
        curl -s -X POST "http://localhost:8002/execute_proto" \
            -H "Content-Type: application/json" \
            -d "{\"proto_file\":\"$proto_name\",\"task_id\":\"PROTO-LOOP-$(date +%s)\"}" \
            >> $LOG_FILE 2>&1
        
        log "✅ 完成: $proto_name"
        
        # 间隔30秒
        sleep 30
    done
    
    log "🔄 一轮完成，等待 60 秒..."
    sleep 60
done
