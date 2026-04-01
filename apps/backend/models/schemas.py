"""
Pydantic Schemas - API 请求/响应模型
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ========================
# 项目相关
# ========================

class ProjectCreate(BaseModel):
    """创建项目"""
    title: str = Field(..., min_length=1, max_length=255)
    user_id: str = Field(..., min_length=1)
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ProjectUpdate(BaseModel):
    """更新项目"""
    title: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


class ProjectResponse(BaseModel):
    """项目响应"""
    id: str
    user_id: str
    title: str
    status: str
    settings: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ========================
# 角色相关
# ========================

class CharacterCreate(BaseModel):
    """创建角色"""
    name: str = Field(..., min_length=1, max_length=64)
    description: Optional[str] = None
    emotion_default: Optional[str] = "neutral"
    reference_images: Optional[List[str]] = Field(default_factory=list)


class CharacterResponse(BaseModel):
    """角色响应"""
    id: str
    project_id: str
    name: str
    description: Optional[str]
    lora_path: Optional[str]
    features_vector: Optional[List[float]]
    reference_images: List[str]
    emotion_default: str
    created_at: datetime

    class Config:
        from_attributes = True


# ========================
# 剧本解析
# ========================

class ScriptParseRequest(BaseModel):
    """剧本解析请求"""
    script_text: str = Field(..., min_length=1)
    style: Optional[str] = "anime"  # anime/realistic/cyberpunk/ink/bw


class DialogueItem(BaseModel):
    """对话项"""
    character: str
    text: str
    emotion: Optional[str] = "neutral"


class ShotData(BaseModel):
    """镜头数据"""
    id: str
    type: str = "medium"
    duration: float = 3.0
    keywords: str = ""
    description: str = ""
    dialogue: List[DialogueItem] = Field(default_factory=list)


class SceneData(BaseModel):
    """场景数据"""
    id: str
    location: str
    shots: List[ShotData] = Field(default_factory=list)


class CharacterData(BaseModel):
    """角色数据"""
    name: str
    description: str = ""
    emotion_default: str = "neutral"


class ScriptParseResponse(BaseModel):
    """剧本解析响应"""
    project_id: str
    scenes: List[SceneData]
    characters: List[CharacterData]
    warnings: List[str] = Field(default_factory=list)


# ========================
# 分镜相关
# ========================

class ShotUpdate(BaseModel):
    """更新镜头"""
    type: Optional[str] = None
    duration: Optional[float] = None
    keywords: Optional[str] = None
    description: Optional[str] = None
    order_index: Optional[int] = None


class ShotGenerateRequest(BaseModel):
    """生成镜头请求"""
    shot_ids: List[str]
    style: str = "anime"
    quality: str = "hd"  # standard/hd/uhd
    character_consistency: bool = True


class ShotGenerateResponse(BaseModel):
    """生成镜头响应"""
    task_id: str
    status: str = "processing"
    estimated_time: int = 120  # 秒


# ========================
# 动态化相关
# ========================

class MotionApplyRequest(BaseModel):
    """应用动态效果请求"""
    shot_id: str
    motion_type: str = "static"  # static/pan_left/pan_right/zoom_in/tilt_up...
    motion_params: Dict[str, Any] = Field(default_factory=dict)


class LipSyncRequest(BaseModel):
    """口型同步请求"""
    shot_id: str
    dialogue_id: str


# ========================
# 音频相关
# ========================

class TTSRequest(BaseModel):
    """TTS请求"""
    text: str
    character_name: str
    emotion: str = "neutral"
    speed: float = 1.0
    pitch: float = 0.0


class BGMRecommendRequest(BaseModel):
    """BGM推荐请求"""
    scene_type: str  # happy/tense/romantic/sad/action
    duration: float


class BGMRecommendResponse(BaseModel):
    """BGM推荐响应"""
    bgm_url: str
    duration: float
    fade_in: float = 1.0
    fade_out: float = 1.0


# ========================
# 合成导出
# ========================

class ComposeRequest(BaseModel):
    """视频合成请求"""
    project_id: str
    quality: str = "hd"  # 480p/720p/1080p/4k
    format: str = "mp4"  # mp4/gif


class ComposeResponse(BaseModel):
    """视频合成响应"""
    task_id: str
    status: str = "processing"
    estimated_time: int = 300


class ExportRequest(BaseModel):
    """导出请求"""
    project_id: str
    format: str = "mp4"  # png_sequence/mp4/pdf/gif
    resolution: str = "1080p"  # 480p/720p/1080p/4k
    quality: str = "1080p"
    fps: int = 15
    title: Optional[str] = None


class ExportResponse(BaseModel):
    """导出任务响应"""
    task_id: str
    status: str = "processing"
    progress: int = 0
    estimated_time: int = 300


class ShareKitResponse(BaseModel):
    """分享信息响应"""
    project_id: str
    title: str
    share_url: str
    qr_code_url: str
    embed_code: str
    platforms: Dict[str, Dict[str, str]]


# ========================
# WebSocket 进度
# ========================

class ProgressUpdate(BaseModel):
    """进度更新"""
    type: str = "progress"
    task_id: str
    shot_id: Optional[str] = None
    progress: float  # 0.0 - 1.0
    status: str  # processing/completed/failed
    message: str = ""
    result: Optional[Dict[str, Any]] = None
