"""角色一致性服务 - LoRA注入逻辑"""
import os
import json
import hashlib
from typing import Optional, Dict, Any, List
from datetime import datetime
import asyncio

# 模拟的特征提取和相似度计算（实际项目中替换为真实ML模型）
class CharacterConsistencyService:
    """角色一致性服务"""
    
    def __init__(self):
        self.feature_cache: Dict[str, List[float]] = {}
        self.lora_cache: Dict[str, Dict[str, Any]] = {}
        
    async def extract_features(self, reference_images: List[str]) -> Dict[str, Any]:
        """
        提取角色特征
        实际项目中调用 CLIP/VIT 特征提取模型
        """
        # 模拟特征提取
        cache_key = hashlib.md5("".join(sorted(reference_images)).encode()).hexdigest()
        
        if cache_key in self.feature_cache:
            return {"cached": True, "features": self.feature_cache[cache_key]}
        
        # 模拟生成特征向量（实际项目中调用ML模型）
        features = {
            "facial_features": [0.1 * i for i in range(512)],
            "clothing_features": [0.2 * i for i in range(256)],
            "hairstyle_features": [0.3 * i for i in range(128)],
            "eye_color": "brown",
            "skin_tone": "fair",
            "accessories": [],
            "tags": ["anime", "young", "short_hair"]
        }
        
        self.feature_cache[cache_key] = [
            features["facial_features"], 
            features["clothing_features"],
            features["hairstyle_features"]
        ]
        
        return {"cached": False, "features": features}
    
    async def inject_lora(
        self, 
        role_id: str, 
        lora_model_path: Optional[str] = None,
        lora_strength: float = 0.85,
        base_prompt: str = ""
    ) -> Dict[str, Any]:
        """
        LoRA注入逻辑
        将角色LoRA信息注入到生成参数中
        """
        if not lora_model_path:
            return {
                "injected": False,
                "reason": "no_lora_bound",
                "enhanced_prompt": base_prompt
            }
        
        # 检查LoRA文件是否存在
        if not os.path.exists(lora_model_path):
            return {
                "injected": False,
                "reason": "lora_file_not_found",
                "enhanced_prompt": base_prompt
            }
        
        # 构建增强Prompt
        enhanced_prompt = self._build_enhanced_prompt(base_prompt, role_id, lora_strength)
        
        # 构建LoRA注入参数
        lora_params = {
            "model_path": lora_model_path,
            "strength": lora_strength,
            "trigger_word": f"char_{role_id}",
            "injection_mode": "lora_only" if lora_strength > 0.7 else "lora_blend"
        }
        
        return {
            "injected": True,
            "lora_params": lora_params,
            "enhanced_prompt": enhanced_prompt,
            "strength": lora_strength
        }
    
    def _build_enhanced_prompt(self, base_prompt: str, role_id: str, strength: float) -> str:
        """构建增强的生成Prompt"""
        role_token = f"<char_{role_id}>"
        
        if strength > 0.8:
            # 强LoRA模式
            enhanced = f"{role_token} {base_prompt} {role_token}"
        elif strength > 0.5:
            # 混合模式
            enhanced = f"{role_token} {base_prompt}"
        else:
            # 弱LoRA模式
            enhanced = f"{base_prompt}"
        
        return enhanced.strip()
    
    async def calculate_consistency(
        self, 
        reference_features: Dict[str, Any], 
        generated_image_features: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        计算一致性得分
        公式: 镜头一致性得分 = α × 面部相似度 + β × 服装相似度 + γ × 风格一致性
        默认权重：α=0.5, β=0.3, γ=0.2
        """
        # 模拟计算相似度（实际项目中调用特征匹配模型）
        facial_sim = 0.92  # 模拟值
        clothing_sim = 0.88  # 模拟值
        style_consistency = 0.90  # 模拟值
        
        # 一致性得分计算
        alpha, beta, gamma = 0.5, 0.3, 0.2
        overall_score = alpha * facial_sim + beta * clothing_sim + gamma * style_consistency
        
        return {
            "overall_score": round(overall_score, 3),
            "facial_similarity": round(facial_sim, 3),
            "clothing_similarity": round(clothing_sim, 3),
            "style_consistency": round(style_consistency, 3),
            "passed": overall_score >= 0.85
        }
    
    async def prepare_injection_params(
        self,
        role_id: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        准备角色注入参数
        用于镜头生成时自动携带角色信息
        """
        from models.character import Character, CharacterInjectionParams
        
        # 查找角色卡片（实际从数据库查询）
        character = await self._get_character(role_id)
        
        if not character:
            return {
                "success": False,
                "error": "character_not_found",
                "message": f"角色 {role_id} 不存在"
            }
        
        # 提取特征
        features_result = await self.extract_features(character.reference_images)
        
        # 构建注入参数
        injection_params = CharacterInjectionParams(
            role_id=role_id,
            character_features=features_result.get("features"),
            lora_model_path=character.lora_model_path,
            lora_strength=character.lora_strength,
            style_prompt=character.style_prompt,
            mode="consistency_motion"
        )
        
        # LoRA注入
        lora_result = await self.inject_lora(
            role_id=role_id,
            lora_model_path=character.lora_model_path,
            lora_strength=character.lora_strength,
            base_prompt=params.get("prompt", "")
        )
        
        return {
            "success": True,
            "injection_params": injection_params.dict(),
            "lora_result": lora_result,
            "features_cached": features_result.get("cached", False)
        }
    
    async def _get_character(self, role_id: str) -> Optional[Any]:
        """获取角色卡片（模拟）"""
        # 实际从数据库查询
        return None
    
    async def check_consistency_threshold(
        self,
        role_id: str,
        generated_features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        检查一致性是否达标
        返回建议或警告
        """
        # 模拟计算
        score_result = await self.calculate_consistency({}, generated_features)
        
        if score_result["overall_score"] >= 0.85:
            return {
                "passed": True,
                "score": score_result,
                "message": "一致性检查通过 ✅",
                "suggestions": []
            }
        else:
            return {
                "passed": False,
                "score": score_result,
                "message": f"一致性得分 {score_result[overall_score]:.1%} 低于阈值 85%",
                "suggestions": [
                    "建议增加参考图数量",
                    "建议训练专用LoRA模型",
                    "建议优化角色风格描述词"
                ]
            }


# 全局单例
consistency_service = CharacterConsistencyService()
