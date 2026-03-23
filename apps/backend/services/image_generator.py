"""
图像生成服务
集成 Stable Diffusion / FLUX 进行漫画画面生成
"""
import httpx
import base64
import json
import uuid
from typing import Optional, List, Dict, Any
from io import BytesIO

from app.config import settings


class ImageGenerator:
    """AI图像生成器"""

    QUALITY_PRESETS = {
        "standard": {"steps": 25, "cfg": 7.5, "resolution": (1024, 768)},
        "hd": {"steps": 35, "cfg": 8.0, "resolution": (1024, 1024)},
        "uhd": {"steps": 50, "cfg": 8.5, "resolution": (2048, 2048)}
    }

    STYLE_PRESETS = {
        "anime": "anime style, manga illustration, vibrant colors, clean lines",
        "realistic": "realistic painting, cinematic lighting, photorealistic",
        "cyberpunk": "cyberpunk, neon lights, futuristic, dark atmosphere, rain",
        "ink": "chinese ink painting, traditional art, brush strokes, minimalist",
        "bw": "black and white manga, halftone dots, comic panel style"
    }

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or settings.sd_api_key
        self.base_url = base_url or settings.sd_base_url
        self.timeout = 120.0

    async def generate(
        self,
        prompt: str,
        style: str = "anime",
        quality: str = "hd",
        negative_prompt: Optional[str] = None,
        reference_images: Optional[List[str]] = None,
        width: Optional[int] = None,
        height: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        生成漫画风格图片

        Args:
            prompt: 画面描述关键词
            style: 风格 (anime/realistic/cyberpunk/ink/bw)
            quality: 质量等级 (standard/hd/uhd)
            negative_prompt: 负面提示词
            reference_images: 参考图URL列表（用于角色一致性）
            width/height: 自定义分辨率

        Returns:
            {"image_url": str, "thumbnail_url": str, "seed": int}
        """
        preset = self.QUALITY_PRESETS.get(quality, self.QUALITY_PRESETS["hd"])
        style_prefix = self.STYLE_PRESETS.get(style, self.STYLE_PRESETS["anime"])

        # 构建完整prompt
        full_prompt = f"{style_prefix}, {prompt}"

        # 默认负面词
        default_neg = (
            "low quality, blurry, distorted, deformed, "
            "bad anatomy, watermark, text, signature, "
            "multiple heads, extra limbs, poorly drawn hands"
        )
        neg_prompt = negative_prompt or default_neg

        # 分辨率
        w = width or preset["resolution"][0]
        h = height or preset["resolution"][1]

        # 构造请求体（兼容 Stability AI / Stable Diffusion API）
        payload = {
            "text_prompts": [
                {"text": full_prompt, "weight": 1.0},
                {"text": neg_prompt, "weight": -1.0}
            ],
            "cfg_scale": preset["cfg"],
            "height": h,
            "width": w,
            "steps": preset["steps"],
            "samples": 1
        }

        # 如果有参考图，添加图像到图像模式
        if reference_images:
            # TODO: 实现图生图模式（ControlNet / img2img）
            pass

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # 这里以 Stability AI 为例
                response = await client.post(
                    f"{self.base_url}/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
                response.raise_for_status()
                result = response.json()

                # 解析返回的图片
                artifacts = result.get("artifacts", [])
                if artifacts:
                    image_base64 = artifacts[0]["base64"]
                    seed = artifacts[0].get("seed", 0)
                    image_data = base64.b64decode(image_base64)

                    # 保存到本地/对象存储
                    image_url = await self._save_image(image_data, f"{uuid.uuid4()}.png")

                    return {
                        "image_url": image_url,
                        "seed": seed,
                        "prompt": full_prompt,
                        "resolution": f"{w}x{h}"
                    }

                raise ValueError("No artifacts returned from SD API")

        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"SD API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise RuntimeError(f"Image generation failed: {str(e)}")

    async def generate_batch(
        self,
        prompts: List[str],
        style: str = "anime",
        quality: str = "hd"
    ) -> List[Dict[str, Any]]:
        """
        批量生成图片

        Args:
            prompts: 画面描述列表
            style: 风格
            quality: 质量

        Returns:
            图片结果列表
        """
        results = []
        for prompt in prompts:
            try:
                result = await self.generate(prompt, style, quality)
                results.append(result)
            except Exception as e:
                results.append({
                    "prompt": prompt,
                    "error": str(e),
                    "status": "failed"
                })
        return results

    async def img2img(
        self,
        source_image_url: str,
        prompt: str,
        style: str = "anime",
        strength: float = 0.5,
        quality: str = "hd",
        negative_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        图生图模式：基于参考图生成新图

        Args:
            source_image_url: 参考图URL（支持 file:// 或 http:// 或 s3://）
            prompt: 描述词
            style: 风格 (anime/realistic/cyberpunk/ink/bw)
            strength: 变换强度 0.0-1.0，值越大变化越大
            quality: 质量等级 (standard/hd/uhd)
            negative_prompt: 负面提示词

        Returns:
            {"image_url": str, "seed": int, "resolution": str}
        """
        preset = self.QUALITY_PRESETS.get(quality, self.QUALITY_PRESETS["hd"])
        style_prefix = self.STYLE_PRESETS.get(style, self.STYLE_PRESETS["anime"])

        # 构建完整prompt
        full_prompt = f"{style_prefix}, {prompt}"

        # 默认负面词
        default_neg = (
            "low quality, blurry, distorted, deformed, "
            "bad anatomy, watermark, text, signature, "
            "multiple heads, extra limbs, poorly drawn hands"
        )
        neg_prompt = negative_prompt or default_neg

        # 下载并编码参考图
        image_base64 = await self._download_and_encode_image(source_image_url)

        # 分辨率
        w, h = preset["resolution"][0], preset["resolution"][1]

        # 构造 img2img 请求（兼容 Stability AI SDXL img2img）
        payload = {
            "text_prompts": [
                {"text": full_prompt, "weight": 1.0},
                {"text": neg_prompt, "weight": -1.0}
            ],
            "init_image": image_base64,  # base64 编码的参考图
            "image_strength": 1.0 - strength,  # Stability API 用 image_strength（值越小越接近原图）
            "cfg_scale": preset["cfg"],
            "height": h,
            "width": w,
            "steps": preset["steps"],
            "samples": 1
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/v1/generation/stable-diffusion-xl-1024-v1-0/image-to-image",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
                response.raise_for_status()
                result = response.json()

                # 解析返回的图片
                artifacts = result.get("artifacts", [])
                if artifacts:
                    result_base64 = artifacts[0]["base64"]
                    seed = artifacts[0].get("seed", 0)
                    image_data = base64.b64decode(result_base64)

                    image_url = await self._save_image(image_data, f"{uuid.uuid4()}.png")

                    return {
                        "image_url": image_url,
                        "seed": seed,
                        "prompt": full_prompt,
                        "resolution": f"{w}x{h}",
                        "source_image": source_image_url,
                        "strength": strength
                    }

                raise ValueError("No artifacts returned from SD img2img API")

        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"SD img2img API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise RuntimeError(f"img2img generation failed: {str(e)}")

    async def inpaint(
        self,
        source_image_url: str,
        mask_image_url: str,
        prompt: str,
        style: str = "anime",
        quality: str = "hd",
        negative_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        局部重绘：基于原图和遮罩进行局部修改

        Args:
            source_image_url: 原图URL（支持 file://, http://, s3://）
            mask_image_url: 遮罩图URL，白色区域=需要重绘的部分
            prompt: 重绘区域的描述词
            style: 风格 (anime/realistic/cyberpunk/ink/bw)
            quality: 质量等级 (standard/hd/uhd)
            negative_prompt: 负面提示词

        Returns:
            {"image_url": str, "seed": int, "resolution": str}
        """
        preset = self.QUALITY_PRESETS.get(quality, self.QUALITY_PRESETS["hd"])
        style_prefix = self.STYLE_PRESETS.get(style, self.STYLE_PRESETS["anime"])

        full_prompt = f"{style_prefix}, {prompt}"

        default_neg = (
            "low quality, blurry, distorted, deformed, "
            "bad anatomy, watermark, text, signature, "
            "multiple heads, extra limbs, poorly drawn hands"
        )
        neg_prompt = negative_prompt or default_neg

        # 下载并编码原图和遮罩
        source_base64 = await self._download_and_encode_image(source_image_url)
        mask_base64 = await self._download_and_encode_image(mask_image_url)

        w, h = preset["resolution"][0], preset["resolution"][1]

        # Stability AI 局部重绘 API
        payload = {
            "text_prompts": [
                {"text": full_prompt, "weight": 1.0},
                {"text": neg_prompt, "weight": -1.0}
            ],
            "init_image": source_base64,
            "mask": mask_base64,
            "cfg_scale": preset["cfg"],
            "height": h,
            "width": w,
            "steps": preset["steps"],
            "samples": 1
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/v1/generation/stable-diffusion-xl-1024-v1-0/image-to-image-masking",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
                response.raise_for_status()
                result = response.json()

                artifacts = result.get("artifacts", [])
                if artifacts:
                    result_base64 = artifacts[0]["base64"]
                    seed = artifacts[0].get("seed", 0)
                    image_data = base64.b64decode(result_base64)

                    image_url = await self._save_image(image_data, f"{uuid.uuid4()}.png")

                    return {
                        "image_url": image_url,
                        "seed": seed,
                        "prompt": full_prompt,
                        "resolution": f"{w}x{h}",
                        "source_image": source_image_url,
                        "mask_image": mask_image_url
                    }

                raise ValueError("No artifacts returned from SD inpaint API")

        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"SD inpaint API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise RuntimeError(f"inpaint generation failed: {str(e)}")

    async def apply_lora(
        self,
        base_image_url: str,
        character_features: List[float],
        lora_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        应用角色LoRA，保持角色一致性

        Args:
            base_image_url: 基础图片URL
            character_features: 角色特征向量
            lora_path: LoRA模型路径

        Returns:
            {"image_url": str}
        """
        # TODO: 实现LoRA特征注入
        # 方案1: 在SD生成时加载LoRA权重
        # 方案2: 使用IP-Adapter进行特征融合
        raise NotImplementedError("LoRA not yet implemented")

    async def _download_and_encode_image(self, image_url: str) -> str:
        """
        下载图片并转为 base64 编码

        Args:
            image_url: 图片URL，支持 file://, http://, s3://

        Returns:
            base64 编码的图片字符串（不含 data URI 前缀）
        """
        import os

        # file:// 本地文件
        if image_url.startswith("file://"):
            filepath = image_url[7:]
            with open(filepath, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")

        # s3:// 对象存储
        if image_url.startswith("s3://"):
            # TODO: 使用 boto3 下载 S3 对象
            raise NotImplementedError("S3 image download not yet implemented")

        # http:///https:// 网络图片
        if image_url.startswith("http://") or image_url.startswith("https://"):
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(image_url)
                response.raise_for_status()
                return base64.b64encode(response.content).decode("utf-8")

        raise ValueError(f"Unsupported image URL scheme: {image_url}")

    async def _save_image(self, image_data: bytes, filename: str) -> str:
        """保存图片到存储"""
        # 实际应该上传到 S3/OSS
        # 这里简化为本地保存
        output_dir = "/opt/AiComic/代码/outputs"
        import os
        os.makedirs(output_dir, exist_ok=True)

        filepath = os.path.join(output_dir, filename)
        with open(filepath, "wb") as f:
            f.write(image_data)

        return f"file://{filepath}"

    def build_prompt_from_shot(
        self,
        keywords: str,
        style: str,
        shot_type: str,
        characters: List[Dict[str, Any]]
    ) -> str:
        """
        根据镜头信息构建完整prompt

        Args:
            keywords: 镜头关键词
            style: 漫画风格
            shot_type: 镜头类型
            characters: 角色列表

        Returns:
            完整的SD prompt
        """
        shot_type_desc = {
            "wide": "wide angle shot, establishing shot",
            "full": "full body shot",
            "medium": "medium shot, waist up",
            "close_up": "close-up shot, detailed",
            "two_shot": "two shot, both characters in frame",
            "over_shoulder": "over shoulder shot",
            "pov": "first person perspective"
        }.get(shot_type, "")

        char_desc = []
        for char in characters:
            name = char.get("name", "")
            emotion = char.get("emotion_default", "neutral")
            desc = char.get("description", "")
            emotion_map = {
                "happy": "smiling, cheerful",
                "sad": "sad, tears",
                "angry": "angry, furious",
                "surprised": "surprised, shocked",
                "neutral": "calm, neutral expression"
            }
            emotion_str = emotion_map.get(emotion, "neutral")
            if desc:
                char_desc.append(f"{name}: {desc}, {emotion_str}")
            else:
                char_desc.append(f"{name}: {emotion_str}")

        parts = [
            self.STYLE_PRESETS.get(style, ""),
            keywords,
            shot_type_desc,
            ", ".join(char_desc) if char_desc else ""
        ]

        return ", ".join([p for p in parts if p])


# 全局实例
image_generator = ImageGenerator()
