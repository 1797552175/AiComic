# /opt/AiComic/backend/app/api/share_export.py
# 后端API - 分享与导出

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from enum import Enum
import asyncio
import uuid
import os
from datetime import datetime
from io import BytesIO

router = APIRouter(prefix="/api/share-export", tags=["分享与导出"])

# 导出格式枚举
class ExportFormat(str, Enum):
    PNG_SEQUENCE = "png_sequence"
    MP4 = "mp4"
    PDF = "pdf"
    GIF = "gif"

# 分辨率枚举
class Resolution(str, Enum):
    HD_720P = "720p"
    FHD_1080P = "1080p"
    UHD_4K = "4k"

# 帧率枚举
class FrameRate(str, Enum):
    FPS_24 = "24fps"
    FPS_30 = "30fps"
    FPS_60 = "60fps"

# 请求模型
class ExportRequest(BaseModel):
    project_id: str
    format: ExportFormat
    resolution: Optional[Resolution] = Resolution.FHD_1080P
    frame_rate: Optional[FrameRate] = FrameRate.FPS_30

class ShareLinkRequest(BaseModel):
    project_id: str

# 响应模型
class ExportTaskResponse(BaseModel):
    task_id: str
    status: str
    message: str

class ExportProgressResponse(BaseModel):
    task_id: str
    progress: float
    status: str
    download_url: Optional[str] = None

class ShareLinkResponse(BaseModel):
    share_id: str
    share_url: str
    qrcode_url: str
    embed_code: str
    expires_at: str

# 导出任务存储(生产环境应使用Redis)
export_tasks = {}

@router.post("/export", response_model=ExportTaskResponse)
async def create_export_task(request: ExportRequest, background_tasks: BackgroundTasks):
    """创建导出任务"""
    task_id = str(uuid.uuid4())
    
    export_tasks[task_id] = {
        "project_id": request.project_id,
        "format": request.format,
        "resolution": request.resolution,
        "frame_rate": request.frame_rate,
        "progress": 0,
        "status": "pending",
        "created_at": datetime.now().isoformat()
    }
    
    # 后台执行导出任务
    background_tasks.add_task(run_export_task, task_id)
    
    return ExportTaskResponse(
        task_id=task_id,
        status="pending",
        message=f"导出任务已创建,格式: {request.format.value}"
    )

async def run_export_task(task_id: str):
    """模拟导出任务执行"""
    for i in range(0, 101, 10):
        await asyncio.sleep(0.5)
        export_tasks[task_id]["progress"] = i
        export_tasks[task_id]["status"] = "processing"
        # broadcast_progress stub - 实际环境替换为 WebSocket 推送
        try:
            from app.services.websocket_manager import broadcast_progress
            await broadcast_progress(task_id, {
                "task_id": task_id, "progress": i, "status": "processing"
            })
        except Exception:
            pass  # WebSocket manager 未实现时静默跳过

    # 生成下载URL
    download_url = f"/api/share-export/download/{task_id}"
    export_tasks[task_id]["status"] = "completed"
    export_tasks[task_id]["progress"] = 100
    export_tasks[task_id]["download_url"] = download_url

@router.get("/export/{task_id}/status", response_model=ExportProgressResponse)
async def get_export_status(task_id: str):
    """获取导出任务状态"""
    if task_id not in export_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = export_tasks[task_id]
    return ExportProgressResponse(
        task_id=task_id,
        progress=task["progress"],
        status=task["status"],
        download_url=task.get("download_url")
    )

@router.get("/download/{task_id}")
async def download_export(task_id: str):
    """下载导出文件"""
    if task_id not in export_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = export_tasks[task_id]
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="导出任务未完成")
    
    # 实际应返回真实文件,这里返回模拟响应
    filename = f"export_{task['format'].value}_{task_id[:8]}.{task['format'].value.split('_')[0] if '_' in task['format'].value else task['format'].value}"
    
    # 生成临时文件
    temp_dir = "/tmp/exports"
    os.makedirs(temp_dir, exist_ok=True)
    filepath = os.path.join(temp_dir, filename)
    
    with open(filepath, "w") as f:
        f.write(f"Mock export file for task {task_id}")
    
    return FileResponse(
        filepath,
        filename=filename,
        media_type="application/octet-stream"
    )

@router.post("/share-link", response_model=ShareLinkResponse)
async def create_share_link(request: ShareLinkRequest):
    """生成分享链接"""
    share_id = str(uuid.uuid4())[:12]
    
    base_url = os.getenv("BASE_URL", "https://aicomic.app")
    share_url = f"{base_url}/view/{share_id}"
    qrcode_url = f"/api/share-export/qrcode/{share_id}"
    embed_code = f'<iframe src="{share_url}/embed" width="100%" height="600" frameborder="0"></iframe>'
    
    # 7天后过期
    from datetime import timedelta
    expires_at = (datetime.now() + timedelta(days=7)).isoformat()
    
    return ShareLinkResponse(
        share_id=share_id,
        share_url=share_url,
        qrcode_url=qrcode_url,
        embed_code=embed_code,
        expires_at=expires_at
    )

@router.get("/qrcode/{share_id}")
async def generate_qrcode(share_id: str):
    """生成二维码"""
    import qrcode
    
    base_url = os.getenv("BASE_URL", "https://aicomic.app")
    share_url = f"{base_url}/view/{share_id}"
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(share_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    
    return StreamingResponse(buffer, media_type="image/png")

@router.post("/social-share")
async def social_share(platform: str, project_id: str):
    """社交分享(返回分享配置)"""
    share_configs = {
        "weibo": {
            "url": "https://service.weibo.com/share/share.php",
            "params": {"url": f"/view/{project_id}", "type": "button"}
        },
        "wechat": {
            "url": "weixin://dl/share",
            "params": {"url": f"/view/{project_id}"}
        },
        "douyin": {
            "url": "snssdk1128://dl/share",
            "params": {"content": f"我在AiComic创作了漫画,快来看看!"}
        }
    }
    
    if platform not in share_configs:
        raise HTTPException(status_code=400, detail="不支持的分享平台")
    
    return JSONResponse(share_configs[platform])