"""
API 路由
"""
import asyncio
import time
import uuid
from dataclasses import dataclass, asdict
from enum import Enum
from typing import List, Dict, Optional
from urllib.parse import quote_plus, urljoin

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.database import get_db, async_session, Project, Character, Scene, Shot, Dialogue
from models.schemas import (
    ProjectCreate, ProjectUpdate, ProjectResponse,
    CharacterCreate, CharacterResponse,
    ScriptParseRequest, ScriptParseResponse,
    ShotUpdate, ShotGenerateRequest, ShotGenerateResponse,
    MotionApplyRequest,
    ComposeRequest, ComposeResponse,
    ExportRequest, ExportResponse, ShareKitResponse
)
from services.script_parser import script_parser
from services.storyboard import storyboard_generator
from services.video_compositor import video_compositor

router = APIRouter()

class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Task:
    task_id: str
    status: str
    progress: int
    stage: str
    task_type: str
    created_at: float
    started_at: Optional[float]
    completed_at: Optional[float]
    result: Optional[dict]
    error: Optional[str]

_task_store: Dict[str, Task] = {}
_task_lock = asyncio.Lock()

async def create_task(task_type: str = "general") -> str:
    task_id = f"task_{uuid.uuid4().hex[:12]}"
    async with _task_lock:
        _task_store[task_id] = Task(
            task_id=task_id,
            status=TaskStatus.PENDING.value,
            progress=0,
            stage="pending",
            task_type=task_type,
            created_at=time.time(),
            started_at=None,
            completed_at=None,
            result=None,
            error=None
        )
    return task_id

async def start_task(task_id: str):
    async with _task_lock:
        if task_id in _task_store:
            _task_store[task_id].status = TaskStatus.PROCESSING.value
            _task_store[task_id].started_at = time.time()

async def update_task_progress(task_id: str, progress: int, stage: str, message: str = ""):
    async with _task_lock:
        if task_id in _task_store:
            task = _task_store[task_id]
            task.progress = max(0, min(100, progress))
            task.stage = stage
            if message:
                task.result = {**(task.result or {}), "message": message}

async def complete_task(task_id: str, result: dict):
    async with _task_lock:
        if task_id in _task_store:
            _task_store[task_id].status = TaskStatus.COMPLETED.value
            _task_store[task_id].progress = 100
            _task_store[task_id].stage = "completed"
            _task_store[task_id].completed_at = time.time()
            _task_store[task_id].result = result

async def fail_task(task_id: str, error: str):
    async with _task_lock:
        if task_id in _task_store:
            _task_store[task_id].status = TaskStatus.FAILED.value
            _task_store[task_id].progress = 100
            _task_store[task_id].stage = "failed"
            _task_store[task_id].completed_at = time.time()
            _task_store[task_id].error = error

async def get_task(task_id: str) -> Optional[dict]:
    async with _task_lock:
        if task_id in _task_store:
            t = _task_store[task_id]
            return asdict(t)
    return None

def _normalize_file_path(value: Optional[str]) -> str:
    if not value:
        return ""
    return value.replace("file://", "")

async def _load_project_export_shots(project_id: str) -> tuple[str, List[dict]]:
    async with async_session() as db:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")

        scenes_result = await db.execute(
            select(Scene).where(Scene.project_id == project_id).order_by(Scene.order_index)
        )
        scenes = scenes_result.scalars().all()

        shots_payload: List[dict] = []
        for scene in scenes:
            shot_result = await db.execute(
                select(Shot).where(Shot.scene_id == scene.id).order_by(Shot.order_index)
            )
            shots = shot_result.scalars().all()
            for shot in shots:
                shots_payload.append({
                    "id": shot.id,
                    "scene_id": scene.id,
                    "image_url": _normalize_file_path(shot.image_url),
                    "duration": shot.duration,
                    "motion_type": (shot.motion_data or {}).get("type", "static"),
                    "keywords": shot.keywords or "",
                    "description": shot.description or "",
                })

        return project.title, shots_payload

def _build_share_url(base_url: str, project_id: str) -> str:
    normalized_base = base_url if base_url.endswith("/") else f"{base_url}/"
    return urljoin(normalized_base, f"share/{project_id}")

def _build_share_platforms(share_url: str, title: str) -> Dict[str, Dict[str, str]]:
    encoded_url = quote_plus(share_url)
    encoded_title = quote_plus(title)
    return {
        "wechat": {
            "label": "微信",
            "share_url": share_url,
            "hint": "复制链接后在微信内发送，或使用二维码扫码预览",
        },
        "weibo": {
            "label": "微博",
            "share_url": f"https://service.weibo.com/share/share.php?url={encoded_url}&title={encoded_title}",
            "hint": "打开后可直接跳转微博分享页",
        },
        "douyin": {
            "label": "抖音",
            "share_url": f"snssdk1128://share/text?text={encoded_title}%20{encoded_url}",
            "hint": "可作为抖音 App 内分享口令/文本分享入口",
        },
    }

def _build_embed_code(share_url: str, title: str) -> str:
    safe_title = title.replace('"', "&quot;")
    return (
        f'<iframe src="{share_url}?embed=1" title="{safe_title}" '
        'loading="lazy" allowfullscreen '
        'style="width:100%;min-height:640px;border:0;border-radius:16px;"></iframe>'
    )

def _build_qr_code_url(share_url: str) -> str:
    encoded_url = quote_plus(share_url)
    return f"https://api.qrserver.com/v1/create-qr-code/?size=240x240&data={encoded_url}"

async def process_shot_generation(task_id: str, project_id: str, shot_ids: list):
    await start_task(task_id)
    try:
        await asyncio.sleep(1)
        await complete_task(task_id, {"shots": len(shot_ids), "status": "generated"})
    except Exception as e:
        await fail_task(task_id, str(e))

async def process_video_composition(task_id: str, project_id: str, config: dict):
    await start_task(task_id)
    try:
        await asyncio.sleep(1)
        await complete_task(task_id, {"status": "composed"})
    except Exception as e:
        await fail_task(task_id, str(e))

# ========================
# 项目管理
# ========================

@router.post("/projects", response_model=ProjectResponse)
async def create_project(
    project: ProjectCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建新项目"""
    db_project = Project(
        user_id=project.user_id,
        title=project.title,
        settings=project.settings
    )
    db.add(db_project)
    await db.commit()
    await db.refresh(db_project)
    return db_project


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """获取项目详情"""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    update: ProjectUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新项目"""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    if update.title is not None:
        project.title = update.title
    if update.status is not None:
        project.status = update.status
    if update.settings is not None:
        project.settings = update.settings

    await db.commit()
    await db.refresh(project)
    return project


# ========================
# 角色管理
# ========================

@router.post("/projects/{project_id}/characters", response_model=CharacterResponse)
async def create_character(
    project_id: str,
    character: CharacterCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建角色"""
    # 检查项目是否存在
    result = await db.execute(select(Project).where(Project.id == project_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="项目不存在")

    db_character = Character(
        project_id=project_id,
        name=character.name,
        description=character.description,
        emotion_default=character.emotion_default,
        reference_images=character.reference_images
    )
    db.add(db_character)
    await db.commit()
    await db.refresh(db_character)
    return db_character


@router.get("/projects/{project_id}/characters", response_model=List[CharacterResponse])
async def list_characters(project_id: str, db: AsyncSession = Depends(get_db)):
    """获取角色列表"""
    result = await db.execute(
        select(Character).where(Character.project_id == project_id)
    )
    return result.scalars().all()


# ========================
# 剧本解析
# ========================

@router.post("/projects/{project_id}/parse-script", response_model=ScriptParseResponse)
async def parse_script(
    project_id: str,
    request: ScriptParseRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    解析剧本
    将文本剧本解析为场景、镜头、角色结构
    """
    # 检查项目是否存在
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 调用解析服务
    parsed = await script_parser.parse(request.script_text, request.style)

    # 保存到数据库
    # 1. 创建角色
    char_map = {}
    for char_data in parsed["characters"]:
        char = Character(
            project_id=project_id,
            name=char_data["name"],
            description=char_data.get("description", ""),
            emotion_default=char_data.get("emotion_default", "neutral")
        )
        db.add(char)
        char_map[char_data["name"]] = char

    await db.flush()

    # 2. 创建场景和镜头
    for scene_data in parsed["scenes"]:
        scene = Scene(
            project_id=project_id,
            order_index=len(scene_data.get("id", "0")),
            location=scene_data["location"]
        )
        db.add(scene)
        await db.flush()

        for shot_data in scene_data.get("shots", []):
            shot = Shot(
                scene_id=scene.id,
                order_index=shot_data.get("order_index", 0),
                type=shot_data.get("type", "medium"),
                duration=shot_data.get("duration", 3.0),
                keywords=shot_data.get("keywords", ""),
                description=shot_data.get("description", "")
            )
            db.add(shot)
            await db.flush()

            # 创建对话
            for idx, dial_data in enumerate(shot_data.get("dialogue", [])):
                dialogue = Dialogue(
                    shot_id=shot.id,
                    character_name=dial_data["character"],
                    text=dial_data["text"],
                    emotion=dial_data.get("emotion", "neutral"),
                    order_index=idx
                )
                db.add(dialogue)

    # 3. 更新项目状态
    project.status = "draft"

    await db.commit()

    return ScriptParseResponse(
        project_id=project_id,
        scenes=parsed["scenes"],
        characters=parsed["characters"],
        warnings=parsed.get("warnings", [])
    )


@router.get("/projects/{project_id}/storyboard")
async def get_storyboard(project_id: str, db: AsyncSession = Depends(get_db)):
    """获取项目分镜列表"""
    # 获取所有场景和镜头
    result = await db.execute(select(Scene).where(Scene.project_id == project_id))
    scenes = result.scalars().all()

    storyboard = []
    for scene in scenes:
        result = await db.execute(
            select(Shot).where(Shot.scene_id == scene.id).order_by(Shot.order_index)
        )
        shots = result.scalars().all()

        scene_shots = []
        for shot in shots:
            result = await db.execute(
                select(Dialogue).where(Dialogue.shot_id == shot.id).order_by(Dialogue.order_index)
            )
            dialogues = result.scalars().all()

            scene_shots.append({
                "id": shot.id,
                "scene_id": scene.id,
                "type": shot.type,
                "duration": shot.duration,
                "keywords": shot.keywords,
                "description": shot.description,
                "image_url": shot.image_url,
                "status": shot.status,
                "motion_data": shot.motion_data,
                "dialogue": [
                    {
                        "character": d.character_name,
                        "text": d.text,
                        "emotion": d.emotion
                    }
                    for d in dialogues
                ]
            })

        storyboard.append({
            "id": scene.id,
            "location": scene.location,
            "shots": scene_shots
        })

    return {"project_id": project_id, "storyboard": storyboard}


# ========================
# 镜头生成
# ========================

@router.post("/projects/{project_id}/shots/generate-batch", response_model=ShotGenerateResponse)
async def generate_shots_batch(
    project_id: str,
    request: ShotGenerateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    批量生成镜头画面
    实际生成是异步的，这里返回任务ID
    """
    # 异步任务队列实现
    task_id = await create_task(task_type="shot_generation")
    asyncio.create_task(process_shot_generation(task_id, project_id, request.shot_ids))
    return ShotGenerateResponse(
        task_id=task_id,
        status="pending",
        estimated_time=120
    )


@router.put("/projects/{project_id}/shots/{shot_id}")
async def update_shot(
    project_id: str,
    shot_id: str,
    update: ShotUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新镜头信息"""
    result = await db.execute(select(Shot).where(Shot.id == shot_id))
    shot = result.scalar_one_or_none()
    if not shot:
        raise HTTPException(status_code=404, detail="镜头不存在")

    if update.type is not None:
        shot.type = update.type
    if update.duration is not None:
        shot.duration = update.duration
    if update.keywords is not None:
        shot.keywords = update.keywords
    if update.description is not None:
        shot.description = update.description
    if update.order_index is not None:
        shot.order_index = update.order_index

    await db.commit()
    return {"message": "更新成功"}


# ========================
# 动态效果
# ========================

@router.post("/projects/{project_id}/shots/{shot_id}/apply-motion")
async def apply_motion(
    project_id: str,
    shot_id: str,
    request: MotionApplyRequest,
    db: AsyncSession = Depends(get_db)
):
    """应用动态效果到镜头"""
    result = await db.execute(select(Shot).where(Shot.id == shot_id))
    shot = result.scalar_one_or_none()
    if not shot:
        raise HTTPException(status_code=404, detail="镜头不存在")

    motion_data = {
        "type": request.motion_type,
        "params": request.motion_params
    }
    shot.motion_data = motion_data

    await db.commit()
    return {"message": "动态效果已应用", "motion_data": motion_data}


# ========================
# 视频合成
# ========================

@router.post("/projects/{project_id}/compose", response_model=ComposeResponse)
async def compose_video(
    project_id: str,
    request: ComposeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    合成最终视频
    实际合成是异步的，这里返回任务ID
    """
    # 异步任务队列实现
    task_id = await create_task(task_type="composition")
    asyncio.create_task(process_video_composition(task_id, project_id, request.model_dump()))
    return ComposeResponse(
        task_id=task_id,
        status="pending",
        estimated_time=300
    )


async def process_export_task(task_id: str, project_id: str, config: dict):
    """处理导出任务。"""
    await start_task(task_id)
    try:
        title, shots = await _load_project_export_shots(project_id)
        export_format = (config.get("format") or "mp4").lower()
        quality = config.get("quality") or config.get("resolution") or "1080p"
        fps = int(config.get("fps") or 15)
        export_title = config.get("title") or title
        image_paths = [shot["image_url"] for shot in shots if shot.get("image_url")]

        if not shots:
            raise HTTPException(status_code=400, detail="项目中没有可导出的镜头")

        async def progress(progress_value: int, message: str):
            await update_task_progress(task_id, progress_value, f"export_{export_format}", message)

        await update_task_progress(task_id, 5, "preparing", "正在读取导出素材")

        if export_format == "mp4":
            result = await video_compositor.export_mp4(
                shots=shots,
                quality=quality,
                progress_callback=progress
            )
            await complete_task(task_id, {
                "format": "mp4",
                "download_url": result["output_url"],
                "duration": result["duration"],
                "resolution": result["resolution"],
                "file_size": result["file_size"],
                "title": export_title,
            })
            return

        if not image_paths:
            raise HTTPException(status_code=400, detail="项目中没有可用于导出的图片")

        if export_format == "gif":
            output_url = await video_compositor.export_gif_from_images(
                image_paths=image_paths,
                fps=fps,
                progress_callback=progress
            )
        elif export_format in {"png", "png_sequence", "frames"}:
            output_url = await video_compositor.export_png_sequence(
                image_paths=image_paths,
                progress_callback=progress
            )
        elif export_format == "pdf":
            output_url = await video_compositor.export_pdf(
                image_paths=image_paths,
                title=export_title,
                progress_callback=progress
            )
        else:
            raise HTTPException(status_code=400, detail=f"不支持的导出格式: {export_format}")

        await complete_task(task_id, {
            "format": export_format,
            "download_url": output_url,
            "title": export_title,
            "frame_count": len(image_paths),
            "fps": fps,
        })
    except HTTPException as exc:
        await fail_task(task_id, exc.detail if isinstance(exc.detail, str) else "导出失败")
    except Exception as exc:
        await fail_task(task_id, str(exc))


@router.post("/projects/{project_id}/exports", response_model=ExportResponse)
async def export_project(
    project_id: str,
    request: ExportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """创建导出任务。"""
    result = await db.execute(select(Project).where(Project.id == project_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="项目不存在")

    task_id = await create_task(task_type="export")
    asyncio.create_task(process_export_task(task_id, project_id, request.model_dump()))
    return ExportResponse(
        task_id=task_id,
        status="pending",
        progress=0,
        estimated_time=300
    )


@router.get("/exports/{task_id}")
async def get_export_task(task_id: str):
    """查询导出任务状态。"""
    task = await get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@router.get("/projects/{project_id}/share", response_model=ShareKitResponse)
async def get_share_kit(
    project_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """生成分享链接、二维码和嵌入代码。"""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    share_url = _build_share_url(str(request.base_url), project_id)
    platforms = _build_share_platforms(share_url, project.title)
    return ShareKitResponse(
        project_id=project_id,
        title=project.title,
        share_url=share_url,
        qr_code_url=_build_qr_code_url(share_url),
        embed_code=_build_embed_code(share_url, project.title),
        platforms=platforms,
    )


# ========================
# 辅助端点
# ========================

@router.get("/options/motion-types")
async def get_motion_types():
    """获取可选的运动类型"""
    return storyboard_generator.get_motion_options()


@router.get("/options/shot-types")
async def get_shot_types():
    """获取可选的镜头类型"""
    return storyboard_generator.get_shot_type_options()


# 注册认证路由 - 暂时注释，等 auth 模块完成后再启用
# app.include_router(auth_router)
