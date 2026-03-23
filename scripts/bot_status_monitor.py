#!/usr/bin/env python3
"""
Bot 状态监控系统
监控机器人定期轮询各 Bot 状态，检测是否在工作
"""
import requests
import time
import json
from datetime import datetime

API_KEY = "aicomic-shared-secret-key-2026"
HEADERS = {"X-API-Key": API_KEY}

BOTS = [
    {"name": "状态监控机器人", "port": 8001},
    {"name": "产品经理机器人", "port": 8002},
    {"name": "研发机器人", "port": 8003},
    {"name": "营销机器人", "port": 8004},
]

def check_bot_status(name: str, port: int) -> dict:
    """检查单个 Bot 状态"""
    try:
        # 1. 健康检查
        health_resp = requests.get(f"http://127.0.0.1:{port}/health", timeout=3)
        if health_resp.status_code != 200:
            return {"name": name, "port": port, "status": "error", "message": "健康检查失败"}
        
        health_data = health_resp.json()
        
        # 2. 获取详细状态（通过 /status 端点）
        try:
            status_resp = requests.get(f"http://127.0.0.1:{port}/status", timeout=3)
            if status_resp.status_code == 200:
                status_data = status_resp.json()
            else:
                status_data = {"state": "unknown"}
        except:
            status_data = {"state": "unknown"}
        
        return {
            "name": name,
            "port": port,
            "status": "ok",
            "health": health_data,
            "state": status_data.get("state", "unknown"),
            "current_task": status_data.get("current_task", None),
            "last_heartbeat": status_data.get("last_heartbeat", None),
        }
        
    except requests.exceptions.ConnectionError:
        return {"name": name, "port": port, "status": "offline", "message": "连接失败"}
    except requests.exceptions.Timeout:
        return {"name": name, "port": port, "status": "timeout", "message": "请求超时"}
    except Exception as e:
        return {"name": name, "port": port, "status": "error", "message": str(e)}

def get_bot_status_icon(state: str) -> str:
    """获取状态图标"""
    icons = {
        "idle": "🟢",       # 空闲
        "processing": "🔵",  # 处理中
        "error": "🔴",      # 错误
        "unknown": "⚪",     # 未知
    }
    return icons.get(state, "⚪")

def check_all_bots():
    """检查所有 Bot 状态"""
    print("=" * 60)
    print(f"Bot 状态监控 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    results = []
    for bot in BOTS:
        result = check_bot_status(bot["name"], bot["port"])
        results.append(result)
        
        icon = get_bot_status_icon(result.get("state", "unknown"))
        
        if result["status"] == "ok":
            task_info = ""
            if result.get("current_task"):
                task_info = f" | 任务: {result['current_task']}"
            print(f"{icon} {result['name']} (端口 {result['port']}) - 状态: {result.get('state', 'unknown')}{task_info}")
        else:
            print(f"🔴 {result['name']} (端口 {result['port']}) - {result.get('message', '未知错误')}")
    
    print()
    
    # 统计
    states = [r.get("state", "unknown") for r in results if r["status"] == "ok"]
    idle_count = states.count("idle")
    processing_count = states.count("processing")
    error_count = states.count("error")
    
    print(f"📊 统计: 🟢 空闲 {idle_count} | 🔵 处理中 {processing_count} | 🔴 错误 {error_count}")
    
    if error_count > 0:
        print("\n⚠️ 有 Bot 处于错误状态，需要人工检查！")
    
    return results

def continuous_monitor(interval: int = 30):
    """持续监控模式"""
    print(f"\n🔄 启动持续监控模式（每 {interval} 秒检查一次）")
    print("按 Ctrl+C 停止\n")
    
    try:
        while True:
            check_all_bots()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n\n监控已停止")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--watch":
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        continuous_monitor(interval)
    else:
        check_all_bots()
