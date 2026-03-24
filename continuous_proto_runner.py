#!/usr/bin/env python3
"""持续执行原型研发任务 - 同步模式，直接在Server B执行"""
import os
import sys
import time
import glob
import hashlib
import json
import subprocess
from datetime import datetime

PROTOTYPE_DIR = "/opt/AiComic/原型"
QUEUE_FILE = "/opt/AiComic/状态报告/原型开发队列_20260325.md"
LOG_FILE = "/opt/AiComic/continuous_proto.log"
STATE_FILE = "/opt/AiComic/状态报告/研发状态_持续监控.json"
PROCESSED_FILE = "/tmp/processed_protos.txt"

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, 'a') as f:
        f.write(line + "\n")

def get_agent_status():
    """获取CrewAI Agent运行状态"""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}:{{.Status}}"],
            capture_output=True, text=True, timeout=30
        )
        lines = [l for l in result.stdout.split('\n') if 'crewai' in l]
        return '\n'.join(lines) if lines else "无Agent运行"
    except:
        return "获取失败"

def main():
    log("🚀 启动持续原型研发任务（同步模式）")
    log(f"任务清单: {QUEUE_FILE}")
    
    # 添加脚本路径
    sys.path.insert(0, '/opt/AiComic/scripts')
    
    while True:
        queue = []
        if os.path.exists(QUEUE_FILE):
            with open(QUEUE_FILE, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.endswith('.md'):
                        queue.append(line)
        
        processed = set()
        if os.path.exists(PROCESSED_FILE):
            with open(PROCESSED_FILE, 'r') as f:
                for line in f:
                    processed.add(line.strip())
        
        pending = [p for p in queue if p not in processed]
        completed = len(queue) - len(pending)
        total = len(queue)
        
        # 获取Agent状态
        agent_status = get_agent_status()
        log(f"🤖 Agent状态: {agent_status.replace(chr(10), ' | ')}")
        
        if not pending:
            log("✅ 所有原型已处理完成！")
            save_state(completed, total, "已完成", "无", agent_status)
            log("等待 10 分钟...")
            time.sleep(600)
            continue
        
        current = pending[0]
        next_proto = pending[1] if len(pending) > 1 else "无"
        
        log(f"📋 进度: {completed}/{total} 完成, 待处理: {len(pending)} 个")
        log(f"📋 当前: {current}")
        
        try:
            proto_path = os.path.join(PROTOTYPE_DIR, current)
            if not os.path.exists(proto_path):
                log(f"❌ 原型文件不存在: {proto_path}")
                with open(PROCESSED_FILE, 'a') as f:
                    f.write(current + "\n")
                continue
            
            task_id = f"PROTO-AUTO-{hashlib.md5(current.encode()).hexdigest()[:8]}"
            
            with open(proto_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            log(f"🤖 触发任务: {task_id}")
            
            # 直接调用 execute_proto_task
            from bot_http_server_v2 import execute_proto_task
            
            payload = {
                "proto_file": current,
                "description": content[:3000],
                "record_id": ""
            }
            
            log(f"⏳ 执行中: {current}")
            result = execute_proto_task(task_id, payload)
            
            log(f"📄 结果: {result}")
            log(f"✅ 完成: {current}")
            
            with open(PROCESSED_FILE, 'a') as f:
                f.write(current + "\n")
            
        except Exception as e:
            log(f"❌ 失败: {current} - {e}")
        
        log("等待 120 秒...")
        time.sleep(120)

def save_state(completed, total, current, next_proto, agent_status=""):
    state = {
        "completed": completed,
        "total": total,
        "current": current,
        "next_proto": next_proto,
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "agent_status": agent_status
    }
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
