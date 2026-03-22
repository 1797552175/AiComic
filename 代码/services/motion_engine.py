"""
动态化服务
镜头运动、口型同步、特效叠加
"""
import json
import subprocess
import uuid
import os
from typing import Dict, Any, List, Optional, Tuple


class MotionEngine:
    """动态效果引擎"""

    # 镜头运动预设
    CAMERA_MOTIONS = {
        "static": {
            "name": "静止",
            "type": "none",
            "params": {}
        },
        "pan_left": {
            "name": "左平推",
            "type": "pan",
            "params": {"direction": "left", "speed": 0.02}
        },
        "pan_right": {
            "name": "右平推",
            "type": "pan",
            "params": {"direction": "right", "speed": 0.02}
        },
        "tilt_up": {
            "name": "上摇",
            "type": "tilt",
            "params": {"direction": "up", "speed": 0.02}
        },
        "tilt_down": {
            "name": "下摇",
            "type": "tilt",
            "params": {"direction": "down", "speed": 0.02}
        },
        "zoom_in": {
            "name": "推进",
            "type": "zoom",
            "params": {"from": 1.0, "to": 1.3, "speed": 0.02}
        },
        "zoom_out": {
            "name": "拉远",
            "type": "zoom",
            "params": {"from": 1.0, "to": 0.8, "speed": 0.02}
        },
        "rotate": {
            "name": "旋转",
            "type": "rotate",
            "params": {"angle": 3, "speed": 0.5}
        },
        "shake": {
            "name": "抖动",
            "type": "shake",
            "params": {"intensity": 0.02}
        }
    }

    # 口型关键帧
    LIP_SHAPES = ["closed", "A", "E", "I", "O", "U", "F", "L", "M", "W"]

    # 特效预设
    EFFECT_PRESETS = {
        "speed_line": {
            "name": "速度线",
            "type": "overlay",
            "params": {"asset": "speed_lines.png", "opacity": 0.3}
        },
        "wind": {
            "name": "气流/风",
            "type": "particle",
            "params": {"direction": "left", "intensity": 0.5, "type": "air"}
        },
        "spark": {
            "name": "火花/光效",
            "type": "particle",
            "params": {"color": "orange", "intensity": 0.7}
        },
        "petal": {
            "name": "花瓣/落叶",
            "type": "particle",
            "params": {"type": "petal", "intensity": 0.4}
        },
        "rain": {
            "name": "雨/雪",
            "type": "particle",
            "params": {"type": "rain", "intensity": 0.6}
        },
        "blackout": {
            "name": "黑场过渡",
            "type": "transition",
            "params": {"duration": 0.5}
        },
        "whiteout": {
            "name": "白场过渡",
            "type": "transition",
            "params": {"duration": 0.5}
        }
    }

    def __init__(self, output_dir: str = "/opt/AiComic/代码/outputs"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def apply_camera_motion(
        self,
        image_path: str,
        motion_type: str = "static",
        duration: float = 3.0,
        output_path: Optional[str] = None
    ) -> str:
        """
        对单张图片应用镜头运动，生成视频片段

        Args:
            image_path: 输入图片路径
            motion_type: 运动类型
            duration: 视频时长（秒）
            output_path: 输出视频路径

        Returns:
            输出视频路径
        """
        if output_path is None:
            output_path = os.path.join(
                self.output_dir,
                f"motion_{uuid.uuid4().hex[:8]}.mp4"
            )

        motion = self.CAMERA_MOTIONS.get(motion_type, self.CAMERA_MOTIONS["static"])

        if motion["type"] == "none":
            # 静止：直接复制为视频
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", image_path,
                "-t", str(duration),
                "-vf", "fps=30",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-shortest",
                output_path
            ]
        elif motion["type"] == "pan":
            # 平移
            direction = motion["params"]["direction"]
            speed = motion["params"]["speed"]

            if direction == "left":
                zoompan_expr = f"zoompan=z='min(zoom+0.001,1.5)':x='iw/2-(iw/zoom/2)-{int(speed*100)}*n':y='ih/2-(ih/zoom/2)':d={int(duration*30)}:s=1024x768"
            elif direction == "right":
                zoompan_expr = f"zoompan=z='min(zoom+0.001,1.5)':x='iw/2-(iw/zoom/2)+{int(speed*100)}*n':y='ih/2-(ih/zoom/2)':d={int(duration*30)}:s=1024x768"
            elif direction == "up":
                zoompan_expr = f"zoompan=z='min(zoom+0.001,1.5)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)-{int(speed*100)}*n':d={int(duration*30)}:s=1024x768"
            else:  # down
                zoompan_expr = f"zoompan=z='min(zoom+0.001,1.5)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)+{int(speed*100)}*n':d={int(duration*30)}:s=1024x768"

            cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", image_path,
                "-vf", zoompan_expr,
                "-t", str(duration),
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                output_path
            ]
        elif motion["type"] == "zoom":
            # 推进/拉远
            zoom_from = motion["params"]["from"]
            zoom_to = motion["params"]["to"]
            zoompan_expr = f"zoompan=z='if(lte(zoom,{zoom_from}),{zoom_from},{zoom}-{abs(zoom_to-zoom_from)/({int(duration*30)})})':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(duration*30)}:s=1024x768"

            cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", image_path,
                "-vf", zoompan_expr,
                "-t", str(duration),
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                output_path
            ]
        elif motion["type"] == "shake":
            # 抖动
            intensity = motion["params"]["intensity"]
            # 使用随机位移模拟抖动
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", image_path,
                "-vf", f"zoompan=z='1.05':x='iw/2+(rand(0)*iw*{intensity})-(iw/zoom/2)':y='ih/2+(rand(0)*ih*{intensity})-(ih/zoom/2)':d={int(duration*30)}:s=1024x768",
                "-t", str(duration),
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                output_path
            ]
        else:
            # 默认静止
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", image_path,
                "-t", str(duration),
                "-vf", "fps=30",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-shortest",
                output_path
            ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=int(duration) + 10
            )
            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg error: {result.stderr}")
        except FileNotFoundError:
            raise RuntimeError("FFmpeg not found. Please install ffmpeg.")
        except subprocess.TimeoutExpired:
            raise RuntimeError("FFmpeg process timeout")

        return output_path

    def generate_lip_sync(
        self,
        text: str,
        duration: float,
        frame_rate: int = 30
    ) -> List[Dict[str, Any]]:
        """
        生成口型关键帧数据

        Args:
            text: 对话文本
            duration: 总时长（秒）
            frame_rate: 帧率

        Returns:
            关键帧列表 [{"frame": int, "mouth_shape": str, "time": float}]
        """
        # 简单实现：按音节均分
        # 实际应该用语音识别+音素预测
        total_frames = int(duration * frame_rate)
        char_count = len(text)

        if char_count == 0:
            return [{"frame": 0, "mouth_shape": "closed", "time": 0.0}]

        frames_per_char = total_frames / char_count
        lip_frames = []

        for i, char in enumerate(text):
            frame_idx = int(i * frames_per_char)
            time_sec = frame_idx / frame_rate

            # 简单映射（中英文常见音素）
            # 实际应该基于音素识别
            if char in "aeiouAEIOU":
                shapes = ["A", "E", "I", "O", "U"]
                mouth_shape = shapes["aeiouAEIOU".index(char) % 5]
            elif char in "bmpf":
                mouth_shape = "M"
            elif char in "tdnl":
                mouth_shape = "L"
            elif char in "gkh":
                mouth_shape = "F"
            else:
                mouth_shape = "closed"

            lip_frames.append({
                "frame": frame_idx,
                "mouth_shape": mouth_shape,
                "time": round(time_sec, 3)
            })

        # 最后一帧设为closed
        lip_frames.append({
            "frame": total_frames - 1,
            "mouth_shape": "closed",
            "time": duration
        })

        return lip_frames

    def apply_lip_sync_to_video(
        self,
        video_path: str,
        lip_frames: List[Dict[str, Any]],
        output_path: Optional[str] = None
    ) -> str:
        """
        将口型数据应用到视频

        这个是简化版，实际需要：
        1. 提取视频中的角色面部区域
        2. 替换嘴巴区域
        3. 合成回去

        Args:
            video_path: 输入视频路径
            lip_frames: 口型关键帧数据
            output_path: 输出路径

        Returns:
            输出视频路径
        """
        if output_path is None:
            output_path = video_path  # 原地修改

        # 保存口型数据为JSON
        lip_data_path = os.path.join(self.output_dir, f"lipsync_{uuid.uuid4().hex[:8]}.json")
        with open(lip_data_path, "w") as f:
            json.dump(lip_frames, f, indent=2)

        # TODO: 实现实际的口型替换
        # 方案：使用MediaPipe/DeepFake技术替换嘴部区域
        # 目前仅保存数据，不做实际处理

        return output_path

    def apply_effect(
        self,
        video_path: str,
        effect_type: str,
        params: Dict[str, Any],
        output_path: Optional[str] = None
    ) -> str:
        """
        为视频应用特效

        Args:
            video_path: 输入视频路径
            effect_type: 特效类型
            params: 特效参数
            output_path: 输出路径

        Returns:
            输出视频路径
        """
        if output_path is None:
            output_path = os.path.join(
                self.output_dir,
                f"effect_{uuid.uuid4().hex[:8]}.mp4"
            )

        effect = self.EFFECT_PRESETS.get(effect_type)
        if not effect:
            return video_path  # 未知特效，原样返回

        effect_type_val = effect["type"]

        if effect_type_val == "overlay":
            # 叠加层特效（如速度线）
            asset = params.get("asset", effect["params"].get("asset", ""))
            opacity = params.get("opacity", effect["params"].get("opacity", 0.5))

            if os.path.exists(asset):
                cmd = [
                    "ffmpeg", "-y",
                    "-i", video_path,
                    "-i", asset,
                    "-filter_complex", f"[1:v]format=rgba,colorchannelmixer=aa={opacity}[fg];[0:v][fg]overlay=0:0",
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    output_path
                ]
            else:
                # asset不存在，跳过
                return video_path

        elif effect_type_val == "particle":
            # 粒子特效（雨/雪/花瓣等）- 需要程序化生成
            # 这里简化为添加模糊效果作为替代
            intensity = params.get("intensity", 0.5)
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-vf", f"boxblur={int(intensity*5)}:1",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                output_path
            ]

        elif effect_type_val == "transition":
            # 转场特效（黑场/白场）
            duration = params.get("duration", 0.5)
            color = "black" if effect_type == "blackout" else "white"

            # 在片段前后添加淡入淡出
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", f"color={color}:s=1024x768:d={duration}",
                "-i", video_path,
                "-filter_complex", f"[0:v]fade=t=out:st=0:d={duration}:d=1[fv];[1:v]fade=t=in:st=0:d={duration}[v];[fv][v]concat:n=2:v=1:a=0",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                output_path
            ]
        else:
            return video_path

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg error: {result.stderr}")
        except Exception as e:
            raise RuntimeError(f"Effect application failed: {str(e)}")

        return output_path

    def compose_with_effects(
        self,
        shot_video_path: str,
        motion_type: str,
        effects: List[str],
        duration: float
    ) -> str:
        """
        为镜头应用运动+特效，生成最终片段

        Args:
            shot_video_path: 原始图片路径
            motion_type: 运动类型
            effects: 特效列表
            duration: 时长

        Returns:
            最终视频片段路径
        """
        # 1. 应用镜头运动
        current_path = self.apply_camera_motion(
            shot_video_path,
            motion_type,
            duration
        )

        # 2. 应用各个特效
        for effect in effects:
            effect_name = effect if isinstance(effect, str) else effect.get("type", "speed_line")
            effect_params = effect if isinstance(effect, dict) else {}
            current_path = self.apply_effect(current_path, effect_name, effect_params)

        return current_path

    def get_available_motions(self) -> List[Dict[str, Any]]:
        """获取可选的运动类型列表"""
        return [
            {"value": k, "label": v["name"], "type": v["type"]}
            for k, v in self.CAMERA_MOTIONS.items()
        ]

    def get_available_effects(self) -> List[Dict[str, Any]]:
        """获取可选的特效列表"""
        return [
            {"value": k, "label": v["name"], "type": v["type"]}
            for k, v in self.EFFECT_PRESETS.items()
        ]


# 全局实例
motion_engine = MotionEngine()
