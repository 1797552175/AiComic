#!/usr/bin/env python3
"""
方案B：独立 Bot 调度器
监控任务板 + HTTP 调用各 Bot + 故障降级
"""
import requests
import time
import json
from datetime import datetime
from typing import Optional, Dict, Any

API_KEY = "aicomic-shared-secret-key-2026"
HEADERS = {"X-API-Key": API_KEY}

# 端口配置
BOTS = {
    "monitor": {"port": 8001, "name": "状态监控机器人"},
    "pm": {"port": 8002, "name": "产品经理机器人"},
    "dev": {"port": 8003, "name": "研发机器人"},
    "marketing": {"port": 8004, "name": "营销机器人"},
}

class Dispatcher:
    """调度器 - 方案B核心"""
    
    def __init__(self):
        self.failure_count = {}  # 每个 Bot 的连续失败次数
        self.active_tasks = {}   # 当前进行中的任务
        self.use_plan_b = False  # 是否降级到方案B
        
    def dispatch_task(self, task: dict, target_bot: str) -> dict:
        """向指定 Bot 分发任务"""
        if target_bot not in BOTS:
            return {"code": 1, "message": f"未知 Bot: {target_bot}"}
        
        port = BOTS[target_bot]["port"]
        name = BOTS[target_bot]["name"]
        
        print(f"\n[调度器] 向 {name} 分发任务: {task['task_id']}")
        
        try:
            response = requests.post(
                f"http://127.0.0.1:{port}/execute",
                json=task,
                headers=HEADERS,
                timeout=300
            )
            
            if response.status_code == 200:
                result = response.json()
                self.failure_count[target_bot] = 0  # 重置失败计数
                
                # 检查是否需要降级
                if self.use_plan_b and result.get("code") == 0:
                    print(f"[调度器] {name} 恢复，切换回方案A")
                    self.use_plan_b = False
                
                return result
            else:
                return {"code": 1, "message": f"HTTP {response.status_code}"}
                
        except requests.exceptions.ConnectionError:
            self.failure_count[target_bot] = self.failure_count.get(target_bot, 0) + 1
            print(f"[调度器] {name} 连接失败 ({self.failure_count[target_bot]}/3)")
            return {"code": 1, "message": "连接失败"}
            
        except requests.exceptions.Timeout:
            self.failure_count[target_bot] = self.failure_count.get(target_bot, 0) + 1
            print(f"[调度器] {name} 请求超时 ({self.failure_count[target_bot]}/3)")
            return {"code": 1, "message": "请求超时"}
    
    def check_bot_health(self, target_bot: str) -> bool:
        """检查 Bot 是否健康"""
        if target_bot not in BOTS:
            return False
        
        port = BOTS[target_bot]["port"]
        
        try:
            response = requests.get(f"http://127.0.0.1:{port}/health", timeout=3)
            return response.status_code == 200
        except:
            return False
    
    def should_degrade_to_plan_b(self) -> bool:
        """检查是否需要降级到方案B"""
        for bot, count in self.failure_count.items():
            if count >= 3:
                print(f"[调度器] {BOTS[bot]['name']} 连续失败 {count} 次，触发降级到方案B")
                return True
        return False

def assign_tasks_to_bots():
    """向各 Bot 分配任务，让它们忙起来"""
    dispatcher = Dispatcher()
    
    print("=" * 60)
    print(f"调度器启动 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 分配任务
    tasks = [
        {
            "task": {
                "task_id": "T005-dev-frontend-001",
                "task_type": "dev",
                "source": "状态监控机器人",
                "target": "研发机器人",
                "payload": {
                    "任务描述": "T005 前端开发 - 实现用户登录注册界面，使用 React + Tailwind CSS",
                    "优先级": "P0",
                    "截止时间": "2026-03-23 18:00",
                    "依赖文件": ["/opt/AiComic/原型/AI创作动态漫功能原型_20260322.md"]
                }
            },
            "bot": "dev"
        },
        {
            "task": {
                "task_id": "T005-pm-verify-001",
                "task_type": "analyze",
                "source": "状态监控机器人",
                "target": "产品经理机器人",
                "payload": {
                    "任务描述": "验证研发输出的前端代码是否符合原型要求",
                    "优先级": "P1",
                    "截止时间": "2026-03-23 17:00",
                    "依赖文件": ["/opt/AiComic/原型/AI创作动态漫功能原型_20260322.md"]
                }
            },
            "bot": "pm"
        },
        {
            "task": {
                "task_id": "T005-marketing-prep-001",
                "task_type": "market",
                "source": "状态监控机器人",
                "target": "营销机器人",
                "payload": {
                    "任务描述": "准备 T005 前端发布的推广素材和发布计划",
                    "优先级": "P1",
                    "截止时间": "2026-03-23 19:00",
                    "依赖文件": []
                }
            },
            "bot": "marketing"
        },
    ]
    
    print("\n📋 开始分配任务...\n")
    
    for item in tasks:
        task = item["task"]
        bot = item["bot"]
        
        result = dispatcher.dispatch_task(task, bot)
        
        if result.get("code") == 0:
            print(f"✅ {BOTS[bot]['name']} 接收到任务: {task['task_id']}")
        else:
            print(f"❌ {BOTS[bot]['name']} 任务分发失败: {result.get('message')}")
        
        time.sleep(0.5)  # 间隔发送
    
    print("\n" + "=" * 60)
    print("任务分配完成")
    print("=" * 60)
    
    return dispatcher

if __name__ == "__main__":
    dispatcher = assign_tasks_to_bots()
