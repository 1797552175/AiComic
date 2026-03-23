"""
角色一致性服务
负责角色ID跨镜头一致性保障和LoRA注入逻辑

与 database.py 的 Character 模型对接，预留 LoRA 注入接口。
仅构建框架，不调用外部API。
"""
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field


# ========================
# 数据结构定义
# ========================

@dataclass
class CharacterFeatures:
    """角色特征向量（从 Character.features_vector 读取）"""
    features_vector: Optional[List[float]] = None
    reference_images: List[str] = field(default_factory=list)
    lora_path: Optional[str] = None
    lora_strength: float = 0.85


@dataclass
class InjectionResult:
    """LoRA注入结果"""
    success: bool
    enhanced_prompt: str
    lora_path: Optional[str] = None
    lora_strength: float = 0.0
    warning: Optional[str] = None


@dataclass
class ConsistencyCheckResult:
    """一致性检查结果"""
    character_id: str
    character_name: str
    features_loaded: bool
    lora_available: bool
    consistency_score: Optional[float] = None
    warnings: List[str] = field(default_factory=list)


# ========================
# CharacterConsistency 服务类
# ========================

class CharacterConsistency:
    """
    角色一致性服务

    核心职责：
    1. ensure_character_id - 确保角色ID在跨镜头生成时一致
    2. inject_lora_prompt  - 将LoRA信息注入到生成Prompt
    3. get_character_features - 获取角色特征向量
    """

    # 一致性阈值：得分 >= 0.85 视为达标
    CONSISTENCY_THRESHOLD = 0.85

    # 默认LoRA强度
    DEFAULT_LORA_STRENGTH = 0.85

    def __init__(self, db_session=None):
        """
        初始化角色一致性服务

        Args:
            db_session: SQLAlchemy 异步会话（可选，延迟传入）
        """
        self.db_session = db_session

    # ========================
    # 核心方法
    # ========================

    async def ensure_character_id(
        self,
        character_id: str,
        project_id: Optional[str] = None,
        raise_if_missing: bool = False
    ) -> ConsistencyCheckResult:
        """
        确保角色ID有效，并返回一致性检查结果

        流程：
        1. 根据 character_id 从数据库查询 Character 记录
        2. 校验 Character.project_id 与传入的 project_id 是否匹配
        3. 检查必要字段（reference_images、features_vector）是否完备
        4. 返回检查结果

        Args:
            character_id: 角色UUID字符串
            project_id: 项目ID（用于交叉校验，可选）
            raise_if_missing: 角色不存在时是否抛出异常

        Returns:
            ConsistencyCheckResult: 包含角色信息和一致性状态

        Raises:
            ValueError: 当 raise_if_missing=True 且角色不存在时
        """
        if not character_id:
            raise ValueError("character_id cannot be empty")

        # 从数据库查询角色
        character = await self._query_character_by_id(character_id)

        if character is None:
            if raise_if_missing:
                raise ValueError(f"Character not found: {character_id}")
            return ConsistencyCheckResult(
                character_id=character_id,
                character_name="",
                features_loaded=False,
                lora_available=False,
                warnings=[f"Character {character_id} not found in database"]
            )

        # 项目ID校验
        warnings = []
        if project_id and character.project_id != project_id:
            warnings.append(
                f"Character {character_id} belongs to project {character.project_id}, "
                f"but requested by project {project_id}"
            )

        # 字段完备性检查
        if not character.reference_images:
            warnings.append("Character has no reference_images; consistency may degrade")

        if not character.features_vector:
            warnings.append("Character has no features_vector; LoRA injection required for best consistency")

        lora_available = character.lora_path is not None and character.lora_path != ""

        return ConsistencyCheckResult(
            character_id=character.id,
            character_name=character.name,
            features_loaded=character.features_vector is not None,
            lora_available=lora_available,
            warnings=warnings
        )

    async def inject_lora_prompt(
        self,
        character_id: str,
        base_prompt: str,
        lora_strength: Optional[float] = None,
        mode: str = "lora_blend"
    ) -> InjectionResult:
        """
        将角色LoRA信息注入到生成Prompt

        预留 LoRA 注入接口，内部逻辑按如下步骤：
        1. 查询 Character 记录，获取 lora_path
        2. 检查 LoRA 文件是否存在（路径有效性）
        3. 根据 mode 构建增强Prompt：
           - "lora_only": 强LoRA模式，Prompt = <char_{id}> + base_prompt + <char_{id}>
           - "lora_blend": 混合模式，Prompt = <char_{id}> + base_prompt
           - "feature_inject": 使用 features_vector 注入，不依赖LoRA
        4. 返回 InjectionResult

        Args:
            character_id: 角色UUID
            base_prompt: 原始生成Prompt
            lora_strength: LoRA强度，覆盖默认值
            mode: 注入模式

        Returns:
            InjectionResult: 包含增强后的Prompt和LoRA参数
        """
        if not character_id:
            return InjectionResult(
                success=False,
                enhanced_prompt=base_prompt,
                warning="No character_id provided"
            )

        # 查询角色记录
        character = await self._query_character_by_id(character_id)

        if character is None:
            return InjectionResult(
                success=False,
                enhanced_prompt=base_prompt,
                warning=f"Character {character_id} not found"
            )

        # 确定LoRA路径和强度
        lora_path = character.lora_path
        strength = lora_strength if lora_strength is not None else (
            self.DEFAULT_LORA_STRENGTH
        )

        # 无LoRA时降级为纯Prompt/特征注入
        if not lora_path:
            return InjectionResult(
                success=False,
                enhanced_prompt=self._build_feature_prompt(character, base_prompt),
                lora_path=None,
                lora_strength=0.0,
                warning="No LoRA bound for this character; using feature-based prompt"
            )

        # 构建增强Prompt
        enhanced_prompt = self._build_lora_prompt(
            character_id, base_prompt, mode, strength
        )

        return InjectionResult(
            success=True,
            enhanced_prompt=enhanced_prompt,
            lora_path=lora_path,
            lora_strength=strength
        )

    async def get_character_features(
        self,
        character_id: str
    ) -> Optional[CharacterFeatures]:
        """
        获取角色特征向量

        从 Character.features_vector 读取特征，
        同时返回参考图列表和LoRA路径信息。

        Args:
            character_id: 角色UUID

        Returns:
            CharacterFeatures: 角色特征对象，角色不存在时返回 None
        """
        character = await self._query_character_by_id(character_id)

        if character is None:
            return None

        return CharacterFeatures(
            features_vector=character.features_vector,
            reference_images=character.reference_images or [],
            lora_path=character.lora_path,
            lora_strength=self.DEFAULT_LORA_STRENGTH
        )

    # ========================
    # 内部辅助方法
    # ========================

    async def _query_character_by_id(self, character_id: str):
        """
        从数据库查询 Character 记录

        使用延迟注入的 db_session 进行异步查询。
        若 db_session 未设置，返回 None（框架模式下不实际操作数据库）。

        Args:
            character_id: 角色UUID

        Returns:
            Character 模型实例或 None
        """
        if self.db_session is None:
            # 框架模式：无数据库会话，仅返回结构
            return None

        from sqlalchemy import select
        from models.database import Character

        result = await self.db_session.execute(
            select(Character).where(Character.id == character_id)
        )
        return result.scalar_one_or_none()

    def _build_lora_prompt(
        self,
        character_id: str,
        base_prompt: str,
        mode: str,
        strength: float
    ) -> str:
        """
        构建带LoRA标记的增强Prompt

        Args:
            character_id: 角色UUID
            base_prompt: 原始Prompt
            mode: lora_only | lora_blend | feature_inject
            strength: LoRA强度

        Returns:
            str: 增强后的Prompt
        """
        char_token = f"<char_{character_id}>"

        if mode == "lora_only" or strength > 0.7:
            # 强LoRA模式
            return f"{char_token} {base_prompt} {char_token}".strip()
        elif mode == "lora_blend":
            # 混合模式
            return f"{char_token} {base_prompt}".strip()
        else:
            # 弱LoRA或降级
            return base_prompt

    def _build_feature_prompt(
        self,
        character,
        base_prompt: str
    ) -> str:
        """
        无LoRA时，使用角色特征向量构建增强Prompt（框架预留）

        实际项目中这里会调用特征提取/比对服务。
        当前仅做框架层面的占位返回。

        Args:
            character: Character 模型实例
            base_prompt: 原始Prompt

        Returns:
            str: 基于特征的增强Prompt
        """
        # 框架预留：特征注入Prompt占位符
        feature_hint = f"[character:{character.name}]"
        return f"{feature_hint} {base_prompt}".strip()


# ========================
# 导出全局单例（框架模式）
# ========================

# 注意：仅在未注入 db_session 时使用
# 实际业务中应在依赖注入容器中创建实例
character_consistency_service = CharacterConsistency()
