#!/usr/bin/env python3
"""
Bot HTTP 接口模拟服务 v2
使用 subprocess 启动多个 uvicorn 进程
"""
import subprocess
import time
import sys
import signal

API_KEY = "aicomic-shared-secret-key-2026"

# 各 Bot 配置
BOTS = [
    {"name": "monitor", "port": 8001, "app": "bot_http_server:monitor_app"},
    {"name": "pm", "port": 8002, "app": "bot_http_server:pm_app"},
    {"name": "dev", "port": 8003, "app": "bot_http_server:dev_app"},
    {"name": "marketing", "port": 8004, "app": "bot_http_server:marketing_app"},
]

def main():
    print("=" * 60)
    print("启动 Bot HTTP 接口模拟服务")
    print("=" * 60)
    
    # 先导入并创建 app（需要确保导入成功）
    sys.path.insert(0, '/opt/AiComic/scripts')
    
    # 导入 bot_http_server 模块（会重新加载）
    import importlib
    import bot_http_server
    importlib.reload(bot_http_server)
    
    processes = []
    
    try:
        for bot in BOTS:
            print(f"启动 {bot['name']} 机器人 (端口 {bot['port']})...")
            
            cmd = [
                "python3", "-m", "uvicorn",
                bot["app"],
                "--host", "127.0.0.1",
                "--port", str(bot["port"]),
                "--log-level", "info"
            ]
            
            p = subprocess.Popen(
                cmd,
                cwd="/opt/AiComic/scripts",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )
            processes.append((bot["name"], p))
            print(f"  PID: {p.pid}")
        
        print("\n所有 Bot 服务已启动:")
        for name, p in processes:
            print(f"  - {name}: PID {p.pid}")
        
        print(f"\nAPI Key: {API_KEY}")
        print("\n按 Ctrl+C 停止服务\n")
        
        # 保持运行
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n停止所有服务...")
        for name, p in processes:
            p.terminate()
            print(f"  已停止 {name}")
        print("完成")
    except Exception as e:
        print(f"错误: {e}")
        for name, p in processes:
            p.terminate()

if __name__ == "__main__":
    main()
