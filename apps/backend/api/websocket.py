"""WebSocket进度推送服务"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import Dict, Optional, Any
from datetime import datetime
import json
import asyncio
import redis
import os
from enum import Enum

router = APIRouter(prefix="/ws", tags=["websocket"])


class MessageType(str, Enum):
    """WebSocket消息类型"""
    CONNECTED = "connected"
    PROGRESS = "progress"
    STAGE_CHANGE = "stage_change"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PING = "ping"
    PONG = "pong"


class TaskWebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # task_id -> WebSocket connection
        self.active_connections: Dict[str, WebSocket] = {}
        # task_id -> last progress (用于去重)
        self.last_progress: Dict[str, int] = {}
        # task_id -> last message time (用于推送频率控制)
        self.last_message_time: Dict[str, float] = {}
    
    async def connect(self, task_id: str, websocket: WebSocket):
        """建立WebSocket连接"""
        await websocket.accept()
        self.active_connections[task_id] = websocket
        self.last_message_time[task_id] = asyncio.get_event_loop().time()
        
        # 发送连接确认
        await self.send_message(task_id, {
            "type": MessageType.CONNECTED.value,
            "task_id": task_id,
            "message": "已建立连接，等待任务更新",
            "timestamp": datetime.now().isoformat()
        })
    
    def disconnect(self, task_id: str):
        """断开WebSocket连接"""
        if task_id in self.active_connections:
            del self.active_connections[task_id]
        if task_id in self.last_progress:
            del self.last_progress[task_id]
        if task_id in self.last_message_time:
            del self.last_message_time[task_id]
    
    async def send_message(self, task_id: str, data: Dict[str, Any]):
        """发送消息到客户端"""
        if task_id not in self.active_connections:
            return False
        
        websocket = self.active_connections[task_id]
        try:
            await websocket.send_json(data)
            self.last_message_time[task_id] = asyncio.get_event_loop().time()
            return True
        except Exception as e:
            # 连接断开，清理
            self.disconnect(task_id)
            return False
    
    async def send_progress(
        self, 
        task_id: str, 
        progress: int,
        stage: str,
        stage_detail: str = "",
        sub_progress: Optional[Dict[str, Any]] = None,
        estimated_remaining_seconds: Optional[int] = None
    ):
        """
        发送进度更新
        自动控制推送频率
        """
        # 检查推送频率
        if not self._should_send_progress(task_id, progress, stage):
            return
        
        message = {
            "type": MessageType.PROGRESS.value,
            "task_id": task_id,
            "progress": progress,
            "stage": stage,
            "stage_detail": stage_detail,
            "sub_progress": sub_progress or {},
            "timestamp": datetime.now().isoformat()
        }
        
        if estimated_remaining_seconds is not None:
            message["estimated_remaining_seconds"] = estimated_remaining_seconds
        
        await self.send_message(task_id, message)
    
    def _should_send_progress(
        self, 
        task_id: str, 
        progress: int, 
        stage: str
    ) -> bool:
        """
        判断是否应该推送进度更新
        根据推送频率控制策略
        """
        current_time = asyncio.get_event_loop().time()
        last_time = self.last_message_time.get(task_id, 0)
        time_delta = current_time - last_time
        
        # 阶段切换时立即推送
        if stage != getattr(self, _last_stage, {}).get(task_id):
            self._last_stage = getattr(self, _last_stage, {})
            self._last_stage[task_id] = stage
            return True
        
        # 0-10%: 每5秒
        if progress < 10:
            return time_delta >= 5
        # 10-90%: 每3秒
        elif progress < 90:
            return time_delta >= 3
        # 90-100%: 每1秒
        else:
            return time_delta >= 1
    
    async def send_stage_change(
        self,
        task_id: str,
        from_stage: str,
        to_stage: str,
        message: str = ""
    ):
        """发送阶段切换消息"""
        await self.send_message(task_id, {
            "type": MessageType.STAGE_CHANGE.value,
            "task_id": task_id,
            "from_stage": from_stage,
            "to_stage": to_stage,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
    
    async def send_success(
        self, 
        task_id: str, 
        result: Dict[str, Any]
    ):
        """发送成功消息"""
        await self.send_message(task_id, {
            "type": MessageType.SUCCESS.value,
            "task_id": task_id,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
        # 成功后断开连接
        self.disconnect(task_id)
    
    async def send_failure(
        self, 
        task_id: str, 
        error: Dict[str, Any]
    ):
        """发送失败消息"""
        await self.send_message(task_id, {
            "type": MessageType.FAILED.value,
            "task_id": task_id,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
        # 失败后断开连接
        self.disconnect(task_id)
    
    async def send_cancelled(self, task_id: str, message: str = ""):
        """发送取消确认消息"""
        await self.send_message(task_id, {
            "type": MessageType.CANCELLED.value,
            "task_id": task_id,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
        self.disconnect(task_id)
    
    def is_connected(self, task_id: str) -> bool:
        """检查任务是否已连接"""
        return task_id in self.active_connections
    
    def get_connection_count(self) -> int:
        """获取当前连接数"""
        return len(self.active_connections)


# 全局WebSocket管理器
websocket_manager = TaskWebSocketManager()


# ========== Redis状态存储 ==========

class TaskStatusStore:
    """任务状态Redis存储"""
    
    def __init__(self):
        self.redis_client = None
        self._connect()
    
    def _connect(self):
        """连接Redis"""
        try:
            redis_host = os.getenv("REDIS_HOST", "localhost")
            redis_port = int(os.getenv("REDIS_PORT", 6379))
            redis_db = int(os.getenv("REDIS_DB", 0))
            self.redis_client = redis.Redis(
                host=redis_host, 
                port=redis_port, 
                db=redis_db,
                decode_responses=True
            )
        except Exception as e:
            print(f"Redis connection failed: {e}")
            self.redis_client = None
    
    def set_task_status(
        self, 
        task_id: str, 
        status: str, 
        data: Optional[Dict[str, Any]] = None
    ):
        """设置任务状态"""
        if not self.redis_client:
            return
        
        key = f"task:{task_id}"
        import time
        import json
        
        mapping = {
            "status": status,
            "updated_at": int(time.time())
        }
        if data:
            mapping["data"] = json.dumps(data)
        
        self.redis_client.hset(key, mapping=mapping)
        self.redis_client.expire(key, 86400)  # 24小时过期
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        if not self.redis_client:
            return None
        
        key = f"task:{task_id}"
        data = self.redis_client.hgetall(key)
        
        if not data:
            return None
        
        result = {
            "task_id": task_id,
            "status": data.get("status"),
            "updated_at": data.get("updated_at")
        }
        
        if "data" in data:
            result["data"] = json.loads(data["data"])
        
        return result
    
    def delete_task_status(self, task_id: str):
        """删除任务状态"""
        if not self.redis_client:
            return
        
        key = f"task:{task_id}"
        self.redis_client.delete(key)


# 全局状态存储
task_status_store = TaskStatusStore()


# ========== WebSocket端点 ==========

@router.websocket("/tasks/{task_id}")
async def websocket_task_progress(websocket: WebSocket, task_id: str):
    """
    WebSocket连接端点
    客户端通过此端点订阅任务进度
    """
    await websocket_manager.connect(task_id, websocket)
    
    try:
        # 发送初始状态
        status = task_status_store.get_task_status(task_id)
        if status:
            await websocket_manager.send_message(task_id, {
                "type": "status_sync",
                "task_id": task_id,
                "status": status.get("status"),
                "timestamp": datetime.now().isoformat()
            })
        
        # 保持连接，处理心跳
        while True:
            try:
                # 接收客户端消息（心跳检测）
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                
                # 处理心跳
                if data == "ping":
                    await websocket.send_text("pong")
                    
            except asyncio.TimeoutError:
                # 超时，发送心跳检测
                try:
                    await websocket.send_json({
                        "type": "ping",
                        "timestamp": datetime.now().isoformat()
                    })
                except:
                    break
                    
    except WebSocketDisconnect:
        pass
    finally:
        websocket_manager.disconnect(task_id)


@router.get("/tasks/{task_id}/status")
async def get_task_status_endpoint(task_id: str):
    """HTTP端点：获取任务状态"""
    status = task_status_store.get_task_status(task_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return status


# ========== 辅助函数 ==========

async def broadcast_to_task(task_id: str, message: Dict[str, Any]):
    """广播消息到指定任务"""
    await websocket_manager.send_message(task_id, message)


async def broadcast_to_all(message: Dict[str, Any]):
    """广播消息到所有连接"""
    for task_id in list(websocket_manager.active_connections.keys()):
        await websocket_manager.send_message(task_id, message)
