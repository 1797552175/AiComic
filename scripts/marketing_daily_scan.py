#!/usr/bin/env python3
"""
每日待研发原型清单扫描脚本
由营销机器人心跳调用
扫描功能进度表，生成待研发原型清单
"""
import requests, json, datetime

BITABLE_APP_TOKEN = "DhQubk8AMa3UbcsjnXvctqThnJg"
BITABLE_TABLE_ID = "tbliL8yWMw2p4QR9"
FEISHU_TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
FEISHU_BITABLE_URL = "https://open.feishu.cn/open-apis/bitable/v1/apps"

def get_token():
    resp = requests.post(FEISHU_TOKEN_URL, json={
        "app_id": "cli_a935f3edee78dcd1",
        "app_secret": "TiARqfojrCJYzSdSG2vP4fsINSAHFAUg"
    }, timeout=10)
    return resp.json().get("tenant_access_token", "")

def scan_ready_prototypes(token):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{FEISHU_BITABLE_URL}/{BITABLE_APP_TOKEN}/tables/{BITABLE_TABLE_ID}/records"
    resp = requests.get(url, headers=headers, timeout=10)
    if resp.status_code != 200:
        return []
    records = resp.json().get("data", {}).get("items", [])
    ready = []
    for r in records:
        fields = r.get("fields", {})
        proto_status = fields.get("原型状态", {})
        dev_status = fields.get("研发状态", {})
        # 单选返回的是对象或字符串
        if isinstance(proto_status, dict):
            proto_status_name = proto_status.get("name", "")
        else:
            proto_status_name = str(proto_status)
        if isinstance(dev_status, dict):
            dev_status_name = dev_status.get("name", "")
        else:
            dev_status_name = str(dev_status)
        if proto_status_name == "已评审" and dev_status_name == "待领取":
            name = fields.get("AiComic 功能研发进度表", "未知")
            task_id = fields.get("研发任务ID", "")
            module = fields.get("功能模块", "")
            if isinstance(module, dict):
                module = module.get("name", "")
            ready.append({"name": name, "task_id": task_id, "module": module})
    return ready

def main():
    token = get_token()
    if not token:
        print("ERROR: Failed to get token")
        return
    prototypes = scan_ready_prototypes(token)
    today = datetime.date.today().strftime("%Y-%m-%d")
    output_path = "/opt/AiComic/docs/待研发原型清单_自动推送.md"
    if prototypes:
        lines = [f"# 待研发原型清单\n", f"> 自动生成：{today} | 营销机器人\n\n"]
        lines.append(f"共 **{len(prototypes)}** 个原型已评审，等待研发：\n\n")
        lines.append("| # | 原型名称 | 功能模块 | 研发任务ID |\n")
        lines.append("|---|----------|----------|------------|\n")
        for i, p in enumerate(prototypes, 1):
            lines.append(f"| {i} | {p['name']} | {p['module']} | {p['task_id']} |\n")
        lines.append("\n---\n")
        lines.append("**请 @产品经理机器人 创建相应研发任务**\n")
    else:
        lines = [f"# 待研发原型清单\n", f"> 自动生成：{today} | 营销机器人\n\n", "✅ 目前没有待研发的原型，所有已评审原型均已在研发中。\n"]
    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"Generated: {output_path}, prototypes: {len(prototypes)}")

if __name__ == "__main__":
    main()
