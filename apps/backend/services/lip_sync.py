"""口型同步服务 - 基于音频生成口型动画"""
from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
import base64


class LipShape(str, Enum):
    """口型类型"""
    CLOSED = "closed"     # 闭唇 - 休止、m/b/p音
    SLIGHT_OPEN = "slight_open"  # 微张 - i/y音
    OPEN = "open"         # 张开 - a/o/e音
    ROUNDED = "rounded"   # 圆唇 - u/o音
    WIDE = "wide"         # 咧嘴 - s/z/c音


class LipSyncMode(str, Enum):
    """口型同步模式"""
    AUTO = "auto"         # 自动识别
    MANUAL = "manual"     # 手动指定


class PhonemeMapping(BaseModel):
    """音素到口型的映射"""
    phoneme: str
    lip_shape: LipShape
    duration_ms: int


class LipSyncResult(BaseModel):
    """口型同步结果"""
    lip_shape_sequence: List[Dict[str, Any]]
    audio_duration_ms: int
    fps: int = 24
    confidence: float = Field(default=0.0, ge=0, le=1)


class LipSyncRequest(BaseModel):
    """口型同步请求"""
    audio_data: Optional[str] = None  # Base64编码音频 或 URL
    audio_url: Optional[str] = None
    text: Optional[str] = None        # 台词文本（用于TTS场景）
    character_id: str
    mode: LipSyncMode = LipSyncMode.AUTO
    intensity: float = Field(default=0.85, ge=0, le=1)
    alignment: str = Field(default="high", description="high/medium/low 对齐精度")


class LipSyncService:
    """口型同步服务"""
    
    # 标准音素到口型映射表
    PHONEME_TO_LIPSHAPE = {
        # 闭唇音
        "SIL": LipShape.CLOSED, "M": LipShape.CLOSED, "B": LipShape.CLOSED, "P": LipShape.CLOSED,
        # 微张音
        "I": LipShape.SLIGHT_OPEN, "Y": LipShape.SLIGHT_OPEN, "IY": LipShape.SLIGHT_OPEN,
        # 张开音
        "A": LipShape.OPEN, "O": LipShape.OPEN, "E": LipShape.OPEN, "AE": LipShape.OPEN,
        "AA": LipShape.OPEN, "AH": LipShape.OPEN, "ER": LipShape.OPEN,
        # 圆唇音
        "U": LipShape.ROUNDED, "UW": LipShape.ROUNDED, "OW": LipShape.ROUNDED, "AO": LipShape.ROUNDED,
        # 咧嘴音
        "S": LipShape.WIDE, "Z": LipShape.WIDE, "C": LipShape.WIDE, "SH": LipShape.WIDE,
        "CH": LipShape.WIDE, "ZH": LipShape.WIDE, "JH": LipShape.WIDE,
    }
    
    def __init__(self):
        self.default_intensity = 0.85
        self.default_fps = 24
    
    async def sync_from_audio(
        self,
        audio_data: Optional[str] = None,
        audio_url: Optional[str] = None,
        character_id: str = "",
        intensity: float = 0.85,
        alignment: str = "high"
    ) -> LipSyncResult:
        """
        从音频生成口型同步序列
        流程：ASR音素识别 → 时间轴对齐 → 口型序列生成
        """
        if not audio_data and not audio_url:
            raise ValueError("需要提供 audio_data 或 audio_url")
        
        # Step 1: 提取音频特征（实际调用ASR服务）
        phoneme_sequence = await self._extract_phonemes(audio_data or audio_url, alignment)
        
        # Step 2: 时间轴对齐
        aligned_sequence = await self._align_timeline(phoneme_sequence, self.default_fps)
        
        # Step 3: 生成口型序列
        lip_shape_sequence = self._generate_lip_sequence(aligned_sequence, intensity)
        
        # 计算总时长
        total_duration = sum(p["duration_ms"] for p in aligned_sequence)
        
        return LipSyncResult(
            lip_shape_sequence=lip_shape_sequence,
            audio_duration_ms=total_duration,
            fps=self.default_fps,
            confidence=0.92  # 模拟置信度
        )
    
    async def sync_from_text(
        self,
        text: str,
        character_id: str = "",
        intensity: float = 0.85
    ) -> LipSyncResult:
        """
        从台词文本生成口型同步序列
        用于TTS场景，直接从文本生成口型
        """
        # 简化的文本转口型（实际项目中使用Glow-TTS等模型）
        phoneme_sequence = self._text_to_phonemes(text)
        aligned_sequence = await self._align_timeline(phoneme_sequence, self.default_fps)
        lip_shape_sequence = self._generate_lip_sequence(aligned_sequence, intensity)
        
        # 估算时长（按每字符100ms计算）
        total_duration = len(text) * 100
        
        return LipSyncResult(
            lip_shape_sequence=lip_shape_sequence,
            audio_duration_ms=total_duration,
            fps=self.default_fps,
            confidence=0.88
        )
    
    async def _extract_phonemes(
        self, 
        audio_source: str, 
        alignment: str
    ) -> List[Dict[str, Any]]:
        """
        从音频提取音素序列
        实际项目中调用 ASR / 唇形同步模型（如Wav2Vec2 + 音素模型）
        """
        # 模拟返回音素序列
        # 实际项目中：
        # 1. 使用Whisper进行语音识别
        # 2. 使用Montreal Forced Aligner进行音素对齐
        # 3. 使用唇形同步模型生成口型
        
        mock_phonemes = [
            {"phoneme": "JIN", "start_ms": 0, "end_ms": 150, "text": "今"},
            {"phoneme": "TIAN", "start_ms": 150, "end_ms": 350, "text": "天"},
            {"phoneme": "QI", "start_ms": 350, "end_ms": 500, "text": "气"},
            {"phoneme": "ZHEN", "start_ms": 500, "end_ms": 650, "text": "真"},
            {"phoneme": "HAO", "start_ms": 650, "end_ms": 850, "text": "好"},
            {"phoneme": "SIL", "start_ms": 850, "end_ms": 1000, "text": "。"},
        ]
        
        return mock_phonemes
    
    def _text_to_phonemes(self, text: str) -> List[Dict[str, Any]]:
        """
        文本转音素（简化的中文拼音映射）
        实际项目中使用 拼音词典 + 规则
        """
        # 简化实现：按字符模拟音素
        phonemes = []
        start_ms = 0
        
        for char in text:
            duration = 100 + (10 if char in "aeiou" else 0)  # 元音稍长
            phoneme = char  # 简化
            phonemes.append({
                "phoneme": phoneme,
                "start_ms": start_ms,
                "end_ms": start_ms + duration,
                "text": char
            })
            start_ms += duration
        
        return phonemes
    
    async def _align_timeline(
        self, 
        phoneme_sequence: List[Dict[str, Any]], 
        fps: int
    ) -> List[Dict[str, Any]]:
        """将音素序列对齐到视频帧时间轴"""
        aligned = []
        frame_duration_ms = 1000 / fps
        
        for phoneme in phoneme_sequence:
            start_ms = phoneme["start_ms"]
            end_ms = phoneme["end_ms"]
            
            # 计算起始帧和结束帧
            start_frame = int(start_ms / frame_duration_ms)
            end_frame = int(end_ms / frame_duration_ms)
            
            aligned.append({
                "phoneme": phoneme["phoneme"],
                "text": phoneme.get("text", ""),
                "start_frame": start_frame,
                "end_frame": end_frame,
                "start_ms": start_ms,
                "end_ms": end_ms,
                "duration_ms": end_ms - start_ms
            })
        
        return aligned
    
    def _generate_lip_sequence(
        self, 
        aligned_sequence: List[Dict[str, Any]],
        intensity: float
    ) -> List[Dict[str, Any]]:
        """根据音素序列生成口型序列"""
        lip_sequence = []
        
        for item in aligned_sequence:
            phoneme = item["phoneme"]
            
            # 查找对应的口型
            lip_shape = self.PHONEME_TO_LIPSHAPE.get(
                phoneme, 
                LipShape.OPEN
            )
            
            # 根据强度调整
            adjusted_shape = self._adjust_lip_intensity(lip_shape, intensity)
            
            lip_sequence.append({
                "frame_start": item["start_frame"],
                "frame_end": item["end_frame"],
                "lip_shape": adjusted_shape,
                "phoneme": phoneme,
                "text": item.get("text", ""),
                "duration_ms": item["duration_ms"]
            })
        
        return lip_sequence
    
    def _adjust_lip_intensity(
        self, 
        lip_shape: LipShape, 
        intensity: float
    ) -> Dict[str, Any]:
        """
        根据强度调整口型
        强度越低，口型越轻微
        """
        base_shape = {
            LipShape.CLOSED: {"openness": 0.0, "width": 0.3, "protrusion": 0.1},
            LipShape.SLIGHT_OPEN: {"openness": 0.3 * intensity, "width": 0.5, "protrusion": 0.2},
            LipShape.OPEN: {"openness": 0.7 * intensity, "width": 0.6, "protrusion": 0.3},
            LipShape.ROUNDED: {"openness": 0.5 * intensity, "width": 0.3, "protrusion": 0.6},
            LipShape.WIDE: {"openness": 0.4 * intensity, "width": 0.9, "protrusion": 0.2},
        }
        
        return {
            "type": lip_shape.value,
            "params": base_shape.get(lip_shape, base_shape[LipShape.OPEN]),
            "intensity": intensity
        }
    
    async def apply_lip_sync_to_video(
        self,
        video_frames: List[Dict[str, Any]],
        lip_sync_result: LipSyncResult,
        character_id: str
    ) -> List[Dict[str, Any]]:
        """
        将口型同步结果应用到视频帧
        返回带有口型动画的帧序列
        """
        modified_frames = []
        
        for i, frame in enumerate(video_frames):
            # 查找当前帧对应的口型
            current_lip = self._get_lip_for_frame(i, lip_sync_result.lip_shape_sequence)
            
            modified_frame = {
                **frame,
                "character_id": character_id,
                "lip_sync": current_lip,
                "has_lip_animation": current_lip is not None
            }
            modified_frames.append(modified_frame)
        
        return modified_frames
    
    def _get_lip_for_frame(
        self, 
        frame_idx: int, 
        lip_sequence: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """获取指定帧的口型"""
        for item in lip_sequence:
            if item["frame_start"] <= frame_idx <= item["frame_end"]:
                return item
        return None
    
    def get_supported_phonemes(self) -> List[str]:
        """获取支持の音素列表"""
        return list(self.PHONEME_TO_LIPSHAPE.keys())


# 全局单例
lip_sync_service = LipSyncService()
