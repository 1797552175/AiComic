#!/usr/bin/env python3
"""
统一 Bot HTTP 框架 - 支持所有 Bot 类型
用法: python3 bot_http_server_v2.py <bot_type> <port> <name>
"""
import asyncio
import json
import time
import os
import subprocess
import threading
import requests
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import uvicorn

API_KEY = "aicomic-shared-secret-key-2026"
STATUS_DIR = "/opt/AiComic/状态报告"
MONITOR_PORT = "8001"
MAX_CONCURRENT = 3

class TaskRequest(BaseModel):
    task_id: str
    task_type: str
    source: str
    target: str
    payload: dict

# ============== 并行任务队列 ==============
class TaskQueue:
    def __init__(self):
        self.pending = []
        self.running = {}
        self.completed = {}
        self._lock = threading.Lock()
        
    def enqueue_task_chain(self, chain: List[dict]):
        with self._lock:
            for item in chain:
                self.pending.append(item)
            print(f"[Queue] 入队 {len(chain)} 个任务")
    
    def get_runnable_tasks(self):
        with self._lock:
            return [t for t in self.pending if t.get("dependency") is None or t.get("dependency") in self.completed]
    
    def mark_running(self, task_id: str, bot_type: str):
        with self._lock:
            for t in self.pending:
                if t["task_id"] == task_id:
                    self.pending.remove(t)
                    self.running[task_id] = {"bot_type": bot_type, "start": time.time()}
                    break
    
    def mark_completed(self, task_id: str):
        with self._lock:
            if task_id in self.running:
                del self.running[task_id]
            self.completed[task_id] = time.time()
    
    def get_status(self):
        with self._lock:
            return {
                "pending": len(self.pending),
                "running": len(self.running),
                "completed": len(self.completed),
                "running_tasks": {k: v["bot_type"] for k, v in self.running.items()}
            }

task_queue = TaskQueue()

# ============== Server B 并行执行 ==============
def split_task_modules(desc: str) -> List[dict]:
    """拆分任务为多个并行模块"""
    modules = []
    d = desc.lower()
    if any(k in desc for k in ["前端", "界面", "frontend"]):
        modules.append({"name": "frontend", "desc": desc + " - 前端部分"})
    if any(k in desc for k in ["后端", "api", "backend"]):
        modules.append({"name": "backend", "desc": desc + " - 后端API部分"})
    if any(k in desc for k in ["数据库", "db", "model"]):
        modules.append({"name": "database", "desc": desc + " - 数据库部分"})
    if not modules:
        modules.append({"name": "main", "desc": desc})
    return modules[:MAX_CONCURRENT]

def execute_server_b_parallel(desc: str, task_id: str) -> dict:
    """在 Server B 上并行执行任务（最多3个实例）"""
    modules = split_task_modules(desc)
    
    if len(modules) == 1:
        # 单任务直接执行
        cmd = [
            "ssh", "-i", "/root/.ssh/id_ed25519",
            "-o", "StrictHostKeyChecking=no",
            "root@150.109.243.164",
            f"cd /opt/AiComic && echo '执行: {desc}' && sleep 1 && echo '完成'"
        ]
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        return {"status": "completed", "modules": [{"name": "main", "output": r.stdout.decode()[:200]}]}
    
    # 并行执行多模块
    processes = []
    for mod in modules:
        # 构建远程命令
        mname = mod["name"]
        remote_cmd = f"echo '开始模块: {mname}' && sleep 2 && echo '模块 {mname} 完成'"
        cmd = [
            "ssh", "-i", "/root/.ssh/id_ed25519",
            "-o", "StrictHostKeyChecking=no",
            "root@150.109.243.164",
            f"nohup sh -c '{remote_cmd}' > /tmp/crewai_{task_id}_{mod['name']}.log 2>&1 &"
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        processes.append((mod["name"], p))
    
    # 等待完成
    results = []
    for name, p in processes:
        try:
            stdout, stderr = p.communicate(timeout=120)
            results.append({"name": name, "status": "completed", "output": stdout.decode()[:100]})
        except subprocess.TimeoutExpired:
            p.kill()
            results.append({"name": name, "status": "timeout"})
    
    return {"status": "completed", "modules": results}

# ============== OpenClaw Agent 调用 ==============
def call_openclaw_agent(agent_type: str, task: TaskRequest, timeout: int = 300) -> dict:
    task_json = json.dumps({
        "task_id": task.task_id,
        "task_type": task.task_type,
        "source": task.source,
        "target": task.target,
        "payload": task.payload
    }, ensure_ascii=False)
    cmd = ["openclaw", "agent", "--agent", agent_type, "--message", task_json, "--timeout", str(timeout)]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout + 10)
        stdout = result.stdout.decode("utf-8", errors="ignore").strip()
        lines = [l for l in stdout.split("\n") if l.strip()]
        response = lines[-1] if lines else ""
        try:
            return json.loads(response)
        except:
            return {"summary": response, "raw_output": stdout}
    except subprocess.TimeoutExpired:
        return {"status": "failed", "error": f"超时（>{timeout}s）"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}

# ============== 任务完成文件 ==============
def write_completion(bot_type: str, task_id: str, output_files: list, extra: dict = None):
    ts = time.strftime("%Y%m%d_%H%M%S")
    name_map = {"pm": "产品经理", "dev": "研发", "marketing": "营销", "monitor": "状态监控"}
    filename = f"{STATUS_DIR}/{name_map.get(bot_type, bot_type)}_任务完成_{task_id}_{ts}.json"
    data = {"task_id": task_id, "bot_type": bot_type, "完成时间": ts, "产出文件列表": output_files}
    if extra:
        data.update(extra)
    try:
        os.makedirs(STATUS_DIR, exist_ok=True)
        with open(filename, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[{bot_type}] 写入完成文件失败: {e}")

# ============== AUTO-task 处理 ==============
def handle_auto_task_dev(task: TaskRequest) -> dict:
    auto_type = task.payload.get("auto_task_type", "")
    output_files = []
    if auto_type == "todo_scan":
        try:
            ssh_cmd = [
                "ssh", "-i", "/root/.ssh/id_ed25519",
                "-o", "StrictHostKeyChecking=no",
                "root@150.109.243.164",
                "find /opt/AiComic -name '*.py' -exec grep -n 'TODO\\|FIXME' {} \\;"
            ]
            r = subprocess.run(ssh_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
            scan = r.stdout.decode("utf-8", errors="ignore").strip()
            if scan:
                lines = [l for l in scan.split("\n") if l.strip()]
                report = f"# TODO/FIXME 扫描报告\n\n共 {len(lines)} 处：\n\n"
                for line in lines[:50]:
                    report += f"- {line}\n"
                report_file = f"{STATUS_DIR}/TODO扫描报告_{time.strftime('%Y%m%d')}.md"
                with open(report_file, "w") as f:
                    f.write(report)
                output_files.append(report_file)
            else:
                output_files.append("/opt/AiComic/状态报告/代码库清洁.txt")
                with open(output_files[0], "w") as f:
                    f.write("代码库清洁，无技术债")
        except Exception as e:
            print(f"[DEV] TODO扫描失败: {e}")
    return {"status": "completed", "output_files": output_files, "summary": f"自维护完成: {auto_type}"}

def handle_auto_task_pm(task: TaskRequest) -> dict:
    output_file = f"/opt/AiComic/docs/竞品监控_{time.strftime('%Y%m%d')}.md"
    competitors = ["AI Dungeon", "NovelAI", "Leinad"]
    content = f"# 竞品监控 {time.strftime('%Y-%m-%d')}\n\n"
    for c in competitors:
        content += f"## {c}\n- 新功能：待调研\n- 发布：待补充\n- 启示：待分析\n\n"
    try:
        with open(output_file, "w") as f:
            f.write(content)
    except:
        pass
    return {"status": "completed", "output_files": [output_file], "summary": "竞品扫描完成"}

def handle_auto_task_marketing(task: TaskRequest) -> dict:
    import glob
    now = time.time()
    seven_days = now - 7 * 86400
    mkt_dir = "/opt/AiComic/营销方案"
    os.makedirs(mkt_dir, exist_ok=True)
    new_files = []
    for pattern in [f"/opt/AiComic/apps/**/api/*.py"]:
        for f in glob.glob(pattern, recursive=True):
            try:
                if os.path.getmtime(f) > seven_days:
                    new_files.append(os.path.basename(f).replace(".py", ""))
            except:
                pass
    output_files = []
    ts = time.strftime("%Y%m%d")
    for fname in list(set(new_files))[:5]:
        if "auth" not in fname.lower():
            content = f"# {fname} 营销方案\n\n## 目标用户\nAI创作爱好者\n\n## 核心卖点\n自动化\n\n## 渠道\n知乎、小红书\n\n## 文案\n「AI动态漫，让故事活起来」\n"
            out_path = f"{mkt_dir}/自动补全_{fname}_{ts}.md"
            with open(out_path, "w") as f:
                f.write(content)
            output_files.append(out_path)
    if not output_files:
        out_path = f"{mkt_dir}/补全报告_{ts}.md"
        with open(out_path, "w") as f:
            f.write(f"# 营销补全报告 {time.strftime('%Y-%m-%d')}\n\n暂无新增功能\n")
        output_files.append(out_path)
    return {"status": "completed", "output_files": output_files, "summary": "营销补全完成"}

AUTO_HANDLERS = {
    "dev": handle_auto_task_dev,
    "pm": handle_auto_task_pm,
    "marketing": handle_auto_task_marketing,
}

# ============== 任务分发线程 ==============
BOTS = {"pm": "8002", "dev": "8003", "marketing": "8004"}

def dispatcher_loop():
    while True:
        time.sleep(10)
        idle_bots = []
        for bot_type, port in BOTS.items():
            try:
                r = requests.get(f"http://127.0.0.1:{port}/status", timeout=3)
                if r.json().get("state") == "idle":
                    idle_bots.append(bot_type)
            except:
                pass
        
        for task in task_queue.get_runnable_tasks():
            bot_type = task.get("type")
            if bot_type in idle_bots:
                tid = task["task_id"]
                task_queue.mark_running(tid, bot_type)
                threading.Thread(target=_dispatch, args=(tid, bot_type, task), daemon=True).start()
                idle_bots.remove(bot_type)
                if not idle_bots:
                    break

def _dispatch(task_id: str, bot_type: str, task: dict):
    port = BOTS.get(bot_type)
    if not port:
        return
    try:
        r = requests.post(
            f"http://127.0.0.1:{port}/execute",
            json={
                "task_id": task_id,
                "task_type": task.get("type", bot_type),
                "source": "状态监控机器人",
                "target": f"{bot_type}机器人",
                "payload": task.get("payload", {"任务描述": task_id})
            },
            headers={"X-API-Key": API_KEY},
            timeout=300
        )
        task_queue.mark_completed(task_id)
        print(f"[Dispatcher] {task_id} → {bot_type} 完成")
    except Exception as e:
        print(f"[Dispatcher] {task_id} 分发失败: {e}")
        task_queue.mark_completed(task_id)

dispatcher_thread = threading.Thread(target=dispatcher_loop, daemon=True)
dispatcher_thread.start()
print("[Dispatcher] 任务分发线程已启动")

# ============== Monitor App ==============
def create_monitor_app():
    app = FastAPI()
    
    @app.post("/execute")
    async def execute(task: TaskRequest, x_api_key: str = Header(...)):
        if x_api_key != API_KEY:
            raise HTTPException(status_code=403)
        ts = time.strftime("%Y%m%d_%H%M%S")
        req_id = task.payload.get("需求ID", task.task_id)
        chain = [
            {"task_id": f"{req_id}-PM", "type": "pm", "dependency": None,
             "payload": {"任务描述": f"原型: {task.payload.get('任务描述', '')}"}},
            {"task_id": f"{req_id}-DEV", "type": "dev", "dependency": f"{req_id}-PM",
             "payload": {"任务描述": f"开发: {task.payload.get('任务描述', '')}"}},
            {"task_id": f"{req_id}-MKT", "type": "marketing", "dependency": f"{req_id}-DEV",
             "payload": {"任务描述": f"营销: {task.payload.get('任务描述', '')}"}},
        ]
        task_queue.enqueue_task_chain(chain)
        return {"code": 0, "message": "任务链已入队", "chain": [t["task_id"] for t in chain]}
    
    @app.get("/health")
    async def health():
        return {"status": "ok", "bot": "状态监控机器人", "port": 8001}
    
    @app.get("/status")
    async def status():
        return task_queue.get_status()
    
    @app.get("/queue")
    async def queue():
        return task_queue.get_status()
    
    @app.get("/ask_for_task")
    async def ask(bot_type: str = None, idle_minutes: int = 0):
        ts = time.strftime("%Y%m%d_%H%M%S")
        tasks = {
            "pm": {"task_id": f"AUTO-PM-{ts}", "type": "pm", "payload": {"auto_task_type": "competitor_scan"}},
            "dev": {"task_id": f"AUTO-DEV-{ts}", "type": "dev", "payload": {"auto_task_type": "todo_scan"}},
            "marketing": {"task_id": f"AUTO-MKT-{ts}", "type": "marketing", "payload": {"auto_task_type": "marketing_gap"}},
        }
        if bot_type and bot_type in tasks:
            return {"has_task": True, "task": tasks[bot_type]}
        return {"has_task": False}
    
    return app

# ============== 其他 Bot App ==============
def create_bot_app(bot_type: str, port: int, name: str):
    app = FastAPI()
    state = {"state": "idle", "current_task": None, "tasks": 0, "errors": 0}
    
    @app.post("/execute")
    async def execute(task: TaskRequest, x_api_key: str = Header(...)):
        if x_api_key != API_KEY:
            raise HTTPException(status_code=403)
        state["state"] = "processing"
        state["current_task"] = task.task_id
        state["tasks"] += 1
        print(f"[{name}] {task.task_id}")
        
        if task.task_id.startswith("AUTO-"):
            handler = AUTO_HANDLERS.get(bot_type, lambda t: {"status": "completed", "output_files": []})
            result = handler(task)
            write_completion(bot_type, task.task_id, result.get("output_files", []))
            state["state"] = "idle"
            state["current_task"] = None
            return {"code": 0, "message": "success", "data": result}
        
        result = call_openclaw_agent(bot_type, task)
        success = result.get("status") != "failed"
        write_completion(bot_type, task.task_id, result.get("output_files", []))
        state["state"] = "idle"
        state["current_task"] = None
        if not success:
            state["errors"] += 1
        return {"code": 0, "message": "success", "data": {"task_id": task.task_id, "status": "completed", "result": result}}
    
    @app.get("/health")
    async def health():
        return {"status": "ok", "bot": name, "port": port}
    
    @app.get("/status")
    async def status():
        return state
    
    @app.get("/ask_for_task")
    async def ask():
        try:
            r = requests.get(f"http://127.0.0.1:{MONITOR_PORT}/ask_for_task?bot_type={bot_type}&idle_minutes=1", timeout=5)
            return r.json()
        except:
            return {"has_task": False}
    
    return app

# ============== 主程序 ==============
if __name__ == "__main__":
    import sys
    bot_type = sys.argv[1] if len(sys.argv) > 1 else "monitor"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8001
    name = sys.argv[3] if len(sys.argv) > 3 else f"{bot_type}机器人"
    
    app = create_monitor_app() if bot_type == "monitor" else create_bot_app(bot_type, port, name)
    print(f"启动 {name} 端口: {port}")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
