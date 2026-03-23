"""
数据库模型 - SQLAlchemy 1.4 + SQLite (本地开发/测试用)
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
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from sqlalchemy.sql import func

# 获取数据库 URL（优先使用环境变量，默认为本地 SQLite）
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:////tmp/aicomic.db"
)


# 同步引擎
engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

# 创建同步会话工厂
SessionLocal = sessionmaker(
    engine, expire_on_commit=False
)

Base = declarative_base()


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

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    status = Column(String(32), default=ProjectStatus.DRAFT)
    settings = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    characters = relationship("Character", back_populates="project", cascade="all, delete-orphan")
    scenes = relationship("Scene", back_populates="project", cascade="all, delete-orphan")


class Character(Base):
    """角色"""
    __tablename__ = "characters"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(64), nullable=False)
    description = Column(Text, nullable=True)
    lora_path = Column(String(512), nullable=True)
    features_vector = Column(JSON, nullable=True)
    reference_images = Column(JSON, default=list)
    emotion_default = Column(String(32), default=DialogueEmotion.NEUTRAL)
    created_at = Column(DateTime, server_default=func.now())

    project = relationship("Project", back_populates="characters")


class Scene(Base):
    """场景"""
    __tablename__ = "scenes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    order_index = Column(Integer, default=0)
    location = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    project = relationship("Project", back_populates="scenes")
    shots = relationship("Shot", back_populates="scene", cascade="all, delete-orphan")


class Shot(Base):
    """镜头"""
    __tablename__ = "shots"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scene_id = Column(String(36), ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False)
    order_index = Column(Integer, default=0)
    type = Column(String(32), default=ShotType.MEDIUM)
    duration = Column(Float, default=3.0)
    keywords = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    image_url = Column(String(512), nullable=True)
    motion_data = Column(JSON, default=dict)
    status = Column(String(32), default=ShotStatus.PENDING)
    retry_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    scene = relationship("Scene", back_populates="shots")
    dialogues = relationship("Dialogue", back_populates="shot", cascade="all, delete-orphan")


class Dialogue(Base):
    """对话/旁白"""
    __tablename__ = "dialogues"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    shot_id = Column(String(36), ForeignKey("shots.id", ondelete="CASCADE"), nullable=False)
    character_name = Column(String(64), nullable=False)
    text = Column(Text, nullable=False)
    emotion = Column(String(32), default=DialogueEmotion.NEUTRAL)
    audio_url = Column(String(512), nullable=True)
    lip_sync_data = Column(JSON, default=dict)
    order_index = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    shot = relationship("Shot", back_populates="dialogues")


# ========================
# 数据库初始化
# ========================

def init_db():
    """初始化数据库表"""
    with engine.begin() as conn:
        Base.metadata.create_all(conn)


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
