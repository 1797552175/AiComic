"""动态漫动效引擎 - 镜头运动预设 + 微动效"""
from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class MotionType(str, Enum):
    """镜头运动类型"""
    FIXED = "fixed"           # 固定
    PUSH_IN = "push_in"       # 推进
    PUSH_OUT = "push_out"     # 拉远
    PAN_LEFT = "pan_left"     # 左摇
    PAN_RIGHT = "pan_right"   # 右摇
    TILT_UP = "tilt_up"       # 上摇
    TILT_DOWN = "tilt_down"   # 下摇
    ORBIT = "orbit"           # 环绕
    FOLLOW = "follow"         # 跟随
    SHAKE = "shake"           # 震动


class MotionSpeed(str, Enum):
    """运动速度"""
    SLOW = "slow"
    MEDIUM = "medium"
    FAST = "fast"


class MicroEffectType(str, Enum):
    """微动效类型"""
    HAIR_FLOAT = "hair_float"           # 头发飘动
    BREATHING = "breathing"             # 呼吸起伏
    EXPRESSION_MICRO = "expression_micro"  # 表情微动
    CLOTHES_SWING = "clothes_swing"     # 衣物摆动
    EYE_BLINK = "eye_blink"             # 眼睛眨眼
    BACKGROUND_MICRO = "background_micro"  # 背景微动
    LIGHT_SHADOW = "light_shadow"       # 光影流动
    EFFECTS_OVERLAY = "effects_overlay"  # 特效叠加


class TransitionType(str, Enum):
    """转场动效类型"""
    NONE = "none"           # 硬切
    BLACK = "black"         # 黑场
    WHITE = "white"         # 白场
    CROSSFADE = "crossfade" # 叠化
    SLIDE = "slide"         # 滑动
    ZOOM = "zoom"           # 缩放
    MANGA_SPEED = "manga_speed"  # 漫画式速度线
    SHAKE_TRANSITION = "shake_transition"  # 震动转场


class CameraMotionPreset(BaseModel):
    """镜头运动预设"""
    motion_type: MotionType = MotionType.FIXED
    speed: MotionSpeed = MotionSpeed.MEDIUM
    
    # 起始/结束位置（0-100%）
    start_position: float = Field(default=0.0, ge=0, le=100)
    end_position: float = Field(default=100.0, ge=0, le=100)
    
    # 运动角度（用于摇镜头）
    angle: Optional[float] = Field(default=None, ge=-180, le=180)
    
    # 跟随目标
    follow_target_id: Optional[str] = None
    
    # 震动强度
    shake_intensity: Optional[float] = Field(default=None, ge=0, le=1)
    
    # 全局强度控制
    intensity: float = Field(default=1.0, ge=0, le=1)


class MicroEffectPreset(BaseModel):
    """微动效预设"""
    effect_type: MicroEffectType
    enabled: bool = True
    intensity: float = Field(default=0.5, ge=0, le=1)
    custom_params: Dict[str, Any] = Field(default_factory=dict)


class MicroEffectPackage(BaseModel):
    """微动效预设包"""
    name: str
    description: str
    effects: List[MicroEffectPreset]
    
    @classmethod
    def natural_breathing(cls) -> "MicroEffectPackage":
        """自然呼吸预设"""
        return cls(
            name="自然呼吸",
            description="自然的呼吸节奏，适合日常对话场景",
            effects=[
                MicroEffectPreset(effect_type=MicroEffectType.BREATHING, enabled=True, intensity=0.3),
                MicroEffectPreset(effect_type=MicroEffectType.EYE_BLINK, enabled=True, intensity=0.5),
                MicroEffectPreset(effect_type=MicroEffectType.BACKGROUND_MICRO, enabled=False),
            ]
        )
    
    @classmethod
    def dynamic_youth(cls) -> "MicroEffectPackage":
        """动感少年预设"""
        return cls(
            name="动感少年",
            description="活力四射的动感效果，适合动作场景",
            effects=[
                MicroEffectPreset(effect_type=MicroEffectType.HAIR_FLOAT, enabled=True, intensity=0.5),
                MicroEffectPreset(effect_type=MicroEffectType.CLOTHES_SWING, enabled=True, intensity=0.4),
                MicroEffectPreset(effect_type=MicroEffectType.EXPRESSION_MICRO, enabled=True, intensity=0.3),
            ]
        )
    
    @classmethod
    def serene_atmosphere(cls) -> "MicroEffectPackage":
        """静谧氛围预设"""
        return cls(
            name="静谧氛围",
            description="柔和的氛围效果，适合抒情场景",
            effects=[
                MicroEffectPreset(effect_type=MicroEffectType.LIGHT_SHADOW, enabled=True, intensity=0.2),
                MicroEffectPreset(effect_type=MicroEffectType.BACKGROUND_MICRO, enabled=True, intensity=0.15),
                MicroEffectPreset(effect_type=MicroEffectType.BREATHING, enabled=True, intensity=0.15),
            ]
        )
    
    @classmethod
    def battle_action(cls) -> "MicroEffectPackage":
        """战斗动感预设"""
        return cls(
            name="战斗动感",
            description="激烈的战斗效果，适合战斗场景",
            effects=[
                MicroEffectPreset(effect_type=MicroEffectType.HAIR_FLOAT, enabled=True, intensity=0.8),
                MicroEffectPreset(effect_type=MicroEffectType.CLOTHES_SWING, enabled=True, intensity=0.7),
                MicroEffectPreset(effect_type=MicroEffectType.SHAKE_TRANSITION, enabled=True, intensity=0.3),
            ]
        )


class TransitionEffect(BaseModel):
    """转场动效配置"""
    transition_type: TransitionType = TransitionType.NONE
    duration: float = Field(default=0.3, ge=0.1, le=2.0)  # 秒
    direction: Optional[str] = None  # 用于滑动方向


class MotionEngine:
    """动态漫动效引擎"""
    
    # 预设包注册表
    PRESET_PACKAGES: Dict[str, MicroEffectPackage] = {
        "natural_breathing": MicroEffectPackage.natural_breathing(),
        "dynamic_youth": MicroEffectPackage.dynamic_youth(),
        "serene_atmosphere": MicroEffectPackage.serene_atmosphere(),
        "battle_action": MicroEffectPackage.battle_action(),
    }
    
    def __init__(self):
        self.global_intensity: float = 0.7  # 全局动效强度
    
    def get_motion_preset(
        self,
        motion_type: MotionType,
        speed: MotionSpeed = MotionSpeed.MEDIUM,
        intensity: float = 1.0,
        **kwargs
    ) -> CameraMotionPreset:
        """获取镜头运动预设"""
        return CameraMotionPreset(
            motion_type=motion_type,
            speed=speed,
            intensity=intensity * self.global_intensity,
            **kwargs
        )
    
    def generate_motion_keyframes(
        self,
        preset: CameraMotionPreset,
        duration: float,
        fps: int = 24
    ) -> List[Dict[str, Any]]:
        """
        生成镜头运动关键帧
        返回关键帧序列用于渲染
        """
        keyframes = []
        total_frames = int(duration * fps)
        
        for frame in range(total_frames):
            progress = frame / total_frames
            
            # 根据运动类型计算变换参数
            transform = self._calculate_transform(preset, progress)
            
            keyframes.append({
                "frame": frame,
                "timestamp": frame / fps,
                "progress": progress,
                "transform": transform
            })
        
        return keyframes
    
    def _calculate_transform(
        self, 
        preset: CameraMotionPreset, 
        progress: float
    ) -> Dict[str, Any]:
        """计算当前进度的变换参数"""
        motion = preset.motion_type
        intensity = preset.intensity
        
        if motion == MotionType.FIXED:
            return {"scale": 1.0, "translate_x": 0, "translate_y": 0, "rotate": 0}
        
        elif motion == MotionType.PUSH_IN:
            # 推进效果
            scale = 1.0 + (0.2 * progress * intensity)
            return {"scale": scale, "translate_x": 0, "translate_y": 0, "rotate": 0}
        
        elif motion == MotionType.PUSH_OUT:
            # 拉远效果
            scale = 1.2 - (0.2 * progress * intensity)
            return {"scale": scale, "translate_x": 0, "translate_y": 0, "rotate": 0}
        
        elif motion == MotionType.PAN_LEFT:
            # 左摇
            offset = 50 * progress * intensity
            return {"scale": 1.0, "translate_x": -offset, "translate_y": 0, "rotate": 0}
        
        elif motion == MotionType.PAN_RIGHT:
            # 右摇
            offset = 50 * progress * intensity
            return {"scale": 1.0, "translate_x": offset, "translate_y": 0, "rotate": 0}
        
        elif motion == MotionType.TILT_UP:
            # 上摇
            offset = 30 * progress * intensity
            return {"scale": 1.0, "translate_x": 0, "translate_y": -offset, "rotate": 0}
        
        elif motion == MotionType.TILT_DOWN:
            # 下摇
            offset = 30 * progress * intensity
            return {"scale": 1.0, "translate_x": 0, "translate_y": offset, "rotate": 0}
        
        elif motion == MotionType.SHAKE:
            # 震动效果
            import random
            shake_x = random.uniform(-5, 5) * intensity * (1 - progress)
            shake_y = random.uniform(-5, 5) * intensity * (1 - progress)
            return {"scale": 1.0, "translate_x": shake_x, "translate_y": shake_y, "rotate": 0}
        
        elif motion == MotionType.ORBIT:
            # 环绕效果
            import math
            angle_rad = progress * 2 * math.pi * intensity
            orbit_x = 30 * math.sin(angle_rad)
            orbit_y = 20 * math.cos(angle_rad)
            return {"scale": 1.0, "translate_x": orbit_x, "translate_y": orbit_y, "rotate": progress * 360}
        
        return {"scale": 1.0, "translate_x": 0, "translate_y": 0, "rotate": 0}
    
    def apply_micro_effects(
        self,
        frame_data: Dict[str, Any],
        effects: List[MicroEffectPreset],
        timestamp: float
    ) -> Dict[str, Any]:
        """应用微动效到当前帧"""
        modified_frame = frame_data.copy()
        effect_results = []
        
        for effect in effects:
            if not effect.enabled:
                continue
            
            effect_result = self._apply_single_micro_effect(
                effect.effect_type, 
                modified_frame, 
                timestamp,
                effect.intensity
            )
            effect_results.append(effect_result)
        
        modified_frame["micro_effects"] = effect_results
        return modified_frame
    
    def _apply_single_micro_effect(
        self,
        effect_type: MicroEffectType,
        frame_data: Dict[str, Any],
        timestamp: float,
        intensity: float
    ) -> Dict[str, Any]:
        """应用单个微动效"""
        import math
        
        if effect_type == MicroEffectType.HAIR_FLOAT:
            # 头发飘动 - 正弦波模拟
            float_offset = math.sin(timestamp * 3) * 5 * intensity
            return {
                "type": "hair_float",
                "offset": float_offset,
                "timestamp": timestamp
            }
        
        elif effect_type == MicroEffectType.BREATHING:
            # 呼吸起伏 - 缓慢的正弦波
            breath_scale = 1.0 + math.sin(timestamp * 1.5) * 0.02 * intensity
            return {
                "type": "breathing",
                "scale": breath_scale,
                "timestamp": timestamp
            }
        
        elif effect_type == MicroEffectType.EYE_BLINK:
            # 眨眼 - 周期性
            blink_phase = (timestamp % 4) / 4
            if 0.9 < blink_phase < 1.0:
                eye_openness = 1.0 - (blink_phase - 0.9) * 10
            else:
                eye_openness = 1.0
            return {
                "type": "eye_blink",
                "eye_openness": eye_openness,
                "timestamp": timestamp
            }
        
        elif effect_type == MicroEffectType.LIGHT_SHADOW:
            # 光影流动
            shadow_offset = math.sin(timestamp * 0.5) * 10 * intensity
            return {
                "type": "light_shadow",
                "shadow_offset": shadow_offset,
                "timestamp": timestamp
            }
        
        return {"type": effect_type, "timestamp": timestamp}
    
    def apply_transition(
        self,
        prev_frame: Dict[str, Any],
        next_frame: Dict[str, Any],
        transition: TransitionEffect,
        progress: float
    ) -> Dict[str, Any]:
        """应用转场动效"""
        t_type = transition.transition_type
        duration = transition.duration
        
        if t_type == TransitionType.NONE:
            return next_frame
        
        elif t_type == TransitionType.BLACK:
            # 黑场过渡
            opacity = 1.0 - progress
            return {**next_frame, "overlay": {"type": "black", "opacity": opacity}}
        
        elif t_type == TransitionType.WHITE:
            # 白场过渡
            opacity = 1.0 - progress
            return {**next_frame, "overlay": {"type": "white", "opacity": opacity}}
        
        elif t_type == TransitionType.CROSSFADE:
            # 叠化
            prev_alpha = 1.0 - progress
            next_alpha = progress
            return {
                **next_frame,
                "crossfade": {"prev_alpha": prev_alpha, "next_alpha": next_alpha}
            }
        
        elif t_type == TransitionType.SLIDE:
            # 滑动
            direction = transition.direction or "left"
            offset = (1.0 - progress) * 100
            return {**next_frame, "slide_offset": offset, "slide_direction": direction}
        
        elif t_type == TransitionType.MANGA_SPEED:
            # 漫画式速度线
            line_intensity = (1.0 - abs(progress - 0.5) * 2) * intensity
            return {**next_frame, "speed_lines": line_intensity}
        
        return next_frame
    
    def set_global_intensity(self, intensity: float):
        """设置全局动效强度（0-1）"""
        self.global_intensity = max(0.0, min(1.0, intensity))
    
    def render_motion_sequence(
        self,
        frames: List[Dict[str, Any]],
        motion_preset: CameraMotionPreset,
        micro_effects: List[MicroEffectPreset],
        fps: int = 24
    ) -> List[Dict[str, Any]]:
        """渲染完整的动效序列"""
        rendered = []
        
        for i, frame in enumerate(frames):
            timestamp = i / fps
            
            # 应用镜头运动
            keyframes = self.generate_motion_keyframes(motion_preset, len(frames) / fps, fps)
            frame_transform = keyframes[i]["transform"] if i < len(keyframes) else {}
            
            # 应用微动效
            modified_frame = self.apply_micro_effects(frame, micro_effects, timestamp)
            modified_frame["transform"] = frame_transform
            modified_frame["frame_index"] = i
            modified_frame["timestamp"] = timestamp
            
            rendered.append(modified_frame)
        
        return rendered


# 全局实例
motion_engine = MotionEngine()
