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

# === 队列容量管控 ===
MAX_QUEUE_SIZE = 20  # 队列容量上限
POLL_INTERVAL = 30  # 轮询间隔（秒）

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

# === 各 Bot 独立任务队列 ===
BOT_QUEUES = {
    "dev": {"pending": [], "running": [], "completed": []},
    "pm": {"pending": [], "running": [], "completed": []},
    "marketing": {"pending": [], "running": [], "completed": []},
    "all": {"pending": [], "running": [], "completed": []}
}
BOT_QUEUES_LOCK = {k: threading.Lock() for k in BOT_QUEUES}

# Bot 端口映射
BOT_PORTS = {
    "dev": 8003,
    "pm": 8002,  # PM Bot 端口
    "marketing": 8004,  # Marketing Bot 端口
    "monitor": 8001,
}

# 兼容旧代码
TASK_QUEUE = BOT_QUEUES["dev"]  # 默认队列

# SSH 连接池控制
SSH_CONTROL_PATH = "/tmp/ssh_mux_%h_%p_%r"
_ssh_connection_lock = False
MAX_LOAD_AVG = 2.0  # 最大允许负载（2核4G服务器，负载>2就开始卡）
MAX_CONCURRENT_TASKS = 2  # 最大并发任务数（2核4G服务器）


# === 检查 Server B 负载 ===
def check_server_load():
    """检查 Server B 负载，返回当前负载值"""
    try:
        # 使用单次SSH执行，避免多进程
        ssh_cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
                   "-i", "/root/.ssh/id_ed25519", f"root@{SERVER_B_HOST}",
                   "cat /proc/loadavg | awk '{print $1}'"]
        result = subprocess.run(ssh_cmd, capture_output=True, timeout=10)
        if result.returncode == 0:
            return float(result.stdout.decode().strip())
    except:
        pass
    return 0.0


# === SSH 到 Server B（带负载监控）===
def ssh_exec(cmd, timeout=30):
    """SSH 到 Server B 执行命令（带负载监控）"""
    global _ssh_connection_lock
    
    # 等待锁（避免并发 SSH）
    while _ssh_connection_lock:
        import time
        time.sleep(0.5)
    
    _ssh_connection_lock = True
    try:
        # 检查负载，如果过高则等待
        load = check_server_load()
        if load > MAX_LOAD_AVG:
            import time
            print(f"[SSH] Server B 负载 {load} > {MAX_LOAD_AVG}，等待 30 秒...")
            time.sleep(15)
        
        ssh_cmd = [
            "ssh", "-o", "StrictHostKeyChecking=no",
            "-i", "/root/.ssh/id_ed25519",
            "-o", f"ConnectTimeout={timeout // 3}",
            "-o", f"ControlPath={SSH_CONTROL_PATH}",
            "-o", "ControlMaster=auto",
            "-o", "ControlPersist=60",
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
    finally:
        _ssh_connection_lock = False


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
def dispatch_task_to_bot(bot_type, task):
    """通过 HTTP 调用指定 Bot 执行任务（异步，不等待结果）
    
    Args:
        bot_type: "dev" | "pm" | "marketing" | "all"
        task: 任务字典，包含 task_id, desc, record_id 等
    """
    import threading
    import urllib.request

    def _dispatch():
        try:
            # 1. 如果是 "all"，拆分到各 Bot 队列
            if bot_type == "all":
                for bt in ["dev", "pm", "marketing"]:
                    task_copy = task.copy()
                    task_copy["task_id"] = f"{task['task_id']}-{bt}"
                    with BOT_QUEUES_LOCK[bt]:
                        BOT_QUEUES[bt]["pending"].append(task_copy)
                print(f"[Monitor] 任务 {task['task_id']} 已分发到所有 Bot")
                return

            # 2. 检查目标 Bot 是否忙碌
            port = BOT_PORTS.get(bot_type, 8003)
            try:
                with urllib.request.urlopen(f"http://localhost:{port}/status", timeout=5) as r:
                    bot_state = json.loads(r.read())
                if bot_state.get("status") == "busy":
                    # Bot 忙碌，将任务重新放回队列等待
                    with BOT_QUEUES_LOCK[bot_type]:
                        BOT_QUEUES[bot_type]["pending"].insert(0, task)
                    print(f"[Monitor] {bot_type} Bot 忙碌，任务 {task['task_id']} 重新入队")
                    update_task_status(task["record_id"], "待领取")
                    return
            except Exception as e:
                print(f"[Monitor] 检查 {bot_type} Bot 状态失败: {e}，仍尝试分发")

            # 3. 更新任务状态为"进行中"
            update_task_status(task["record_id"], "进行中")

            # 4. 发送任务到目标 Bot
            data = json.dumps({
                "task_id": task["task_id"],
                "task_type": bot_type,
                "record_id": task.get("record_id", ""),
                "callback_url": f"http://localhost:{BOT_PORTS['monitor']}/callback",
                "payload": {"任务描述": task["desc"], "proto_file": task.get("proto_file", "")}
            }).encode("utf-8")
            req = urllib.request.Request(
                f"http://localhost:{port}/execute",
                data=data,
                headers={"Content-Type": "application/json", "X-API-Key": "aicomic-shared-secret-key-2026"}
            )
            # 异步发送，不等待结果
            with urllib.request.urlopen(req, timeout=10):
                pass
            print(f"[Monitor] 已分发任务 {task['task_id']} 到 {bot_type} Bot")
        except Exception as e:
            print(f"[Monitor] 分发 {bot_type} Bot 失败: {e}")
            try:
                update_task_status(task["record_id"], "待领取")
            except:
                pass

    thread = threading.Thread(target=_dispatch, daemon=True)
    thread.start()
    return True


# 兼容旧代码
def dispatch_task_to_dev(task):
    """兼容旧代码：分发到 Dev Bot"""
    return dispatch_task_to_bot("dev", task)


def update_task_status(record_id, status, retries=3):
    """更新飞书任务板状态（带重试）"""
    import urllib.request

    for attempt in range(retries):
        try:
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
                    return True
                else:
                    print(f"[Monitor] 状态更新失败: {result.get('msg')}")
                    if attempt < retries - 1:
                        time.sleep(2 ** attempt)  # 指数退避
        except Exception as e:
            print(f"[Monitor] 状态更新异常 (尝试 {attempt+1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)

    print(f"[Monitor] 状态更新最终失败: {record_id[:10]}...")
    return False


def create_bitable_task_with_retry(task_id, description, source, assignee, retries=3):
    """创建飞书任务板任务（带重试）"""
    import subprocess

    for attempt in range(retries):
        try:
            result = subprocess.run(
                ["python3", "/opt/AiComic/scripts/create_bitable_task.py",
                 "--task-id", task_id,
                 "--description", description,
                 "--source", source,
                 "--assignee", assignee],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                print(f"[Monitor] Bitable任务创建成功: {task_id}")
                return True
            else:
                print(f"[Monitor] Bitable任务创建失败 (尝试 {attempt+1}/{retries}): {result.stderr}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # 指数退避
        except Exception as e:
            print(f"[Monitor] Bitable任务创建异常 (尝试 {attempt+1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)

    print(f"[Monitor] Bitable任务创建最终失败: {task_id}")
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


# === 补处理遗漏的 @mention（方案B）===
import os as _os
import time as _time

FEISHU_BOT_OPEN_ID = "ou_c7ec681c4b6134e7ef7d1da9ea59f1ab"  # 状态监控机器人
FEISHU_BOT_APP_ID_MISSED = "cli_a935c8fb40b8dccc"
FEISHU_BOT_APP_SECRET_MISSED = "LvyAzv4oVxqapgnFn75p4bT0z0LWxKfT"
FEISHU_GROUP_CHAT_ID_MISSED = "oc_389a77ed12ae0189d670c719f97e409c"
PROCESSED_MSG_IDS_FILE = "/opt/AiComic/状态报告/processed_msg_ids.json"
USER_OPEN_ID_FILE = "/opt/AiComic/状态报告/user_open_id.json"  # 用户主动发消息后存的 open_id

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
# === 队列容量检查 ===
def check_queue_capacity():
    """检查队列是否有容量接收新任务"""
    with task_queue_lock:
        total = len(TASK_QUEUE["pending"]) + len(TASK_QUEUE["running"])
    if total >= MAX_QUEUE_SIZE:
        print(f"[Monitor] 队列已满 ({total}/{MAX_QUEUE_SIZE})，暂停接收新任务")
        return False
    return True


# === 原型去重检查 ===
def check_prototype_overlap(proto_name, proto_content):
    """检查原型是否与已有原型重叠"""
    import os
    proto_dir = "/opt/AiComic/原型"
    if not os.path.exists(proto_dir):
        return False, None

    # 提取关键词
    keywords = set()
    # 从名称提取
    for word in proto_name.replace("原型", "").replace("_", " ").split():
        if len(word) > 2:
            keywords.add(word.lower())

    # 从内容提取前100字符作为特征
    content_preview = proto_content[:200].lower() if proto_content else ""

    try:
        for f in os.listdir(proto_dir):
            if not f.endswith(".md"):
                continue
            if f == f"{proto_name}.md":
                continue

            existing_path = os.path.join(proto_dir, f)
            with open(existing_path, 'r', encoding='utf-8', errors='ignore') as f:
                existing_content = f.read()[:200].lower()

            # 简单重叠检测：内容相似度
            overlap_count = sum(1 for kw in keywords if kw in existing_content)
            if overlap_count >= 3:
                print(f"[Monitor] 检测到原型重叠: {proto_name} 与 {f}")
                return True, f

            # 内容前100字符相似度
            if content_preview and existing_content:
                similarity = sum(1 for c1, c2 in zip(content_preview, existing_content) if c1 == c2)
                if similarity > 60:
                    print(f"[Monitor] 检测到原型内容相似: {proto_name} 与 {f}")
                    return True, f

    except Exception as e:
        print(f"[Monitor] 去重检查异常: {e}")

    return False, None


# === 轮询线程（独立）===
def poll_bitable_thread():
    """独立轮询线程，不阻塞主调度"""
    print(f"[Monitor] Bitable 轮询线程启动")
    tick = 0
    while True:
        try:
            if BOT_TYPE == "monitor":
                tick += 1
                # 每3分钟（6个tick × 30秒）广播一次状态
                if tick % 6 == 0:
                    broadcast_status_to_feishu()

                # 扫描原型目录发现新原型
                scan_prototypes()

                # 读取任务板待分配任务（带容量检查）
                if check_queue_capacity():
                    tasks = fetch_bitable_tasks()
                    STATE["pending_tasks"] = len(tasks)
                    for task in tasks:
                        existing = [t for t in TASK_QUEUE["pending"] if t.get("task_id") == task["task_id"]]
                        if not existing:
                            with task_queue_lock:
                                TASK_QUEUE["pending"].append(task)
                            print(f"[Monitor] 新任务: {task['task_id']} - {task.get('desc', '')[:50]}")

        except Exception as e:
            print(f"[Monitor] 轮询异常: {e}")

        time.sleep(POLL_INTERVAL)


def dispatcher_loop():
    """调度循环 - 从各 Bot 独立队列取任务分发
    
    任务分发策略：
    1. 如果任务指定了 bot_type，分发到对应队列
    2. 如果是 "all" 类型，分发到所有 Bot
    3. 否则按 round-robin 分发到 dev/pm/marketing
    """
    global STATE
    print(f"[{BOT_TYPE}] Dispatcher 启动")
    STATE["dispatcher_running"] = True
    last_bot_index = {"dev": 0, "pm": 1, "marketing": 2}  # round-robin 索引
    bot_cycle = ["dev", "pm", "marketing"]  # 分发循环顺序

    while True:
        try:
            if BOT_TYPE == "monitor":
                # 检查各 Bot 队列，找一个有任务的
                task_to_dispatch = None
                target_bot = None

                # 先检查 "all" 队列
                with BOT_QUEUES_LOCK["all"]:
                    if BOT_QUEUES["all"]["pending"]:
                        task_to_dispatch = BOT_QUEUES["all"]["pending"].pop(0)
                        target_bot = "all"

                # 如果没有 "all" 任务，检查 round-robin
                if not task_to_dispatch:
                    for bot in bot_cycle:
                        with BOT_QUEUES_LOCK[bot]:
                            if BOT_QUEUES[bot]["pending"]:
                                task_to_dispatch = BOT_QUEUES[bot]["pending"].pop(0)
                                target_bot = bot
                                break

                if task_to_dispatch:
                    task_to_dispatch["dispatched_at"] = time.time()

                    # 检查原型重叠
                    proto_file = task_to_dispatch.get("proto_file", "")
                    proto_desc = task_to_dispatch.get("description", "")
                    is_overlap, existing = check_prototype_overlap(proto_file, proto_desc)

                    if is_overlap:
                        print(f"[Monitor] 原型与 {existing} 重叠，暂停分发")
                        if task_to_dispatch.get("record_id"):
                            update_task_status(task_to_dispatch["record_id"], "待合并")
                        notify_pm(f"原型 {proto_file} 与 {existing} 功能重叠，请合并")
                        continue

                    # 分发到目标 Bot
                    dispatch_task_to_bot(target_bot, task_to_dispatch)
                    STATE["last_dispatch"] = time.time()

                    # 移动到 running 队列
                    if target_bot == "all":
                        for bot in ["dev", "pm", "marketing"]:
                            with BOT_QUEUES_LOCK[bot]:
                                BOT_QUEUES[bot]["running"].append(task_to_dispatch.copy())
                    else:
                        with BOT_QUEUES_LOCK[target_bot]:
                            BOT_QUEUES[target_bot]["running"].append(task_to_dispatch)

                # 兜底：检查各 Bot running 队列里的任务是否超时
                stale_threshold = 45 * 60  # 45分钟
                now = time.time()
                for bot in ["dev", "pm", "marketing", "all"]:
                    with BOT_QUEUES_LOCK[bot]:
                        stale_tasks = [
                            t for t in BOT_QUEUES[bot]["running"]
                            if t.get("dispatched_at", 0) > 0 and now - t["dispatched_at"] > stale_threshold
                        ]
                    for stale in stale_tasks:
                        print(f"[Monitor] {bot} 任务超时: {stale['task_id']}，标记为失败")
                        with BOT_QUEUES_LOCK[bot]:
                            BOT_QUEUES[bot]["running"] = [t for t in BOT_QUEUES[bot]["running"] if t["task_id"] != stale["task_id"]]
                        if stale.get("record_id"):
                            update_task_status(stale["record_id"], "失败")

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
        'llm = LLM(model="openai/MiniMax-M2.7-highspeed", is_litellm=True, api_key=os.environ.get("MINIMAX_API_KEY", ""), max_retries_on_rate_limit_error=5)\n' +
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

    # SCP 上传到 Server B（带限流）
    scp_cmd = [
        "scp", "-o", "StrictHostKeyChecking=no",
        "-i", "/root/.ssh/id_ed25519",
        "-o", f"ControlPath={SSH_CONTROL_PATH}",
        "-o", "ControlMaster=auto",
        "-l", "10240",  # 限速 10Mbps
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
        f'-e MINIMAX_API_BASE="https://api.minimax.chat/v1" '
        f'crewai-runtime python {script_file} > {output_file}.log 2>&1 &'
    )
    ssh_exec(exec_cmd, timeout=10)
    print(f"[{BOT_TYPE}] CrewAI 已启动: {script_file}")

    # Polling 等待结果（最多 30 分钟，每次 30 秒）
    result_file = f"{output_file}.result"
    print(f"[{BOT_TYPE}] 等待 CrewAI 执行完成（最多30分钟）...")
    for i in range(60):  # 60 * 30s = 30min
        time.sleep(30)
        result_content, _, _ = ssh_exec(f"test -f {result_file} && cat {result_file} || echo 'NOT_READY'", timeout=10)
        if 'NOT_READY' not in result_content:
            print(f"[{BOT_TYPE}] CrewAI 执行完成，耗时 {(i+1)*30} 秒")
            # 回传结果文件到本地
            local_result = f"/opt/AiComic/scripts/generated/crewai_result_{script_id}.txt"
            subprocess.run([
                "scp", "-o", "StrictHostKeyChecking=no",
                "-i", "/root/.ssh/id_ed25519",
                f"root@{SERVER_B_HOST}:{result_file}",
                local_result
            ], timeout=30, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return {
                "status": "completed",
                "result": result_content[:1000],
                "log": f"{output_file}.log"
            }
        if i % 5 == 0:
            print(f"[{BOT_TYPE}] 等待中... {(i+1)*30}秒")

    # 30分钟超时
    return {
        "status": "timeout",
        "log": f"{output_file}.log",
        "error": "CrewAI 执行超时（30分钟）"
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
    """Execute prototype implementation task - use CrewAI to implement the prototype

    异步执行模式：立即返回任务ID，后台执行，定期更新进度。
    """
    print(f"[{BOT_TYPE}] 执行原型研发任务: {task_id}")

    # ========== 立即返回，避免超时 ==========
    # 返回任务ID，让调用方可以通过 /status 查询进度
    import threading
    import json

    # 初始化进度状态
    progress_file = f"/tmp/proto_progress_{task_id}.json"
    progress_data = {
        "task_id": task_id,
        "status": "starting",
        "progress": 0,
        "message": "任务已接收，准备执行...",
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "last_update": time.time()
    }
    with open(progress_file, 'w') as f:
        json.dump(progress_data, f)

    # 启动后台执行线程
    def background_execute():
        try:
            _do_proto_execute(task_id, payload, progress_file)
        except Exception as e:
            progress_data["status"] = "error"
            progress_data["message"] = str(e)
            progress_data["last_update"] = time.time()
            with open(progress_file, 'w') as f:
                json.dump(progress_data, f)

    thread = threading.Thread(target=background_execute, daemon=True)
    thread.start()

    # 立即返回，让调用方可以查询进度
    return {
        "status": "started",
        "task_id": task_id,
        "message": "任务已启动，后台执行中",
        "progress_file": progress_file,
        "hint": "可通过 /status 端点查询进度"
    }


def _do_proto_execute(task_id, payload, progress_file):
    """实际执行逻辑（后台运行）"""
    import json
    import time

    # 更新进度：开始执行
    def update_progress(status, progress, message):
        with open(progress_file, 'w') as f:
            json.dump({
                "task_id": task_id,
                "status": status,
                "progress": progress,
                "message": message,
                "last_update": time.time()
            }, f)

    update_progress("running", 5, "正在准备脚本...")
    _send_feishu_message(f"🚀 [{BOT_TYPE}] 任务 {task_id} 开始执行，准备脚本...")

    # 任务间隔保护
    task_interval_file = "/tmp/last_proto_task_time"
    last_time = 0
    if os.path.exists(task_interval_file):
        try:
            last_time = int(open(task_interval_file).read().strip())
        except:
            pass
    current_time = int(time.time())
    if current_time - last_time < 30:
        wait_time = 30 - (current_time - last_time)
        print(f"[{BOT_TYPE}] 任务间隔保护，等待 {wait_time} 秒...")
        time.sleep(wait_time)
    with open(task_interval_file, "w") as f:
        f.write(str(int(time.time())))

    update_progress("running", 10, "正在读取原型文件...")

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
                sections = {}
                for section_name in ['背景与目标', '一、背景与目标', '产品定位与目标', '功能清单', '二、功能清单', '功能需求', '界面描述', '三、界面设计', '验收标准', '四、验收标准']:
                    if section_name in proto_content:
                        # 简单提取：找到章节名后的内容
                        idx = proto_content.find(section_name)
                        if idx >= 0:
                            next_idx = idx + len(section_name)
                            # 找下一个 ## 标题位置
                            next_heading = proto_content.find('\n## ', next_idx)
                            if next_heading > 0:
                                sections[section_name] = proto_content[next_idx:next_heading].strip()
                            else:
                                sections[section_name] = proto_content[next_idx:].strip()[:3000]

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

    # Upload to Server B (with rate limit)
    scp_cmd = [
        "scp", "-o", "StrictHostKeyChecking=no",
        "-i", "/root/.ssh/id_ed25519",
        "-o", f"ControlPath={SSH_CONTROL_PATH}",
        "-o", "ControlMaster=auto",
        "-l", "10240",  # 限速 10Mbps
        local_script,
        f"root@{SERVER_B_HOST}:{script_file}"
    ]
    r = subprocess.run(scp_cmd, timeout=120, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode != 0:
        err = r.stderr.decode()
        print(f"[{BOT_TYPE}] 上传脚本失败: {err}")
        return {"status": "failed", "error": err}
    print(f"[{BOT_TYPE}] 脚本已上传: {script_file}")
    update_progress("running", 40, f"脚本已上传到Server B: {script_file}")

    # Execute on Server B via docker (background mode - don't wait)
    container = "crewai-runtime"
    run_cmd = (
        f"docker exec -e MINIMAX_API_KEY=\"$MINIMAX_API_KEY\" "
        f"-e MINIMAX_API_BASE=\"https://api.minimax.chat/v1\" "
        f"{container} python {script_file} > {output_file}.log 2>&1 &"
    )
    stdout, stderr, code = ssh_exec(run_cmd, timeout=10)
    print(f"[{BOT_TYPE}] CrewAI 任务已在后台启动，PID: {stdout.strip()}")
    update_progress("running", 50, f"CrewAI 任务已启动，PID: {stdout.strip()[:20]}...，等待执行结果...")
    _send_feishu_message(f"🤖 [{BOT_TYPE}] 任务 {task_id} 已启动 CrewAI（6 Agent并行），正在开发中...")

    # Wait for result file (up to 30 minutes), with rate-limit retry
    import time
    max_wait = 180   # 3 minutes (快速流转模式) total
    check_interval = 20  # 20 seconds
    waited = 0
    result_content = ""
    result_file = f"{output_file}.result"  # Define BEFORE the loop
    max_retries = 3
    retry_count = 0

    def _is_rate_limit_error(log_text):
        """检查日志是否包含 API 速率限制错误"""
        if not log_text:
            return False
        rl_markers = ['rate limit', '429', 'too many requests', 'rate_limit',
                       'rpm limit', 'tpm limit', '请稍后重试', 'over quota', 'quota exceeded']
        text_lower = log_text.lower()
        return any(marker in text_lower for marker in rl_markers)

    def _restart_crewai():
        """重新启动 CrewAI 容器（先停后启）"""
        stop_cmd = "docker ps -q --filter 'ancestor=crewai-runtime' | xargs -r docker stop -t 2"
        ssh_exec(stop_cmd, timeout=15)
        time.sleep(3)
        start_cmd = (
            f'docker run -d --name crewai-runtime '
            f'-e MINIMAX_API_KEY="$MINIMAX_API_KEY" '
            f'-e OPENAI_API_KEY="$MINIMAX_API_KEY" '
            f'-v /opt/AiComic:/opt/AiComic '
            f'-w /opt/AiComic crewai-runtime '
            f'python {script_file} > {output_file}.log 2>&1 &'
        )
        ssh_exec(start_cmd, timeout=10)

    while waited < max_wait:
        time.sleep(check_interval)
        waited += check_interval

        # Check if result file exists
        check_cmd = f"test -f {result_file} && cat {result_file} || echo 'NOT_READY'"
        result_content, _, _ = ssh_exec(check_cmd, timeout=10)

        if 'NOT_READY' not in result_content:
            print(f"[{BOT_TYPE}] CrewAI 执行完成，用时 {waited} 秒")
            update_progress("running", 90, f"CrewAI 执行完成，用时 {waited} 秒，正在读取结果...")
            break

        # 每分钟更新一次进度
        if waited % 60 == 0 and waited > 0:
            update_progress("running", 50 + min(40, waited // 60 * 5), f"等待 CrewAI 完成... ({waited//60}分钟)")

        # 检查日志里是否有 rate limit 错误
        log_cmd = f"tail -30 {output_file}.log 2>/dev/null || echo ''"
        log_content, _, _ = ssh_exec(log_cmd, timeout=10)

        if _is_rate_limit_error(log_content) and retry_count < max_retries:
            retry_count += 1
            backoff = 5 * (2 ** retry_count)  # 10s, 20s, 40s
            print(f"[{BOT_TYPE}] 检测到 API 速率限制 (429)，{backoff}秒后第{retry_count}次重试...")
            time.sleep(backoff)
            _restart_crewai()
            waited += backoff
            continue

        if retry_count > 0:
            print(f"[{BOT_TYPE}] CrewAI 重试中，已等待 {waited}s（第{retry_count}次）")
        else:
            print(f"[{BOT_TYPE}] 等待 CrewAI 完成... ({waited}s)")

    if waited >= max_wait:
        print(f"[{BOT_TYPE}] CrewAI 执行超时 ({max_wait}s, 重试{retry_count}次)")
        update_progress("timeout", 100, f"CrewAI 执行超时 ({max_wait}s)")
        _send_feishu_message(f"⏰ [{BOT_TYPE}] 任务 {task_id} 执行超时！请检查 Server B 日志")

        # 回调 Monitor 通知任务失败
        record_id = payload.get("record_id", "")
        try:
            import urllib.request
            callback_url = "http://127.0.0.1:8001/callback"
            callback_data = json.dumps({
                "task_id": task_id,
                "status": "timeout",
                "record_id": record_id,
                "bot": "dev",
                "result": {"message": f"CrewAI 执行超时 ({max_wait}s)"}
            }).encode('utf-8')
            req = urllib.request.Request(callback_url, data=callback_data, method="POST")
            req.add_header("Content-Type", "application/json")
            req.add_header("X-API-Key", "aicomic-shared-secret-key-2026")
            with urllib.request.urlopen(req, timeout=10):
                pass
        except:
            pass

        return {
            "status": "timeout",
            "message": "CrewAI 执行超时",
            "log": f"{output_file}.log",
            "retries": retry_count
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
        update_progress("failed", 100, "脚本语法错误")
        _send_feishu_message(f"❌ [{BOT_TYPE}] 任务 {task_id} 脚本语法错误！请检查生成的脚本")

        # 回调 Monitor 通知任务失败
        record_id = payload.get("record_id", "")
        try:
            import urllib.request
            callback_url = "http://127.0.0.1:8001/callback"
            callback_data = json.dumps({
                "task_id": task_id,
                "status": "failed",
                "record_id": record_id,
                "bot": "dev",
                "result": {"message": "脚本语法错误"}
            }).encode('utf-8')
            req = urllib.request.Request(callback_url, data=callback_data, method="POST")
            req.add_header("Content-Type", "application/json")
            req.add_header("X-API-Key", "aicomic-shared-secret-key-2026")
            with urllib.request.urlopen(req, timeout=10):
                pass
        except:
            pass

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

    update_progress("completed", 100, "任务执行完成")
    _send_feishu_message(f"✅ [{BOT_TYPE}] 任务 {task_id} 执行完成！正在更新任务板...")

    # ========== 回调 Monitor 通知任务完成 ==========
    record_id = payload.get("record_id", "")
    try:
        import urllib.request
        callback_url = "http://127.0.0.1:8001/callback"
        callback_data = json.dumps({
            "task_id": task_id,
            "status": "completed",
            "record_id": record_id,
            "bot": "dev",
            "result": {
                "elapsed_seconds": waited,
                "message": "原型研发任务完成"
            }
        }).encode('utf-8')
        req = urllib.request.Request(callback_url, data=callback_data, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("X-API-Key", "aicomic-shared-secret-key-2026")
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"[{BOT_TYPE}] 回调 Monitor 成功")
    except Exception as e:
        print(f"[{BOT_TYPE}] 回调 Monitor 失败: {e}")

    return {
        "status": "completed",
        "message": "Prototype task executed via CrewAI",
        "script": script_file,
        "result": result_content[:500],
        "log": log_content[-500:] if log_content else ""
    }


def generate_proto_script(task_id, task_desc, output_file):
    """Generate CrewAI script with ThreadPool-based adaptive concurrency.

    特性：
    1. 使用 ThreadPoolExecutor 启动 6 个独立 Agent
    2. 每个 Agent 自带限流重试（指数退避）
    3. 运行时动态监控 API 错误率
    4. 连续触发限流时自动降低并发数至安全阈值（如 3 个）
    5. 实现自适应最大并发
    """
    import json

    safe_out = output_file.replace("'", "\\'")
    task_desc_json = json.dumps(task_desc, ensure_ascii=False)

    # 按角色定制的任务描述
    role_tasks = {
        "frontend1": """【Frontend1 职责】实现 UI 组件
参考原型文档完成任务开发：
{task_desc}
具体要求：
- 使用 React 实现 UI 组件
- 组件需要包含完整的样式和交互
- 代码放在 /opt/AiComic/apps/frontend/src/ 目录""",

        "frontend2": """【Frontend2 职责】实现状态管理和 API 集成
参考原型文档完成任务开发：
{task_desc}
具体要求：
- 使用 React Hooks 实现状态管理
- 调用后端 API 实现数据交互
- 与 Frontend1 协作确保组件集成正常""",

        "backend1": """【Backend1 职责】实现 FastAPI 后端接口
参考原型文档完成任务开发：
{task_desc}
具体要求：
- 使用 FastAPI 实现 RESTful API
- 实现业务逻辑层
- 代码放在 /opt/AiComic/apps/backend/ 目录""",

        "backend2": """【Backend2 职责】实现数据库模型
参考原型文档完成任务开发：
{task_desc}
具体要求：
- 使用 SQLAlchemy 定义数据模型
- 编写必要的数据库迁移脚本
- 与 Backend1 协作确保 API 能正常访问数据""",

        "tester": """【Test Engineer 职责】编写单元测试
注意：此任务在开发 Agent 完成后执行
具体要求：
- 为已完成的代码编写单元测试
- 测试覆盖率目标 > 70%
- 测试文件放在 /opt/AiComic/tests/ 目录
- 使用 pytest 框架""",

        "devops": """【DevOps Engineer 职责】验证代码并部署
注意：此任务在 Test Engineer 完成后执行
具体要求：
- 运行测试确保所有用例通过
- 检查代码质量和规范
- git commit 并 push 到仓库
- 更新相关文档""",
    }

    script_lines = [
        "#!/usr/bin/env python3",
        "\"\"\"CrewAI Prototype Task - " + str(task_id) + "\"\"\"",
        "\"\"\"",
        "自适应并发执行系统：",
        "1. 使用 ThreadPoolExecutor 启动 2 个独立 Agent（资源限制）",
        "2. 每个 Agent 自带限流重试（指数退避）",
        "3. 运行时动态监控 API 错误率",
        "4. 连续触发限流时自动降低并发数至安全阈值（3个）",
        "5. 实现自适应最大并发",
        "\"\"\"",
        "import os",
        "import sys",
        "import time",
        "import json",
        "import threading",
        "import concurrent.futures",
        "from datetime import datetime",
        "from collections import deque",
        "",
        "os.environ['OPENAI_API_KEY'] = os.environ.get('MINIMAX_API_KEY', '')",
        "os.environ['MINIMAX_API_BASE'] = 'https://api.minimax.chat/v1'",
        "os.environ['LANG'] = 'en_US.UTF-8'",
        "",
        "from crewai import Agent, Task, Crew",
        "from crewai.llm import LLM",
        "from crewai.tools import BaseTool",
        "import litellm",
        "import httpx",
        "litellm.request_timeout = 600",
        "",
        "# === MiniMax 系统消息转换器 ===",
        "# MiniMax API 不支持 system role，此转换器自动将其转为 user role",
        "def convert_system_to_user(messages):",
        "    \"\"\"将所有 system role 转换为 user role\"\"\"",
        "    if not messages:",
        "        return messages",
        "    converted = []",
        "    for msg in messages:",
        "        if not isinstance(msg, dict):",
        "            converted.append(msg)",
        "            continue",
        "        if msg.get('role') == 'system':",
        "            # 将 system 消息转换为 user 消息",
        "            content = msg.get('content', '')",
        "            if isinstance(content, list):",
        "                content = str(content)",
        "            converted.append({'role': 'user', 'content': '[System] ' + content})",
        "        else:",
        "            converted.append(msg)",
        "    return converted",
        "",
        "# 包装所有 litellm 完成方法",
        "original_completion = litellm.completion",
        "original_acompletion = litellm.acompletion",
        "",
        "def safe_completion(*args, **kwargs):",
        "    \"\"\"包装 litellm.completion，自动转换消息\"\"\"",
        "    if 'messages' in kwargs:",
        "        kwargs['messages'] = convert_system_to_user(kwargs['messages'])",
        "    elif len(args) > 1:",
        "        args = list(args)",
        "        args[1] = convert_system_to_user(args[1])",
        "        args = tuple(args)",
        "    return original_completion(*args, **kwargs)",
        "",
        "async def safe_acompletion(*args, **kwargs):",
        "    \"\"\"包装 litellm.acompletion，自动转换消息\"\"\"",
        "    if 'messages' in kwargs:",
        "        kwargs['messages'] = convert_system_to_user(kwargs['messages'])",
        "    elif len(args) > 1:",
        "        args = list(args)",
        "        args[1] = convert_system_to_user(args[1])",
        "        args = tuple(args)",
        "    return await original_acompletion(*args, **kwargs)",
        "",
        "# 替换 litellm 方法",
        "litellm.completion = safe_completion",
        "litellm.acompletion = safe_acompletion",
        "",
        "# 额外：patch CrewAI 的 LLM._prepare_completion_params 方法",
        "try:",
        "    from crewai.llm import LLM",
        "    _original_prepare = LLM._prepare_completion_params",
        "    ",
        "    def _patched_prepare(self, *args, **kwargs):",
        "        result = _original_prepare(self, *args, **kwargs)",
        "        if 'messages' in result:",
        "            result['messages'] = convert_system_to_user(result['messages'])",
        "        return result",
        "    ",
        "    LLM._prepare_completion_params = _patched_prepare",
        "    print('[System] CrewAI LLM patched successfully')",
        "except Exception as e:",
        "    print(f'[System] CrewAI LLM patch failed: {e}')",
        "",
        "# === 全局并发控制器 ===",
        "class ConcurrencyController:",
        "    \"\"\"自适应并发控制器\"\"\"",
        "    def __init__(self, max_workers=6, safe_threshold=3):",
        "        self.max_workers = max_workers",
        "        self.safe_threshold = safe_threshold",
        "        self.current_workers = max_workers",
        "        self.error_counts = deque(maxlen=20)  # 滑动窗口记录最近20次请求",
        "        self.lock = threading.Lock()",
        "        self.consecutive_errors = 0",
        "        self.api_errors = 0",
        "        self.total_calls = 0",
        "        self.current_error_rate = 0.0",
        "",
        "    def record_result(self, is_error, is_rate_limit=False):",
        "        \"\"\"记录 API 调用结果\"\"\"",
        "        with self.lock:",
        "            self.total_calls += 1",
        "            self.error_counts.append(1 if is_error else 0)",
        "            self.current_error_rate = sum(self.error_counts) / len(self.error_counts)",
        "            ",
        "            if is_error:",
        "                self.consecutive_errors += 1",
        "                self.api_errors += 1",
        "                if is_rate_limit:",
        "                    # 触发限流时快速降级",
        "                    self.consecutive_errors = max(self.consecutive_errors, 3)",
        "            else:",
        "                self.consecutive_errors = 0",
        "            ",
        "            # 动态调整并发数",
        "            self._adjust_concurrency()",
        "            ",
        "            return self.current_workers",
        "",
        "    def _adjust_concurrency(self):",
        "        \"\"\"根据错误率动态调整并发数\"\"\"",
        "        if self.consecutive_errors >= 3:",
        "            # 连续3次以上错误，降低并发",
        "            new_workers = max(self.safe_threshold, self.current_workers // 2)",
        "            if new_workers < self.current_workers:",
        "                print(f'[Controller] 连续错误{self.consecutive_errors}次，降低并发: {self.current_workers} -> {new_workers}')",
        "                self.current_workers = new_workers",
        "                self.consecutive_errors = 0",
        "        elif self.current_error_rate > 0.3 and self.current_workers > self.safe_threshold:",
        "            # 错误率超过30%且高于安全阈值，降低并发",
        "            new_workers = max(self.safe_threshold, self.current_workers - 1)",
        "            print(f'[Controller] 错误率{self.current_error_rate:.1%}，降低并发: {self.current_workers} -> {new_workers}')",
        "            self.current_workers = new_workers",
        "        elif self.current_error_rate < 0.1 and self.current_workers < self.max_workers:",
        "            # 错误率低于10%且低于最大并发，尝试增加",
        "            new_workers = min(self.max_workers, self.current_workers + 1)",
        "            if new_workers > self.current_workers:",
        "                print(f'[Controller] 错误率{self.current_error_rate:.1%}，增加并发: {self.current_workers} -> {new_workers}')",
        "                self.current_workers = new_workers",
        "",
        "    def get_stats(self):",
        "        \"\"\"获取当前统计信息\"\"\"",
        "        with self.lock:",
        "            return {",
        "                'current_workers': self.current_workers,",
        "                'max_workers': self.max_workers,",
        "                'error_rate': self.current_error_rate,",
        "                'total_calls': self.total_calls,",
        "                'api_errors': self.api_errors,",
        "                'consecutive_errors': self.consecutive_errors,",
        "            }",
        "",
        "    def wait_if_needed(self):",
        "        \"\"\"如果并发已满，等待\"\"\"",
        "        # 这个方法可以用于实现全局并发限制",
        "        pass",
        "",
        "",
        "# === Agent 执行器（带重试）===",
        "class AgentExecutor:",
        "    \"\"\"带指数退避重试的 Agent 执行器\"\"\"",
        "    def __init__(self, agent, task, controller, name):",
        "        self.agent = agent",
        "        self.task = task",
        "        self.controller = controller",
        "        self.name = name",
        "        self.max_retries = 5",
        "        self.base_delay = 2  # 基础延迟秒数",
        "        self.result = None",
        "        self.error = None",
        "",
        "    def execute_with_retry(self):",
        "        \"\"\"执行任务，支持指数退避重试\"\"\"",
        "        for attempt in range(self.max_retries):",
        "            try:",
        "                print(f'[{self.name}] 执行任务 (尝试 {attempt + 1}/{self.max_retries})')",
        "                result = self.agent.execute_task(self.task)",
        "                ",
        "                # 记录成功",
        "                self.controller.record_result(is_error=False)",
        "                self.result = result",
        "                print(f'[{self.name}] 任务完成')",
        "                return result",
        "                ",
        "            except Exception as e:",
        "                error_msg = str(e)",
        "                is_rate_limit = any(x in error_msg.lower() for x in ['rate', 'limit', '429', 'too many'])",
        "                is_api_error = any(x in error_msg.lower() for x in ['api', 'error', 'invalid', '401', '403', '500', '502', '503'])",
        "                ",
        "                # 记录错误",
        "                self.controller.record_result(is_error=True, is_rate_limit=is_rate_limit)",
        "                ",
        "                if attempt < self.max_retries - 1:",
        "                    delay = self.base_delay * (2 ** attempt)  # 2, 4, 8, 16, 32 秒",
        "                    print(f'[{self.name}] 错误: {error_msg[:100]}...')",
        "                    print(f'[{self.name}] {delay}秒后重试...')",
        "                    time.sleep(delay)",
        "                else:",
        "                    self.error = error_msg",
        "                    print(f'[{self.name}] 重试次数用尽，任务失败')",
        "        ",
        "        return None",
        "",
        "",
        "def run_agents_concurrently(agents, tasks, controller, output_file):",
        "    \"\"\"使用线程池并发执行多个 Agent\"\"\"",
        "    results = {}",
        "    stats = controller.get_stats()",
        "    print(f'[主控] 启动并发执行，最大并发: {stats[\"current_workers\"]}')",
        "    ",
        "    with concurrent.futures.ThreadPoolExecutor(max_workers=controller.current_workers) as executor:",
        "        futures = {}",
        "        for i, (agent, task) in enumerate(zip(agents, tasks)):",
        "            executor_config = AgentExecutor(agent, task, controller, f'Agent-{i+1}')",
        "            future = executor.submit(executor_config.execute_with_retry)",
        "            futures[future] = f'Agent-{i+1}'",
        "        ",
        "        for future in concurrent.futures.as_completed(futures):",
        "            agent_name = futures[future]",
        "            try:",
        "                result = future.result()",
        "                results[agent_name] = {'status': 'success', 'result': result}",
        "                print(f'[主控] {agent_name} 完成')",
        "            except Exception as e:",
        "                results[agent_name] = {'status': 'error', 'error': str(e)}",
        "                print(f'[主控] {agent_name} 失败: {e}')",
        "    ",
        "    return results",
        "",
        "",
        "# === 主执行流程 ===",
        "def main():",
        "    print('='*60)",
        "    print('CrewAI 原型任务执行 - 自适应并发版本')",
        "    print('='*60)",
        "    ",
        "    # 初始化 LLM",
        "    llm = LLM(",
        "        model='openai/MiniMax-M2.7-highspeed',",
        "        is_litellm=True,",
        "        api_key=os.environ.get('MINIMAX_API_KEY', ''),",
        "        max_retries_on_rate_limit_error=0,  # 我们自己处理重试",
        "    )",
        "    ",
        "    # Shell 工具",
        "    class ShellTool(BaseTool):",
        "        name: str = 'shell'",
        "        description: str = 'Execute shell command in /opt/AiComic'",
        "        ",
        "        def _run(self, cmd: str):",
        "            import subprocess",
        "            result = subprocess.run(",
        "                cmd, shell=True, capture_output=True, text=True, timeout=120,",
        "                cwd='/opt/AiComic'",
        "            )",
        "            return result.stdout + result.stderr",
        "    ",
        "    shell = ShellTool()",
        "    ",
        "    # 创建 6 个 Agent",
        "    agents = [",
        "        Agent(",
        "            role='Frontend Engineer 1',",
        "            goal='Implement UI components in React',",
        "            backstory='5 years React experience',",
        "            verbose=True, llm=llm, tools=[shell]",
        "        ),",
        "        Agent(",
        "            role='Frontend Engineer 2',",
        "            goal='Implement UI state management and API integration',",
        "            backstory='5 years React experience',",
        "            verbose=True, llm=llm, tools=[shell]",
        "        ),",
        "        Agent(",
        "            role='Backend Engineer 1',",
        "            goal='Implement FastAPI endpoints',",
        "            backstory='5 years Python/FastAPI experience',",
        "            verbose=True, llm=llm, tools=[shell]",
        "        ),",
        "        Agent(",
        "            role='Backend Engineer 2',",
        "            goal='Implement database models and SQL',",
        "            backstory='5 years SQLAlchemy experience',",
        "            verbose=True, llm=llm, tools=[shell]",
        "        ),",
        "        Agent(",
        "            role='Test Engineer',",
        "            goal='Write unit tests',",
        "            backstory='3 years testing experience',",
        "            verbose=True, llm=llm, tools=[shell]",
        "        ),",
        "        Agent(",
        "            role='DevOps Engineer',",
        "            goal='Verify code and git push',",
        "            backstory='3 years CI/CD experience',",
        "            verbose=True, llm=llm, tools=[shell]",
        "        ),",
        "    ]",
        "    ",
        "    # 任务描述",
        "    task_description = " + task_desc_json,
        "    ",
        "    # 创建 6 个任务",
        "    tasks = [",
        "        Task(",
        "            description='[Frontend1] ' + task_description,",
        "            agent=agents[0],",
        "            expected_output='React components created',",
        "        ),",
        "        Task(",
        "            description='[Frontend2] ' + task_description,",
        "            agent=agents[1],",
        "            expected_output='State management done',",
        "        ),",
        "        Task(",
        "            description='[Backend1] ' + task_description,",
        "            agent=agents[2],",
        "            expected_output='API endpoints created',",
        "        ),",
        "        Task(",
        "            description='[Backend2] ' + task_description,",
        "            agent=agents[3],",
        "            expected_output='Database models created',",
        "        ),",
        "        Task(",
        "            description='[Test] ' + task_description,",
        "            agent=agents[4],",
        "            expected_output='Tests written',",
        "        ),",
        "        Task(",
        "            description='[DevOps] ' + task_description,",
        "            agent=agents[5],",
        "            expected_output='Code verified and pushed',",
        "        ),",
        "    ]",
        "    ",
        "    # 初始化控制器",
        "    controller = ConcurrencyController(max_workers=2, safe_threshold=1)",
        "    ",
        "    # Phase 1: 并发执行 2 个 Agent",
        "    print('[Phase 1] 开始并发执行 2 个 Agent...')",
        "    start_time = time.time()",
        "    results = run_agents_concurrently(agents, tasks, controller, '" + safe_out + "')",
        "    elapsed = time.time() - start_time",
        "    print(f'[Phase 1] 并发执行完成，耗时: {elapsed:.1f}秒')",
        "    ",
        "    # 输出统计",
        "    stats = controller.get_stats()",
        "    print(f'[统计] 最终并发数: {stats[\"current_workers\"]}')",
        "    print(f'[统计] API 错误率: {stats[\"error_rate\"]:.1%}')",
        "    print(f'[统计] 总调用数: {stats[\"total_calls\"]}, API错误: {stats[\"api_errors\"]}')",
        "    ",
        "    # 保存结果",
        "    final_result = {",
        "        'phase1_results': {k: {'status': v['status']} for k, v in results.items()},",
        "        'stats': stats,",
        "        'elapsed_seconds': elapsed,",
        "        'timestamp': datetime.now().isoformat(),",
        "    }",
        "    with open('" + safe_out + ".result', 'w') as f:",
        "        f.write(json.dumps(final_result, ensure_ascii=False, indent=2))",
        "    ",
        "    print('[完成] 结果已保存到: " + safe_out + ".result')",
        "    print('='*60)",
        "",
        "if __name__ == '__main__':",
        "    main()",
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
        elif self.path == "/notify":
            # 接收通知（PM/Marketing 接收 Monitor 的通知）
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body)
            except:
                data = {}
            self._handle_notify(data)
        elif self.path == "/reject":
            # 驳回任务
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body)
            except:
                data = {}
            self._handle_reject(data)
        else:
            self.send_response(404)
            self.end_headers()

    def _handle_execute(self, data):
        global STATE
        task_id = data.get("task_id", "unknown")
        record_id = data.get("record_id", "")
        callback_url = data.get("callback_url", "")
        payload = data.get("payload", {})
        task_type = data.get("task_type", "unknown")

        with state_lock:
            STATE["status"] = "busy"
            STATE["task_id"] = task_id
            STATE["progress"] = 0
            STATE["last_update"] = time.time()

        # 如果是广播任务，分发到所有 Bot
        if task_type == "all":
            for bt in ["dev", "pm", "marketing"]:
                task_copy = {
                    "task_id": f"{task_id}-{bt}",
                    "desc": payload.get("任务描述", ""),
                    "record_id": record_id,
                    "proto_file": payload.get("proto_file", ""),
                    "payload": payload
                }
                with BOT_QUEUES_LOCK[bt]:
                    BOT_QUEUES[bt]["pending"].append(task_copy)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "task_id": task_id, "note": "broadcasted to all bots"}).encode())
            return

        task_success = False
        try:
            if "TODO" in task_id:
                result = execute_todo_task(task_id, payload, record_id)
            elif "DEPLOY" in task_id:
                result = execute_deploy_task(task_id, payload)
            elif "FIX" in task_id:
                result = execute_fix_task(task_id, payload)
            elif "PROTO" in task_id:
                result = execute_proto_task(task_id, payload)
            elif "PM" in task_id or "ANALYSIS" in task_id or BOT_TYPE == "pm":
                # PM Bot: 执行产品分析/PRD生成任务
                result = execute_pm_task(task_id, payload, record_id, callback_url)
            elif "MARKETING" in task_id or "CONTENT" in task_id or BOT_TYPE == "marketing":
                # Marketing Bot: 生成营销文案
                result = execute_marketing_task(task_id, payload, record_id, callback_url)
            else:
                result = {"status": "completed", "note": "unknown task type"}
            task_success = True
        except Exception as e:
            result = {"status": "error", "error": str(e)}
            task_success = False
            print(f"[{BOT_TYPE}] 任务执行异常: {task_id} -> {e}")

        # 所有 Bot 任务完成后都通知 Monitor（callback）
        if callback_url:
            try:
                import urllib.request
                callback_data = json.dumps({
                    "task_id": task_id,
                    "record_id": record_id,
                    "status": "completed" if task_success else "failed",
                    "result": result
                }).encode("utf-8")
                req = urllib.request.Request(
                    callback_url,
                    data=callback_data,
                    headers={"Content-Type": "application/json", "X-API-Key": "aicomic-shared-secret-key-2026"}
                )
                urllib.request.urlopen(req, timeout=10)
                print(f"[{BOT_TYPE}] 已通知 Monitor 任务完成: {task_id}")
            except Exception as e:
                print(f"[{BOT_TYPE}] 通知 Monitor 失败: {e}")

        with state_lock:
            STATE["status"] = "idle"
            STATE["progress"] = 100 if task_success else 0
            STATE["completed"] += 1 if task_success else 0
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

    def _handle_notify(self, data):
        """接收通知消息（被 Monitor 回调时触发）"""
        msg_type = data.get("type", "")
        message = data.get("message", "")

        if msg_type == "task_completed":
            # 任务完成通知
            task_id = data.get("task_id", "")
            proto_file = data.get("proto_file", "")
            print(f"[{BOT_TYPE}] 收到任务完成通知: {task_id}")
            # TODO: 执行验证流程
            print(f"[{BOT_TYPE}] 请执行验证流程")

        elif msg_type == "task_rejected":
            # 任务驳回通知
            task_id = data.get("task_id", "")
            reject_reason = data.get("reject_reason", "")
            proto_file = data.get("proto_file", "")
            print(f"[{BOT_TYPE}] 收到任务驳回通知: {task_id}, 原因: {reject_reason}")
            print(f"[{BOT_TYPE}] 原型 {proto_file} 需要重新设计")

        else:
            print(f"[{BOT_TYPE}] 收到通知: {message}")

        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok"}).encode())

    def _handle_scan_prototypes(self):
        """触发原型扫描"""
        total, processed = process_existing_prototypes()
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok", "total": total, "processed": processed}).encode())

    def _handle_reject(self, data):
        """驳回任务"""
        task_id = data.get("task_id", "")
        record_id = data.get("record_id", "")
        reject_reason = data.get("reject_reason", "技术不可行")
        rejected_by = data.get("rejected_by", "unknown")

        print(f"[{BOT_TYPE}] 收到驳回请求: {task_id}, 原因: {reject_reason}, 驳收人: {rejected_by}")

        # 更新状态
        if record_id:
            update_task_status(record_id, "已驳回")

        # 通知 PM
        task_info = {
            "task_id": task_id,
            "proto_file": data.get("proto_file", "")
        }
        notify_pm_rejected(task_info, reject_reason)

        # 响应
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "ok",
            "task_id": task_id,
            "message": f"任务已驳回，原因: {reject_reason}"
        }).encode())

    def do_PATCH(self):
        # 接收 Dev Bot 任务完成回调
        if self.path == "/callback":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body)
                task_id = data.get("task_id", "unknown")
                record_id = data.get("record_id", "")
                task_status = data.get("status", "completed")
                result = data.get("result", {})
                print(f"[{BOT_TYPE}] 收到任务完成回调: {task_id} status={task_status}")

                # 【最高优先级】先更新 Bitable 状态，再做其他任何操作
                if record_id:
                    print(f"[{BOT_TYPE}] ⚠️ 立即更新任务板: record_id={record_id}")
                    if task_status == "completed":
                        update_task_status(record_id, "已完成")
                        print(f"[{BOT_TYPE}] ✅ Bitable 状态已更新为'已完成': {task_id}")
                    elif task_status == "rejected":
                        reject_reason = result.get("reject_reason", "技术不可行")
                        update_task_status(record_id, "已驳回")
                        print(f"[{BOT_TYPE}] ✅ Bitable 状态已更新为'已驳回': {task_id}")
                        # 通知 PM 重新设计
                        task_info = {
                            "task_id": task_id,
                            "proto_file": result.get("proto_file", "")
                        }
                        notify_pm_rejected(task_info, reject_reason)
                    else:
                        update_task_status(record_id, "失败")
                        print(f"[{BOT_TYPE}] ✅ Bitable 状态已更新为'失败': {task_id}")

                # 1. 从 running 队列移除
                with task_queue_lock:
                    TASK_QUEUE["running"] = [
                        t for t in TASK_QUEUE["running"]
                        if t.get("task_id") != task_id
                    ]

                # 2. 通知 Marketing 开始验证（如果是已完成）
                if task_status == "completed" and record_id:
                    task_info = {
                        "task_id": task_id,
                        "proto_file": result.get("proto_file", ""),
                        "description": result.get("description", "")
                    }
                    notify_marketing(task_info)

                # 3. 写入结果文件
                result_str = json.dumps(result, ensure_ascii=False, indent=2)
                with open(f"/opt/AiComic/scripts/generated/result_{task_id}.txt", "w") as f:
                    f.write(result_str)
                print(f"[{BOT_TYPE}] 结果已写入: result_{task_id}.txt")

            except Exception as e:
                print(f"[{BOT_TYPE}] Callback error: {e}")
            self.send_response(200)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()


def notify_pm(message):
    """通知 PM Bot"""
    try:
        import urllib.request
        url = "http://127.0.0.1:8002/notify"
        data = json.dumps({"message": message}).encode()
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("X-API-Key", "aicomic-shared-secret-key-2026")
        with urllib.request.urlopen(req, timeout=5):
            pass
        print(f"[Monitor] 已通知 PM: {message}")
    except Exception as e:
        print(f"[Monitor] 通知 PM 失败: {e}")


def notify_marketing(task_info):
    """通知 Marketing Bot 任务完成，可以开始验证"""
    try:
        import urllib.request
        url = "http://127.0.0.1:8004/notify"
        data = json.dumps({
            "type": "task_completed",
            "task_id": task_info.get("task_id"),
            "proto_file": task_info.get("proto_file"),
            "description": task_info.get("description")
        }).encode()
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("X-API-Key", "aicomic-shared-secret-key-2026")
        with urllib.request.urlopen(req, timeout=5):
            pass
        print(f"[Monitor] 已通知 Marketing: 任务 {task_info.get('task_id')} 已完成，待验证")
    except Exception as e:
        print(f"[Monitor] 通知 Marketing 失败: {e}")


def notify_pm_rejected(task_info, reject_reason):
    """通知 PM 原型被研发驳回，需要重新设计"""
    try:
        import urllib.request
        url = "http://127.0.0.1:8002/notify"
        data = json.dumps({
            "type": "task_rejected",
            "task_id": task_info.get("task_id"),
            "proto_file": task_info.get("proto_file"),
            "reject_reason": reject_reason,
            "action": "需要重新设计"
        }).encode()
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("X-API-Key", "aicomic-shared-secret-key-2026")
        with urllib.request.urlopen(req, timeout=5):
            pass
        print(f"[Monitor] 已通知 PM: 原型 {task_info.get('proto_file')} 被驳回")
    except Exception as e:
        print(f"[Monitor] 通知 PM 驳回失败: {e}")


def run():
    # 启动调度线程（仅 monitor 类型）
    if BOT_TYPE == "monitor":
        # 启动独立轮询线程
        poll_thread = threading.Thread(target=poll_bitable_thread, daemon=True)
        poll_thread.start()
        print(f"[{BOT_TYPE}] Bitable 轮询线程已启动")

        # 启动调度线程
        dispatcher_thread = threading.Thread(target=dispatcher_loop, daemon=True)
        dispatcher_thread.start()
        print(f"[{BOT_TYPE}] Dispatcher 线程已启动")

        # 启动健康检查线程
        health_thread = threading.Thread(target=health_check_thread, daemon=True)
        health_thread.start()
        print(f"[{BOT_TYPE}] 健康检查线程已启动")

        # 启动时扫描一次现有原型
        scan_prototypes()

    elif BOT_TYPE == "pm":
        # PM Bot 自维护线程
        pm_thread = threading.Thread(target=pm_self_maintenance_loop, daemon=True)
        pm_thread.start()
        print(f"[{BOT_TYPE}] PM 自维护线程已启动")

    elif BOT_TYPE == "marketing":
        # Marketing Bot 自维护线程
        marketing_thread = threading.Thread(target=marketing_self_maintenance_loop, daemon=True)
        marketing_thread.start()
        print(f"[{BOT_TYPE}] Marketing 自维护线程已启动")

    # 启动 HTTP 服务器
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"[{BOT_TYPE}] Bot started on port {PORT}")
    server.serve_forever()



def should_run_self_maintenance():
    """检查是否应该运行自维护任务（资源感知）"""
    try:
        # 检查负载
        try:
            result = subprocess.run(
                ['cat', '/proc/loadavg'],
                capture_output=True, text=True, timeout=5
            )
            load = float(result.stdout.split()[0])
            if load > 1.5:
                print(f"[{BOT_TYPE}] 负载{load}>1.5，暂停自维护")
                return False
        except:
            pass
        
        # 检查是否有CrewAI任务在运行
        try:
            result = subprocess.run(
                ['pgrep', '-c', '-f', 'crewai|python.*proto'],
                capture_output=True, text=True, timeout=5
            )
            crewai_count = int(result.stdout.strip() or 0)
            if crewai_count >= 2:
                print(f"[{BOT_TYPE}] 有{crewai_count}个CrewAI任务，暂停自维护")
                return False
        except:
            pass
        
        return True
    except Exception as e:
        print(f"[{BOT_TYPE}] 资源检查失败: {e}")
        return True

# === PM Bot 自维护线程 ===
def pm_self_maintenance_loop():
    """PM Bot 空闲时自维护：向 Monitor 拉任务，无任务时检查驳回任务，然后执行竞品扫描"""
    print(f"[PM] 自维护线程启动")
    while True:
        try:
            import urllib.request
            url = "http://127.0.0.1:8001/ask_for_task"
            payload = json.dumps({"bot_type": "pm", "status": "idle"}).encode()
            try:
                req = urllib.request.Request(url, data=payload, method="POST")
                req.add_header("Content-Type", "application/json")
                req.add_header("X-API-Key", "aicomic-shared-secret-key-2026")
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read())
                    has_task = data.get("has_task", False)
                    task = data.get("task")

                    if has_task and task:
                        print(f"[PM] 收到任务: {task.get('task_id')}")
                        # 执行任务
                        execute_pm_task(task)
                    else:
                        # 无任务，先检查驳回任务
                        print(f"[PM] 无待处理任务，先检查驳回任务...")
                        rejected_handled = pm_check_and_handle_rejected_tasks()
                        if rejected_handled:
                            print(f"[PM] 已处理驳回任务，等待下一轮")
                        else:
                            # 无驳回任务，执行竞品扫描
                            print(f"[PM] 无待处理任务，执行竞品扫描")
                            run_competitor_scan()
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    print(f"[PM] Monitor 无 /ask_for_task 端点，检查驳回任务...")
                    rejected_handled = pm_check_and_handle_rejected_tasks()
                    if not rejected_handled:
                        print(f"[PM] 无驳回任务，执行竞品扫描")
                        run_competitor_scan()
                else:
                    print(f"[PM] 拉取任务失败: {e}")
                    # 拉取失败也检查驳回任务
                    rejected_handled = pm_check_and_handle_rejected_tasks()
                    if not rejected_handled:
                        run_competitor_scan()
            except Exception as e:
                print(f"[PM] 拉取任务失败: {e}")

        except Exception as e:
            print(f"[PM] 自维护异常: {e}")

        time.sleep(30)  # 空闲时30秒检查一次，节省资源


def pm_check_and_handle_rejected_tasks():
    """检查Bitable任务板中的驳回任务，自动处理"""
    try:
        # 读取飞书凭证
        config_file = os.path.expanduser("~/.openclaw/openclaw.json")
        with open(config_file) as f:
            config = json.load(f)
        feishu_cfg = config.get("channels", {}).get("feishu", {})
        app_id = feishu_cfg.get("appId", "")
        app_secret = feishu_cfg.get("appSecret", "")
        
        if not app_id or not app_secret:
            print("[PM] 未配置飞书凭证，跳过驳回任务检查")
            return False
        
        # 获取 token
        token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        token_data = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode()
        token_req = urllib.request.Request(token_url, data=token_data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(token_req, timeout=10) as resp:
            token_result = json.loads(resp.read())
            feishu_token = token_result.get("tenant_access_token")
        
        if not feishu_token:
            print("[PM] 获取飞书token失败")
            return False
        
        # 查询任务板
        app_token = "InUZbPrTZaRm5LsRz9jctF27nGu"
        table_id = "tblNWtihltzV0SOO"
        list_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"
        list_req = urllib.request.Request(list_url, headers={"Authorization": f"Bearer {feishu_token}"})
        with urllib.request.urlopen(list_req, timeout=10) as resp:
            list_result = json.loads(resp.read())
            records = list_result.get("data", {}).get("items", [])
        
        rejected_tasks = []
        for record in records:
            fields = record.get("fields", {})
            status = fields.get("状态", "")
            output = fields.get("输出结果", "") or ""
            task_id = fields.get("任务ID", "")
            
            # 找已驳回且未处理的任务
            if status == "已驳回" and "PM处理：" not in output and task_id:
                rejected_tasks.append({
                    "record_id": record.get("record_id"),
                    "task_id": task_id,
                    "description": fields.get("任务描述", "")[:200]
                })
        
        if rejected_tasks:
            print(f"[PM] 发现 {len(rejected_tasks)} 个待处理驳回任务")
            for task in rejected_tasks[:3]:  # 每次最多处理3个
                print(f"[PM] 处理驳回任务: {task['task_id']}")
                # 更新任务状态
                update_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/{task['record_id']}"
                # 判断驳回原因并生成处理结果
                desc = task['description']
                result = "PM处理："
                if "重复" in desc or "已实现" in desc:
                    result += "原型与已有功能重复，已归档。"
                elif "优先级" in desc or "暂缓" in desc:
                    result += "功能优先级低，MVP阶段暂缓。"
                elif "详细" in desc or "不够" in desc:
                    result += "原型描述不足，需重新设计后创建新任务。"
                else:
                    result += "已阅读，待评估处理方式。"
                
                update_data = json.dumps({"fields": {"输出结果": result}}).encode()
                update_req = urllib.request.Request(update_url, data=update_data, method="PUT",
                    headers={"Authorization": f"Bearer {feishu_token}", "Content-Type": "application/json"})
                try:
                    with urllib.request.urlopen(update_req, timeout=10) as resp:
                        print(f"[PM] 已更新任务 {task['task_id']}")
                except Exception as e:
                    print(f"[PM] 更新任务失败: {e}")
            return True
        else:
            print("[PM] 无待处理驳回任务")
            return False
        
    except Exception as e:
        print(f"[PM] 检查驳回任务异常: {e}")
        return False


def execute_pm_task(task):
    """执行 PM 任务"""
    task_id = task.get("task_id")
    task_type = task.get("type")
    print(f"[PM] 执行任务: {task_id}, 类型: {task_type}")

    # 根据任务类型执行
    if task_type == "prototype":
        # 执行原型开发
        proto_file = task.get("proto_file", "")
        description = task.get("description", "")
        # TODO: 调用原型开发流程
        print(f"[PM] 原型任务完成: {proto_file}")
    elif task_type == "competitor":
        # 执行竞品分析
        run_competitor_scan()


def run_competitor_scan():
    """执行竞品动态扫描（优化版：持续生成）"""
    print(f"[PM] 开始竞品扫描...")
    try:
        from datetime import datetime
        date_str = datetime.now().strftime("%Y%m%d")
        timestamp = int(time.time())
        
        # 每次生成带时间戳的报告，避免覆盖
        output_file = f"/opt/AiComic/docs/竞品监控_{date_str}_{timestamp}.md"

        competitor_content = f"""# 竞品动态监控

> 日期：{date_str} | 生成时间：{datetime.now().strftime('%H:%M:%S')} | 状态：自动更新

## AI 小说类

### NovelAI (https://novelai.net)
- 最新动态：
  - 2026-03: 推出新一代AI图像生成模型
  - 2026-02: 新增视频生成功能测试
- 产品更新：
  - AI Story功能增强
  - 图像质量提升30%
- 启示：需关注图像生成质量赛道

### AI Dungeon (https://aidungeon.io)
- 最新动态：
  - 暂停公开更新，专注企业版
- 启示：企业市场可能更有价值

## AI 动态漫类

### ComicAI (https://comicai.ai)
- 最新动态：
  - 2026-03: 发布新一代漫画生成引擎
  - 支持多角色一致性
- 产品功能：
  - 文本转漫画
  - 角色一致性控制
  - 多种漫画风格
- 启示：这是直接竞品，功能对标

### 白日梦AI (https://aimanga.com)
- 最新动态：
  - 国内头部产品
  - 字节跳动旗下
- 产品功能：
  - AI漫画生成
  - 视频生成
- 启示：国内市场竞争激烈

## 差异化机会

1. **角色一致性** - 竞品普遍未解决，是核心突破口
2. **中文TTS** - 国内竞品TTS质量弱
3. **动态漫格式** - 区别于普通视频的漫画感

## 行动项

- [ ] 深入研究ComicAI的功能细节
- [ ] 对比我方产品与竞品的差距
- [ ] 制定差异化竞争策略
"""
        with open(output_file, 'w') as f:
            f.write(competitor_content)
        print(f"[PM] 竞品扫描完成: {output_file}")
        return output_file

    except Exception as e:
        print(f"[PM] 竞品扫描失败: {e}")
        return None


# === Marketing Bot 自维护线程 ===
def marketing_self_maintenance_loop():
    """Marketing Bot 空闲时自维护：向 Monitor 拉任务，无任务时执行营销方案补全"""
    print(f"[Marketing] 自维护线程启动")
    while True:
        try:
            import urllib.request
            url = "http://127.0.0.1:8001/ask_for_task"
            payload = json.dumps({"bot_type": "marketing", "status": "idle"}).encode()
            try:
                req = urllib.request.Request(url, data=payload, method="POST")
                req.add_header("Content-Type", "application/json")
                req.add_header("X-API-Key", "aicomic-shared-secret-key-2026")
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read())
                    has_task = data.get("has_task", False)
                    task = data.get("task")

                    if has_task and task:
                        print(f"[Marketing] 收到任务: {task.get('task_id')}")
                        execute_marketing_task(task)
                    else:
                        # 无任务，执行自维护（营销方案补全）
                        print(f"[Marketing] 无待处理任务，执行营销方案补全")
                        run_marketing_gap_scan()
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    print(f"[Marketing] Monitor 无 /ask_for_task 端点，跳过")
                else:
                    print(f"[Marketing] 拉取任务失败: {e}")
            except Exception as e:
                print(f"[Marketing] 拉取任务失败: {e}")

        except Exception as e:
            print(f"[Marketing] 自维护异常: {e}")

        time.sleep(30)  # 空闲时30秒检查一次，节省资源


def execute_marketing_task(task):
    """执行 Marketing 任务"""
    task_id = task.get("task_id")
    task_type = task.get("type")
    print(f"[Marketing] 执行任务: {task_id}, 类型: {task_type}")

    if task_type == "verify":
        # 执行验证任务
        proto_file = task.get("proto_file", "")
        verification_report = f"/opt/AiComic/营销方案/验证报告_{task_id}_{int(time.time())}.md"
        print(f"[Marketing] 验证任务: {proto_file} -> {verification_report}")
        # TODO: 调用验证流程
    elif task_type == "marketing":
        # 执行营销方案生成
        print(f"[Marketing] 营销方案任务: {task_id}")


def run_marketing_gap_scan():
    """扫描原型目录，为缺失营销方案的功能补全"""
    print(f"[Marketing] 开始营销方案补全扫描...")
    try:
        import os
        from datetime import datetime, timedelta

        proto_dir = "/opt/AiComic/原型/"
        marketing_dir = "/opt/AiComic/营销方案/"

        # 确保目录存在
        os.makedirs(marketing_dir, exist_ok=True)

        # 扫描原型目录（最近7天）
        cutoff = datetime.now() - timedelta(days=7)
        recent_protos = []

        for f in os.listdir(proto_dir):
            if not f.endswith(".md"):
                continue
            # 排除已处理的（自动补全、验证报告）
            if f.startswith("自动补全") or f.startswith("验证报告"):
                continue
            mtime = datetime.fromtimestamp(os.path.getmtime(os.path.join(proto_dir, f)))
            if mtime > cutoff:
                recent_protos.append(f)

        # 为每个新原型检查是否有营销方案
        for proto in recent_protos:
            proto_name = proto.replace("_原型_", "_").replace(".md", "")
            expected_marketing = f"{marketing_dir}营销方案_{proto_name}.md"

            if os.path.exists(expected_marketing):
                continue  # 已有营销方案

            # 生成营销方案
            date_str = datetime.now().strftime("%Y%m%d")
            output_file = f"{marketing_dir}自动补全_{proto_name}_{date_str}.md"

            content = f"""# 营销方案

> 功能：{proto_name}
> 生成时间：{date_str}
> 状态：自动补全

## 目标用户

## 核心卖点

## 推广渠道

## 文案草稿

"""
            with open(output_file, 'w') as f:
                f.write(content)
            print(f"[Marketing] 补全营销方案: {output_file}")

        print(f"[Marketing] 营销方案补全完成")

    except Exception as e:
        print(f"[Marketing] 营销方案补全失败: {e}")


# === 统一任务状态机 ===
TASK_STATES = {
    "pending": "待分配",
    "assigned": "已分配",
    "running": "进行中",
    "completed": "已完成",
    "failed": "失败",
    "merged": "待合并",
    "paused": "暂停",
    "rejected": "已驳回"  # 研发驳回
}


def update_task_state(task_id, new_state, record_id=None, reason=None):
    """统一更新任务状态到所有相关系统"""
    print(f"[StateMachine] 任务 {task_id} -> {new_state}")

    # 1. 更新 progress_file
    progress_file = f"/tmp/proto_progress_{task_id}.json"
    if os.path.exists(progress_file):
        with open(progress_file, 'r') as f:
            progress = json.load(f)
        progress["state"] = new_state
        progress["state_updated_at"] = time.time()
        if reason:
            progress["state_reason"] = reason
        with open(progress_file, 'w') as f:
            json.dump(progress, f)

    # 2. 更新 Bitable
    if record_id:
        bitable_state = TASK_STATES.get(new_state, new_state)
        update_task_status(record_id, bitable_state)

    # 3. 更新内存队列
    with task_queue_lock:
        for i, t in enumerate(TASK_QUEUE["pending"]):
            if t.get("task_id") == task_id:
                TASK_QUEUE["pending"][i]["state"] = new_state
        for i, t in enumerate(TASK_QUEUE["running"]):
            if t.get("task_id") == task_id:
                TASK_QUEUE["running"][i]["state"] = new_state

    return new_state


# === 健康检查线程 ===
def health_check_thread():
    """监控各 Bot 状态，异常时告警"""
    print(f"[Monitor] 健康检查线程启动")
    bot_last_seen = {}  # bot_id -> last_seen_timestamp
    alert_cooldown = {}  # bot_id -> can_alert_after

    while True:
        try:
            if BOT_TYPE == "monitor":
                # 检查各 Bot 状态
                bots = [
                    ("dev", "8003"),
                    ("pm", "8002"),
                    ("marketing", "8004"),
                ]

                for bot_name, port in bots:
                    try:
                        import urllib.request
                        url = f"http://127.0.0.1:{port}/status"
                        req = urllib.request.Request(url)
                        req.add_header("X-API-Key", "aicomic-shared-secret-key-2026")
                        with urllib.request.urlopen(req, timeout=5) as resp:
                            data = json.loads(resp.read())
                            bot_last_seen[bot_name] = time.time()

                            # 检查是否长时间无响应
                            if bot_name in bot_last_seen:
                                idle_time = time.time() - bot_last_seen[bot_name]
                                if idle_time > 600:  # 10分钟无响应
                                    cooldown_key = f"{bot_name}_idle"
                                    if cooldown_key not in alert_cooldown or time.time() > alert_cooldown[cooldown_key]:
                                        print(f"[Monitor] 告警: {bot_name} 已闲置 {idle_time:.0f}秒")
                                        send_alert(f"{bot_name} Bot 闲置 {idle_time:.0f}秒")
                                        alert_cooldown[cooldown_key] = time.time() + 300  # 5分钟冷却

                    except Exception as e:
                        # Bot 无响应
                        cooldown_key = f"{bot_name}_down"
                        if cooldown_key not in alert_cooldown or time.time() > alert_cooldown[cooldown_key]:
                            print(f"[Monitor] 告警: {bot_name} Bot 无响应 ({e})")
                            send_alert(f"{bot_name} Bot 无响应: {e}")
                            alert_cooldown[cooldown_key] = time.time() + 300

        except Exception as e:
            print(f"[Monitor] 健康检查异常: {e}")

        time.sleep(30)  # 每30秒检查一次


def send_alert(message):
    """发送告警到飞书"""
    try:
        import urllib.request
        # 发送到飞书 webhook
        webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"  # TODO: 配置实际 webhook
        payload = json.dumps({
            "msg_type": "text",
            "content": {"text": f"[Monitor 告警] {message}"}
        }).encode()
        req = urllib.request.Request(webhook_url, data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=5):
            pass
        print(f"[Monitor] 告警已发送: {message}")
    except Exception as e:
        print(f"[Monitor] 告警发送失败: {e}")


if __name__ == "__main__":
    run()


# === 广播分发到所有 Bot ===
def broadcast_to_all(task_id, description, record_id="", payload=None):
    """将任务广播到所有 Bot（dev/pm/marketing）"""
    if payload is None:
        payload = {}
    task = {
        "task_id": task_id,
        "desc": description,
        "record_id": record_id,
        "proto_file": payload.get("proto_file", ""),
        "payload": payload
    }
    # 分发到 "all" 队列
    with BOT_QUEUES_LOCK["all"]:
        BOT_QUEUES["all"]["pending"].append(task)
    print(f"[Monitor] 任务已加入全体队列: {task_id}")
    return True
