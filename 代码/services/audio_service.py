"""
音频服务
TTS语音合成、BGM推荐、音效
"""
import httpx
import os
import uuid
import json
import base64
from typing import Optional, List, Dict, Any
from enum import Enum


class TTSProvider(str, Enum):
    """TTS提供者"""
    AZURE = "azure"
    COSYVOICE = "cosyvoice"
    GPT_SOVITS = "gpt_sovits"
    OPENAI = "openai"


class AudioService:
    """音频服务"""

    # 预设音色
    VOICE_PRESETS = {
        "xiaoming": {
            "name": "小明",
            "provider": "cosyvoice",
            "voice_id": "cosyvoice_v1_male_young",
            "language": "zh"
        },
        "xiaohong": {
            "name": "小红",
            "provider": "cosyvoice",
            "voice_id": "cosyvoice_v1_female_young",
            "language": "zh"
        },
        "narrator": {
            "name": "旁白",
            "provider": "cosyvoice",
            "voice_id": "cosyvoice_v1_narrator",
            "language": "zh"
        },
        "english_male": {
            "name": "英文男",
            "provider": "azure",
            "voice_id": "en-US-JasonNeural",
            "language": "en"
        },
        "english_female": {
            "name": "英文女",
            "provider": "azure",
            "voice_id": "en-US-JennyNeural",
            "language": "en"
        }
    }

    # 情感参数映射
    EMOTION_PARAMS = {
        "happy": {"pitch": "+10%", "speed": "1.1", "energy": "1.2"},
        "sad": {"pitch": "-10%", "speed": "0.9", "energy": "0.8"},
        "angry": {"pitch": "+15%", "speed": "1.2", "energy": "1.5"},
        "surprised": {"pitch": "+20%", "speed": "1.15", "energy": "1.3"},
        "neutral": {"pitch": "0%", "speed": "1.0", "energy": "1.0"}
    }

    # BGM风格
    BGM_STYLES = {
        "happy": ["欢快_001.mp3", "欢快_002.mp3", "轻快_003.mp3"],
        "tense": ["紧张_001.mp3", "悬疑_002.mp3", "压迫感_003.mp3"],
        "romantic": ["浪漫_001.mp3", "温馨_002.mp3", "柔情_003.mp3"],
        "sad": ["悲伤_001.mp3", "低沉_002.mp3", "忧郁_003.mp3"],
        "action": ["战斗_001.mp3", "动感_002.mp3", "激烈_003.mp3"],
        "neutral": ["背景_001.mp3", "舒缓_002.mp3", "轻音乐_003.mp3"]
    }

    def __init__(self, output_dir: str = "/opt/AiComic/代码/outputs"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.bgm_dir = os.path.join(os.path.dirname(__file__), "..", "assets", "bgm")
        os.makedirs(self.bgm_dir, exist_ok=True)

    async def generate_tts(
        self,
        text: str,
        character: str = "narrator",
        emotion: str = "neutral",
        speed: float = 1.0,
        pitch: float = 0.0,
        language: Optional[str] = None,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成TTS语音

        Args:
            text: 要转换的文本
            character: 角色名（用于选择音色）
            emotion: 情感类型
            speed: 语速倍率
            pitch: 音调调整（0=正常，+10高八度，-10低八度）
            language: 语言代码（如 "zh", "en", "ja"）
            output_path: 输出文件路径

        Returns:
            {"audio_url": str, "duration": float}
        """
        if output_path is None:
            output_path = os.path.join(
                self.output_dir,
                f"tts_{uuid.uuid4().hex[:8]}.mp3"
            )

        # 查找匹配的音色
        voice = self.VOICE_PRESETS.get(character, self.VOICE_PRESETS["narrator"])
        emotion_params = self.EMOTION_PARAMS.get(emotion, self.EMOTION_PARAMS["neutral"])

        # 根据提供商生成
        provider = voice["provider"]

        if provider == "cosyvoice":
            audio_url = await self._cosyvoice_tts(
                text=text,
                voice_id=voice["voice_id"],
                emotion_params=emotion_params,
                speed=speed,
                pitch=pitch,
                output_path=output_path
            )
        elif provider == "azure":
            audio_url = await self._azure_tts(
                text=text,
                voice_id=voice["voice_id"],
                emotion_params=emotion_params,
                speed=speed,
                output_path=output_path
            )
        else:
            # 默认使用HTTP TTS API
            audio_url = await self._http_tts(
                text=text,
                voice_id=voice["voice_id"],
                output_path=output_path
            )

        # 获取音频时长
        duration = self._get_audio_duration(output_path)

        return {
            "audio_url": audio_url,
            "duration": duration,
            "character": character,
            "emotion": emotion,
            "text": text
        }

    async def _cosyvoice_tts(
        self,
        text: str,
        voice_id: str,
        emotion_params: Dict[str, str],
        speed: float,
        pitch: float,
        output_path: str
    ) -> str:
        """CosyVoice TTS（示例实现）"""
        # TODO: 实现CosyVoice API调用
        # CosyVoice API: POST /v1/tts
        # Body: {"text": text, "voice": voice_id, "speed": speed, "pitch": pitch}
        # Response: audio/wav

        # 目前生成静音文件作为placeholder
        import subprocess
        cmd = [
            "ffmpeg", "-f", "lavfi",
            "-i", f"anullsrc=r=24000:cl=mono",
            "-t", "3",  # 3秒占位
            "-q:a", "0",
            output_path
        ]
        subprocess.run(cmd, capture_output=True)
        return f"file://{output_path}"

    async def _azure_tts(
        self,
        text: str,
        voice_id: str,
        emotion_params: Dict[str, str],
        speed: float,
        output_path: str
    ) -> str:
        """Azure TTS（示例实现）"""
        # TODO: 实现Azure Cognitive Services TTS
        # 需要 AZURE_TTS_KEY 和 AZURE_TTS_REGION 环境变量
        raise NotImplementedError("Azure TTS not yet configured")

    async def _http_tts(
        self,
        text: str,
        voice_id: str,
        output_path: str
    ) -> str:
        """通用HTTP TTS API"""
        # 适用于自建的TTS服务
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    "http://localhost:8001/tts",
                    json={"text": text, "voice": voice_id}
                )
                response.raise_for_status()

                with open(output_path, "wb") as f:
                    f.write(response.content)

                return f"file://{output_path}"
        except Exception:
            # TTS服务不可用，生成静音
            import subprocess
            subprocess.run([
                "ffmpeg", "-f", "lavfi",
                "-i", "anullsrc=r=24000:cl=mono",
                "-t", "3", "-y", output_path
            ], capture_output=True)
            return f"file://{output_path}"

    def _get_audio_duration(self, audio_path: str) -> float:
        """获取音频时长"""
        import subprocess
        try:
            result = subprocess.run([
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "json",
                audio_path
            ], capture_output=True, text=True)
            data = json.loads(result.stdout)
            return float(data["format"]["duration"])
        except Exception:
            return 3.0  # 默认3秒

    async def recommend_bgm(
        self,
        scene_type: str = "neutral",
        duration: Optional[float] = None,
        fade_in: float = 1.0,
        fade_out: float = 1.0
    ) -> Dict[str, Any]:
        """
        推荐BGM

        Args:
            scene_type: 场景类型（happy/tense/romantic/sad/action/neutral）
            duration: 目标时长（秒），如果BGM更长会裁剪
            fade_in: 淡入时长
            fade_out: 淡出时长

        Returns:
            {"bgm_url": str, "duration": float, "fade_in": float, "fade_out": float}
        """
        bgm_files = self.BGM_STYLES.get(scene_type, self.BGM_STYLES["neutral"])

        # 简单随机选择
        import random
        bgm_filename = random.choice(bgm_files)
        bgm_path = os.path.join(self.bgm_dir, bgm_filename)

        # 如果BGM不存在，返回空
        if not os.path.exists(bgm_path):
            return {
                "bgm_url": "",
                "duration": 0,
                "fade_in": fade_in,
                "fade_out": fade_out,
                "note": "BGM file not found"
            }

        # 如果需要裁剪或调整时长
        if duration:
            trimmed_path = os.path.join(
                self.output_dir,
                f"bgm_{uuid.uuid4().hex[:8]}.mp3"
            )
            cmd = [
                "ffmpeg", "-y",
                "-i", bgm_path,
                "-t", str(duration),
                "-af", f"afade=t=in:st=0:d={fade_in},afade=t=out:st={duration-fade_out}:d={fade_out}",
                "-q:a", "0",
                trimmed_path
            ]
            subprocess.run(cmd, capture_output=True)
            bgm_url = f"file://{trimmed_path}"
            actual_duration = duration
        else:
            bgm_url = f"file://{bgm_path}"
            actual_duration = self._get_audio_duration(bgm_path)

        return {
            "bgm_url": bgm_url,
            "duration": actual_duration,
            "fade_in": fade_in,
            "fade_out": fade_out,
            "scene_type": scene_type
        }

    async def mix_audio(
        self,
        voice_track_url: str,
        bgm_track_url: str,
        voice_volume: float = 1.0,
        bgm_volume: float = 0.3,
        output_path: Optional[str] = None
    ) -> str:
        """
        混合语音和BGM

        Args:
            voice_track_url: 人声音轨
            bgm_track_url: BGM音轨
            voice_volume: 人声音量（0.0-2.0）
            bgm_volume: BGM音量（0.0-1.0）
            output_path: 输出路径

        Returns:
            混合后的音频路径
        """
        if output_path is None:
            output_path = os.path.join(
                self.output_dir,
                f"mixed_{uuid.uuid4().hex[:8]}.mp3"
            )

        # 获取两个音轨的时长
        voice_duration = self._get_audio_duration(voice_track_url.replace("file://", ""))
        bgm_duration = self._get_audio_duration(bgm_track_url.replace("file://", ""))

        # 如果BGM比语音短，循环BGM
        if bgm_duration < voice_duration:
            # 循环BGM直到覆盖整个人声
            looped_bgm = os.path.join(self.output_dir, f"bgm_loop_{uuid.uuid4().hex[:8]}.mp3")
            subprocess.run([
                "ffmpeg", "-y",
                "-stream_loop", str(int(voice_duration / bgm_duration) + 1),
                "-i", bgm_track_url.replace("file://", ""),
                "-t", str(voice_duration),
                "-c", "copy",
                looped_bgm
            ], capture_output=True)
            bgm_track_url = f"file://{looped_bgm}"

        # 混合
        cmd = [
            "ffmpeg", "-y",
            "-i", voice_track_url.replace("file://", ""),
            "-i", bgm_track_url.replace("file://", ""),
            "-filter_complex",
            f"[0:a]volume={voice_volume}[voice];[1:a]volume={bgm_volume}[bgm];[voice][bgm]amix=inputs=2:duration=longest",
            "-q:a", "0",
            output_path
        ]

        subprocess.run(cmd, capture_output=True)
        return f"file://{output_path}"

    def get_available_voices(self) -> List[Dict[str, str]]:
        """获取可选音色列表"""
        return [
            {"value": k, "label": v["name"], "language": v["language"]}
            for k, v in self.VOICE_PRESETS.items()
        ]

    def get_available_bgm_styles(self) -> List[str]:
        """获取可选BGM风格列表"""
        return list(self.BGM_STYLES.keys())


# 全局实例
audio_service = AudioService()
