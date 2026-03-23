"""
镜头生成异步任务
"""
import asyncio
import uuid
from typing import List, Dict, Any

from celery import shared_task

# 导入图像生成器（延迟导入避免循环依赖）
_image_generator = None


def get_image_generator():
    global _image_generator
    if _image_generator is None:
        from services.image_generator import ImageGenerator
        _image_generator = ImageGenerator()
    return _image_generator


@shared_task(bind=True, name="tasks.shot_tasks.generate_shot")
def generate_shot(self, shot_id: str, prompt: str, style: str = "anime", 
                   quality: str = "hd", reference_images: List[str] = None) -> Dict[str, Any]:
    """
    异步生成单个镜头画面
    
    Args:
        shot_id: 镜头ID
        prompt: 画面描述
        style: 风格
        quality: 质量
        reference_images: 参考图URL列表
    
    Returns:
        {"shot_id": str, "image_url": str, "status": str}
    """
    try:
        generator = get_image_generator()
        
        # 在事件循环中执行异步生成
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                generator.generate(
                    prompt=prompt,
                    style=style,
                    quality=quality,
                    reference_images=reference_images
                )
            )
        finally:
            loop.close()
        
        return {
            "shot_id": shot_id,
            "image_url": result.get("image_url", ""),
            "seed": result.get("seed", 0),
            "status": "completed"
        }
    except Exception as e:
        return {
            "shot_id": shot_id,
            "error": str(e),
            "status": "failed"
        }


@shared_task(bind=True, name="tasks.shot_tasks.generate_shot_batch")
def generate_shot_batch(self, shots: List[Dict[str, Any]], style: str = "anime",
                         quality: str = "hd") -> Dict[str, Any]:
    """
    批量生成镜头画面
    
    Args:
        shots: [{"shot_id": str, "prompt": str, "reference_images": List[str]}, ...]
        style: 风格
        quality: 质量
    
    Returns:
        {"results": [...], "completed": int, "failed": int}
    """
    generator = get_image_generator()
    results = []
    completed = 0
    failed = 0
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        for shot in shots:
            shot_id = shot.get("shot_id")
            prompt = shot.get("prompt", "")
            reference_images = shot.get("reference_images")
            
            try:
                result = loop.run_until_complete(
                    generator.generate(
                        prompt=prompt,
                        style=style,
                        quality=quality,
                        reference_images=reference_images
                    )
                )
                results.append({
                    "shot_id": shot_id,
                    "image_url": result.get("image_url", ""),
                    "seed": result.get("seed", 0),
                    "status": "completed"
                })
                completed += 1
            except Exception as e:
                results.append({
                    "shot_id": shot_id,
                    "error": str(e),
                    "status": "failed"
                })
                failed += 1
    finally:
        loop.close()
    
    return {
        "results": results,
        "completed": completed,
        "failed": failed,
        "total": len(shots)
    }
