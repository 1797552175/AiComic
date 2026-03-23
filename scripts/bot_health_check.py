#!/usr/bin/env python3
"""
Bot 健康检查 + 自动唤醒脚本
- 检查 stub 服务是否在线
- 如果离线则自动重启
- 如果异常则通知用户
"""
import requests
import subprocess
import time
from datetime import datetime

API_KEY = "aicomic-shared-secret-key-2026"
HEADERS = {"X-API-Key": API_KEY}

# Bot 配置
BOTS = [
    {"name": "状态监控机器人", "port": 8001, "type": "monitor"},
    {"name": "产品经理机器人", "port": 8002, "type": "pm"},
    {"name": "研发机器人", "port": 8003, "type": "dev"},
    {"name": "营销机器人", "port": 8004, "type": "marketing"},
]

def check_bot_health(port: int) -> dict:
    """检查 Bot 健康状态"""
    try:
        resp = requests.get(f"http://127.0.0.1:{port}/health", timeout=3)
        if resp.status_code == 200:
            return {"status": "ok", "data": resp.json()}
        else:
            return {"status": "error", "message": f"HTTP {resp.status_code}"}
    except requests.exceptions.ConnectionError:
        return {"status": "offline", "message": "连接失败"}
    except requests.exceptions.Timeout:
        return {"status": "timeout", "message": "请求超时"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def start_bot(port: int, bot_type: str, name: str) -> bool:
    """启动 Bot stub 服务"""
    print(f"[{name}] 服务离线，尝试启动...")
    
    try:
        # 启动 stub 服务
        cmd = f"cd /opt/AiComic/scripts && python3 start_bots.py > /tmp/bot_start_{port}.log 2>&1 &"
        subprocess.run(cmd, shell=True, timeout=10)
        
        # 等待启动
        time.sleep(5)
        
        # 再次检查
        health = check_bot_health(port)
        if health["status"] == "ok":
            print(f"[{name}] 启动成功！")
            return True
        else:
            print(f"[{name}] 启动后仍异常: {health}")
            return False
            
    except Exception as e:
        print(f"[{name}] 启动失败: {e}")
        return False

def check_and_wake_bots() -> dict:
    """检查所有 Bot 并唤醒离线服务"""
    results = {}
    offline_bots = []
    
    print(f"\n{'='*60}")
    print(f"Bot 健康检查 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    for bot in BOTS:
        name = bot["name"]
        port = bot["port"]
        
        health = check_bot_health(port)
        
        if health["status"] == "ok":
            print(f"✅ {name} (端口 {port}): 健康")
            results[bot["type"]] = "ok"
        else:
            print(f"❌ {name} (端口 {port}): {health['status']} - {health.get('message', '')}")
            
            # 尝试唤醒
            if start_bot(port, bot["type"], name):
                results[bot["type"]] = "recovered"
                offline_bots.append(bot)
            else:
                results[bot["type"]] = "failed"
                offline_bots.append(bot)
    
    print(f"\n{'='*60}")
    print("检查完成")
    print(f"{'='*60}")
    
    if offline_bots:
        print(f"\n⚠️ 有 {len(offline_bots)} 个 Bot 需要关注:")
        for bot in offline_bots:
            print(f"  - {bot['name']} (端口 {bot['port']})")
    
    return results

def test_task_dispatch(bot_type: str, port: int, task_id: str = "HEALTH-CHECK") -> dict:
    """测试任务下发"""
    task = {
        "task_id": task_id,
        "task_type": "health_check",
        "source": "健康检查",
        "target": bot_type,
        "payload": {
            "任务描述": "健康检查",
        }
    }
    
    try:
        resp = requests.post(
            f"http://127.0.0.1:{port}/execute",
            json=task,
            headers=HEADERS,
            timeout=30
        )
        if resp.status_code == 200:
            return {"status": "ok", "response": resp.json()}
        else:
            return {"status": "error", "message": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def main():
    """主函数"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--watch":
        # 持续监控模式
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60
        print(f"\n🔄 启动持续监控模式 (间隔 {interval} 秒)")
        print("按 Ctrl+C 停止\n")
        
        try:
            while True:
                check_and_wake_bots()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n\n监控已停止")
    else:
        # 单次检查
        results = check_and_wake_bots()
        
        # 测试任务下发
        print("\n\n【任务下发测试】")
        for bot in BOTS:
            port = bot["port"]
            result = test_task_dispatch(bot["type"], port)
            status = "✅" if result["status"] == "ok" else "❌"
            print(f"  {status} {bot['name']}: {result['status']}")

if __name__ == "__main__":
    main()
