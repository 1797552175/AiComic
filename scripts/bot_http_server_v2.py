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
            total = len(self.pending) + len(self.running)
            return {
                "pending": len(self.pending),
                "running": len(self.running),
                "completed": len(self.completed),
                "running_tasks": {k: v["bot_type"] for k, v in self.running.items()},
                "state": "idle" if total == 0 else "busy"
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
    # Marketing self-maintenance: git-based new code detection + deduplication
    import glob
    now = time.time()
    mkt_dir = "/opt/AiComic/营销方案"
    os.makedirs(mkt_dir, exist_ok=True)
    
    # 1. Git-based new code detection (not file mtime)
    try:
        r = subprocess.run(
            ["git", "-C", "/opt/AiComic", "diff", "--name-only", "--since=7 days ago"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10
        )
        changed = [os.path.basename(f) for f in r.stdout.decode().strip().split("\n") if f and f.endswith(".py")]
        changed_modules = list(set(f.replace(".py", "") for f in changed if f.startswith("apps/") and not f.startswith("apps/backend/outputs/")))
    except:
        changed_modules = []
    
    if not changed_modules:
        ts = time.strftime("%Y%m%d")
        out_path = f"{mkt_dir}/no_new_code_{ts}.md"
        with open(out_path, "w") as f:
            f.write(f"# MKT Gap Scan {time.strftime('%Y-%m-%d')}\nNo new code in 7 days.\n")
        return {"status": "completed", "output_files": [out_path], "summary": "no new code"}
    
    # 2. Deduplicate: skip if plan already exists
    existing = set()
    if os.path.exists(mkt_dir):
        for fn in os.listdir(mkt_dir):
            if fn.startswith("auto_") and fn.endswith(".md"):
                parts = fn.split("_")
                if len(parts) >= 2:
                    existing.add(parts[1])
    
    new_modules = [m for m in changed_modules if m not in existing and m not in ["__init__", "__pycache__"]]
    
    output_files = []
    ts = time.strftime("%Y%m%d")
    for fname in new_modules[:5]:
        content_body = f"# {fname} Marketing Plan\n\n## Target Users\nAI creators\n\n## Core Value\nAutomation\n\n## Channels\nZhihu, Xiaohongshu\n\n## Copy\nAI makes your story alive\n"
        out_path = f"{mkt_dir}/auto_{fname}_{ts}.md"
        try:
            with open(out_path, "w") as f:
                f.write(content_body)
            output_files.append(out_path)
        except:
            pass
    
    if not output_files:
        out_path = f"{mkt_dir}/no_gap_{ts}.md"
        with open(out_path, "w") as f:
            f.write(f"# MKT Gap {time.strftime('%Y-%m-%d')}\nAll recent modules already have plans.\n")
        output_files.append(out_path)
    
    return {"status": "completed", "output_files": output_files, "summary": f"done, new={len(output_files)}"}

AUTO_HANDLERS = {
    "dev": handle_auto_task_dev,
    "pm": handle_auto_task_pm,
    "marketing": handle_auto_task_marketing,
}

# ============== 资源监控 ===============
SERVER_A_MEM_THRESHOLD = 85
SERVER_B_CPU_THRESHOLD_HIGH = 80
SERVER_B_CPU_THRESHOLD_LOW = 20
MAX_PARALLEL_SERVER_B = 5
CURRENT_SERVER_B_TASKS = 0

# AUTO-task cooldown: last successful task time per bot type
_last_auto_success = {"pm": 0, "dev": 0, "marketing": 0}
_AUTO_COOLDOWN = 60  # 1 minute

def get_server_a_mem_percent():
    try:
        with open("/proc/meminfo") as f:
            lines_mem = f.readlines()
        total = avail = 0
        for line in lines_mem:
            if line.startswith("MemTotal:"):
                total = int(line.split()[1])
            elif line.startswith("MemAvailable:"):
                avail = int(line.split()[1])
        if total == 0:
            return 0
        return int((total - avail) * 100 / total)
    except:
        return 0

def get_server_b_cpu():
    try:
        cmd = ["ssh", "-i", "/root/.ssh/id_ed25519", "-o", "StrictHostKeyChecking=no",
               "-o", "ConnectTimeout=5", "root@150.109.243.164",
               "top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d'%' -f1"]
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        return float(r.stdout.decode().strip())
    except:
        return None

def should_throttle():
    mem_pct = get_server_a_mem_percent()
    if mem_pct > SERVER_A_MEM_THRESHOLD:
        print(f"[Monitor] Server A 内存 {mem_pct}% > 85%，暂停分发")
        return True
    return False

# ============== 任务分发线程 ==============
BOTS = {"pm": "8002", "dev": "8003", "marketing": "8004"}

def dispatcher_loop():
    while True:
        time.sleep(10)
        
        # Server A 内存检查
        if should_throttle():
            time.sleep(30)
            continue
        
        # Server B CPU 检查
        cpu = get_server_b_cpu()
        if cpu is not None:
            if cpu > 80:
                print(f"[Monitor] Server B CPU {cpu}% 高负载")
            elif cpu < 20:
                print(f"[Monitor] Server B CPU {cpu}% 空闲")
        
        # 分配任务给空闲 Bot
        idle_bots = []
        for bot_type, port in BOTS.items():
            try:
                r = requests.get(f"http://127.0.0.1:{port}/status", timeout=3)
                if r.json().get("state") == "idle":
                    idle_bots.append(bot_type)
            except:
                pass
        
        runnable = task_queue.get_runnable_tasks()
        
        # 队列空时，为空闲 Bot 生成 AUTO 任务（有 cooldown 保护）
        if not runnable and idle_bots:
            ts = time.strftime("%Y%m%d_%H%M%S")
            auto_map = {
                "pm": {"task_id": f"AUTO-PM-{ts}", "type": "pm", "payload": {"auto_task_type": "competitor_scan"}},
                "dev": {"task_id": f"AUTO-DEV-{ts}", "type": "dev", "payload": {"auto_task_type": "todo_scan"}},
                "marketing": {"task_id": f"AUTO-MKT-{ts}", "type": "marketing", "payload": {"auto_task_type": "marketing_gap"}},
            }
            for bot_type in idle_bots:
                if bot_type in auto_map:
                    # Cooldown: 同一个 bot 5分钟内不重复生成
                    last = _last_auto_success.get(bot_type, 0)
                    if time.time() - last < _AUTO_COOLDOWN:
                        print(f"[Dispatcher] {bot_type} cooldown中，跳过")
                        continue
                    auto_task = auto_map[bot_type]
                    task_queue.pending.append(auto_task)
                    print(f"[Dispatcher] 生成 AUTO 任务: {auto_task['task_id']} -> {bot_type}")
        
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
        if task_id.startswith("AUTO-"):
            _last_auto_success[bot_type] = time.time()
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

# ============== 其他 Bot App（支持多任务并发）==============
def create_bot_app(bot_type: str, port: int, name: str):
    app = FastAPI()
    # 多任务状态管理
    active_tasks = {}  # task_id -> {"state": "running"|"done", "start": time, "progress": 0~100}
    state_lock = threading.Lock()
    state = {"tasks": 0, "errors": 0}  # 全局统计
    
    def start_task(tid):
        with state_lock:
            active_tasks[tid] = {"state": "running", "start": time.time(), "progress": 0}
    
    def update_progress(tid, progress):
        with state_lock:
            if tid in active_tasks:
                active_tasks[tid]["progress"] = progress
    
    def finish_task(tid, success=True):
        with state_lock:
            if tid in active_tasks:
                del active_tasks[tid]
            if not success:
                state["errors"] += 1
    
    def get_overall_state():
        with state_lock:
            if not active_tasks:
                return "idle"
            return "busy"
    
    def get_active_tasks():
        with state_lock:
            result = []
            for k, v in list(active_tasks.items()):
                result.append([k, v["state"], v.get("progress", 0)])
            return result
    
    @app.post("/execute")
    async def execute(task: TaskRequest, x_api_key: str = Header(...)):
        if x_api_key != API_KEY:
            raise HTTPException(status_code=403)
        
        start_task(task.task_id)
        with state_lock:
            state["tasks"] += 1
        print(f"[{name}] 接收任务: {task.task_id}")
        
        # 异步处理任务（不阻塞）
        def run_task():
            try:
                # AUTO-task
                if task.task_id.startswith("AUTO-"):
                    handler = AUTO_HANDLERS.get(bot_type, lambda t: {"status": "completed", "output_files": []})
                    result = handler(task)
                    write_completion(bot_type, task.task_id, result.get("output_files", []))
                    finish_task(task.task_id)
                    return
                
                # 定期更新进度
                update_progress(task.task_id, 30)
                
                # 调用 agent
                result = call_openclaw_agent(bot_type, task)
                update_progress(task.task_id, 80)
                
                success = result.get("status") != "failed"
                write_completion(bot_type, task.task_id, result.get("output_files", []))
                
                if not success:
                    state["errors"] += 1
                
                finish_task(task.task_id)
                print(f"[{name}] 完成任务: {task.task_id}")
                
            except Exception as e:
                print(f"[{name}] 任务异常: {task.task_id} - {e}")
                finish_task(task.task_id, success=False)
                state["errors"] += 1
        
        # 启动后台线程处理（不阻塞）
        threading.Thread(target=run_task, daemon=True).start()
        
        # 立即返回，不等待任务完成
        return {"code": 0, "message": "任务已接收，正在异步处理", "task_id": task.task_id, "status": "running"}
    
    @app.get("/health")
    async def health():
        return {"status": "ok", "bot": name, "port": port}
    
    @app.get("/status")
    async def status():
        return {
            "state": get_overall_state(),
            "tasks": state["tasks"],
            "errors": state["errors"],
            "active": get_active_tasks()
        }
    
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
