#!/usr/bin/env python3
"""
Bot HTTP Server v2 - 完整版
- dispatcher_loop: 轮询 Bitable 任务板
- execute_todo_task: 生成多 Agent 脚本并传送到 Server B
"""
import os
import sys
import json
import time
import threading
import subprocess
import uuid
import re
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8001
BOT_TYPE = sys.argv[1] if len(sys.argv) > 1 else "unknown"
SERVER_B_HOST = "150.109.243.164"

STATE = {
    "status": "idle",
    "task_id": None,
    "progress": 0,
    "last_update": time.time(),
    "errors": 0,
    "completed": 0,
    "pending_tasks": 0,
}

TASK_QUEUE = {"pending": [], "running": [], "completed": []}


# === SSH 到 Server B ===
def ssh_exec(cmd, timeout=30):
    """SSH 到 Server B 执行命令"""
    ssh_cmd = [
        "ssh", "-o", "StrictHostKeyChecking=no",
        "-i", "/root/.ssh/id_ed25519",
        "-o", f"ConnectTimeout={timeout // 3}",
        f"root@{SERVER_B_HOST}", cmd
    ]
    try:
        result = subprocess.run(
            ssh_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout
        )
        return (
            result.stdout.decode("utf-8", errors="ignore"),
            result.stderr.decode("utf-8", errors="ignore"),
            result.returncode
        )
    except subprocess.TimeoutExpired:
        return "", "SSH timeout", -1
    except Exception as e:
        return "", str(e), -1


# === 从飞书任务板读取待分配任务 ===
def fetch_bitable_tasks():
    """从飞书任务板读取待分配任务"""
    try:
        result = subprocess.run(
            ["python3", "/tmp/fetch_bitable_tasks.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15
        )
        output_file = "/tmp/bitable_pending_tasks.json"
        if os.path.exists(output_file):
            with open(output_file) as f:
                data = json.load(f)
            return data.get("tasks", [])
    except Exception as e:
        print(f"[Monitor] 读取任务板失败: {e}")
    return []


# === 分发任务给 dev bot ===
def dispatch_task_to_dev(task):
    """通过 HTTP 调用 dev bot 执行任务"""
    try:
        import urllib.request
        data = json.dumps({
            "task_id": task["task_id"],
            "task_type": "dev",
            "payload": {"任务描述": task["desc"]}
        }).encode("utf-8")
        req = urllib.request.Request(
            "http://localhost:8003/execute",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5):
            pass
        print(f"[Monitor] 已分发任务: {task['task_id']}")
        return True
    except Exception as e:
        print(f"[Monitor] 分发失败: {e}")
        return False


# === 调度循环 ===
def dispatcher_loop():
    """调度循环 - 轮询任务板并分发"""
    print(f"[{BOT_TYPE}] Dispatcher 启动")
    while True:
        try:
            if BOT_TYPE == "monitor":
                tasks = fetch_bitable_tasks()
                STATE["pending_tasks"] = len(tasks)
                for task in tasks:
                    existing = [t for t in TASK_QUEUE["pending"] if t.get("task_id") == task["task_id"]]
                    if not existing:
                        TASK_QUEUE["pending"].append(task)
                        print(f"[Monitor] 新任务: {task['task_id']} - {task['desc'][:50]}")
                if TASK_QUEUE["pending"]:
                    task = TASK_QUEUE["pending"].pop(0)
                    TASK_QUEUE["running"].append(task)
                    dispatch_task_to_dev(task)
            time.sleep(10)
        except Exception as e:
            print(f"[{BOT_TYPE}] Dispatcher 错误: {e}")
            time.sleep(30)


# === 生成 CrewAI 脚本 ===
def generate_crewai_script(task_id, task_desc, output_file):
    """生成 3 Agent 顺序执行的 CrewAI 脚本（带 ShellExecutor）"""
    t = (task_id, task_desc, task_desc, task_desc, output_file)
    script = (
        "#!/usr/bin/env python3\n"
        '''"""CrewAI 多 Agent 任务脚本 - %s"""\n''' % t[0] +
        "import os\n"
        "import subprocess\n"
        'os.environ["OPENAI_API_KEY"] = os.environ.get("MINIMAX_API_KEY", "")\n' +
        "\n"
        "from crewai import Agent, Task, Crew, Process\n"
        "from crewai.llm import LLM\n"
        "from crewai.tools import BaseTool\n"
        "\n"
        'llm = LLM(model="openai/MiniMax-M2.7-highspeed", is_litellm=True, api_key=os.environ.get("MINIMAX_API_KEY", ""))\n' +
        "\n"
        "# Shell 命令执行工具\n"
        "class ShellCommandTool(BaseTool):\n"
        '    name: str = "shell_command"\n'
        '    description: str = "执行 shell 命令并返回输出结果"\n'
        "\n"
        "    def _run(self, cmd: str):\n"
        "        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30, cwd='/opt/AiComic')\n"
        "        output = result.stdout + result.stderr\n"
        "        print('[shell] $ ' + cmd + ' -> ' + str(result.returncode))\n"
        "        return output\n"
        "\n"
        "shell_tool = ShellCommandTool()\n"
        "\n"
        "# 3 个 Agent\n"
        'pm = Agent(role="产品经理", goal="分析需求，输出实现方案", backstory="资深产品经理，擅长技术方案设计", verbose=True, llm=llm)\n'
        'backend = Agent(role="后端工程师", goal="根据方案实现后端代码，必须使用 shell_command 工具执行真正的命令", backstory="10年后端，精通Python/FastAPI", verbose=True, llm=llm, tools=[shell_tool])\n'
        'reviewer = Agent(role="代码审查员", goal="审查代码质量和安全性", backstory="资深代码审查员，擅长Python安全", verbose=True, llm=llm)\n'
        "\n"
        "# 顺序任务\n"
        'task_analysis = Task(description="分析任务：%s", agent=pm, expected_output="实现方案文档")\n' % t[1] +
        'task_code = Task(description="根据方案实现代码：%s。重要：必须使用 shell_command 工具执行真正的命令来完成任务，不要只生成代码。完成后将结果写入 %s.result", agent=backend, expected_output="命令执行结果")\n' % (t[2], t[4]) +
        'task_review = Task(description="审查代码：%s", agent=reviewer, expected_output="审查报告")\n' % t[3] +
        "\n"
        "crew = Crew(agents=[pm, backend, reviewer], tasks=[task_analysis, task_code, task_review], process=Process.sequential, verbose=True)\n"
        "\n"
        "result = crew.kickoff()\n"
        "print('任务完成: ' + str(result))\n"
        "with open('%s.result', 'w') as f:\n" % t[4] +
        "    f.write(str(result))\n"
    )
    return script





def execute_todo_task(task_id, payload):
    """执行 TODO 任务 - 调用 CrewAI"""
    desc = payload.get("任务描述", "实现功能")
    print(f"[{BOT_TYPE}] 执行 CrewAI 任务: {task_id}")
    print(f"[{BOT_TYPE}] 任务描述: {desc}")

    script_id = str(uuid.uuid4())[:8]
    script_file = f"/opt/AiComic/scripts/generated/crewai_{task_id}_{script_id}.py"
    output_file = f"/opt/AiComic/scripts/generated/crewai_result_{script_id}"

    script = generate_crewai_script(task_id, desc, output_file)

    # 写入脚本到本地
    local_script = f"/tmp/crewai_{task_id}_{script_id}.py"
    with open(local_script, "w") as f:
        f.write(script)

    # SCP 上传到 Server B
    scp_cmd = [
        "scp", "-o", "StrictHostKeyChecking=no",
        "-i", "/root/.ssh/id_ed25519",
        local_script,
        f"root@{SERVER_B_HOST}:{script_file}"
    ]
    r = subprocess.run(scp_cmd, timeout=30, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode != 0:
        err = r.stderr.decode()
        print(f"[{BOT_TYPE}] 上传脚本失败: {err}")
        return {"status": "failed", "error": err}
    print(f"[{BOT_TYPE}] 脚本已上传: {script_file}")

    # 在 Server B 执行 CrewAI（后台运行）
    exec_cmd = (
        f'docker exec -e MINIMAX_API_KEY="$MINIMAX_API_KEY" '
        f'crewai-runtime python {script_file} > {output_file}.log 2>&1 &'
    )
    ssh_exec(exec_cmd, timeout=10)

    print(f"[{BOT_TYPE}] CrewAI 已启动，脚本: {script_file}")
    print(f"[{BOT_TYPE}] 3个Agent顺序执行: PM -> Backend -> Reviewer")

    return {
        "status": "started",
        "script": script_file,
        "log": f"{output_file}.log",
        "agents": ["pm", "backend", "reviewer"],
        "process": "sequential"
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[{BOT_TYPE}] {args[0]}")

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "bot": BOT_TYPE}).encode())
        elif self.path == "/status":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps(STATE).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/execute":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body)
            except:
                data = {}
            self._handle_execute(data)
        elif self.path == "/ask_for_task":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body)
            except:
                data = {}
            self._handle_ask_for_task(data)
        else:
            self.send_response(404)
            self.end_headers()

    def _handle_execute(self, data):
        global STATE
        task_id = data.get("task_id", "unknown")
        STATE["status"] = "busy"
        STATE["task_id"] = task_id
        STATE["progress"] = 0
        STATE["last_update"] = time.time()

        payload = data.get("payload", {})
        task_type = data.get("task_type", "unknown")

        if "TODO" in task_id:
            result = execute_todo_task(task_id, payload)
        else:
            result = {"status": "completed"}

        STATE["status"] = "idle"
        STATE["progress"] = 100
        STATE["completed"] += 1
        STATE["last_update"] = time.time()

        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "ok",
            "task_id": task_id,
            "result": result
        }).encode())

    def _handle_ask_for_task(self, data):
        has_task = False
        task = None
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps({"has_task": has_task, "task": task}).encode())

    def do_PATCH(self):
        # 接收 CrewAI 结果回调
        if self.path == "/callback":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body)
                task_id = data.get("task_id", "unknown")
                result = data.get("result", "")
                print(f"[{BOT_TYPE}] CrewAI 任务完成: {task_id}")
                print(f"[{BOT_TYPE}] 结果: {str(result)[:200]}")
                # 写入结果文件
                with open(f"/opt/AiComic/scripts/generated/result_{task_id}.txt", "w") as f:
                    f.write(str(result))
            except Exception as e:
                print(f"[{BOT_TYPE}] Callback error: {e}")
            self.send_response(200)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()


def run():
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"[{BOT_TYPE}] Bot started on port {PORT}")
    server.serve_forever()


if __name__ == "__main__":
    run()
