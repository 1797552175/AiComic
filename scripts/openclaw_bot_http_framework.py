#!/usr/bin/env python3
"""
OpenClaw Bot 内嵌 FastAPI 服务 - 方案A实现框架
用于给每个 OpenClaw Bot 添加 HTTP /execute 端点

使用方法：
1. 在 OpenClaw Bot 启动时调用 start_bot_http_server(port=8002)
2. Bot 收到消息时调用 update_bot_state() 更新状态
3. 调用 register_task_handler() 注册任务处理函数
"""
import asyncio
import threading
import time
import json
import requests
from typing import Callable, Optional, Dict, Any
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import uvicorn

# ============== 共享配置 ==============
API_KEY = "aicomic-shared-secret-key-2026"

# ============== 请求/响应模型 ==============
class TaskRequest(BaseModel):
    task_id: str
    task_type: str
    source: str
    target: str
    payload: Dict[str, Any]

class TaskResponse(BaseModel):
    code: int
    message: str
    data: Optional[Dict[str, Any]] = None

# ============== Bot 状态管理 ==============
class BotState:
    """Bot 状态管理"""
    def __init__(self, name: str):
        self.name = name
        self.state = "idle"  # idle, processing, error
        self.current_task = None
        self.last_heartbeat = time.time()
        self.total_tasks_processed = 0
        self.total_errors = 0
    
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
            print(f"[{self.name}] 任务完成，成功")
        else:
            self.total_errors += 1
            print(f"[{self.name}] 任务完成，失败")
    
    def get_status(self) -> dict:
        return {
            "name": self.name,
            "state": self.state,
            "current_task": self.current_task,
            "last_heartbeat": self.last_heartbeat,
            "total_tasks_processed": self.total_tasks_processed,
            "total_errors": self.total_errors,
        }

# ============== 全局状态 ==============
_bot_state: Optional[BotState] = None
_task_handler: Optional[Callable] = None

# ============== 创建 Bot FastAPI 应用 ==============
def create_bot_app(name: str, port: int) -> FastAPI:
    """创建单个 Bot 的 FastAPI 应用"""
    app = FastAPI(title=f"Bot HTTP API - {name}")
    
    @app.post("/execute")
    async def execute_task(
        task: TaskRequest,
        x_api_key: str = Header(...)
    ):
        if x_api_key != API_KEY:
            raise HTTPException(status_code=403, detail="Forbidden: Invalid API Key")
        
        global _bot_state, _task_handler
        
        print(f"\n{'='*50}")
        print(f"[{name}] 收到任务: {task.task_id}")
        print(f"[{name}] 任务类型: {task.task_type}")
        print(f"[{name}] 来源: {task.source}")
        print(f"[{name}] 任务描述: {task.payload.get('任务描述', 'N/A')}")
        print(f"{'='*50}")
        
        # 更新状态为处理中
        _bot_state.start_task(task.task_id)
        
        # 调用任务处理函数
        if _task_handler:
            try:
                result = await _task_handler(task)
                _bot_state.finish_task(success=True)
                return TaskResponse(
                    code=0,
                    message="success",
                    data={
                        "task_id": task.task_id,
                        "status": "completed",
                        "result": result
                    }
                )
            except Exception as e:
                _bot_state.finish_task(success=False)
                return TaskResponse(
                    code=1,
                    message=f"任务执行失败: {str(e)}",
                    data={
                        "task_id": task.task_id,
                        "status": "failed"
                    }
                )
        else:
            _bot_state.finish_task(success=False)
            return TaskResponse(
                code=1,
                message="未注册任务处理函数",
                data={"task_id": task.task_id, "status": "failed"}
            )
    
    @app.get("/health")
    async def health_check():
        return {"status": "ok", "bot": name, "port": port}
    
    @app.get("/status")
    async def get_status():
        """返回 Bot 详细状态"""
        return _bot_state.get_status()
    
    @app.get("/")
    async def root():
        return {
            "bot": name,
            "port": port,
            "endpoints": ["/execute", "/health", "/status"]
        }
    
    return app

# ============== 启动 Bot HTTP 服务 ==============
def start_bot_http_server(
    name: str,
    port: int,
    task_handler: Optional[Callable] = None
):
    """
    启动 Bot 的内嵌 HTTP 服务
    
    参数:
        name: Bot 名称
        port: HTTP 服务端口
        task_handler: 任务处理函数，接受 TaskRequest，返回结果 dict
    """
    global _bot_state, _task_handler
    
    _bot_state = BotState(name)
    _task_handler = task_handler
    
    app = create_bot_app(name, port)
    
    def run_server():
        config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="info")
        server = uvicorn.Server(config)
        # Python 3.6 兼容方式
        loop = asyncio.get_event_loop()
        loop.run_until_complete(server.serve())
    
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    
    print(f"[{name}] HTTP 服务已启动，端口: {port}")
    print(f"[{name}] 端点: /execute, /health, /status")
    
    return _bot_state

# ============== 便捷函数 ==============
def dispatch_task(target_port: int, task: dict) -> dict:
    """
    向其他 Bot 发送任务
    """
    response = requests.post(
        f"http://127.0.0.1:{target_port}/execute",
        json=task,
        headers={"X-API-Key": API_KEY},
        timeout=300
    )
    return response.json()

def get_bot_status(port: int) -> dict:
    """获取其他 Bot 的状态"""
    response = requests.get(f"http://127.0.0.1:{port}/status", timeout=3)
    return response.json()

# ============== 使用示例 ==============
if __name__ == "__main__":
    # 示例：产品经理 Bot
    async def pm_handler(task: TaskRequest) -> dict:
        """产品经理任务处理函数"""
        print(f"[产品经理] 开始处理: {task.payload.get('任务描述', 'N/A')}")
        # 模拟处理
        await asyncio.sleep(1)
        return {
            "output_files": ["/opt/AiComic/原型/竞品分析_20260323.md"],
            "summary": "完成了竞品分析"
        }
    
    # 启动服务
    state = start_bot_http_server(
        name="产品经理机器人",
        port=8002,
        task_handler=pm_handler
    )
    
    # 保持运行
    print("产品经理 Bot HTTP 服务运行中，按 Ctrl+C 停止")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n停止服务")
