"""
公共工具模块 - 所有模板共享的基础工具
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

class TaskOutput:
    """标准化任务输出"""
    def __init__(self, task_name: str):
        self.task_name = task_name
        self.result: Any = None
        self.logs: List[str] = []
        self.start_time = datetime.now()
    
    def success(self, result: Any):
        self.result = result
        self._log(f"✓ 任务完成: {task_name}")
        return self
    
    def error(self, msg: str):
        self._log(f"✗ 任务失败: {msg}")
        return self
    
    def _log(self, msg: str):
        self.logs.append(msg)
        logger.info(msg)
    
    def summary(self) -> str:
        duration = (datetime.now() - self.start_time).seconds
        return f"[{self.task_name}] 耗时 {duration}s | 结果: {self.result}"


def load_config(config_path: str = "/opt/AiComic/config.json") -> Dict:
    """加载配置文件"""
    if os.path.exists(config_path):
        with open(config_path) as f:
            return json.load(f)
    return {}


def save_output(result: Any, output_path: str):
    """保存任务结果到文件"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        if isinstance(result, str):
            f.write(result)
        else:
            json.dump(result, f, ensure_ascii=False, indent=2)
    logger.info(f"结果已保存: {output_path}")


def ensure_dir(path: str):
    """确保目录存在"""
    os.makedirs(path, exist_ok=True)
    return path


def get_project_root() -> str:
    return "/opt/AiComic"


def log_agent_start(agent_name: str, task: str):
    logger.info(f"[{agent_name}] 开始任务: {task}")


def log_agent_done(agent_name: str, output: str):
    logger.info(f"[{agent_name}] 完成，输出: {output[:100]}...")
