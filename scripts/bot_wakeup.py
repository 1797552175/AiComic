#!/usr/bin/env python3
"""
Bot 唤醒机制
检测真正的 OpenClaw Bot 是否在线，如果离线则尝试唤醒或通知用户
"""
import requests
import json
import subprocess
from datetime import datetime

# ============== 配置 ==============
API_KEY = "aicomic-shared-secret-key-2026"

# 真正的 OpenClaw Bot session keys
OPENCLAW_BOTS = {
    "研发机器人": "agent:main:feishu:direct:ou_633e8feb08c1c9b318b707f23cba3850",
    "产品经理机器人": "agent:main:feishu:direct:ou_0fe6e8361ab0874a8d7c0df9df1be598",
    "营销机器人": "agent:main:feishu:direct:ou_1fc8e7e760b4403f1bfe021de16fdcb7",
}

# stub 端口配置
STUB_PORTS = {
    "状态监控机器人": 8001,
    "产品经理机器人": 8002,
    "研发机器人": 8003,
    "营销机器人": 8004,
}

# ============== 检测函数 ==============

def check_stub_health(name: str, port: int) -> dict:
    """检查 stub 是否在线"""
    try:
        resp = requests.get(f"http://127.0.0.1:{port}/health", timeout=3)
        if resp.status_code == 200:
            return {"status": "ok", "stub": True}
    except:
        pass
    return {"status": "offline", "stub": True}

def check_openclaw_bot(bot_name: str, session_key: str) -> dict:
    """检查 OpenClaw Bot 是否在线"""
    # 通过 sessions_list 检查 session 是否存在且活跃
    try:
        # 这里调用 OpenClaw 的 API 来检查 session 状态
        # 由于在同一台机器上，可以通过 Unix socket 或 HTTP localhost
        result = subprocess.run(
            ["openclaw", "sessions", "list", "--format", "json"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10
        )
        
        if result.returncode == 0:
            sessions = json.loads(result.stdout)
            for session in sessions:
                if session.get("key") == session_key:
                    return {
                        "status": "ok" if session.get("active") else "idle",
                        "stub": False,
                        "last_activity": session.get("updatedAt")
                    }
        
        return {"status": "offline", "stub": False}
        
    except Exception as e:
        return {"status": "error", "error": str(e), "stub": False}

def wake_up_bot(bot_name: str, session_key: str) -> bool:
    """尝试唤醒 Bot"""
    print(f"[唤醒] 尝试唤醒 {bot_name}...")
    
    # 方式1：通过 sessions_send 发送唤醒消息
    try:
        result = subprocess.run(
            ["openclaw", "sessions", "send", session_key, "ping"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10
        )
        
        if result.returncode == 0:
            print(f"[唤醒] {bot_name} 已发送唤醒消息")
            return True
    except Exception as e:
        print(f"[唤醒] {bot_name} 失败: {e}")
    
    return False

def notify_user(message: str):
    """通知用户"""
    print(f"\n[通知] {message}")
    print("[通知] 请人工介入处理")
    # 实际实现时会通过飞书消息通知

# ============== 主函数 ==============

def check_all_bots():
    """检查所有 Bot 状态"""
    print(f"\n{'='*60}")
    print(f"Bot 状态检查 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    issues = []  # 需要处理的问题
    
    # 检查 stub
    print("\n【Stub 进程】")
    for name, port in STUB_PORTS.items():
        health = check_stub_health(name, port)
        status = "✅" if health["status"] == "ok" else "❌"
        print(f"  {status} {name} (端口 {port})")
        if health["status"] != "ok":
            issues.append({"type": "stub_offline", "bot": name, "port": port})
    
    # 检查真正的 OpenClaw Bot
    print("\n【OpenClaw Bot】")
    for name, session_key in OPENCLAW_BOTS.items():
        health = check_openclaw_bot(name, session_key)
        
        if health["status"] == "ok":
            print(f"  ✅ {name} - 在线")
        elif health["status"] == "idle":
            print(f"  🟡 {name} - 空闲")
        elif health["status"] == "offline":
            print(f"  ❌ {name} - 离线")
            issues.append({"type": "bot_offline", "bot": name, "session_key": session_key})
        else:
            print(f"  ⚠️ {name} - 错误: {health.get('error')}")
            issues.append({"type": "bot_error", "bot": name, "error": health.get("error")})
    
    # 处理问题
    if issues:
        print(f"\n{'='*60}")
        print(f"发现问题 {len(issues)} 个")
        print(f"{'='*60}")
        
        for issue in issues:
            print(f"\n处理: {issue}")
            
            if issue["type"] == "stub_offline":
                # stub 离线，尝试重启
                print(f"  → 尝试重启 stub {issue['bot']}...")
                # 这里会调用 start_bots.py 重启
                
            elif issue["type"] == "bot_offline":
                # Bot 离线，尝试唤醒
                print(f"  → 尝试唤醒 {issue['bot']}...")
                success = wake_up_bot(issue["bot"], issue["session_key"])
                if not success:
                    # 唤醒失败，通知用户
                    notify_user(f"{issue['bot']} 离线，唤醒失败，需要人工介入")
    
    return issues

if __name__ == "__main__":
    check_all_bots()
