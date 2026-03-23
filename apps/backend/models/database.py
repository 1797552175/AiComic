"""
数据库模型 - SQLAlchemy + PostgreSQL
"""
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean,
    DateTime, ForeignKey, Enum as SQLEnum, JSON, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.asyncio import AsyncAttrs, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column
from sqlalchemy.sql import func

from app.config import settings


# 异步引擎
engine = create_async_engine(settings.database_url, echo=settings.debug, pool_pre_ping=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(AsyncAttrs, DeclarativeBase):
    pass


# ========================
# 枚举类型
# ========================

class ProjectStatus(str):
    DRAFT = "draft"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ShotType(str):
    WIDE = "wide"
    FULL = "full"
    MEDIUM = "medium"
    CLOSE_UP = "close_up"
    TWO_SHOT = "two_shot"
    OVER_SHOULDER = "over_shoulder"
    POV = "pov"


class ShotStatus(str):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class DialogueEmotion(str):
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SURPRISED = "surprised"
    NEUTRAL = "neutral"


# ========================
# 数据模型
# ========================

class Project(Base):
    """项目"""
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=ProjectStatus.DRAFT)
    settings: Mapped[dict] = mapped_column(JSON, default=dict)  # 风格、比例等全局设置
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    characters: Mapped[List["Character"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    scenes: Mapped[List["Scene"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Character(Base):
    """角色"""
    __tablename__ = "characters"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lora_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    features_vector: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # 角色特征向量
    reference_images: Mapped[list] = mapped_column(JSON, default=list)  # 参考图URL列表
    emotion_default: Mapped[str] = mapped_column(String(32), default=DialogueEmotion.NEUTRAL)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 关系
    project: Mapped["Project"] = relationship(back_populates="characters")


class Scene(Base):
    """场景"""
    __tablename__ = "scenes"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    location: Mapped[str] = mapped_column(String(255), nullable=False)  # 如 "街道·白天"
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 关系
    project: Mapped["Project"] = relationship(back_populates="scenes")
    shots: Mapped[List["Shot"]] = relationship(back_populates="scene", cascade="all, delete-orphan")


class Shot(Base):
    """镜头"""
    __tablename__ = "shots"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    scene_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    type: Mapped[str] = mapped_column(String(32), default=ShotType.MEDIUM)  # 镜头类型
    duration: Mapped[float] = mapped_column(Float, default=3.0)  # 秒
    keywords: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 生图关键词
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 镜头描述
    image_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)  # 生成图片URL
    motion_data: Mapped[dict] = mapped_column(JSON, default=dict)  # 运动参数
    status: Mapped[str] = mapped_column(String(32), default=ShotStatus.PENDING)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 关系
    scene: Mapped["Scene"] = relationship(back_populates="shots")
    dialogues: Mapped[List["Dialogue"]] = relationship(back_populates="shot", cascade="all, delete-orphan")


class Dialogue(Base):
    """对话/旁白"""
    __tablename__ = "dialogues"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    shot_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("shots.id", ondelete="CASCADE"), nullable=False)
    character_name: Mapped[str] = mapped_column(String(64), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    emotion: Mapped[str] = mapped_column(String(32), default=DialogueEmotion.NEUTRAL)
    audio_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)  # TTS生成的音频
    lip_sync_data: Mapped[dict] = mapped_column(JSON, default=dict)  # 口型关键帧
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 关系
    shot: Mapped["Shot"] = relationship(back_populates="dialogues")


class User(Base):
    """用户"""
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), unique=True, index=True, nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


# ========================
# 数据库初始化
# ========================

async def init_db():
    """初始化数据库表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """获取数据库会话"""
    async with async_session() as session:
        yield session
