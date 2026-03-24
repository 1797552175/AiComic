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

from config.config import settings


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
        strength: float = 0.5
    ) -> Dict[str, Any]:
        """
        图生图模式：基于参考图生成新图

        Args:
            source_image_url: 参考图URL
            prompt: 描述词
            style: 风格
            strength: 变换强度 0.0-1.0

        Returns:
            {"image_url": str, "thumbnail_url": str, "seed": int}
        """
        # 图生图实现
        import base64
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                init_image_b64 = source_image_url
                if source_image_url.startswith("http"):
                    ref_resp = await client.get(source_image_url)
                    init_image_b64 = base64.b64encode(ref_resp.content).decode()
                
                style_prefix = self.STYLE_PRESETS.get(style, self.STYLE_PRESETS["anime"])
                full_prompt = f"{style_prefix}, {prompt}"
                
                payload = {
                    "text_prompts": [{"text": full_prompt, "weight": 1.0}],
                    "init_image": init_image_b64,
                    "image_strength": strength,
                    "cfg_scale": 7.5,
                    "steps": 30,
                    "samples": 1
                }
                
                response = await client.post(
                    f"{self.base_url}/v1/generation/stable-diffusion-xl-1012-base/image-to-image",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload
                )
                result = response.json()
                
                if "artifacts" in result:
                    img_data = result["artifacts"][0]["base64"]
                    return {
                        "image_url": f"data:image/png;base64,{img_data}",
                        "thumbnail_url": f"data:image/png;base64,{img_data[:1000]}",
                        "seed": result.get("seed", 0)
                    }
                return {"error": str(result)}
        except Exception as e:
            return {"error": str(e)}

    async def inpaint(
        self,
        source_image_url: str,
        mask_image_url: str,
        prompt: str
    ) -> Dict[str, Any]:
        """
        局部重绘：只重绘被mask遮挡的区域

        Args:
            source_image_url: 原图URL
            mask_image_url: mask图URL（白色=重绘区域）
            prompt: 新描述词

        Returns:
            {"image_url": str}
        """
        # 局部重绘实现
        import base64
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # 下载原图和mask
                if source_image_url.startswith("http"):
                    src_resp = await client.get(source_image_url)
                    src_b64 = base64.b64encode(src_resp.content).decode()
                else:
                    src_b64 = source_image_url
                
                if mask_image_url.startswith("http"):
                    mask_resp = await client.get(mask_image_url)
                    mask_b64 = base64.b64encode(mask_resp.content).decode()
                else:
                    mask_b64 = mask_image_url
                
                style_prefix = self.STYLE_PRESETS.get("anime", "")
                full_prompt = f"{style_prefix}, {prompt}"
                
                payload = {
                    "text_prompts": [{"text": full_prompt, "weight": 1.0}],
                    "init_image": src_b64,
                    "mask_image": mask_b64,
                    "mask_source": "upload",
                    "cfg_scale": 7.5,
                    "steps": 30,
                    "samples": 1
                }
                
                response = await client.post(
                    f"{self.base_url}/v1/generation/stable-diffusion-xl-1012-base/image-to-image/masking",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload
                )
                result = response.json()
                
                if "artifacts" in result:
                    img_data = result["artifacts"][0]["base64"]
                    return {
                        "image_url": f"data:image/png;base64,{img_data}",
                        "mask_applied": True
                    }
                return {"error": str(result)}
        except Exception as e:
            return {"error": str(e)}

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
        # LoRA 特征注入实现
        import base64
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # 下载基础图片
                if base_image_url.startswith("http"):
                    img_resp = await client.get(base_image_url)
                    img_b64 = base64.b64encode(img_resp.content).decode()
                else:
                    img_b64 = base_image_url
                
                # 构造 LoRA 请求
                # 方案1: SD LoRA 权重注入
                payload = {
                    "text_prompts": [{"text": "anime character, high quality", "weight": 1.0}],
                    "init_image": img_b64,
                    "model": "stabilityai/stable-diffusion-xl-base-1.0",
                    "lora_weights": lora_path or "default",
                    "character_features": character_features,
                    "cfg_scale": 7.5,
                    "steps": 30,
                    "samples": 1
                }
                
                response = await client.post(
                    f"{self.base_url}/v1/generation/stable-diffusion-xl-1012-base/image-to-image",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload
                )
                result = response.json()
                
                if "artifacts" in result:
                    img_data = result["artifacts"][0]["base64"]
                    return {
                        "image_url": f"data:image/png;base64,{img_data}",
                        "lora_applied": lora_path or "default",
                        "character_consistent": True
                    }
                return {"error": str(result)}
        except Exception as e:
            return {"error": str(e)}

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
