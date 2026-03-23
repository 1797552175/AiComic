#!/usr/bin/env python3
"""
Bot HTTP Server v2 - 简化版
"""
import os
import sys
import json
import time
import subprocess
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8001
BOT_TYPE = sys.argv[1] if len(sys.argv) > 1 else "unknown"

STATE = {
    "bot": f"{BOT_TYPE}机器人",
    "port": PORT,
    "status": "idle",
    "task_id": None,
    "progress": 0,
    "last_update": time.time(),
    "errors": 0,
    "completed": 0
}

TASKS = {}  # task_id -> state

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[{BOT_TYPE}] {fmt % args}")
    
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "bot": BOT_TYPE}).encode())
        elif parsed.path == "/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(STATE).encode())
        elif parsed.path == "/ask_for_task":
            params = parse_qs(parsed.query)
            bot_type = params.get("bot_type", [BOT_TYPE])[0]
            # 从 Monitor 拉取任务
            try:
                result = subprocess.run(
                    ["python3", "/tmp/fetch_bitable_tasks.py"],
                    capture_output=True, timeout=15
                )
            except:
                pass
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"has_task": False}).encode())
        elif parsed.path == "/queue":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"pending": [], "running": [], "completed": []}).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        parsed = urlparse(self.path)
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len) if content_len > 0 else b"{}"
        
        if parsed.path == "/execute":
            try:
                data = json.loads(body)
            except:
                data = {}
            task_id = data.get("task_id", f"task_{int(time.time())}")
            STATE["status"] = "busy"
            STATE["task_id"] = task_id
            STATE["progress"] = 0
            STATE["last_update"] = time.time()
            
            # 执行任务
            payload = data.get("payload", {})
            task_type = data.get("task_type", "unknown")
            
            if "TODO" in task_id:
                # TODO 任务
                result = execute_todo_task(task_id, payload)
            else:
                result = {"status": "completed"}
            
            STATE["status"] = "idle"
            STATE["progress"] = 100
            STATE["completed"] += 1
            STATE["last_update"] = time.time()
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "task_id": task_id, "result": result}).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def send_response(self, code):
        self.send_response_only(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

def execute_todo_task(task_id, payload):
    """执行 TODO 任务"""
    desc = payload.get("任务描述", "")
    print(f"[{BOT_TYPE}] 执行 TODO: {task_id} - {desc}")
    
    # SSH 到 Server B 执行
    try:
        # 这里可以添加 SSH 执行逻辑
        time.sleep(1)
        return {"status": "completed", "output": "TODO completed"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}

def run():
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"[{BOT_TYPE}] Bot started on port {PORT}")
    server.serve_forever()

if __name__ == "__main__":
    run()
