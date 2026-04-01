"""
视频合成服务
使用 FFmpeg 将所有元素合成为最终视频
"""
import subprocess
import os
import json
import uuid
import shutil
import inspect
from typing import List, Dict, Any, Optional, Tuple, Callable, Awaitable
from PIL import Image, ImageOps, ImageDraw

ProgressCallback = Optional[Callable[[int, str], Awaitable[None] | None]]


class VideoCompositor:
    """视频合成器"""

    # 输出质量预设
    QUALITY_PRESETS = {
        "480p": {"resolution": "854x480", "bitrate": "1M", "codec": "libx264"},
        "720p": {"resolution": "1280x720", "bitrate": "2M", "codec": "libx264"},
        "1080p": {"resolution": "1920x1080", "bitrate": "5M", "codec": "libx264"},
        "4k": {"resolution": "3840x2160", "bitrate": "20M", "codec": "libx265"}
    }

    # 导出格式
    EXPORT_FORMATS = ["png_sequence", "mp4", "pdf", "gif", "h265", "webm", "frames"]

    def __init__(
        self,
        output_dir: str = "/opt/AiComic/代码/outputs",
        temp_dir: str = "/tmp/aicomic"
    ):
        self.output_dir = output_dir
        self.temp_dir = temp_dir
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)

    async def _report_progress(
        self,
        progress_callback: ProgressCallback,
        progress: int,
        message: str
    ) -> None:
        """兼容同步/异步进度回调。"""
        if not progress_callback:
            return
        result = progress_callback(progress, message)
        if inspect.isawaitable(result):
            await result

    async def compose(
        self,
        shots: List[Dict[str, Any]],
        audio_track_url: Optional[str] = None,
        quality: str = "1080p",
        subtitle_path: Optional[str] = None,
        watermark_path: Optional[str] = None,
        output_path: Optional[str] = None,
        progress_callback: ProgressCallback = None
    ) -> Dict[str, Any]:
        """
        合成最终视频

        Args:
            shots: 镜头列表，每个包含:
                - image_url: 图片路径
                - video_url: 视频片段路径（可选，已生成的动态片段）
                - duration: 时长
                - motion_type: 运动类型
                - effects: 特效列表
                - audio_url: 该镜头的配音（可选）
            audio_track_url: 整体音频轨道（背景音乐等）
            quality: 输出质量 (480p/720p/1080p/4k)
            subtitle_path: 字幕文件路径 (.srt)
            watermark_path: 水印图片路径
            output_path: 输出文件路径

        Returns:
            {
                "output_url": str,
                "duration": float,
                "resolution": str,
                "file_size": int
            }
        """
        preset = self.QUALITY_PRESETS.get(quality, self.QUALITY_PRESETS["1080p"])

        await self._report_progress(progress_callback, 0, "开始合成")

        if output_path is None:
            output_path = os.path.join(
                self.output_dir,
                f"comic_{uuid.uuid4().hex[:8]}.mp4"
            )

        # 创建临时目录
        work_dir = os.path.join(self.temp_dir, uuid.uuid4().hex[:8])
        os.makedirs(work_dir, exist_ok=True)

        try:
            # 1. 为每个镜头生成视频片段
            clip_paths = []
            for i, shot in enumerate(shots):
                shot_progress = 5 + int((i / max(len(shots), 1)) * 60)
                await self._report_progress(
                    progress_callback,
                    shot_progress,
                    f"正在处理镜头 {i + 1}/{len(shots)}"
                )
                clip_path = await self._generate_shot_clip(
                    shot=shot,
                    preset=preset,
                    work_dir=work_dir,
                    index=i
                )
                clip_paths.append(clip_path)

            # 2. 创建拼接列表文件
            await self._report_progress(progress_callback, 68, "正在整理拼接清单")
            concat_list_path = os.path.join(work_dir, "concat.txt")
            with open(concat_list_path, "w") as f:
                for clip in clip_paths:
                    # 使用绝对路径
                    abs_clip = os.path.abspath(clip)
                    f.write(f"file '{abs_clip}'\n")

            # 3. 拼接所有片段
            await self._report_progress(progress_callback, 78, "正在合成视频")
            merged_path = os.path.join(work_dir, "merged.mp4")
            cmd_merge = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_list_path,
                "-c:v", preset["codec"],
                "-crf", "18",
                "-preset", "medium",
                "-pix_fmt", "yuv420p",
                merged_path
            ]
            result = subprocess.run(cmd_merge, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"Merge failed: {result.stderr}")

            # 4. 混入音频
            if audio_track_url:
                await self._report_progress(progress_callback, 86, "正在混入音频")
                final_path = os.path.join(work_dir, "with_audio.mp4")
                cmd_audio = [
                    "ffmpeg", "-y",
                    "-i", merged_path,
                    "-i", audio_track_url.replace("file://", ""),
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-shortest",
                    final_path
                ]
                subprocess.run(cmd_audio, capture_output=True)
                shutil.move(final_path, merged_path)

            # 5. 添加字幕
            if subtitle_path:
                await self._report_progress(progress_callback, 90, "正在添加字幕")
                subtitled_path = os.path.join(work_dir, "subtitled.mp4")
                cmd_sub = [
                    "ffmpeg", "-y",
                    "-i", merged_path,
                    "-vf", f"subtitles='{subtitle_path}'",
                    "-c:v", "libx264",
                    "-crf", "18",
                    "-c:a", "copy",
                    subtitled_path
                ]
                subprocess.run(cmd_sub, capture_output=True)
                shutil.move(subtitled_path, merged_path)

            # 6. 添加水印
            if watermark_path:
                await self._report_progress(progress_callback, 94, "正在添加水印")
                watermarked_path = os.path.join(work_dir, "watermarked.mp4")
                cmd_water = [
                    "ffmpeg", "-y",
                    "-i", merged_path,
                    "-i", watermark_path,
                    "-filter_complex", "[0:v][1:v]overlay=W-w-10:10",
                    "-c:v", "libx264",
                    "-crf", "18",
                    "-c:a", "copy",
                    watermarked_path
                ]
                subprocess.run(cmd_water, capture_output=True)
                shutil.move(watermarked_path, merged_path)

            # 7. 复制到最终输出位置
            shutil.copy(merged_path, output_path)

            # 8. 获取视频信息
            info = self._get_video_info(output_path)
            await self._report_progress(progress_callback, 100, "合成完成")

            return {
                "output_url": f"file://{output_path}",
                "duration": info["duration"],
                "resolution": info["resolution"],
                "file_size": info["file_size"]
            }

        finally:
            # 清理临时目录
            shutil.rmtree(work_dir, ignore_errors=True)

    async def export_mp4(
        self,
        shots: List[Dict[str, Any]],
        audio_track_url: Optional[str] = None,
        quality: str = "1080p",
        subtitle_path: Optional[str] = None,
        watermark_path: Optional[str] = None,
        output_path: Optional[str] = None,
        progress_callback: ProgressCallback = None
    ) -> Dict[str, Any]:
        """导出 MP4，直接复用合成流程。"""
        await self._report_progress(progress_callback, 0, "开始导出 MP4")
        result = await self.compose(
            shots=shots,
            audio_track_url=audio_track_url,
            quality=quality,
            subtitle_path=subtitle_path,
            watermark_path=watermark_path,
            output_path=output_path,
            progress_callback=progress_callback
        )
        await self._report_progress(progress_callback, 100, "MP4 导出完成")
        return result

    async def _generate_shot_clip(
        self,
        shot: Dict[str, Any],
        preset: Dict[str, str],
        work_dir: str,
        index: int
    ) -> str:
        """为单个镜头生成视频片段"""
        image_path = shot.get("image_url", "")
        video_path = shot.get("video_url", "")
        duration = shot.get("duration", 3.0)
        motion_type = shot.get("motion_type", "static")

        output_path = os.path.join(work_dir, f"clip_{index:03d}.mp4")

        # 如果已有视频片段，直接使用
        if video_path and os.path.exists(video_path.replace("file://", "")):
            shutil.copy(video_path.replace("file://", ""), output_path)
            return output_path

        # 如果有图片，转换为视频（带运动效果）
        if image_path:
            abs_image = os.path.abspath(image_path.replace("file://", ""))
            return self._image_to_video(
                abs_image, duration, motion_type, output_path, preset
            )

        # 既没图片也没视频，生成黑场
        return self._generate_black_clip(duration, output_path, preset)

    def _image_to_video(
        self,
        image_path: str,
        duration: float,
        motion_type: str,
        output_path: str,
        preset: Dict[str, str]
    ) -> str:
        """将图片转换为带运动效果的视频"""
        resolution = preset["resolution"]

        # 根据运动类型构建filter
        if motion_type == "static":
            vf = f"scale={resolution.replace('x', ':')},fps=30"
        elif motion_type == "pan_left":
            # 从右向左平移
            vf = f"scale=2000:-1,setpts=PTS/X + (1/T)*({duration})/20,trim=0:{duration},crop={resolution.replace('x', ':')}"
        elif motion_type == "pan_right":
            vf = f"scale=2000:-1,crop={resolution.replace('x', ':')},trim=0:{duration}"
        elif motion_type == "zoom_in":
            vf = f"scale=2000:-1,zoompan=z='min(zoom+0.002,1.5)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(duration*30)}:s={resolution.replace('x', ':')}"
        else:
            vf = f"scale={resolution.replace('x', ':')},fps=30"

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", image_path,
            "-t", str(duration),
            "-vf", vf,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "fast",
            "-shortest",
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            # 如果运动效果失败，使用简单转换
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", image_path,
                "-t", str(duration),
                "-vf", f"scale={resolution.replace('x', ':')},fps=30",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-shortest",
                output_path
            ]
            subprocess.run(cmd, capture_output=True)

        return output_path

    def _generate_black_clip(
        self,
        duration: float,
        output_path: str,
        preset: Dict[str, str]
    ) -> str:
        """生成黑场片段"""
        resolution = preset["resolution"]
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=black:s={resolution}:d={duration}:rate=30",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            output_path
        ]
        subprocess.run(cmd, capture_output=True)
        return output_path

    async def export_gif(
        self,
        video_path: str,
        fps: int = 15,
        max_width: int = 480,
        output_path: Optional[str] = None,
        progress_callback: ProgressCallback = None
    ) -> str:
        """
        导出为GIF格式

        Args:
            video_path: 输入视频路径
            fps: GIF帧率
            max_width: 最大宽度
            output_path: 输出路径

        Returns:
            GIF文件路径
        """
        if output_path is None:
            output_path = os.path.join(
                self.output_dir,
                f"export_{uuid.uuid4().hex[:8]}.gif"
            )

        await self._report_progress(progress_callback, 0, "开始导出 GIF")

        # 转换为调色板GIF（体积小）
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path.replace("file://", ""),
            "-vf", f"fps={fps},scale={max_width}:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
            "-loop", "0",
            output_path
        ]

        subprocess.run(cmd, capture_output=True)
        await self._report_progress(progress_callback, 100, "GIF 导出完成")
        return f"file://{output_path}"

    async def export_gif_from_images(
        self,
        image_paths: List[str],
        fps: int = 12,
        output_path: Optional[str] = None,
        progress_callback: ProgressCallback = None
    ) -> str:
        """将图片序列导出为 GIF。"""
        if output_path is None:
            output_path = os.path.join(
                self.output_dir,
                f"export_{uuid.uuid4().hex[:8]}.gif"
            )

        valid_paths = [self._normalize_path(path) for path in image_paths if path]
        if not valid_paths:
            raise ValueError("没有可用于导出的图片")

        await self._report_progress(progress_callback, 0, "开始生成 GIF")
        frames = []
        total = len(valid_paths)
        for index, image_path in enumerate(valid_paths, start=1):
            if not os.path.exists(image_path):
                continue
            with Image.open(image_path) as source:
                frames.append(source.convert("P", palette=Image.ADAPTIVE))
            progress = int(index / total * 95)
            await self._report_progress(
                progress_callback,
                progress,
                f"正在准备 GIF 帧 {index}/{total}"
            )

        if not frames:
            raise ValueError("没有可用于导出的图片")

        duration = max(int(1000 / max(fps, 1)), 1)
        frames[0].save(
            output_path,
            save_all=True,
            append_images=frames[1:],
            duration=duration,
            loop=0,
            disposal=2
        )
        await self._report_progress(progress_callback, 100, "GIF 导出完成")
        return f"file://{output_path}"

    async def export_frames(
        self,
        video_path: str,
        output_dir: Optional[str] = None,
        progress_callback: ProgressCallback = None
    ) -> str:
        """
        导出为PNG序列帧

        Args:
            video_path: 输入视频路径
            output_dir: 输出目录

        Returns:
            序列帧目录路径
        """
        if output_dir is None:
            output_dir = os.path.join(
                self.output_dir,
                f"frames_{uuid.uuid4().hex[:8]}"
            )
        os.makedirs(output_dir, exist_ok=True)

        await self._report_progress(progress_callback, 0, "开始导出 PNG 序列")

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path.replace("file://", ""),
            "-q:v", "2",
            os.path.join(output_dir, "frame_%04d.png")
        ]

        subprocess.run(cmd, capture_output=True)
        await self._report_progress(progress_callback, 100, "PNG 序列导出完成")
        return f"file://{output_dir}"

    async def export_png_sequence(
        self,
        image_paths: List[str],
        output_dir: Optional[str] = None,
        progress_callback: ProgressCallback = None
    ) -> str:
        """将图片序列导出为 PNG 序列。"""
        if output_dir is None:
            output_dir = os.path.join(
                self.output_dir,
                f"png_sequence_{uuid.uuid4().hex[:8]}"
            )
        os.makedirs(output_dir, exist_ok=True)

        valid_paths = [self._normalize_path(path) for path in image_paths if path]
        total = max(len(valid_paths), 1)
        await self._report_progress(progress_callback, 0, "开始导出 PNG 序列")

        for index, image_path in enumerate(valid_paths, start=1):
            if not os.path.exists(image_path):
                continue
            with Image.open(image_path) as image:
                target = os.path.join(output_dir, f"frame_{index:04d}.png")
                image.save(target, format="PNG")
            progress = int(index / total * 100)
            await self._report_progress(
                progress_callback,
                progress,
                f"正在导出 PNG 帧 {index}/{total}"
            )

        await self._report_progress(progress_callback, 100, "PNG 序列导出完成")
        return f"file://{output_dir}"

    async def export_pdf(
        self,
        image_paths: List[str],
        output_path: Optional[str] = None,
        title: str = "AiComic 导出",
        progress_callback: ProgressCallback = None
    ) -> str:
        """将图片序列导出为 PDF。"""
        if output_path is None:
            output_path = os.path.join(
                self.output_dir,
                f"export_{uuid.uuid4().hex[:8]}.pdf"
            )

        valid_paths = [self._normalize_path(path) for path in image_paths if path]
        total = max(len(valid_paths), 1)
        pages = []
        await self._report_progress(progress_callback, 0, "开始生成 PDF")

        for index, image_path in enumerate(valid_paths, start=1):
            if not os.path.exists(image_path):
                continue
            with Image.open(image_path) as source:
                image = source.convert("RGB")
                page = self._compose_pdf_page(image, title, index, total)
                pages.append(page)
            progress = int(index / total * 90)
            await self._report_progress(
                progress_callback,
                progress,
                f"正在生成 PDF 第 {index}/{total} 页"
            )

        if not pages:
            raise ValueError("没有可用于导出的图片")

        pages[0].save(output_path, save_all=True, append_images=pages[1:])
        await self._report_progress(progress_callback, 100, "PDF 导出完成")
        return f"file://{output_path}"

    def _get_video_info(self, video_path: str) -> Dict[str, Any]:
        """获取视频信息"""
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration,size:stream=width,height",
            "-of", "json",
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)

        duration = float(data.get("format", {}).get("duration", 0))
        file_size = int(data.get("format", {}).get("size", 0))
        streams = data.get("streams", [{}])
        width = streams[0].get("width", 0) if streams else 0
        height = streams[0].get("height", 0) if streams else 0

        return {
            "duration": round(duration, 2),
            "resolution": f"{width}x{height}",
            "file_size": file_size
        }

    def _normalize_path(self, path: str) -> str:
        """清理 file:// 前缀。"""
        return path.replace("file://", "")

    def _compose_pdf_page(
        self,
        image: Image.Image,
        title: str,
        page_index: int,
        total_pages: int
    ) -> Image.Image:
        """把单张图片整理成 PDF 页面。"""
        page_size = (1240, 1754)
        canvas = Image.new("RGB", page_size, "white")
        draw = ImageDraw.Draw(canvas)

        header = f"{title}  ·  {page_index}/{total_pages}"
        draw.text((56, 48), header, fill="black")

        preview = ImageOps.contain(image, (1130, 1540))
        x = (page_size[0] - preview.width) // 2
        y = 140
        canvas.paste(preview, (x, y))
        return canvas

    async def generate_thumbnail(
        self,
        video_path: str,
        timestamp: float = 0.5,
        output_path: Optional[str] = None
    ) -> str:
        """从视频中截取一帧作为缩略图"""
        if output_path is None:
            output_path = os.path.join(
                self.output_dir,
                f"thumb_{uuid.uuid4().hex[:8]}.jpg"
            )

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(timestamp),
            "-i", video_path.replace("file://", ""),
            "-vframes", "1",
            "-q:v", "2",
            output_path
        ]

        subprocess.run(cmd, capture_output=True)
        return f"file://{output_path}"


# 全局实例
video_compositor = VideoCompositor()
