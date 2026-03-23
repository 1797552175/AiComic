#!/usr/bin/env python3
"""
任务下发模块 - 状态监控机器人专用
通过 HTTP 接口向各 Bot 下发任务
"""
import requests
from typing import Dict, Any, Optional

# ============== 配置 ==============
API_KEY = "aicomic-shared-secret-key-2026"
HEADERS = {"X-API-Key": API_KEY}

# Bot 端口配置
BOT_PORTS = {
    "monitor": 8001,    # 状态监控机器人
    "pm": 8002,        # 产品经理机器人
    "dev": 8003,       # 研发机器人
    "marketing": 8004, # 营销机器人
}

# Bot Token 配置
BOT_TOKENS = {
    "monitor": "LvyAzv4oVxqapgnFn75p4bT0z0LWxKfT",
    "pm": "W9E7PajaPByhbiUNMDRJVfm14eBcBnMG",
    "dev": "QMP18ohaSMbOAk4ElROCUbd1NYnkXSf0",
    "marketing": "TiARqfojrCJYzSdSG2vP4fsINSAHFAUg",
}

# Bot 名称映射
BOT_NAMES = {
    "pm": "产品经理机器人",
    "dev": "研发机器人",
    "marketing": "营销机器人",
}

# ============== 核心函数 ==============

def dispatch_task(bot_type: str, task: dict) -> dict:
    """
    向指定 Bot 下发任务
    
    参数:
        bot_type: pm/dev/marketing
        task: 任务详情
            - task_id: 任务ID
            - task_type: analyze/dev/verify/market
            - source: 来源
            - target: 目标
            - payload: 任务描述、优先级等
    返回:
        Bot 的响应结果
    """
    port = BOT_PORTS.get(bot_type)
    if not port:
        return {"code": 1, "message": f"未知 Bot 类型: {bot_type}"}
    
    bot_name = BOT_NAMES.get(bot_type, bot_type)
    
    try:
        print(f"[dispatch] 向 {bot_name} (端口 {port}) 下发任务: {task.get('task_id')}")
        
        response = requests.post(
            f"http://127.0.0.1:{port}/execute",
            json=task,
            headers=HEADERS,
            timeout=300  # 5分钟超时
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"[dispatch] {bot_name} 响应成功: code={result.get('code')}")
            return result
        else:
            print(f"[dispatch] {bot_name} 响应错误: HTTP {response.status_code}")
            return {"code": 1, "message": f"HTTP {response.status_code}"}
            
    except requests.exceptions.ConnectionError:
        print(f"[dispatch] {bot_name} 连接失败")
        return {"code": 1, "message": "连接失败，Bot 可能离线"}
    except requests.exceptions.Timeout:
        print(f"[dispatch] {bot_name} 请求超时")
        return {"code": 1, "message": "请求超时"}
    except Exception as e:
        print(f"[dispatch] {bot_name} 错误: {e}")
        return {"code": 1, "message": str(e)}


def get_bot_status(bot_type: str) -> Optional[dict]:
    """获取 Bot 状态"""
    port = BOT_PORTS.get(bot_type)
    if not port:
        return None
    
    try:
        response = requests.get(f"http://127.0.0.1:{port}/status", timeout=3)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


def check_all_bots() -> dict:
    """检查所有 Bot 状态"""
    results = {}
    for bot_type, port in BOT_PORTS.items():
        status = get_bot_status(bot_type)
        results[bot_type] = status is not None
    return results


def is_bot_available(bot_type: str) -> bool:
    """检查 Bot 是否可用"""
    return get_bot_status(bot_type) is not None


# ============== 便捷函数 ==============

def dispatch_dev_task(task_id: str, description: str, priority: str = "P1", 
                      dependencies: list = None, deadline: str = "") -> dict:
    """下发研发任务"""
    task = {
        "task_id": task_id,
        "task_type": "dev",
        "source": "状态监控机器人",
        "target": "研发机器人",
        "payload": {
            "任务描述": description,
            "优先级": priority,
            "截止时间": deadline,
            "依赖文件": dependencies or []
        }
    }
    return dispatch_task("dev", task)


def dispatch_pm_task(task_id: str, description: str, priority: str = "P1",
                     dependencies: list = None, deadline: str = "") -> dict:
    """下发产品经理任务"""
    task = {
        "task_id": task_id,
        "task_type": "analyze",
        "source": "状态监控机器人",
        "target": "产品经理机器人",
        "payload": {
            "任务描述": description,
            "优先级": priority,
            "截止时间": deadline,
            "依赖文件": dependencies or []
        }
    }
    return dispatch_task("pm", task)


def dispatch_marketing_task(task_id: str, description: str, priority: str = "P1",
                           dependencies: list = None, deadline: str = "") -> dict:
    """下发营销任务"""
    task = {
        "task_id": task_id,
        "task_type": "verify",
        "source": "状态监控机器人",
        "target": "营销机器人",
        "payload": {
            "任务描述": description,
            "优先级": priority,
            "截止时间": deadline,
            "依赖文件": dependencies or []
        }
    }
    return dispatch_task("marketing", task)


# ============== 测试 ==============
if __name__ == "__main__":
    print("=== Bot 状态检查 ===")
    for bot_type, port in BOT_PORTS.items():
        status = get_bot_status(bot_type)
        if status:
            print(f"✅ {BOT_NAMES[bot_type]}: {status.get('state', 'unknown')}")
        else:
            print(f"❌ {BOT_NAMES[bot_type]}: 离线")
    
    print("\n=== 测试下发任务 ===")
    # 示例：下发一个测试任务
    result = dispatch_dev_task(
        task_id="TEST-001",
        description="测试任务下发功能",
        priority="P2"
    )
    print(f"结果: {result}")
