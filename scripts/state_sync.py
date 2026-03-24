#!/usr/bin/env python3
"""
state_sync.py - 状态同步脚本（轻量版）
负责：写入本地状态报告 + 生成通知消息
Bitable更新由各Bot通过 feishu_bitable_update_record 工具执行

用法:
  python3 state_sync.py <task_id> <status> <result> <source_bot>
"""
import sys
import os
import json
import time
import datetime

STATUS_REPORT_DIR = "/opt/AiComic/状态报告"

STATUS_META = {
    "dev_completed": {
        "dev_field": "已完成",
        "verify_field": "待验证",
        "notify": "营销机器人",
        "notify_msg": "【研发完成】task_id={task_id}，请进行功能验证",
        "notify_target": "ou_cf3d8fac7026009509fe76b372418598",
    },
    "dev_failed": {
        "dev_field": "失败",
        "verify_field": "待验证",
        "notify": None,
        "notify_msg": None,
        "notify_target": None,
    },
    "verify_passed": {
        "dev_field": "已完成",
        "verify_field": "通过",
        "notify": "状态监控机器人",
        "notify_msg": "【验证通过】task_id={task_id}，营销方案已生成，功能已追加到已上线清单",
        "notify_target": "ou_cf3d8fac7026009509fe76b372418598",
    },
    "verify_failed": {
        "dev_field": "已完成",
        "verify_field": "不通过",
        "notify": "产品经理机器人",
        "notify_msg": "【验证不通过】task_id={task_id}，不符合项：{result}",
        "notify_target": "ou_496347c383203414faf6bac57b0436e9",
    },
    "marketing_completed": {
        "dev_field": "已完成",
        "verify_field": "通过",
        "notify": None,
        "notify_msg": None,
        "notify_target": None,
    },
}


def write_status_report(task_id, status, result, source_bot):
    os.makedirs(STATUS_REPORT_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_bot = source_bot.replace(" ", "_")
    filename = f"{safe_bot}_完成_{task_id}_{ts}.json"
    filepath = os.path.join(STATUS_REPORT_DIR, filename)
    report = {
        "task_id": task_id,
        "status": status,
        "source_bot": source_bot,
        "result": result,
        "completed_at": datetime.datetime.now().isoformat(),
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return filepath


def append_to_online_features(task_id, feature_name):
    filepath = "/opt/AiComic/docs/已上线功能清单.md"
    if not os.path.exists(filepath):
        return False
    ts = datetime.datetime.now().strftime("%Y-%m-%d")
    entry = f"\n| {feature_name} | {ts} | 新功能 | 新增功能 |\n"
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(entry)
    return True


def state_sync(task_id, status, result, source_bot):
    if status not in STATUS_META:
        print(f"ERROR: 未知status: {status}")
        return None
    
    meta = STATUS_META[status]
    
    # 1. 写本地状态报告
    report_path = write_status_report(task_id, status, result, source_bot)
    print(f"✅ 状态报告: {report_path}")
    
    # 2. 验证通过 → 追加到已上线清单
    if status == "verify_passed":
        ok = append_to_online_features(task_id, task_id)  # feature_name用task_id代替，实际由调用方传入
        print(f"{'✅' if ok else '⚠️'} 已上线清单: {'成功' if ok else '失败'}")
    
    # 3. 生成通知消息
    if meta["notify"]:
        msg = meta["notify_msg"].format(task_id=task_id, result=result)
        print(f"NOTIFY|{meta['notify']}|{meta['notify_target']}|{msg}")
    
    return report_path


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print(__doc__)
        sys.exit(1)
    
    task_id = sys.argv[1]
    status = sys.argv[2]
    result = sys.argv[3]
    source_bot = sys.argv[4]
    
    state_sync(task_id, status, result, source_bot)
