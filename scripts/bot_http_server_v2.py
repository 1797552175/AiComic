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
# 保护 TASK_QUEUE 的线程安全访问
task_queue_lock = threading.Lock()

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
    """通过 HTTP 调用 dev bot 执行任务（异步，不等待结果）"""
    import threading
    import urllib.request

    def _dispatch():
        try:
            # 1. 检查 Dev Bot 是否忙碌
            try:
                with urllib.request.urlopen("http://localhost:8003/status", timeout=5) as r:
                    dev_state = json.loads(r.read())
                if dev_state.get("status") == "busy":
                    # Dev Bot 忙碌，将任务重新放回队列等待
                    with task_queue_lock:
                        TASK_QUEUE["pending"].insert(0, task)
                    print(f"[Monitor] Dev Bot 忙碌，任务 {task['task_id']} 重新入队")
                    update_task_status(task["record_id"], "待领取")
                    return
            except Exception as e:
                print(f"[Monitor] 检查 Dev Bot 状态失败: {e}，仍尝试分发")

            # 2. 更新任务状态为"进行中"
            update_task_status(task["record_id"], "进行中")
            # 1. 更新任务状态为"进行中"
            update_task_status(task["record_id"], "进行中")

            # 2. 发送任务到 Dev Bot
            import urllib.request
            data = json.dumps({
                "task_id": task["task_id"],
                "task_type": "dev",
                "payload": {"任务描述": task["desc"], "proto_file": task.get("proto_file", "")}
            }).encode("utf-8")
            req = urllib.request.Request(
                "http://localhost:8003/execute",
                data=data,
                headers={"Content-Type": "application/json", "X-API-Key": "aicomic-shared-secret-key-2026"}
            )
            # 异步发送，不等待结果
            with urllib.request.urlopen(req, timeout=10):
                pass
            print(f"[Monitor] 已分发任务: {task['task_id']}")
        except Exception as e:
            print(f"[Monitor] 分发失败: {e}")
            # 分发失败时更新状态为"待领取"
            try:
                update_task_status(task["record_id"], "待领取")
            except:
                pass

    thread = threading.Thread(target=_dispatch, daemon=True)
    thread.start()
    return True


def update_task_status(record_id, status):
    """更新飞书任务板状态"""
    import urllib.request
    with open('/root/.openclaw/openclaw.json') as f:
        config = json.load(f)
    feishu = config['channels']['feishu']

    data = json.dumps({"app_id": feishu['appId'], "app_secret": feishu['appSecret']}).encode()
    req = urllib.request.Request("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal", data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        token = json.loads(resp.read()).get("tenant_access_token", "")

    APP_TOKEN = "InUZbPrTZaRm5LsRz9jctF27nGu"
    TABLE_ID = "tblNWtihltzV0SOO"

    update_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/{record_id}"
    update_data = json.dumps({"fields": {"状态": status}}).encode()
    req = urllib.request.Request(update_url, data=update_data, headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"}, method='PUT')
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read())
        if result.get("code") == 0:
            print(f"[Monitor] 任务状态更新: {record_id[:10]}... -> {status}")
        else:
            print(f"[Monitor] 状态更新失败: {result.get('msg')}")


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


# === 补处理遗漏的 @mention（方案B）===
import os as _os
import time as _time

FEISHU_BOT_OPEN_ID = "ou_c7ec681c4b6134e7ef7d1da9ea59f1ab"  # 状态监控机器人
FEISHU_BOT_APP_ID_MISSED = "cli_a935c8fb40b8dccc"
FEISHU_BOT_APP_SECRET_MISSED = "LvyAzv4oVxqapgnFn75p4bT0z0LWxKfT"
FEISHU_GROUP_CHAT_ID_MISSED = "oc_389a77ed12ae0189d670c719f97e409c"
PROCESSED_MSG_IDS_FILE = "/opt/AiComic/状态报告/processed_msg_ids.json"

_missed_token = None
_missed_token_expires = 0

def _get_missed_token():
    global _missed_token, _missed_token_expires
    import time as _t
    if _missed_token and _t.time() < _missed_token_expires - 60:
        return _missed_token
    try:
        req = urllib.request.Request(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            data=json.dumps({"app_id": FEISHU_BOT_APP_ID_MISSED, "app_secret": FEISHU_BOT_APP_SECRET_MISSED}).encode(),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            d = json.loads(r.read())
            if d.get("code") == 0:
                _missed_token = d["tenant_access_token"]
                _missed_token_expires = _t.time() + d.get("expire", 7200)
                return _missed_token
    except Exception as e:
        print(f"[Monitor] 获取Token失败: {e}")
    return None

def _load_processed_ids():
    try:
        if _os.path.exists(PROCESSED_MSG_IDS_FILE):
            with open(PROCESSED_MSG_IDS_FILE, 'r') as f:
                return set(json.load(f))
    except:
        pass
    return set()

def _save_processed_ids(ids):
    try:
        with open(PROCESSED_MSG_IDS_FILE, 'w') as f:
            json.dump(list(ids), f)
    except:
        pass

def _contains_bot_mention(content_str):
    """检查消息内容是否 @ 了机器人（通过 open_id 或 at details）"""
    if not content_str:
        return False
    # 飞书 at 机器人会在 content 里包含 bot 的 open_id
    if FEISHU_BOT_OPEN_ID in content_str:
        return True
    # 也检查 "at details" 格式
    try:
        d = json.loads(content_str) if isinstance(content_str, str) else content_str
        if isinstance(d, dict) and "at_items" in d:
            for item in d.get("at_items", []):
                if item.get("open_id") == FEISHU_BOT_OPEN_ID:
                    return True
    except:
        pass
    return False

def fetch_and_process_missed_mentions():
    """查询飞书群最近消息，找出被遗漏的 @mention 并触发处理"""
    token = _get_missed_token()
    if not token:
        return

    try:
        url = (f"https://open.feishu.cn/open-apis/im/v1/messages"
               f"?container_id_type=chat"
               f"&container_id={FEISHU_GROUP_CHAT_ID_MISSED}"
               f"&page_size=20"
               f"&sort_type=ByCreateTimeDesc")
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=8) as r:
            d = json.loads(r.read())

        if d.get("code") != 0:
            return

        processed_ids = _load_processed_ids()
        new_processed = set()

        items = d.get("data", {}).get("items", [])
        for m in items:
            msg_id = m.get("message_id", "")
            if not msg_id or msg_id in processed_ids:
                continue

            sender = m.get("sender", {})
            sender_id = sender.get("id", "")
            # 跳过机器人自己发的消息
            if sender_id == FEISHU_BOT_OPEN_ID:
                new_processed.add(msg_id)
                continue

            msg_type = m.get("msg_type", "")
            body_raw = m.get("body", {})

            # 解析消息内容
            content_str = ""
            if isinstance(body_raw, dict):
                content_str = body_raw.get("content", "")
            elif isinstance(body_raw, str):
                content_str = body_raw

            if not _contains_bot_mention(content_str):
                new_processed.add(msg_id)
                continue

            # 找到了一个新的 @mention
            try:
                content_dict = json.loads(content_str) if isinstance(content_str, str) else content_str
                text = content_dict.get("text", "") if isinstance(content_dict, dict) else str(content_dict)
            except:
                text = content_str

            print(f"[Monitor] 发现遗漏 @mention: msg_id={msg_id} text={text[:80]}")
            new_processed.add(msg_id)

            # 构造任务并分发
            task = {
                "task_id": f"TODO-{msg_id[:12]}",
                "desc": text,
                "source": "missed_mention",
                "msg_id": msg_id
            }
            with task_queue_lock:
                TASK_QUEUE["pending"].insert(0, task)
            print(f"[Monitor] 已将遗漏任务加入队列: {task['task_id']}")

        # 保存已处理的 message_id
        if new_processed:
            all_processed = processed_ids | new_processed
            # 最多保留1000条
            if len(all_processed) > 1000:
                all_processed = set(list(all_processed)[-1000:])
            _save_processed_ids(all_processed)

    except Exception as e:
        print(f"[Monitor] 查询遗漏消息失败: {e}")


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
                        with task_queue_lock:
                            TASK_QUEUE["pending"].append(task)
                        print(f"[Monitor] 新任务: {task['task_id']} - {task['desc'][:50]}")
                with task_queue_lock:
                    has_pending = bool(TASK_QUEUE["pending"])
                if has_pending:
                    with task_queue_lock:
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
    r = subprocess.run(scp_cmd, timeout=120, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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


def extract_proto_sections(content):
    """从原型内容中提取关键章节"""
    sections = {}
    lines = content.split('\n')
    current_section = '正文'
    current_lines = []

    for line in lines:
        # 检测章节标题
        if line.startswith('## ') or line.startswith('# '):
            if current_lines:
                sections[current_section] = '\n'.join(current_lines)
            current_section = line.lstrip('# ')
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections[current_section] = '\n'.join(current_lines)

    return sections


def execute_proto_task(task_id, payload):
    """Execute prototype implementation task - use CrewAI to implement the prototype"""
    print(f"[{BOT_TYPE}] 执行原型研发任务: {task_id}")

    # Get description from payload
    description = payload.get("description", "实现原型功能")
    proto_file = payload.get("proto_file", "")
    proto_path = None

    # Read prototype file if referenced
    full_content = ""

    # 如果 proto_file 为空，尝试从描述中提取
    if not proto_file and description:
        import re
        match = re.search(r'原型[/\\]([^\\\/\n]+\.md)', description)
        if match:
            proto_file = match.group(1)
            print(f"[{BOT_TYPE}] 从描述中提取proto_file: {proto_file}")

    if proto_file:
        proto_path = os.path.join(PROTOTYPE_DIR, proto_file)
        if os.path.exists(proto_path):
            try:
                with open(proto_path, 'r', encoding='utf-8', errors='ignore') as f:
                    proto_content = f.read()
                print(f"[{BOT_TYPE}] 原型内容已读取: {len(proto_content)} 字符")

                # 提取章节结构化信息
                sections = extract_proto_sections(proto_content)

                # 构建结构化的任务描述
                task_parts = [
                    f"【原型文件】{proto_file}",
                    f"【参考路径】{proto_path}",
                    "",
                ]

                # 添加各章节内容
                for section_name in ['背景与目标', '一、背景与目标', '产品定位与目标', '功能清单', '二、功能清单', '功能需求', '界面描述', '三、界面设计', '验收标准', '四、验收标准']:
                    if section_name in sections:
                        task_parts.append(f"【{section_name}】")
                        task_parts.append(sections[section_name][:3000])  # 限制每个章节长度
                        task_parts.append("")

                # 添加原始描述
                if description:
                    task_parts.append("【原始任务描述】")
                    task_parts.append(description[:1000])

                full_content = '\n'.join(task_parts)
                description = full_content

            except Exception as e:
                print(f"[{BOT_TYPE}] 读取原型失败: {e}")
                description = f"参考原型: {proto_file}\n\n实现要求:\n{description}"
        else:
            description = f"参考原型文件不存在: {proto_path}\n\n实现要求:\n{description}"

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
    r = subprocess.run(scp_cmd, timeout=120, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode != 0:
        err = r.stderr.decode()
        print(f"[{BOT_TYPE}] 上传脚本失败: {err}")
        return {"status": "failed", "error": err}
    print(f"[{BOT_TYPE}] 脚本已上传: {script_file}")

    # Execute on Server B via docker (background mode - don't wait)
    container = "crewai-runtime"
    run_cmd = (
        f"docker exec -e MINIMAX_API_KEY=\"$MINIMAX_API_KEY\" "
        f"{container} python {script_file} > {output_file}.log 2>&1 &"
    )
    stdout, stderr, code = ssh_exec(run_cmd, timeout=10)
    print(f"[{BOT_TYPE}] CrewAI 任务已在后台启动，PID: {stdout.strip()}")

    # Wait for result file (up to 15 minutes)
    import time
    max_wait = 900  # 15 minutes
    check_interval = 30  # 30 seconds
    waited = 0
    result_content = ""
    while waited < max_wait:
        time.sleep(check_interval)
        waited += check_interval

        # Check if result file exists
        check_cmd = f"test -f {result_file} && cat {result_file} || echo 'NOT_READY'"
        result_content, _, _ = ssh_exec(check_cmd, timeout=10)

        if 'NOT_READY' not in result_content:
            print(f"[{BOT_TYPE}] CrewAI 执行完成，用时 {waited} 秒")
            break
        print(f"[{BOT_TYPE}] 等待 CrewAI 完成... ({waited}s)")

    if waited >= max_wait:
        print(f"[{BOT_TYPE}] CrewAI 执行超时 ({max_wait}s)")
        return {
            "status": "timeout",
            "message": "CrewAI 执行超时",
            "log": f"{output_file}.log"
        }

    # Check result
    result_file = f"{output_file}.result"
    log_file = f"{output_file}.log"

    # Check for syntax errors in log
    check_log = f"cat {log_file}"
    log_content, _, _ = ssh_exec(check_log, timeout=10)
    print(f"[{BOT_TYPE}] 日志内容: {log_content[:500]}")

    # Check for syntax errors
    if 'SyntaxError' in log_content:
        return {
            "status": "failed",
            "error": "脚本语法错误",
            "log": log_content[:2000]
        }

    # Result file exists - read it
    check_cmd = f"cat {result_file}"
    result_content, _, _ = ssh_exec(check_cmd, timeout=10)
    print(f"[{BOT_TYPE}] 执行结果: {result_content[:500]}")
    
    # Also check log for any warnings
    check_log = f"tail -50 {log_file}"
    log_content, _, _ = ssh_exec(check_log, timeout=10)
    
    return {
        "status": "completed",
        "message": "Prototype task executed via CrewAI",
        "script": script_file,
        "result": result_content[:500],
        "log": log_content[-500:] if log_content else ""
    }


def generate_proto_script(task_id, task_desc, output_file):
    """Generate CrewAI script for prototype implementation - 5 agents parallel execution."""
    import json
    
    # Escape single quotes in output_file path for Python string
    safe_out = output_file.replace("'", "\\'")
    
    # Use json.dumps to properly escape the task description for embedding in Python string
    task_desc_json = json.dumps(task_desc, ensure_ascii=False)
    
    # Build script using string concatenation
    script_lines = [
        "#!/usr/bin/env python3",
        "\"\"\"CrewAI Prototype Task - " + str(task_id) + " (5 Agents Parallel)\"\"\"",
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
        "class ShellTool(BaseTool):",
        "    name: str = 'shell'",
        "    description: str = 'Execute shell command in /opt/AiComic'",
        "",
        "    def _run(self, cmd: str):",
        "        import subprocess",
        "        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=180, cwd='/opt/AiComic')",
        "        output = result.stdout + result.stderr",
        "        print('[shell] $ ' + cmd[:100] + ' -> ' + str(result.returncode))",
        "        return output",
        "",
        "shell = ShellTool()",
        "",
        "# 5 Agents - All with shell tool access",
        "frontend1 = Agent(",
        "    role='Frontend Engineer 1',",
        "    goal='Implement React/UI components based on prototype',",
        "    backstory='5 years React/Next.js experience, expert in TypeScript',",
        "    verbose=True,",
        "    llm=llm,",
        "    tools=[shell]",
        ")",
        "",
        "frontend2 = Agent(",
        "    role='Frontend Engineer 2',",
        "    goal='Implement UI components and integrate with backend APIs',",
        "    backstory='5 years React/Vue experience, expert in responsive design',",
        "    verbose=True,",
        "    llm=llm,",
        "    tools=[shell]",
        ")",
        "",
        "backend = Agent(",
        "    role='Backend Engineer',",
        "    goal='Implement FastAPI backend and database models',",
        "    backstory='8 years Python/FastAPI experience, expert in PostgreSQL',",
        "    verbose=True,",
        "    llm=llm,",
        "    tools=[shell]",
        ")",
        "",
        "tester = Agent(",
        "    role='Test Engineer',",
        "    goal='Write unit tests and integration tests',",
        "    backstory='4 years QA experience, expert in pytest',",
        "    verbose=True,",
        "    llm=llm,",
        "    tools=[shell]",
        ")",
        "",
        "devops = Agent(",
        "    role='DevOps Engineer',",
        "    goal='Ensure code is production-ready, git add/commit/push',",
        "    backstory='5 years CI/CD experience, expert in Docker',",
        "    verbose=True,",
        "    llm=llm,",
        "    tools=[shell]",
        ")",
        "",
        "task_description = " + task_desc_json,
        "",
        "# Tasks - Frontend1 and Frontend2 work in parallel, then Backend, then Tester, then DevOps",
        "task_fe1 = Task(",
        "    description=task_description + '\\n\\n[Frontend1] Implement UI components in /opt/AiComic/apps/frontend/',",
        "    agent=frontend1,",
        "    expected_output='React components with clean code'",
        ")",
        "",
        "task_fe2 = Task(",
        "    description=task_description + '\\n\\n[Frontend2] Implement UI components and API integration in /opt/AiComic/apps/frontend/',",
        "    agent=frontend2,",
        "    expected_output='React components with API integration'",
        ")",
        "",
        "task_be = Task(",
        "    description=task_description + '\\n\\n[Backend] Implement API endpoints in /opt/AiComic/apps/backend/',",
        "    agent=backend,",
        "    expected_output='FastAPI endpoints with proper models'",
        ")",
        "",
        "task_test = Task(",
        "    description=task_description + '\\n\\n[Test] Write tests in /opt/AiComic/tests/',",
        "    agent=tester,",
        "    expected_output='pytest test files'",
        ")",
        "",
        "task_devops = Task(",
        "    description='Git add, commit and push all changes. Run: cd /opt/AiComic && git add . && git commit -m \"feat: ' + str(task_id) + ' - prototype implementation\" && git push',",
        "    agent=devops,",
        "    expected_output='Git push successful'",
        ")",
        "",
        "# Parallel execution - FE1 and FE2 together, then sequential BE->Test->DevOps",
        "crew = Crew(",
        "    agents=[frontend1, frontend2, backend, tester, devops],",
        "    tasks=[task_fe1, task_fe2, task_be, task_test, task_devops],",
        "    process=Process.parallel,",
        "    verbose=True",
        ")",
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

        try:
            if "TODO" in task_id:
                result = execute_todo_task(task_id, payload)
            elif "DEPLOY" in task_id:
                result = execute_deploy_task(task_id, payload)
            elif "FIX" in task_id:
                result = execute_fix_task(task_id, payload)
            elif "PROTO" in task_id:
                result = execute_proto_task(task_id, payload)
            else:
                result = {"status": "completed", "note": "unknown task type"}
            task_success = True
        except Exception as e:
            result = {"status": "error", "error": str(e)}
            task_success = False
            print(f"[{BOT_TYPE}] 任务执行异常: {task_id} -> {e}")

        with state_lock:
            STATE["status"] = "idle"
            STATE["progress"] = 100 if task_success else 0
            STATE["completed"] += 1 if task_success else 0
            STATE["last_update"] = time.time()
            STATE["status"] = "idle"
            STATE["progress"] = 100
            STATE["completed"] += 1
            STATE["last_update"] = time.time()

        # 任务完成后，补处理遗漏的 @mention（方案B）
        if BOT_TYPE == "monitor":
            try:
                fetch_and_process_missed_mentions()
            except Exception as e:
                print(f"[Monitor] 补处理遗漏消息失败: {e}")

        try:
            self.send_response(200)
            self.end_headers()
            response_data = json.dumps({
                "status": "ok",
                "task_id": task_id,
                "result": result
            }).encode()
            self.wfile.write(response_data)
        except (BrokenPipeError, ConnectionResetError) as e:
            print(f"[{BOT_TYPE}] 客户端连接已关闭，任务仍正常执行: {task_id}")
        except Exception as e:
            print(f"[{BOT_TYPE}] 发送响应失败: {e}")

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
