"""
API 路由
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.database import get_db, Project, Character, Scene, Shot, Dialogue
from models.schemas import (
    ProjectCreate, ProjectUpdate, ProjectResponse,
    CharacterCreate, CharacterResponse,
    ScriptParseRequest, ScriptParseResponse,
    ShotUpdate, ShotGenerateRequest, ShotGenerateResponse,
    MotionApplyRequest,
    ComposeRequest, ComposeResponse
)
from services.script_parser import script_parser
from services.storyboard import storyboard_generator

router = APIRouter()


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
    # TODO: 实现异步任务队列
    return ShotGenerateResponse(
        task_id="task_placeholder",
        status="processing",
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
    异步任务队列：Celery + Redis
    返回任务ID，前端可轮询 /api/v1/tasks/{task_id} 查询状态
    """
    # 验证项目存在
    result = await db.execute(select(Project).where(Project.id == project_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="项目不存在")

    # 获取项目所有镜头（按顺序）
    result = await db.execute(
        select(Shot.id).where(Shot.scene_id.in_(
            select(Scene.id).where(Scene.project_id == project_id)
        )).order_by(Shot.order_index)
    )
    shot_ids = [row[0] for row in result.fetchall()]

    if not shot_ids:
        raise HTTPException(status_code=400, detail="项目没有镜头可合成")

    # 触发异步任务
    from tasks.compose_tasks import compose_video as compose_video_task
    celery_task = compose_video_task.delay(
        project_id=project_id,
        shot_ids=shot_ids,
        output_format=request.output_format or "mp4",
        fps=request.fps or 24,
        resolution=request.resolution or "1920x1080"
    )

    return ComposeResponse(
        task_id=celery_task.id,
        status="processing",
        estimated_time=len(shot_ids) * 3  # 估算每镜头3秒
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


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """
    查询异步任务状态
    用于轮询 video compose 等异步任务的进度
    """
    from tasks.compose_tasks import check_task_status
    result = check_task_status.delay(task_id)
    # 注意：这里返回的是 celery task 的 id，真正的状态需要等待异步结果
    return {
        "task_id": task_id,
        "status": "processing",
        "message": "任务已提交，请稍后查询"
    }


@router.get("/tasks/{task_id}/result")
async def get_task_result(task_id: str):
    """
    获取异步任务结果
    """
    from celery.result import AsyncResult
    from celery_app import celery_app
    
    result = AsyncResult(task_id, app=celery_app)
    
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
        "ready": result.ready(),
        "successful": result.successful() if result.ready() else False
    }
