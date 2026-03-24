#!/usr/bin/env python3
"""从飞书任务板读取待分配任务"""
import urllib.request
import urllib.error
import json
import os
import time

# 读取 OpenClaw 配置获取飞书凭证
CONFIG_FILE = os.path.expanduser("~/.openclaw/openclaw.json")
APP_TOKEN = "InUZbPrTZaRm5LsRz9jctF27nGu"
TABLE_ID = "tblNWtihltzV0SOO"

def get_feishu_token():
    """获取飞书 tenant_access_token"""
    try:
        with open(CONFIG_FILE) as f:
            config = json.load(f)
        feishu_cfg = config.get("channels", {}).get("feishu", {})
        app_id = feishu_cfg.get("appId", "")
        app_secret = feishu_cfg.get("appSecret", "")
        
        if not app_id or not app_secret:
            print("未找到飞书凭证")
            return None
        
        # 获取 tenant_access_token
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        data = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            if result.get("code") == 0:
                return result.get("tenant_access_token")
            else:
                print(f"获取token失败: {result}")
                return None
    except Exception as e:
        print(f"获取token异常: {e}")
        return None

def list_bitable_records(token):
    """获取任务板记录"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("data", {}).get("items", [])
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code}")
        return []
    except Exception as e:
        print(f"Error: {e}")
        return []

def main():
    # 获取 token
    token = get_feishu_token()
    if not token:
        print("无法获取飞书访问令牌")
        return
    
    # 获取记录
    records = list_bitable_records(token)
    pending_tasks = []
    
    for item in records:
        fields = item.get("fields", {})
        status = fields.get("状态", "")
        
        # 处理 SingleSelect 类型
        if isinstance(status, list) and len(status) > 0:
            status = status[0].get("text", "") if isinstance(status[0], dict) else str(status[0])
        elif isinstance(status, dict):
            status = status.get("text", "")
        
        # 只取"待分配"或"待领取"状态
        if "待分配" in str(status) or "待领取" in str(status):
            task_id = str(fields.get("任务ID", ""))
            desc = str(fields.get("任务描述", ""))
            
            # 支持 TODO-* 和 PROTO-* 任务
            if task_id and desc and ("TODO-" in task_id or "PROTO-" in task_id):
                # 从描述中提取原型文件路径
                proto_file = ""
                if "参考：" in desc or "参考路径：" in desc:
                    import re
                    match = re.search(r'参考[：:]([^\n]+)', desc)
                    if match:
                        path = match.group(1).strip()
                        # 提取文件名
                        fname_match = re.search(r'([^/]+\.md)', path)
                        if fname_match:
                            proto_file = fname_match.group(1)
                        else:
                            proto_file = path.split('/')[-1]

                pending_tasks.append({
                    "task_id": task_id,
                    "type": "dev",
                    "desc": desc,
                    "proto_file": proto_file,
                    "record_id": item.get("record_id", "")
                })
    
    # 输出到临时文件
    output = {
        "timestamp": time.time(),
        "tasks": pending_tasks,
        "count": len(pending_tasks)
    }
    
    output_file = "/opt/AiComic/tmp/bitable_pending_tasks.json"
    with open(output_file, "w") as f:
        json.dump(output, f, ensure_ascii=False)
    
    print(f"找到 {len(pending_tasks)} 个待分配任务")
    for t in pending_tasks:
        print(f"  - {t['task_id']}: {t['desc'][:60]}")

if __name__ == "__main__":
    main()
