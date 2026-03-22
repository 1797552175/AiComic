"""
数据库模型 - SQLAlchemy + SQLite (本地开发/测试用)
生产环境请切换到 PostgreSQL
"""
import uuid
import os
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean,
    DateTime, ForeignKey, JSON, Index, create_engine
)
from sqlalchemy.ext.asyncio import AsyncAttrs, create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column
from sqlalchemy.sql import func

# 获取数据库 URL（优先使用环境变量，默认为本地 SQLite）
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:////tmp/aicomic.db"
)


# 异步引擎
engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(AsyncAttrs, DeclarativeBase):
    pass


# ========================
# 枚举类型
# ========================

class ProjectStatus:
    DRAFT = "draft"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ShotType:
    WIDE = "wide"
    FULL = "full"
    MEDIUM = "medium"
    CLOSE_UP = "close_up"
    TWO_SHOT = "two_shot"
    OVER_SHOULDER = "over_shoulder"
    POV = "pov"


class ShotStatus:
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class DialogueEmotion:
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

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=ProjectStatus.DRAFT)
    settings: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    characters: Mapped[List["Character"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    scenes: Mapped[List["Scene"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Character(Base):
    """角色"""
    __tablename__ = "characters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lora_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    features_vector: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    reference_images: Mapped[list] = mapped_column(JSON, default=list)
    emotion_default: Mapped[str] = mapped_column(String(32), default=DialogueEmotion.NEUTRAL)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    project: Mapped["Project"] = relationship(back_populates="characters")


class Scene(Base):
    """场景"""
    __tablename__ = "scenes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    project: Mapped["Project"] = relationship(back_populates="scenes")
    shots: Mapped[List["Shot"]] = relationship(back_populates="scene", cascade="all, delete-orphan")


class Shot(Base):
    """镜头"""
    __tablename__ = "shots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scene_id: Mapped[str] = mapped_column(String(36), ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    type: Mapped[str] = mapped_column(String(32), default=ShotType.MEDIUM)
    duration: Mapped[float] = mapped_column(Float, default=3.0)
    keywords: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    motion_data: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default=ShotStatus.PENDING)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    scene: Mapped["Scene"] = relationship(back_populates="shots")
    dialogues: Mapped[List["Dialogue"]] = relationship(back_populates="shot", cascade="all, delete-orphan")


class Dialogue(Base):
    """对话/旁白"""
    __tablename__ = "dialogues"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    shot_id: Mapped[str] = mapped_column(String(36), ForeignKey("shots.id", ondelete="CASCADE"), nullable=False)
    character_name: Mapped[str] = mapped_column(String(64), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    emotion: Mapped[str] = mapped_column(String(32), default=DialogueEmotion.NEUTRAL)
    audio_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    lip_sync_data: Mapped[dict] = mapped_column(JSON, default=dict)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    shot: Mapped["Shot"] = relationship(back_populates="dialogues")


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
