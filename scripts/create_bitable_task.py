#!/usr/bin/env python3
"""创建飞书任务板任务"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

APP_TOKEN = "InUZbPrTZaRm5LsRz9jctF27nGu"
TABLE_ID = "tblNWtihltzV0SOO"

def get_feishu_token():
    """获取飞书 tenant_access_token"""
    config_file = os.path.expanduser("~/.openclaw/openclaw.json")
    try:
        with open(config_file) as f:
            config = json.load(f)
        feishu_cfg = config.get("channels", {}).get("feishu", {})
        app_id = feishu_cfg.get("appId", "")
        app_secret = feishu_cfg.get("appSecret", "")
        
        if not app_id or not app_secret:
            print("未找到飞书凭证", file=sys.stderr)
            return None
        
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        data = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            return result.get("tenant_access_token")
    except Exception as e:
        print(f"获取飞书token失败: {e}", file=sys.stderr)
        return None

def task_exists(token, task_id):
    """检查任务是否已存在"""
    url = "https://open.feishu.cn/open-apis/bitable/v1/apps/" + APP_TOKEN + "/tables/" + TABLE_ID + "/records?page_size=100"
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            items = result.get('data', {}).get('items', [])
            for item in items:
                if item.get('fields', {}).get('任务ID') == task_id:
                    return True
    except:
        pass
    return False


def create_task(task_id, description, source, assignee):
    """创建飞书任务"""
    token = get_feishu_token()
    if not token:
        return False

    # Check if task already exists
    if task_exists(token, task_id):
        print(f"任务 {task_id} 已存在，跳过")
        return True
        return False
    
    # 构建任务数据
    fields = {
        "任务ID": task_id,
        "任务描述": description[:500] if description else "",
        "Agent协同任务板": source,
        "分配给": assignee,
        "状态": "待领取",
    }
    
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records"
    data = json.dumps({"fields": fields}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    })
    
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            if result.get("code") == 0:
                print(f"任务创建成功: {task_id}")
                return True
            else:
                print(f"任务创建失败: {result.get('msg')}", file=sys.stderr)
                return False
    except Exception as e:
        print(f"创建任务异常: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--description", required=True)
    parser.add_argument("--source", default="prototype")
    parser.add_argument("--assignee", default="研发机器人")
    args = parser.parse_args()
    
    success = create_task(args.task_id, args.description, args.source, args.assignee)
    sys.exit(0 if success else 1)
