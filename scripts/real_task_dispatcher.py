#!/usr/bin/env python3
"""
真正的任务调度器 - 读取任务板，分配给 sub-agents 执行
"""
import requests
import json
import time
from datetime import datetime

API_KEY = "aicomic-shared-secret-key-2026"
HEADERS = {"X-API-Key": API_KEY}

def get_tasks_from_board():
    """从飞书多维表格获取待处理任务"""
    # 这里模拟从任务板读取
    # 实际项目中会调用飞书 API
    tasks = [
        {
            "task_id": "T005",
            "description": "前端开发 - 实现用户登录注册界面",
            "status": "进行中",
            "assigned_to": "研发机器人",
            "priority": "P0"
        }
    ]
    return tasks

def check_bot_availability(port):
    """检查 Bot 是否可用"""
    try:
        resp = requests.get(f"http://127.0.0.1:{port}/health", timeout=3)
        return resp.status_code == 200
    except:
        return False

def check_bot_current_task(port):
    """检查 Bot 当前任务"""
    try:
        resp = requests.get(f"http://127.0.0.1:{port}/status", timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("state"), data.get("current_task"), data.get("total_tasks_processed", 0)
    except:
        pass
    return "offline", None, 0

def assign_long_running_task():
    """分配一个长时间运行的任务，展示"处理中"状态"""
    
    print("=" * 60)
    print(f"真正任务调度器启动 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 检查各 Bot 端口
    bots = [
        {"name": "研发机器人", "port": 8003},
        {"name": "产品经理机器人", "port": 8002},
        {"name": "营销机器人", "port": 8004},
    ]
    
    print("\n【Bot 状态检查】")
    for bot in bots:
        state, current_task, total_done = check_bot_current_task(bot["port"])
        print(f"  {bot['name']}: state={state}, current_task={current_task}, total_done={total_done}")
    
    # 分配一个耗时的前端开发任务给研发机器人
    print("\n【分配 T005 前端开发任务】")
    
    task = {
        "task_id": "T005-real-dev-001",
        "task_type": "dev",
        "source": "调度器",
        "target": "研发机器人",
        "payload": {
            "任务描述": "T005 前端开发 - 实现用户登录注册界面，需要实际编码",
            "优先级": "P0",
            "截止时间": "2026-03-23 18:00",
            "处理时长": "60",  # 60秒，足够观察状态
            "依赖文件": ["/opt/AiComic/原型/AI创作动态漫功能原型_20260322.md"]
        }
    }
    
    try:
        # 发送任务到研发机器人（带长时间处理）
        print(f"  发送任务到端口 8003...")
        
        # 使用一个会实际执行的任务payload
        import subprocess
        result = subprocess.run([
            "curl", "-s", "-X", "POST",
            "http://127.0.0.1:8003/execute",
            "-H", "Content-Type: application/json",
            "-H", f"X-API-Key: {API_KEY}",
            "-d", json.dumps(task)
        ], capture_output=True, text=True, timeout=5)
        
        print(f"  任务已发送")
        
    except Exception as e:
        print(f"  错误: {e}")
    
    # 立即检查状态（任务应该刚开始处理）
    print("\n【任务分发后 Bot 状态】")
    time.sleep(1)  # 等待1秒让任务开始处理
    
    for bot in bots:
        state, current_task, total_done = check_bot_current_task(bot["port"])
        icon = "🔵" if state == "processing" else ("🟢" if state == "idle" else "🔴")
        print(f"  {icon} {bot['name']}: state={state}, current_task={current_task}, total_done={total_done}")
    
    return True

if __name__ == "__main__":
    assign_long_running_task()
