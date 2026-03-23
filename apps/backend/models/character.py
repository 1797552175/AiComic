"""角色模型 - 角色库管理核心模型"""
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class RoleType(str, Enum):
    """角色类型枚举"""
    PROTAGONIST = "protagonist"   # 主角
    SUPPORTING = "supporting"     # 配角
    EXTRA = "extra"               # 群演


class LoraxStatus(str, Enum):
    """LoRA状态枚举"""
    NONE = "none"                # 未绑定
    TRAINING = "training"        # 训练中
    READY = "ready"              # 可用
    FAILED = "failed"            # 训练失败


class CharacterFeature(BaseModel):
    """角色特征向量"""
    facial_features: List[float] = Field(default_factory=list, description="面部特征向量")
    clothing_features: List[float] = Field(default_factory=list, description="服装特征向量")
    hairstyle_features: List[float] = Field(default_factory=list, description="发型特征向量")
    eye_color: str = Field(default="", description="瞳色")
    skin_tone: str = Field(default="", description="肤色")
    accessories: List[str] = Field(default_factory=list, description="配饰列表")
    tags: List[str] = Field(default_factory=list, description="特征标签")


class Character(BaseModel):
    """角色卡片模型"""
    role_id: str = Field(default_factory=lambda: f"role_{uuid.uuid4().hex[:12]}", description="全局唯一角色ID")
    role_name: str = Field(..., description="角色名称")
    role_type: RoleType = Field(default=RoleType.SUPPORTING, description="角色类型")
    
    # 参考图管理
    reference_images: List[str] = Field(default_factory=list, description="参考图URL列表（3-5张多角度）")
    
    # 角色特征
    character_features: CharacterFeature = Field(default_factory=CharacterFeature, description="角色特征向量")
    
    # LoRA管理
    lora_model_path: Optional[str] = Field(default=None, description="绑定的LoRA模型路径")
    lora_strength: float = Field(default=0.85, ge=0.0, le=1.0, description="LoRA强度（0.0-1.0）")
    lora_status: LoraxStatus = Field(default=LoraxStatus.NONE, description="LoRA状态")
    
    # 风格描述
    style_prompt: str = Field(default="", description="角色风格描述词")
    
    # 关联管理
    project_ids: List[str] = Field(default_factory=list, description="关联项目ID列表")
    
    # 元数据
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    
    # 一致性评分
    consistency_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="最近一致性得分")
    
    class Config:
        use_enum_values = True


class CharacterCreateRequest(BaseModel):
    """创建角色请求"""
    role_name: str
    role_type: RoleType = RoleType.SUPPORTING
    reference_images: List[str] = Field(..., min_length=3, max_length=10, description="至少3张参考图")
    style_prompt: Optional[str] = ""
    project_id: Optional[str] = None


class CharacterUpdateRequest(BaseModel):
    """更新角色请求"""
    role_name: Optional[str] = None
    role_type: Optional[RoleType] = None
    reference_images: Optional[List[str]] = None
    style_prompt: Optional[str] = None
    lora_model_path: Optional[str] = None
    lora_strength: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    project_ids: Optional[List[str]] = None


class CharacterInjectionParams(BaseModel):
    """角色注入参数 - 用于生成时携带角色信息"""
    role_id: str
    character_features: Optional[CharacterFeature] = None
    lora_model_path: Optional[str] = None
    lora_strength: float = 0.85
    style_prompt: str = ""
    mode: str = Field(default="consistency_only", description="consistency_only=仅保持一致性, consistency_motion=保持一致+动作变化")


class ConsistencyScore(BaseModel):
    """一致性评分结果"""
    overall_score: float = Field(..., ge=0.0, le=1.0, description="总体一致性得分")
    facial_similarity: float = Field(..., ge=0.0, le=1.0, description="面部相似度")
    clothing_similarity: float = Field(..., ge=0.0, le=1.0, description="服装相似度")
    style_consistency: float = Field(..., ge=0.0, le=1.0, description="风格一致性")
    
    # 权重配置
    alpha: float = 0.5  # 面部权重
    beta: float = 0.3   # 服装权重
    gamma: float = 0.2  # 风格权重
    
    @classmethod
    def calculate(cls, facial: float, clothing: float, style: float) -> "ConsistencyScore":
        """计算一致性得分"""
        alpha, beta, gamma = 0.5, 0.3, 0.2
        overall = alpha * facial + beta * clothing + gamma * style
        return cls(
            overall_score=round(overall, 3),
            facial_similarity=round(facial, 3),
            clothing_similarity=round(clothing, 3),
            style_consistency=round(style, 3)
        )
