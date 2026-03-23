"""Celery异步任务队列配置"""
from celery import Celery
from celery.signals import task_success, task_failure, task_retry
from kombu import Exchange, Queue
import os
import json
from typing import Dict, Any, Optional
from datetime import datetime

# Redis配置
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

# Celery配置
app = Celery(
    "aicomic",
    broker=f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
    backend=f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
)

# 任务路由配置
app.conf.task_routes = {
    "tasks.shot_generate": {"queue": "gpu_high", "priority": 5},
    "tasks.project_generate": {"queue": "gpu_normal", "priority": 5},
    "tasks.lora_train": {"queue": "gpu_low", "priority": 3},
    "tasks.video_merge": {"queue": "cpu", "priority": 5},
    "tasks.tts_generate": {"queue": "cpu", "priority": 7},
    "tasks.feature_extract": {"queue": "cpu", "priority": 7},
}

# 队列配置
app.conf.task_queues = (
    Queue("gpu_high", Exchange("gpu"), routing_key="gpu.high"),
    Queue("gpu_normal", Exchange("gpu"), routing_key="gpu.normal"),
    Queue("gpu_low", Exchange("gpu"), routing_key="gpu.low"),
    Queue("cpu", Exchange("cpu"), routing_key="cpu"),
)

# 任务结果过期时间（24小时）
app.conf.result_expires = 86400

# 任务序列化方式
app.conf.task_serializer = "json"
app.conf.result_serializer = "json"
app.conf.accept_content = ["json"]

# Worker配置
app.conf.worker_prefetch_multiplier = 1
app.conf.worker_max_tasks_per_child = 100

# Redis Stream配置（用于Celery事件）
app.conf.broker_transport_options = {
    "stream_prefix": "aicomic",
    "visibility_timeout": 3600,
}

# 任务状态定义
class TaskStatus:
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType:
    SHOT_GENERATE = "shot_generate"
    PROJECT_GENERATE = "project_generate"
    LORA_TRAIN = "lora_train"
    FEATURE_EXTRACT = "feature_extract"
    VIDEO_MERGE = "video_merge"
    TTS_GENERATE = "tts_generate"


# 任务优先级映射
PRIORITY_MAP = {
    "high": 9,
    "normal": 5,
    "low": 1,
}


def create_task(
    task_type: str,
    params: Dict[str, Any],
    task_id: Optional[str] = None,
    priority: str = "normal"
) -> str:
    """
    创建任务的工厂函数
    返回任务ID
    """
    from celery import uuid
    
    if not task_id:
        task_id = f"task_{uuid()}"
    
    # 根据任务类型分发
    task_map = {
        TaskType.SHOT_GENERATE: shot_generate,
        TaskType.PROJECT_GENERATE: project_generate,
        TaskType.LORA_TRAIN: lora_train,
        TaskType.FEATURE_EXTRACT: feature_extract,
        TaskType.VIDEO_MERGE: video_merge,
        TaskType.TTS_GENERATE: tts_generate,
    }
    
    task_func = task_map.get(task_type)
    if not task_func:
        raise ValueError(f"Unknown task type: {task_type}")
    
    # 延迟调用获取 celery task 对象
    async_result = task_func.apply_async(
        kwargs={**params, "task_id": task_id},
        task_id=task_id,
        priority=PRIORITY_MAP.get(priority, 5)
    )
    
    return task_id


def update_task_progress(
    task_id: str,
    progress: int,
    stage: str,
    stage_detail: str = "",
    sub_progress: Optional[Dict[str, Any]] = None,
    **kwargs
):
    """
    更新任务进度
    由Celery任务内部调用，推送到WebSocket
    """
    from services.websocket_manager import websocket_manager
    
    progress_data = {
        "type": "progress",
        "task_id": task_id,
        "progress": progress,
        "stage": stage,
        "stage_detail": stage_detail,
        "sub_progress": sub_progress or {},
        "timestamp": datetime.now().isoformat()
    }
    
    # 异步推送到WebSocket
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            websocket_manager.send_progress(task_id, progress_data)
        )
    except RuntimeError:
        # 没有事件循环，创建新的
        asyncio.run(websocket_manager.send_progress(task_id, progress_data))


# ========== Celery Tasks ==========

@app.task(bind=True, name="tasks.shot_generate")
def shot_generate(self, **params):
    """
    单镜头生成任务
    预计时长: 15-30s
    """
    task_id = params.get("task_id", self.request.id)
    project_id = params.get("project_id")
    shot_index = params.get("shot_index", 0)
    total_shots = params.get("total_shots", 1)
    
    try:
        # 阶段1: 角色一致性检查 (0-20%)
        update_task_progress(task_id, 5, "character_check", "检查角色一致性...")
        character_result = _check_character_consistency(params)
        update_task_progress(task_id, 15, "character_check", "角色一致性检查完成", {
            "character_id": character_result.get("character_id"),
            "consistency_score": character_result.get("score", 0)
        })
        
        # 阶段2: 镜头生成 (20-80%)
        for step in range(5):
            step_progress = 20 + int((step / 5) * 60)
            update_task_progress(task_id, step_progress, "shot_generating", 
                f"正在生成第{shot_index + 1}个镜头... ({step + 1}/5)",
                {"current_shot": shot_index + 1, "total_shots": total_shots, "step": step + 1}
            )
        
        # 阶段3: 后处理 (80-95%)
        update_task_progress(task_id, 85, "post_processing", "应用动效...")
        _apply_motion_effects(params)
        
        update_task_progress(task_id, 90, "post_processing", "口型同步...")
        _apply_lip_sync(params)
        
        # 阶段4: 完成 (95-100%)
        update_task_progress(task_id, 98, "finalizing", "输出最终结果...")
        output_url = _generate_output(params)
        
        update_task_progress(task_id, 100, "completed", "镜头生成完成")
        
        return {
            "success": True,
            "task_id": task_id,
            "output_url": output_url,
            "shot_index": shot_index
        }
        
    except Exception as e:
        update_task_progress(task_id, 0, "failed", f"生成失败: {str(e)}")
        raise


@app.task(bind=True, name="tasks.project_generate")
def project_generate(self, **params):
    """整项目生成任务（预计5-30分钟）"""
    task_id = params.get("task_id", self.request.id)
    project_id = params.get("project_id")
    shots = params.get("shots", [])
    total_shots = len(shots)
    
    try:
        # 阶段1: 剧本解析 (0-10%)
        update_task_progress(task_id, 3, "script_parsing", "解析剧本...")
        _parse_script(params)
        update_task_progress(task_id, 8, "script_parsing", "剧本解析完成")
        
        # 阶段2: 角色提取 (10-20%)
        update_task_progress(task_id, 12, "character_extraction", "提取角色信息...")
        characters = _extract_characters(params)
        update_task_progress(task_id, 18, "character_extraction", 
            f"提取到{len(characters)}个角色", {"character_count": len(characters)})
        
        # 阶段3: 逐个镜头生成 (20-80%)
        for i, shot in enumerate(shots):
            shot_progress = 20 + int((i / total_shots) * 60)
            update_task_progress(task_id, shot_progress, "shot_generating",
                f"生成第{i + 1}/{total_shots}个镜头",
                {"current_shot": i + 1, "total_shots": total_shots}
            )
            _generate_single_shot(shot, params)
        
        # 阶段4: 视频合成 (80-95%)
        update_task_progress(task_id, 82, "video_merge", "合并视频片段...")
        _merge_videos(params)
        update_task_progress(task_id, 92, "video_merge", "视频合并完成")
        
        # 阶段5: 导出 (95-100%)
        update_task_progress(task_id, 95, "exporting", "生成最终文件...")
        output_url = _export_project(params)
        
        update_task_progress(task_id, 100, "completed", "项目生成完成", {
            "total_shots": total_shots,
            "duration": params.get("duration", 0)
        })
        
        return {
            "success": True,
            "task_id": task_id,
            "output_url": output_url,
            "total_shots": total_shots
        }
        
    except Exception as e:
        update_task_progress(task_id, 0, "failed", f"项目生成失败: {str(e)}")
        raise


@app.task(bind=True, name="tasks.lora_train")
def lora_train(self, **params):
    """LoRA模型训练任务（预计30-60分钟）"""
    task_id = params.get("task_id", self.request.id)
    character_id = params.get("character_id")
    
    try:
        # 阶段1: 数据准备
        update_task_progress(task_id, 5, "data_preparation", "准备训练数据...")
        _prepare_training_data(params)
        
        # 阶段2: 特征提取
        update_task_progress(task_id, 15, "feature_extraction", "提取特征...")
        _extract_training_features(params)
        
        # 阶段3: LoRA训练（多个epoch）
        for epoch in range(10):
            epoch_progress = 20 + int((epoch / 10) * 70)
            update_task_progress(task_id, epoch_progress, "training",
                f"训练中... Epoch {epoch + 1}/10",
                {"epoch": epoch + 1, "total_epochs": 10, "loss": 0.1 * (10 - epoch)}
            )
        
        # 阶段4: 模型保存
        update_task_progress(task_id, 95, "saving", "保存模型...")
        model_path = _save_lora_model(params)
        
        update_task_progress(task_id, 100, "completed", "LoRA训练完成", {
            "character_id": character_id,
            "model_path": model_path
        })
        
        return {"success": True, "model_path": model_path}
        
    except Exception as e:
        update_task_progress(task_id, 0, "failed", f"LoRA训练失败: {str(e)}")
        raise


@app.task(name="tasks.feature_extract")
def feature_extract(self, **params):
    """角色特征提取任务（预计5-10s）"""
    from services.character_consistency import consistency_service
    
    task_id = params.get("task_id", self.request.id)
    reference_images = params.get("reference_images", [])
    
    update_task_progress(task_id, 50, "extracting", "提取角色特征...")
    
    result = consistency_service.extract_features(reference_images)
    
    update_task_progress(task_id, 100, "completed", "特征提取完成")
    
    return {"success": True, "features": result}


@app.task(name="tasks.video_merge")
def video_merge(self, **params):
    """视频合并任务（预计2-5分钟）"""
    task_id = params.get("task_id", self.request.id)
    shot_urls = params.get("shot_urls", [])
    
    update_task_progress(task_id, 30, "merging", "合并视频片段...")
    output_path = _merge_videos(params)
    
    update_task_progress(task_id, 100, "completed", "合并完成")
    return {"success": True, "output_path": output_path}


@app.task(name="tasks.tts_generate")
def tts_generate(self, **params):
    """语音合成任务（预计3-10s）"""
    task_id = params.get("task_id", self.request.id)
    text = params.get("text", "")
    
    update_task_progress(task_id, 50, "synthesizing", "合成语音...")
    audio_url = _synthesize_speech(params)
    
    update_task_progress(task_id, 100, "completed", "语音合成完成")
    return {"success": True, "audio_url": audio_url}


# ========== 内部辅助函数（模拟） ==========

def _check_character_consistency(params):
    return {"character_id": params.get("character_id"), "score": 0.92}

def _apply_motion_effects(params):
    pass

def _apply_lip_sync(params):
    pass

def _generate_output(params):
    return f"https://cdn.example.com/output/{params.get(task_id)}.mp4"

def _parse_script(params):
    pass

def _extract_characters(params):
    return []

def _generate_single_shot(shot, params):
    pass

def _merge_videos(params):
    return f"/output/merged_{params.get(task_id)}.mp4"

def _export_project(params):
    return f"https://cdn.example.com/output/project_{params.get(task_id)}.mp4"

def _prepare_training_data(params):
    pass

def _extract_training_features(params):
    pass

def _save_lora_model(params):
    return f"/models/lora_{params.get(character_id)}.safetensors"

def _synthesize_speech(params):
    return f"https://cdn.example.com/audio/{params.get(task_id)}.wav"


# ========== 信号处理 ==========

@task_success.connect
def task_success_handler(sender=None, result=None, **kwargs):
    """任务成功时的处理"""
    pass

@task_failure.connect
def task_failure_handler(sender=None, exception=None, **kwargs):
    """任务失败时的处理"""
    pass

@task_retry.connect
def task_retry_handler(sender=None, reason=None, **kwargs):
    """任务重试时的处理"""
    pass


if __name__ == "__main__":
    app.start()
