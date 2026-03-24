#!/usr/bin/env python3
"""
Full-Load Monitor - 实时调度脚本（带队列限制）
⚠️ 核心修复：限制队列大小，只在有空闲槽位时分发任务
"""

import sys
import time
import json
import urllib.request
from datetime import datetime
import threading

# Bot 端口配置
BOT_PORTS = {
    "dev": 8003,
    "pm": 8002,
    "marketing": 8004,
    "monitor": 8001,
}

# ⚠️ 核心配置：队列限制
MAX_CONCURRENT = 2       # 最多同时执行任务数
MAX_QUEUE = 5            # 队列最大长度（不能超过！）

# 任务池
DEV_TASKS = [
    "执行原型研发任务，6 Agent并行开发",
    "优化后端API接口",
    "修复Bug并编写测试用例",
    "实现图片生成模块",
    "优化数据库查询性能",
    "编写API文档和示例",
]

PM_TASKS = [
    "优化原型文档（获客导向）- 简化操作流程",
    "补充真实使用场景，让用户一看就懂",
    "分析竞品功能差距，制定差异化策略",
    "评估功能优先级，输出MVP清单",
    "整理产品需求变更日志",
]

MARKETING_TASKS = [
    "验证已完成任务的营销价值，判断是否符合市场和获客导向",
    "分析结论：不符合市场 → 向PM提出产品优化需求",
    "分析结论：符合导向 → 产出营销方案",
    "生成小红书种草文案",
    "生成知乎技术文章",
    "制作产品使用场景案例",
]

API_KEY = "aicomic-shared-secret-key-2026"
CHECK_INTERVAL = 5
REPORT_INTERVAL = 60

# 全局调度器状态（带锁保护）
scheduler_state = {
    "active_tasks": {},  # {task_id: {"bot": "dev", "started": timestamp}}
    "queue": [],         # 等待执行的任务列表
    "lock": threading.Lock(),
    "total_accepted": 0,
    "total_rejected": 0,
}


def get_bot_status(bot_type):
    """获取 Bot 状态"""
    port = BOT_PORTS.get(bot_type)
    if not port:
        return None
    try:
        url = f"http://localhost:{port}/status"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
            return data
    except Exception as e:
        return {"status": "error", "error": str(e)}


def get_active_task_count(bot_type):
    """获取 Bot 当前活跃任务数"""
    with scheduler_state["lock"]:
        count = 0
        for task_id, info in scheduler_state["active_tasks"].items():
            if info.get("bot") == bot_type:
                count += 1
        return count


def get_total_active():
    """获取总活跃任务数"""
    with scheduler_state["lock"]:
        return len(scheduler_state["active_tasks"])


def add_to_queue(task_id, bot_type, desc):
    """加入队列（带队列大小限制）"""
    with scheduler_state["lock"]:
        # 检查队列是否已满
        if len(scheduler_state["queue"]) >= MAX_QUEUE:
            scheduler_state["total_rejected"] += 1
            return False, f"Queue full (max {MAX_QUEUE})"
        
        scheduler_state["queue"].append({
            "task_id": task_id,
            "bot": bot_type,
            "desc": desc,
            "queued_at": time.time()
        })
        scheduler_state["total_accepted"] += 1
        return True, f"Queued (position {len(scheduler_state['queue'])})"


def dispatch_next_if_available():
    """如果有空闲槽位且队列不为空，分发下一个任务"""
    with scheduler_state["lock"]:
        # 检查是否有空闲槽位
        if len(scheduler_state["active_tasks"]) >= MAX_CONCURRENT:
            return None
        
        # 队列是否为空
        if not scheduler_state["queue"]:
            return None
        
        # 取下一个任务
        task = scheduler_state["queue"].pop(0)
        
        # 标记为活跃
        scheduler_state["active_tasks"][task["task_id"]] = {
            "bot": task["bot"],
            "started": time.time()
        }
        
        return task


def mark_task_complete(task_id):
    """标记任务完成"""
    with scheduler_state["lock"]:
        if task_id in scheduler_state["active_tasks"]:
            del scheduler_state["active_tasks"][task_id]


def report_status(bot_statuses):
    """汇报所有 Bot 状态（最高优先级）"""
    with scheduler_state["lock"]:
        active = len(scheduler_state["active_tasks"])
        queue_len = len(scheduler_state["queue"])
    
    lines = []
    lines.append("=" * 60)
    lines.append(f"📊 全员工作状态汇报 ({datetime.now().strftime('%H:%M:%S')})")
    lines.append(f"⚠️ 队列限制: 活跃≤{MAX_CONCURRENT}, 队列≤{MAX_QUEUE}")
    lines.append("=" * 60)
    
    for bot_type, status in bot_statuses.items():
        icon = "✅" if status.get("status") != "error" else "❌"
        lines.append(f"{icon} {bot_type.upper()}: {status.get('status', 'unknown')}")
        if status.get("task_id"):
            lines.append(f"   当前任务: {status.get('task_id')}")
    
    lines.append(f"📈 调度状态: 活跃{active}/{MAX_CONCURRENT}, 队列{queue_len}/{MAX_QUEUE}")
    lines.append(f"📈 统计: 已接受{scheduler_state['total_accepted']}, 已拒绝{scheduler_state['total_rejected']}")
    lines.append("=" * 60)
    
    report = "\n".join(lines)
    print(report)
    return report


def dispatch_task(bot_type, task_id, description):
    """分发任务到指定 Bot"""
    try:
        data = json.dumps({
            "task_id": task_id,
            "task_type": bot_type,
            "desc": description,
        }).encode("utf-8")
        req = urllib.request.Request(
            "http://localhost:8001/execute",
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
        mark_task_complete(task_id)  # 标记完成，释放槽位
        return False


def main():
    if len(sys.argv) < 2:
        print("用法: python3 full_load_monitor.py <小时数>")
        sys.exit(1)
    
    hours = int(sys.argv[1])
    duration_seconds = hours * 3600
    end_time = time.time() + duration_seconds
    task_counter = 0
    last_report_time = time.time()
    last_dispatch_time = 0
    
    print(f"=" * 60)
    print(f"[Monitor] 全员满负载调度开始（带队列限制）")
    print(f"[Monitor] ⚠️ 限制: 活跃≤{MAX_CONCURRENT}, 队列≤{MAX_QUEUE}")
    print(f"[Monitor] 持续时间: {hours} 小时")
    print(f"=" * 60)
    
    while time.time() < end_time:
        remaining = int(end_time - time.time())
        elapsed = duration_seconds - remaining
        
        # ⚠️ 最高优先级：每60秒汇报状态
        if time.time() - last_report_time >= REPORT_INTERVAL:
            bot_statuses = {}
            for bot in ["monitor", "dev", "pm", "marketing"]:
                bot_statuses[bot] = get_bot_status(bot)
            report_status(bot_statuses)
            last_report_time = time.time()
        
        # 每30秒打印一次剩余时间
        if elapsed % 30 < CHECK_INTERVAL:
            mins = remaining // 60
            secs = remaining % 60
            with scheduler_state["lock"]:
                active = len(scheduler_state["active_tasks"])
                queue_len = len(scheduler_state["queue"])
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 剩余 {mins}分{secs}秒... 活跃{active}/{MAX_CONCURRENT}, 队列{queue_len}/{MAX_QUEUE}")
        
        # ⚠️ 核心修复：检查是否有空闲槽位，分发队列中的任务
        current_active = get_total_active()
        if current_active < MAX_CONCURRENT:
            # 有空闲槽位，分发下一个任务
            task = dispatch_next_if_available()
            if task:
                bot_type = task["bot"]
                task_id = task["task_id"]
                desc = task["desc"]
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 分发 {task_id} → {bot_type} (活跃{current_active+1}/{MAX_CONCURRENT})")
                if dispatch_task(bot_type, task_id, desc):
                    print(f"[{bot_type.upper()}] 分发成功")
                else:
                    print(f"[{bot_type.upper()}] 分发失败")
                    mark_task_complete(task_id)
        
        # 检查是否有新任务可以加入队列（限制分发频率）
        current_time = time.time()
        if current_time - last_dispatch_time >= CHECK_INTERVAL:
            last_dispatch_time = current_time
            
            # 检查各 Bot 状态
            for bot_type in ["dev", "pm", "marketing"]:
                status_info = get_bot_status(bot_type)
                if not status_info or status_info.get("status") == "error":
                    continue
                
                # 检查该 Bot 是否有空闲
                active_for_bot = get_active_task_count(bot_type)
                if status_info.get("status") == "idle" and active_for_bot == 0:
                    # Bot 空闲且没有活跃任务，可以加任务
                    task_counter += 1
                    
                    if bot_type == "dev":
                        task_id = f"PROTO-DEV-{task_counter:03d}"
                        desc = DEV_TASKS[task_counter % len(DEV_TASKS)]
                    elif bot_type == "pm":
                        task_id = f"PM-TASK-{task_counter:03d}"
                        desc = PM_TASKS[task_counter % len(PM_TASKS)]
                    else:
                        task_id = f"MARKETING-{task_counter:03d}"
                        desc = MARKETING_TASKS[task_counter % len(MARKETING_TASKS)]
                    
                    # ⚠️ 加入队列（带限制）
                    success, msg = add_to_queue(task_id, bot_type, desc)
                    if success:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] {bot_type.upper()} Bot 空闲 → {task_id}: {desc[:30]}...")
                        print(f"[Monitor] 任务已加入队列: {msg}")
                    else:
                        print(f"[Monitor] 任务被拒绝: {msg}")
        
        time.sleep(CHECK_INTERVAL)
    
    # 最终汇报
    print(f"=" * 60)
    print(f"[Monitor] 调度结束")
    print(f"[Monitor] 总计接受: {scheduler_state['total_accepted']}, 拒绝: {scheduler_state['total_rejected']}")
    print(f"=" * 60)


if __name__ == "__main__":
    main()
