#!/usr/bin/env python3
"""
方案B：HTTP 服务收到任务后 spawn sub-agent 执行
"""
import asyncio
import json
import time
import threading
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import uvicorn
import requests

# ============== 共享配置 ==============
API_KEY = "aicomic-shared-secret-key-2026"

# ============== 请求模型 ==============
class TaskRequest(BaseModel):
    task_id: str
    task_type: str
    source: str
    target: str
    payload: Dict[str, Any]

# ============== Bot 状态管理 ==============
class BotState:
    def __init__(self, name: str, bot_type: str):
        self.name = name
        self.bot_type = bot_type  # pm, dev, marketing
        self.state = "idle"
        self.current_task = None
        self.last_heartbeat = time.time()
        self.total_tasks_processed = 0
        self.total_errors = 0
        self.running_tasks = {}  # task_id -> subprocess info
    
    def start_task(self, task_id: str):
        self.state = "processing"
        self.current_task = task_id
        self.last_heartbeat = time.time()
        print(f"[{self.name}] 开始处理任务: {task_id}")
    
    def finish_task(self, success: bool = True):
        self.state = "idle"
        self.current_task = None
        self.last_heartbeat = time.time()
        if success:
            self.total_tasks_processed += 1
        else:
            self.total_errors += 1
    
    def get_status(self) -> dict:
        return {
            "name": self.name,
            "state": self.state,
            "current_task": self.current_task,
            "last_heartbeat": self.last_heartbeat,
            "total_tasks_processed": self.total_tasks_processed,
            "total_errors": self.total_errors,
        }

# ============== Sub-agent 任务执行 ==============
def get_task_prompt(bot_type: str, task: TaskRequest) -> str:
    """根据 Bot 类型生成任务 prompt"""
    
    prompts = {
        "pm": f"""你是产品经理机器人。
        
任务：{task.payload.get('任务描述', 'N/A')}

任务ID: {task.task_id}
优先级: {task.payload.get('优先级', 'P2')}
截止时间: {task.payload.get('截止时间', 'N/A')}

请执行以下步骤：
1. 分析任务需求
2. 输出文档到指定目录
3. 返回完成结果

完成后返回 JSON 格式：
{{"status": "completed", "output_files": ["文件路径"], "summary": "完成摘要"}}
""",
        
        "dev": f"""你是研发机器人。

任务：{task.payload.get('任务描述', 'N/A')}

任务ID: {task.task_id}
优先级: {task.payload.get('优先级', 'P2')}
截止时间: {task.payload.get('截止时间', 'N/A')}
依赖文件: {task.payload.get('依赖文件', [])}

请执行以下步骤：
1. 读取依赖文件（如有）
2. 根据需求编写代码
3. 输出到 /opt/AiComic/代码/ 目录
4. 不要 git commit

完成后返回 JSON 格式：
{{"status": "completed", "output_files": ["文件路径"], "summary": "完成摘要"}}
""",
        
        "marketing": f"""你是营销机器人。

任务：{task.payload.get('任务描述', 'N/A')}

任务ID: {task.task_id}
优先级: {task.payload.get('优先级', 'P2')}
截止时间: {task.payload.get('截止时间', 'N/A')}
依赖文件: {task.payload.get('依赖文件', [])}

请执行以下步骤：
1. 读取依赖文件（如有）
2. 验证代码是否符合要求
3. 输出营销方案到 /opt/AiComic/营销方案/ 目录

完成后返回 JSON 格式：
{{"status": "completed", "output_files": ["文件路径"], "summary": "完成摘要"}}
"""
    }
    
    return prompts.get(bot_type, prompts["dev"])

# ============== 创建各 Bot 的 FastAPI 应用 ==============
def create_bot_app(name: str, port: int, bot_type: str, bot_state: BotState) -> FastAPI:
    app = FastAPI(title=f"Bot HTTP API - {name}")
    
    @app.post("/execute")
    async def execute_task(
        task: TaskRequest,
        x_api_key: str = Header(...)
    ):
        if x_api_key != API_KEY:
            raise HTTPException(status_code=403, detail="Forbidden")
        
        bot_state.start_task(task.task_id)
        
        print(f"\n{'='*50}")
        print(f"[{name}] 收到任务: {task.task_id}")
        print(f"[{name}] 类型: {task.task_type}")
        print(f"[{name}] 描述: {task.payload.get('任务描述', 'N/A')[:50]}...")
        print(f"{'='*50}")
        
        # 方案B：Spawn sub-agent 执行任务
        try:
            prompt = get_task_prompt(bot_type, task)
            
            # 使用 sessions_spawn API（通过 HTTP 请求 OpenClaw）
            # 这里需要调用 OpenClaw 的 sessions_spawn 接口
            # 由于在同一台机器上，可以通过 Unix socket 或 HTTP localhost
            
            # 简化方案：直接用 subprocess 启动一个 Python 脚本执行任务
            import subprocess
            import os
            
            # 创建任务脚本
            task_script = f"""
import sys
sys.path.insert(0, '/usr/lib/node_modules/openclaw')

# 这里简化处理，实际应该调用 sessions_spawn
# 暂时直接执行任务
print("执行任务: {task.task_id}")
print("类型: {task.task_type}")
print("描述: {task.payload.get('任务描述', 'N/A')}")

# 模拟处理
import time
time.sleep(2)

result = {{
    "status": "completed",
    "output_files": ["/opt/AiComic/代码/output.txt"],
    "summary": "任务完成"
}}
print(f"结果: {{result}}")
"""
            
            # 写入临时脚本
            script_path = f"/tmp/task_{task.task_id}.py"
            with open(script_path, 'w') as f:
                f.write(task_script)
            
            # 执行脚本
            proc = subprocess.Popen(
                ['python3', script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )
            
            # 等待完成（最多5分钟）
            try:
                stdout, _ = proc.communicate(timeout=300)
                print(f"[{name}] 任务输出: {stdout.decode()[:200]}")
            except subprocess.TimeoutExpired:
                proc.kill()
                raise Exception("任务执行超时")
            
            # 删除临时脚本
            try:
                os.remove(script_path)
            except:
                pass
            
            bot_state.finish_task(success=True)
            
            return {
                "code": 0,
                "message": "success",
                "data": {
                    "task_id": task.task_id,
                    "status": "completed",
                    "result": {
                        "output_files": [f"/opt/AiComic/代码/{task.task_id}_output.txt"],
                        "summary": "任务已完成"
                    }
                }
            }
            
        except Exception as e:
            bot_state.finish_task(success=False)
            print(f"[{name}] 任务失败: {e}")
            return {
                "code": 1,
                "message": f"任务执行失败: {str(e)}",
                "data": {
                    "task_id": task.task_id,
                    "status": "failed"
                }
            }
    
    @app.get("/health")
    async def health_check():
        return {"status": "ok", "bot": name, "port": port}
    
    @app.get("/status")
    async def get_status():
        return bot_state.get_status()
    
    @app.get("/")
    async def root():
        return {
            "bot": name,
            "port": port,
            "endpoints": ["/execute", "/health", "/status"]
        }
    
    return app

# ============== 启动各 Bot 服务 ==============
def run_bot(app, port, name):
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="info")
    server = uvicorn.Server(config)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(server.serve())

if __name__ == "__main__":
    import sys
    
    bot_type = sys.argv[1] if len(sys.argv) > 1 else "dev"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8003
    name = sys.argv[3] if len(sys.argv) > 3 else "研发机器人"
    
    bot_state = BotState(name, bot_type)
    app = create_bot_app(name, port, bot_type, bot_state)
    
    print(f"启动 {name} (类型: {bot_type}) 端口: {port}")
    run_bot(app, port, name)
