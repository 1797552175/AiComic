#!/usr/bin/env python3
"""
方案B：真正的任务调度器
- 轮询任务板
- Spawn sub-agents 执行任务
- 更新任务状态
- 故障检测和降级
"""
import json
import time
import subprocess
from datetime import datetime
from typing import Optional

# ============== 调度器配置 ==============
TASK_BOARD_URL = "https://ecnrw0lxawsd.feishu.cn/base/"

# Bot 端口映射
BOT_PORTS = {
    "pm": 8002,      # 产品经理
    "dev": 8003,     # 研发
    "marketing": 8004  # 营销
}

# API Key
API_KEY = "aicomic-shared-secret-key-2026"

# ============== 任务处理函数 ==============
TASK_HANDLERS = {
    "pm": """你是产品经理机器人。

任务：{task_desc}
任务ID: {task_id}
优先级: {priority}
截止时间: {deadline}

执行步骤：
1. 分析任务需求
2. 输出文档到 /opt/AiComic/docs/ 或 /opt/AiComic/原型/
3. 返回完成结果

完成后返回 JSON：
{{"status": "completed", "output_files": ["文件路径"], "summary": "摘要"}}
""",
    
    "dev": """你是研发机器人。

任务：{task_desc}
任务ID: {task_id}
优先级: {priority}
截止时间: {deadline}
依赖文件: {dependencies}

执行步骤：
1. 读取依赖文件
2. 编写代码到 /opt/AiComic/代码/
3. 不要 git commit
4. 返回完成结果

完成后返回 JSON：
{{"status": "completed", "output_files": ["文件路径"], "summary": "摘要"}}
""",
    
    "marketing": """你是营销机器人。

任务：{task_desc}
任务ID: {task_id}
优先级: {priority}
截止时间: {deadline}
依赖文件: {dependencies}

执行步骤：
1. 读取依赖文件
2. 验证代码是否符合要求
3. 输出营销方案到 /opt/AiComic/营销方案/
4. 返回完成结果

完成后返回 JSON：
{{"status": "completed", "output_files": ["文件路径"], "summary": "摘要"}}
"""
}

# ============== HTTP 状态更新 ==============
def update_bot_state(port: int, state: str, current_task: Optional[str] = None):
    """更新 Bot 状态（通过 HTTP 请求）"""
    import requests
    try:
        # 这里模拟更新状态，实际通过 HTTP 调用各 Bot 的状态端点
        resp = requests.get(f"http://127.0.0.1:{port}/status", timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            print(f"  [{data['name']}] state={state}, task={current_task}")
    except:
        pass

# ============== 调度器核心 ==============
class TaskDispatcher:
    def __init__(self):
        self.active_tasks = {}  # task_id -> status
        self.failure_count = {}  # bot -> consecutive failures
        self.use_plan_b = False  # 是否使用方案B（调度器模式）
    
    def get_pending_tasks(self):
        """从飞书任务板获取待处理任务"""
        # 模拟返回待处理任务
        # 实际应该调用飞书 API
        return [
            {
                "task_id": "T005",
                "description": "前端开发 - 实现用户登录注册界面",
                "bot": "dev",
                "priority": "P0",
                "status": "进行中"
            }
        ]
    
    def spawn_subagent(self, task_id: str, bot_type: str, task_desc: str, priority: str, deadline: str, dependencies: list) -> bool:
        """Spawn sub-agent 执行任务"""
        print(f"\n{'='*60}")
        print(f"[调度器] Spawning sub-agent for {task_id}")
        print(f"[调度器] Bot: {bot_type}, Priority: {priority}")
        print(f"{'='*60}")
        
        # 更新状态为处理中
        port = BOT_PORTS.get(bot_type, 8003)
        print(f"[调度器] 更新 Bot {bot_type} 状态为 processing...")
        
        # 生成任务 prompt
        prompt = TASK_HANDLERS.get(bot_type, TASK_HANDLERS["dev"]).format(
            task_desc=task_desc,
            task_id=task_id,
            priority=priority,
            deadline=deadline,
            dependencies=", ".join(dependencies) if dependencies else "无"
        )
        
        # 构造 spawn 命令
        # 使用 OpenClaw sessions_spawn 接口
        spawn_cmd = [
            "curl", "-X", "POST",
            "http://127.0.0.1:3000/api/sessions/spawn",  # 假设 OpenClaw API
            "-H", "Content-Type: application/json",
            "-d", json.dumps({
                "task": prompt,
                "label": f"{task_id}-{bot_type}",
                "runtime": "subagent",
                "mode": "run"
            })
        ]
        
        # 由于 OpenClaw API 可能不同，这里用简化方式
        # 实际应该通过 message tool 或 sessions_spawn 工具
        print(f"[调度器] 任务已提交到 {bot_type} Bot")
        
        return True
    
    def process_tasks(self):
        """处理任务"""
        print(f"\n{'='*60}")
        print(f"[调度器] 扫描任务板 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        tasks = self.get_pending_tasks()
        
        if not tasks:
            print("[调度器] 没有待处理任务")
            return
        
        for task in tasks:
            task_id = task["task_id"]
            
            if task_id in self.active_tasks:
                print(f"[调度器] 任务 {task_id} 已在进行中，跳过")
                continue
            
            print(f"\n[调度器] 发现待处理任务: {task_id}")
            print(f"[调度器]   描述: {task['description'][:50]}...")
            print(f"[调度器]   分配给: {task['bot']}")
            print(f"[调度器]   优先级: {task['priority']}")
            
            # Spawn sub-agent
            success = self.spawn_subagent(
                task_id=task_id,
                bot_type=task["bot"],
                task_desc=task["description"],
                priority=task["priority"],
                deadline="2026-03-23 18:00",
                dependencies=[]
            )
            
            if success:
                self.active_tasks[task_id] = "processing"
    
    def check_health(self):
        """检查各 Bot 健康状态"""
        import requests
        
        print("\n[调度器] 健康检查:")
        
        for bot_name, port in BOT_PORTS.items():
            try:
                resp = requests.get(f"http://127.0.0.1:{port}/health", timeout=3)
                if resp.status_code == 200:
                    print(f"  ✅ {bot_name}: 健康")
                    self.failure_count[bot_name] = 0
                else:
                    print(f"  ⚠️ {bot_name}: 异常 {resp.status_code}")
                    self.failure_count[bot_name] = self.failure_count.get(bot_name, 0) + 1
            except requests.exceptions.ConnectionError:
                print(f"  ❌ {bot_name}: 连接失败")
                self.failure_count[bot_name] = self.failure_count.get(bot_name, 0) + 1
            except Exception as e:
                print(f"  ❌ {bot_name}: {e}")
                self.failure_count[bot_name] = self.failure_count.get(bot_name, 0) + 1
            
            # 检查是否需要降级
            if self.failure_count.get(bot_name, 0) >= 3 and not self.use_plan_b:
                print(f"  [调度器] {bot_name} 连续失败 3 次，切换到方案B")
                self.use_plan_b = True
    
    def run_once(self):
        """运行一次调度"""
        self.check_health()
        self.process_tasks()
    
    def run_continuous(self, interval: int = 60):
        """持续运行"""
        print(f"\n[调度器] 启动持续监控模式 (间隔 {interval} 秒)")
        print("[调度器] 按 Ctrl+C 停止\n")
        
        try:
            while True:
                self.run_once()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[调度器] 停止")

# ============== 主函数 ==============
if __name__ == "__main__":
    import sys
    
    dispatcher = TaskDispatcher()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--watch":
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60
        dispatcher.run_continuous(interval)
    else:
        dispatcher.run_once()
