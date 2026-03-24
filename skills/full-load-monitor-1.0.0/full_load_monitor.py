#!/usr/bin/env python3
"""
Full-Load Monitor - 实时调度脚本
当用户说"全员干活X小时"，启动此脚本

用法:
    python3 full_load_monitor.py <小时数>
示例:
    python3 full_load_monitor.py 2  # 监控2小时
"""

import sys
import time
import json
import subprocess
import urllib.request
from datetime import datetime

# Bot 端口配置
BOT_PORTS = {
    "dev": 8003,
    "pm": 8002,
    "marketing": 8004,
}

# 任务池（实际可执行的工作，按优先级排序）
# 优先级：DEV > PM产出原型 > PM驳回优化 > PM自维护 > MARKETING验证 > MARKETING营销

DEV_TASKS = [
    "执行原型研发任务，6 Agent并行开发",
    "优化后端API接口",
    "修复Bug并编写测试用例",
    "实现图片生成模块",
    "优化数据库查询性能",
    "编写API文档和示例",
]

PM_TASKS = [
    # 最高优先：任务板原型<5个时立马产出
    "分析任务板原型数量，不足5个立即产出新原型",
    # 第二优先：处理研发驳回的任务
    "处理研发驳回的原型，优化后更新任务状态",
    # 自维护工作
    "优化原型文档（获客导向）- 简化操作流程",
    "补充真实使用场景，让用户一看就懂",
    "分析竞品功能差距，制定差异化策略",
    "评估功能优先级，输出MVP清单",
]

MARKETING_TASKS = [
    # 最高优先：分析已完成的任务
    "分析已完成任务的营销价值，判断是否符合市场和获客导向",
    "分析结论：不符合市场 → 向PM提出产品优化需求",
    "分析结论：符合导向 → 产出营销方案",
    # 已完成的任务分析完 → 改成待删除状态
    "分析完成后更新任务状态为待删除",
    # 闲时任务
    "以获客为导向，提项目营销方面的需求",
    "整理项目的原型和文档",
    "分析产品产出的原型是否重复或者不合理",
    # 营销方案产出
    "生成小红书种草文案",
    "生成知乎技术文章",
    "生成公众号推广文章",
]

API_KEY = "aicomic-shared-secret-key-2026"
CHECK_INTERVAL = 5  # 每5秒检查一次


def get_bot_status(bot_type):
    """获取 Bot 状态"""
    port = BOT_PORTS.get(bot_type)
    if not port:
        return None
    try:
        url = f"http://localhost:{port}/status"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
            return data.get("status")
    except Exception as e:
        print(f"[{bot_type}] 状态检查失败: {e}")
        return None


def dispatch_task(bot_type, task_id, description, record_id=""):
    """分发任务到指定 Bot"""
    port = BOT_PORTS.get(bot_type)
    if not port:
        return False
    try:
        data = json.dumps({
            "task_id": task_id,
            "task_type": bot_type,
            "desc": description,
            "record_id": record_id,  # 任务板记录ID，用于后续更新
        }).encode("utf-8")
        req = urllib.request.Request(
            f"http://localhost:8001/execute",
            data=data,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": API_KEY
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            return result.get("status") == "ok"
    except Exception as e:
        print(f"[{bot_type}] 分发失败: {e}")
        return False


def update_task_status(record_id, status, result=""):
    """更新任务板状态（最高优先级）"""
    try:
        # 调用飞书 API 更新状态
        # 这是最高优先级，必须在通知之前完成
        print(f"[Monitor] ⚠️ 更新任务板: {record_id} → {status}")
        # 实际更新逻辑由 feishu_bitable_update_record 工具执行
        return True
    except Exception as e:
        print(f"[Monitor] 更新任务板失败: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("用法: python3 full_load_monitor.py <小时数>")
        sys.exit(1)
    
    hours = int(sys.argv[1])
    duration_seconds = hours * 3600
    end_time = time.time() + duration_seconds
    task_counter = 0
    
    print(f"=" * 60)
    print(f"[Monitor] 全员满负载调度开始")
    print(f"[Monitor] 持续时间: {hours} 小时")
    print(f"[Monitor] 结束时间: {datetime.fromtimestamp(end_time).strftime('%H:%M:%S')}")
    print(f"=" * 60)
    
    while time.time() < end_time:
        remaining = int(end_time - time.time())
        elapsed = duration_seconds - remaining
        
        # 每30秒打印一次状态
        if elapsed % 30 < CHECK_INTERVAL:
            mins = remaining // 60
            secs = remaining % 60
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 剩余 {mins}分{secs}秒...")
        
        # 检查各 Bot 状态
        for bot_type in ["dev", "pm", "marketing"]:
            status = get_bot_status(bot_type)
            
            if status == "idle":
                task_counter += 1
                task_id = f"TASK-{bot_type.upper()[:3]}-{task_counter:03d}"
                
                # 选择任务
                if bot_type == "dev":
                    desc = DEV_TASKS[task_counter % len(DEV_TASKS)]
                elif bot_type == "pm":
                    desc = PM_TASKS[task_counter % len(PM_TASKS)]
                else:
                    desc = MARKETING_TASKS[task_counter % len(MARKETING_TASKS)]
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {bot_type.upper()} Bot 空闲 → 分配 {task_id}: {desc}")
                
                if dispatch_task(bot_type, task_id, desc):
                    print(f"[{bot_type.upper()}] 任务分发成功")
                else:
                    print(f"[{bot_type.upper()}] 任务分发失败")
        
        time.sleep(CHECK_INTERVAL)
    
    print(f"=" * 60)
    print(f"[Monitor] 调度结束")
    print(f"[Monitor] 总计分配: {task_counter} 个任务")
    print(f"=" * 60)


if __name__ == "__main__":
    main()
