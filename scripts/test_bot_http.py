#!/usr/bin/env python3
"""
测试 Bot HTTP 接口通信
测试状态监控机器人能否通过 HTTP 调用其他 Bot
"""
import requests
import json
import time

API_KEY = "aicomic-shared-secret-key-2026"
HEADERS = {"X-API-Key": API_KEY}

def test_bot_health(port: int, name: str) -> bool:
    """测试 Bot 健康状态"""
    try:
        resp = requests.get(f"http://127.0.0.1:{port}/health", timeout=5)
        if resp.status_code == 200:
            print(f"  ✅ {name} 健康检查通过")
            return True
        else:
            print(f"  ❌ {name} 健康检查失败: {resp.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ {name} 无法连接: {e}")
        return False

def test_task_dispatch(target_port: int, target_name: str) -> dict:
    """测试向目标 Bot 发送任务"""
    task = {
        "task_id": f"test-{int(time.time())}",
        "task_type": "analyze",
        "source": "状态监控机器人",
        "target": target_name,
        "payload": {
            "任务描述": "测试任务：验证 HTTP 接口通信是否正常",
            "优先级": "P1",
            "截止时间": "2026-03-23 12:00"
        }
    }
    
    try:
        print(f"\n  发送请求到 {target_name} (端口 {target_port})...")
        resp = requests.post(
            f"http://127.0.0.1:{target_port}/execute",
            json=task,
            headers=HEADERS,
            timeout=30
        )
        
        if resp.status_code == 200:
            result = resp.json()
            print(f"  ✅ {target_name} 响应成功")
            print(f"     code: {result.get('code')}")
            print(f"     message: {result.get('message')}")
            if result.get('data'):
                print(f"     result: {json.dumps(result['data'], ensure_ascii=False)}")
            return result
        else:
            print(f"  ❌ {target_name} 响应错误: {resp.status_code}")
            print(f"     {resp.text}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"  ❌ {target_name} 请求超时")
        return None
    except Exception as e:
        print(f"  ❌ {target_name} 请求失败: {e}")
        return None

def test_full_workflow():
    """测试完整工作流"""
    print("\n" + "=" * 60)
    print("测试完整工作流：监控 → 产品经理 → 研发 → 营销")
    print("=" * 60)
    
    workflow = [
        (8002, "产品经理机器人"),
        (8003, "研发机器人"),
        (8004, "营销机器人"),
    ]
    
    results = []
    for port, name in workflow:
        print(f"\n📤 步骤 {len(results)+1}: 调用 {name}")
        result = test_task_dispatch(port, name)
        results.append(result is not None)
        time.sleep(1)
    
    print("\n" + "=" * 60)
    print("工作流测试结果")
    print("=" * 60)
    
    all_success = all(results)
    if all_success:
        print("✅ 所有步骤成功！多 Bot HTTP 通信测试通过！")
    else:
        print("❌ 部分步骤失败，请检查日志")
    
    return all_success

def main():
    print("=" * 60)
    print("Bot HTTP 接口通信测试")
    print("=" * 60)
    
    # 1. 健康检查
    print("\n【1. 健康检查】")
    bots = [
        (8001, "状态监控机器人"),
        (8002, "产品经理机器人"),
        (8003, "研发机器人"),
        (8004, "营销机器人"),
    ]
    
    health_results = []
    for port, name in bots:
        health_results.append(test_bot_health(port, name))
    
    if not all(health_results):
        print("\n⚠️ 部分 Bot 未启动或无法连接，请先运行 bot_http_server.py")
        return
    
    # 2. 单点调用测试
    print("\n【2. 单点调用测试】")
    test_task_dispatch(8002, "产品经理机器人")
    
    # 3. 完整工作流测试
    print("\n【3. 完整工作流测试】")
    test_full_workflow()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
