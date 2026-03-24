#!/bin/bash
# monitor_cron.sh - 定时扫描原型目录，发现新原型则自动创建研发任务
# crontab: */5 * * * * /bin/bash /opt/AiComic/状态报告/monitor_cron.sh >> /opt/AiComic/状态报告/cron.log 2>&1

PROTOTYPE_DIR="/opt/AiComic/原型"
PROCESSED_FILE="/tmp/processed_prototypes.txt"
LOG_FILE="/opt/AiComic/状态报告/cron.log"

echo "[$(date)] monitor_cron 开始执行" >> "$LOG_FILE"

# 如果原型目录不存在，退出
if [ ! -d "$PROTOTYPE_DIR" ]; then
    echo "[$(date)] 原型目录不存在" >> "$LOG_FILE"
    exit 0
fi

# 获取已处理列表
get_processed() {
    if [ -f "$PROCESSED_FILE" ]; then
        cat "$PROCESSED_FILE"
    fi
}

# 标记已处理
mark_processed() {
    echo "$1" >> "$PROCESSED_FILE"
}

# 提取功能名称（从文件名去除日期后缀）
extract_name() {
    echo "$1" | sed 's/_202603[0-9]*\.md$//' | sed 's/_[0-9]\+\.md$//' | sed 's/\.md$//' | tr '_' ' '
}

# 扫描原型目录
total=0
new_count=0

for f in "$PROTOTYPE_DIR"/*.md; do
    [ -f "$f" ] || continue
    fname=$(basename "$f")
    total=$((total + 1))
    
    # 检查是否已处理
    processed=$(get_processed)
    if echo "$processed" | grep -qF "$fname"; then
        continue
    fi
    
    # 发现新原型 → 调用 create_bitable_task.py 创建研发任务
    feature_name=$(extract_name "$fname")
    task_hash=$(echo -n "$fname" | md5sum | cut -c1-6 | tr 'a-z' 'A-Z')
    task_id="PROTO-${task_hash}"
    
    echo "[$(date)] 发现新原型: $fname -> 任务: $task_id" >> "$LOG_FILE"
    
    # 读取原型前500字符作为描述
    description="【原型研发】${feature_name}

参考：$f

状态：待领取"

    # 调用飞书API创建任务
    python3 /opt/AiComic/scripts/create_bitable_task.py \
        --task-id "$task_id" \
        --description "$description" \
        --source "prototype" \
        --assignee "研发机器人" >> "$LOG_FILE" 2>&1
    
    # 标记已处理
    mark_processed "$fname"
    new_count=$((new_count + 1))
    
    echo "[$(date)] 已创建任务: $task_id" >> "$LOG_FILE"
done

echo "[$(date)] 原型扫描完成：共${total}个，新增${new_count}个" >> "$LOG_FILE"
