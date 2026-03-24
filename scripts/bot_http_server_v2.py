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

# 保护 STATE 字典的线程安全访问
state_lock = threading.Lock()

import subprocess
import uuid
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

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
    "dispatcher_running": False,
    "last_dispatch": None,
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
            ["python3", "/opt/AiComic/tmp/fetch_bitable_tasks.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15
        )
        output_file = "/opt/AiComic/tmp/bitable_pending_tasks.json"
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


# === 原型扫描与任务创建 ===
PROTOTYPE_DIR = "/opt/AiComic/原型/"
PROCESSED_PROTOTYPES_FILE = "/opt/AiComic/tmp/processed_prototypes.txt"
os.makedirs("/opt/AiComic/tmp", exist_ok=True)

def get_processed_prototypes():
    """获取已处理的原型文件列表"""
    if os.path.exists(PROCESSED_PROTOTYPES_FILE):
        try:
            with open(PROCESSED_PROTOTYPES_FILE, encoding="utf-8", errors="ignore") as f:
                content = f.read().strip()
                if content:
                    return set(content.split("\n"))
                return set()
        except:
            return set()
    return set()

def mark_prototype_processed(filename):
    """标记原型已处理"""
    processed = get_processed_prototypes()
    processed.add(filename)
    with open(PROCESSED_PROTOTYPES_FILE, "w") as f:
        f.write("\n".join(processed))

def extract_feature_name(proto_file):
    """从原型文件名提取功能名称"""
    import re
    # 去除日期后缀和.md
    name = re.sub(r'_\d+\.md$', '', proto_file)
    name = re.sub(r'\.md$', '', name)
    name = name.replace('_', ' ')
    return name

def on_new_prototype(proto_file, proto_path):
    """发现新原型时：创建研发任务"""
    global STATE
    print(f"[{BOT_TYPE}] 发现新原型: {proto_file}")

    # 读取原型内容，获取功能描述
    try:
        with open(proto_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(500)  # 只读前500字符
    except Exception as e:
        print(f"[{BOT_TYPE}] 读取原型失败: {e}")
        content = ""

    # 生成任务ID
    import hashlib
    task_hash = hashlib.md5(proto_file.encode()).hexdigest()[:6]
    task_id = f"PROTO-{task_hash.upper()}"

    # 直接调用 create_bitable_task.py 创建任务
    try:
        import subprocess
        result = subprocess.run(
            ["python3", "/opt/AiComic/scripts/create_bitable_task.py",
             "--task-id", task_id,
             "--description", f"【原型研发】{extract_feature_name(proto_file)}\n参考：{proto_path}\n\n{content[:200]}",
             "--source", "prototype",
             "--assignee", "研发机器人"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30
        )
        if result.returncode == 0:
            print(f"[{BOT_TYPE}] 已创建研发任务: {task_id}")
        else:
            print(f"[{BOT_TYPE}] 创建任务失败: {result.stderr.decode()}")
    except Exception as e:
        print(f"[{BOT_TYPE}] 创建任务异常: {e}")

    mark_prototype_processed(proto_file)
    STATE["last_update"] = time.time()

def scan_prototypes():
    """扫描原型目录，发现新文件"""
    if not os.path.exists(PROTOTYPE_DIR):
        return
    processed = get_processed_prototypes()
    for fname in os.listdir(PROTOTYPE_DIR):
        if not fname.endswith(".md"):
            continue
        if fname not in processed:
            proto_path = os.path.join(PROTOTYPE_DIR, fname)
            on_new_prototype(fname, proto_path)

def process_existing_prototypes():
    """处理所有现有原型（启动时调用一次）"""
    print(f"[{BOT_TYPE}] 扫描现有原型...")
    scan_prototypes()
    # 统计
    if os.path.exists(PROTOTYPE_DIR):
        total = len([f for f in os.listdir(PROTOTYPE_DIR) if f.endswith(".md")])
        processed = len(get_processed_prototypes())
        print(f"[{BOT_TYPE}] 原型统计：共{total}个，已处理{processed}个")
        return total, processed
    return 0, 0


# === 飞书群状态广播 ===
import urllib.request
import urllib.error

FEISHU_BOT_APP_ID = "cli_a935c8fb40b8dccc"
FEISHU_BOT_APP_SECRET = "LvyAzv4oVxqapgnFn75p4bT0z0LWxKfT"
FEISHU_GROUP_CHAT_ID = "oc_389a77ed12ae0189d670c719f97e409c"  # AI工作室

_feishu_cached_token = None
_feishu_token_expires_at = 0

def _get_feishu_token():
    """获取飞书 tenant_access_token，带缓存"""
    global _feishu_cached_token, _feishu_token_expires_at
    import time
    if _feishu_cached_token and time.time() < _feishu_token_expires_at - 60:
        return _feishu_cached_token
    try:
        req = urllib.request.Request(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            data=json.dumps({"app_id": FEISHU_BOT_APP_ID, "app_secret": FEISHU_BOT_APP_SECRET}).encode(),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            d = json.loads(r.read())
            if d.get("code") == 0:
                _feishu_cached_token = d["tenant_access_token"]
                _feishu_token_expires_at = time.time() + d.get("expire", 7200)
                return _feishu_cached_token
    except Exception as e:
        print(f"[Monitor] 获取飞书Token失败: {e}")
    return None

def _send_feishu_message(text):
    """发送文本消息到飞书群"""
    token = _get_feishu_token()
    if not token:
        return False
    try:
        payload = json.dumps({
            "receive_id": FEISHU_GROUP_CHAT_ID,
            "msg_type": "text",
            "content": json.dumps({"text": text})  # content is a JSON-encoded STRING
        }).encode()
        req = urllib.request.Request(
            f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
            data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            d = json.loads(r.read())
            return d.get("code") == 0
    except Exception as e:
        print(f"[Monitor] 发送飞书消息失败: {e}")
        return False

def _query_bot_status(port):
    """查询单个 Bot 的状态"""
    try:
        with urllib.request.urlopen(f"http://localhost:{port}/status", timeout=3) as r:
            return json.loads(r.read())
    except:
        return None

def broadcast_status_to_feishu():
    """查询所有 Bot 状态并广播到飞书群"""
    bots = [
        (8001, "🤖 Monitor"),
        (8002, "📋 PM"),
        (8003, "🛠️ Dev"),
        (8004, "📢 Marketing"),
    ]
    lines = ["📊 **AiComic Bot 状态**", ""]
    all_ok = True
    for port, name in bots:
        s = _query_bot_status(port)
        if s is None:
            lines.append(f"{name}: 🔴 无响应")
            all_ok = False
        elif s.get("status") == "busy":
            task = s.get("task_id") or "?"
            prog = s.get("progress", 0)
            done = s.get("completed", 0)
            lines.append(f"{name}: 🔄 进行中 `{task}` {prog}% | 已完成 {done} 个任务")
        elif s.get("status") == "idle":
            pending = s.get("pending_tasks", 0)
            done = s.get("completed", 0)
            lines.append(f"{name}: ✅ 空闲 | 待处理 {pending} | 已完成 {done}")
        else:
            lines.append(f"{name}: 🟡 {s.get('status', '?')}")

    if all_ok:
        lines.append("")
        lines.append("所有 Bot 运行正常 ✅")
    else:
        lines.append("")
        lines.append("⚠️ 有 Bot 无响应，请检查")

    _send_feishu_message("\n".join(lines))

# === 调度循环 ===
def dispatcher_loop():
    """调度循环 - 轮询任务板并分发"""
    global STATE
    print(f"[{BOT_TYPE}] Dispatcher 启动")
    STATE["dispatcher_running"] = True
    tick = 0
    while True:
        try:
            if BOT_TYPE == "monitor":
                tick += 1
                # 每3分钟（18个tick × 10秒）广播一次状态到飞书群
                if tick % 18 == 0:
                    broadcast_status_to_feishu()
                # 扫描原型目录发现新原型
                scan_prototypes()
                # 读取任务板待分配任务
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
                    STATE["last_dispatch"] = time.time()
                    dispatch_task_to_dev(task)
            time.sleep(10)
        except Exception as e:
            print(f"[{BOT_TYPE}] Dispatcher 错误: {e}")
            time.sleep(30)


# === 生成 CrewAI 脚本 ===
def generate_crewai_script(task_id, task_desc, output_file):
    """生成 3 Agent 顺序执行的 CrewAI 脚本（带 ShellExecutor）"""
    # Escape % to %% to prevent "not enough arguments for format string"
    # when task_desc contains percent signs (e.g. "50% 完成度")
    safe = lambda s: str(s).replace('%', '%%')
    t = (task_id, safe(task_desc), safe(task_desc), safe(task_desc), output_file.replace('%', '%%'))
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
        "        # Fix fullwidth punctuation in generated Python code\n"
        "        import re\n"
        "        fullwidth_map = {'\\uff1a': ':', '\\uff08': '(', '\\uff09': ')', '\\uff0c': ',', '\\uff0e': '.', '\\uff01': '!', '\\uff1f': '?', '\\uff1b': ';', '\\uff0d': '-', '\\uff1d': '=', '\\uff0b': '+', '\\uff02': '\"', '\\uff07': \"'\"}\n"
        "        for fw, asc in fullwidth_map.items():\n"
        "            cmd = cmd.replace(fw, asc)\n"
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
    local_script = f"/opt/AiComic/tmp/crewai_{task_id}_{script_id}.py"
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


def execute_deploy_task(task_id, payload):
    """Execute deployment task - sync code to Server B and run docker-compose"""
    print(f"[{BOT_TYPE}] 执行部署任务: {task_id}")

    # Step 1: Create tarball locally
    local_tar = "/opt/AiComic/tmp/aicomic_deploy.tar.gz"
    print(f"[{BOT_TYPE}] 创建代码包...")
    tar_result = subprocess.run(
        ["tar", "czf", local_tar, "--exclude=.git", "--exclude=__pycache__", "--exclude=*.pyc", "-C", "/opt/AiComic", "."],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60
    )
    if tar_result.returncode != 0:
        return {"status": "failed", "error": "tar failed: %s" % tar_result.stderr.decode()}

    # Step 2: Upload using SCP
    print(f"[{BOT_TYPE}] 上传代码包到 Server B...")
    scp_result = subprocess.run(
        ["scp", "-o", "StrictHostKeyChecking=no", "-i", "/root/.ssh/id_ed25519", local_tar, "root@%s:/tmp/aicomic_deploy.tar.gz" % SERVER_B_HOST],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120
    )
    if scp_result.returncode != 0:
        err_msg = scp_result.stderr.decode()
        print(f"[{BOT_TYPE}] SCP failed: {err_msg}")
        return {"status": "failed", "error": "scp failed: %s" % err_msg}
    print(f"[{BOT_TYPE}] 上传完成")

    # Step 3: Extract on Server B
    print(f"[{BOT_TYPE}] 解压代码...")
    out, err, code = ssh_exec("mkdir -p /opt/AiComic && tar xzf /tmp/aicomic_deploy.tar.gz -C /opt/AiComic && rm /tmp/aicomic_deploy.tar.gz", timeout=60)
    if code != 0:
        return {"status": "failed", "error": "extract failed: %s" % err}
    print(f"[{BOT_TYPE}] 代码同步完成")

    # Step 4: Check docker-compose file exists
    exists, _, _ = ssh_exec("test -f /opt/AiComic/apps/backend/docker-compose.yml && echo exists || echo missing", timeout=10)
    if "missing" in exists:
        return {"status": "failed", "error": "docker-compose.yml not found on Server B"}

    # Step 5: Stop existing containers
    print(f"[{BOT_TYPE}] 停止旧容器...")
    ssh_exec("cd /opt/AiComic/apps/backend && docker-compose down 2>/dev/null || true", timeout=60)

    # Step 6: Build and start containers
    print(f"[{BOT_TYPE}] 构建并启动 Docker 容器...")
    out, err, code = ssh_exec("cd /opt/AiComic/apps/backend && docker-compose up -d --build", timeout=600)
    if code != 0:
        print(f"[{BOT_TYPE}] Docker 构建失败: {err}")
        return {"status": "failed", "error": err}
    print(f"[{BOT_TYPE}] Docker 容器启动完成")

    # Step 7: Verify service is running
    print(f"[{BOT_TYPE}] 验证服务状态...")
    out, _, _ = ssh_exec("docker ps --filter name=aicomic --format '{{.Names}}: {{.Status}}'", timeout=10)
    print(f"[{BOT_TYPE}] 运行中的容器: {out}")

    return {
        "status": "completed",
        "containers": out.strip(),
        "message": "Deployment completed successfully"
    }


def execute_fix_task(task_id, payload):
    """Execute fix task - sync latest code and rebuild containers"""
    print(f"[{BOT_TYPE}] 执行修复任务: {task_id}")

    # Sync latest code
    print(f"[{BOT_TYPE}] 同步最新代码到 Server B...")
    local_tar = "/opt/AiComic/tmp/aicomic_fix.tar.gz"
    tar_result = subprocess.run(
        ["tar", "czf", local_tar, "--exclude=.git", "--exclude=__pycache__", "--exclude=*.pyc", "-C", "/opt/AiComic", "."],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60
    )
    if tar_result.returncode != 0:
        return {"status": "failed", "error": "tar failed"}

    # Upload
    scp_result = subprocess.run(
        ["scp", "-o", "StrictHostKeyChecking=no", "-i", "/root/.ssh/id_ed25519", local_tar, "root@%s:/tmp/aicomic_fix.tar.gz" % SERVER_B_HOST],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120
    )
    if scp_result.returncode != 0:
        return {"status": "failed", "error": "scp failed"}

    # Extract
    out, err, code = ssh_exec("tar xzf /tmp/aicomic_fix.tar.gz -C /opt/AiComic && rm /tmp/aicomic_fix.tar.gz", timeout=60)
    if code != 0:
        return {"status": "failed", "error": "extract failed"}

    # Rebuild and restart
    print(f"[{BOT_TYPE}] 重建容器...")
    out, err, code = ssh_exec("cd /opt/AiComic/apps/backend && docker-compose down 2>/dev/null; docker-compose build && docker-compose up -d", timeout=600)
    if code != 0:
        return {"status": "failed", "error": err}

    return {"status": "completed", "message": "Fix deployed successfully"}


def execute_proto_task(task_id, payload):
    """Execute prototype implementation task - use CrewAI to implement the prototype"""
    print(f"[{BOT_TYPE}] 执行原型研发任务: {task_id}")

    # Get description from payload
    description = payload.get("description", "实现原型功能")
    proto_file = payload.get("proto_file", "")
    proto_path = None

    # Read prototype file if referenced
    if proto_file:
        proto_path = os.path.join(PROTOTYPE_DIR, proto_file)
        if os.path.exists(proto_path):
            try:
                with open(proto_path, 'r', encoding='utf-8', errors='ignore') as f:
                    proto_content = f.read()
                print(f"[{BOT_TYPE}] 原型内容已读取: {len(proto_content)} 字符")
                # Prepend to description
                description = f"参考原型: {proto_file}\n\n{proto_content[:2000]}\n\n实现要求:\n{description}"
            except Exception as e:
                print(f"[{BOT_TYPE}] 读取原型失败: {e}")

    # Generate CrewAI script for this prototype
    script_id = str(uuid.uuid4())[:8]
    script_file = f"/opt/AiComic/scripts/generated/crewai_proto_{task_id}_{script_id}.py"
    output_file = f"/opt/AiComic/scripts/generated/proto_result_{script_id}"

    script = generate_proto_script(task_id, description, output_file)

    # Write script locally
    local_script = f"/opt/AiComic/tmp/crewai_proto_{task_id}_{script_id}.py"
    with open(local_script, "w") as f:
        f.write(script)

    # Upload to Server B
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

    # Execute on Server B via docker
    container = "crewai-runtime"
    run_cmd = (
        f"docker exec -e MINIMAX_API_KEY=\"$MINIMAX_API_KEY\" "
        f"{container} python {script_file} > {output_file}.log 2>&1"
    )
    stdout, stderr, code = ssh_exec(run_cmd, timeout=600)
    print(f"[{BOT_TYPE}] CrewAI 执行完成，退出码: {code}")

    # Check result
    result_file = f"{output_file}.result"
    check_cmd = f"test -f {result_file} && cat {result_file} || echo 'NO_RESULT'"
    result_content, _, _ = ssh_exec(check_cmd, timeout=10)
    print(f"[{BOT_TYPE}] 执行结果: {result_content[:500]}")

    return {
        "status": "completed",
        "message": "Prototype task executed via CrewAI",
        "script": script_file,
        "result": result_content[:500]
    }


def generate_proto_script(task_id, task_desc, output_file):
    """Generate CrewAI script for prototype implementation."""
    safe_out = output_file.replace("/", "_")
    # Use triple-quoted string with embedded double-quotes to avoid confusion
    script_lines = [
        "#!/usr/bin/env python3",
        "\"\"\"CrewAI Prototype Task - " + str(task_id) + "\"\"\"",
        "import os",
        "import sys",
        "os.environ['OPENAI_API_KEY'] = os.environ.get('MINIMAX_API_KEY', '')",
        "",
        "from crewai import Agent, Task, Crew, Process",
        "from crewai.llm import LLM",
        "from crewai.tools import BaseTool",
        "",
        "llm = LLM(model='openai/MiniMax-M2.7-highspeed', is_litellm=True, api_key=os.environ.get('MINIMAX_API_KEY', ''))",
        "",
        "# Shell command tool",
        "class ShellTool(BaseTool):",
        "    name: str = 'shell'",
        "    description: str = 'Execute shell command'",
        "",
        "    def _run(self, cmd: str):",
        "        import subprocess",
        "        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60, cwd='/opt/AiComic')",
        "        return result.stdout + result.stderr",
        "",
        "shell = ShellTool()",
        "",
        "# Agent",
        "coder = Agent(role='Python Engineer', goal='Implement code based on prototype description', backstory='10 years Python experience, expert in FastAPI', verbose=True, llm=llm, tools=[shell])",
        "",
        "task_description = 'Implement prototype: " + task_desc.replace("'", "\\'") + "'",
        "task = Task(description=task_description, agent=coder, expected_output='Code and git commit')",
        "",
        "crew = Crew(agents=[coder], tasks=[task], process=Process.sequential, verbose=True)",
        "result = crew.kickoff()",
        "with open('" + safe_out + ".result', 'w') as f:",
        "    f.write(str(result))",
    ]
    return '\n'.join(script_lines)

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """支持并发的 HTTP 服务器，避免长任务阻塞 /health 检查"""
    daemon_threads = True
    # 解决 Address already in use 问题
    allow_reuse_address = True

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[{BOT_TYPE}] {args[0]}")

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "bot": BOT_TYPE}).encode())
        elif self.path == "/status":
            with state_lock:
                status_copy = dict(STATE)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps(status_copy).encode())
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
        elif self.path == "/prototype_task":
            # 创建原型研发任务
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body)
            except:
                data = {}
            self._handle_prototype_task(data)
        elif self.path == "/scan_prototypes":
            # 手动触发原型扫描
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            self._handle_scan_prototypes()
        else:
            self.send_response(404)
            self.end_headers()

    def _handle_execute(self, data):
        global STATE
        task_id = data.get("task_id", "unknown")
        with state_lock:
            STATE["status"] = "busy"
            STATE["task_id"] = task_id
            STATE["progress"] = 0
            STATE["last_update"] = time.time()

        payload = data.get("payload", {})
        task_type = data.get("task_type", "unknown")

        if "TODO" in task_id:
            result = execute_todo_task(task_id, payload)
        elif "DEPLOY" in task_id:
            # Deployment task - sync code and run docker-compose
            result = execute_deploy_task(task_id, payload)
        elif "FIX" in task_id:
            # Fix task - run docker-compose build/pull on Server B
            result = execute_fix_task(task_id, payload)
        elif "PROTO" in task_id:
            # Prototype implementation task - call CrewAI to implement
            result = execute_proto_task(task_id, payload)
        else:
            result = {"status": "completed", "note": "task handled"}

        with state_lock:
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

    def _handle_prototype_task(self, data):
        """创建原型研发任务到飞书任务板"""
        global STATE
        task_id = data.get("task_id", "unknown")
        description = data.get("description", "")
        proto_file = data.get("proto_file", "")

        try:
            # 直接导入 feishu 工具创建任务
            # 这里用 subprocess 调用 create_bitable_record.py
            import subprocess
            result = subprocess.run(
                ["python3", "/opt/AiComic/scripts/create_bitable_task.py",
                 "--task-id", task_id,
                 "--description", description,
                 "--source", "prototype",
                 "--assignee", "研发机器人"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                print(f"[{BOT_TYPE}] 原型任务创建成功: {task_id}")
            else:
                print(f"[{BOT_TYPE}] 原型任务创建失败: {result.stderr}")
        except Exception as e:
            print(f"[{BOT_TYPE}] 创建原型任务异常: {e}")

        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok", "task_id": task_id}).encode())

    def _handle_scan_prototypes(self):
        """触发原型扫描"""
        total, processed = process_existing_prototypes()
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok", "total": total, "processed": processed}).encode())

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
    # 启动调度线程（仅 monitor 类型）
    if BOT_TYPE == "monitor":
        dispatcher_thread = threading.Thread(target=dispatcher_loop, daemon=True)
        dispatcher_thread.start()
        print(f"[{BOT_TYPE}] Dispatcher 线程已启动")
        # 启动时扫描一次现有原型
        scan_prototypes()
    # 启动 HTTP 服务器
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"[{BOT_TYPE}] Bot started on port {PORT}")
    server.serve_forever()


if __name__ == "__main__":
    run()
