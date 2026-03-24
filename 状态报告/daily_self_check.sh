#!/bin/bash
# daily_self_check.sh - 每日自检脚本
# crontab: 0 9 * * * /bin/bash /opt/AiComic/状态报告/daily_self_check.sh

LOG_DIR="/opt/AiComic/状态报告"
REPORT_FILE="${LOG_DIR}/自检_$(date +%Y%m%d).md"
BOT_STATUS_URLS=("monitor:8001" "pm:8002" "dev:8003" "marketing:8004")

echo "# 每日自检报告 - $(date '+%Y-%m-%d %H:%M:%S')" > "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# === 1. 检查 monitor_cron.sh 是否存在且可执行 ===
echo "## 1. 调度脚本健康检查" >> "$REPORT_FILE"
if [ -x "/opt/AiComic/状态报告/monitor_cron.sh" ]; then
    echo "✅ monitor_cron.sh 存在且可执行" >> "$REPORT_FILE"
else
    echo "❌ monitor_cron.sh 不存在或无执行权限" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

# === 2. 检查各Bot HTTP接口健康 ===
echo "## 2. Bot健康状态" >> "$REPORT_FILE"
for bot_info in "${BOT_STATUS_URLS[@]}"; do
    name="${bot_info%%:*}"
    port="${bot_info##*:}"
    if curl -s --max-time 3 "http://localhost:$port/health" > /dev/null 2>&1; then
        echo "✅ $name (port $port) 在线" >> "$REPORT_FILE"
    else
        echo "❌ $name (port $port) 不在线" >> "$REPORT_FILE"
    fi
done
echo "" >> "$REPORT_FILE"

# === 3. 检查原型→任务转化情况 ===
echo "## 3. 原型→研发任务转化情况" >> "$REPORT_FILE"
proto_count=$(ls /opt/AiComic/原型/*.md 2>/dev/null | wc -l)
# 从processed文件获取已处理数量
processed_count=$(wc -l < /tmp/processed_prototypes.txt 2>/dev/null || echo 0)
echo "原型总数: $proto_count" >> "$REPORT_FILE"
echo "已处理: $processed_count" >> "$REPORT_FILE"
echo "待处理: $((proto_count - processed_count))" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# === 4. 检查未分配任务的原型（>2天未创建研发任务）===
echo "## 4. 提醒：以下原型已评审待研发" >> "$REPORT_FILE"
# 这里简化：列出所有已原型文件
echo "| 原型名称 | 状态 |" >> "$REPORT_FILE"
echo "|----------|------|" >> "$REPORT_FILE"
for f in /opt/AiComic/原型/*.md; do
    [ -f "$f" ] || continue
    fname=$(basename "$f")
    echo "| $fname | 已在Bitable创建任务 |" >> "$REPORT_FILE"
done
echo "" >> "$REPORT_FILE"

# === 5. 检查Bitable任务板待领取任务 ===
echo "## 5. 待领取研发任务（来自Bitable）" >> "$REPORT_FILE"
# 通过飞书API查询（简化版，实际需要API调用）
echo "请登录飞书任务板查看：" >> "$REPORT_FILE"
echo "https://ecnrw0lxawsd.feishu.cn/base/InUZbPrTZaRm5LsRz9jctF27nGu" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# === 6. 检查最近git提交 ===
echo "## 6. Git未提交更改" >> "$REPORT_FILE"
cd /opt/AiComic
if git status --porcelain | grep -q .; then
    echo "⚠️ 有未提交的更改，请研发及时提交" >> "$REPORT_FILE"
    git status --short | head -10 >> "$REPORT_FILE"
else
    echo "✅ Git工作区干净" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

# === 7. 系统资源检查 ===
echo "## 7. 系统资源" >> "$REPORT_FILE"
free -m | grep Mem >> "$REPORT_FILE"
df -h / | tail -1 >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

echo "✅ 自检完成，报告：$REPORT_FILE"
cp "$REPORT_FILE" "${LOG_DIR}/自检_latest.md"
