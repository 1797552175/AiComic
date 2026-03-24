#!/usr/bin/env python3
"""
原型队列执行器 - Server B 版本
"""
import os
import sys
import subprocess
import time
from datetime import datetime

sys.path.insert(0, '/opt/AiComic/scripts')
from common import TaskOutput, save_output, ensure_dir
import litellm

PROTOTYPES = [
    {"name": "MiniMax-M2.7前端", "path": "/opt/AiComic/原型/MiniMax前端实现原型_20260325.md", "id": 1},
    {"name": "AI创作动态漫", "path": "/opt/AiComic/原型/AI创作动态漫功能原型_20260322.md", "id": 2},
    {"name": "角色一致性", "path": "/opt/AiComic/原型/角色一致性功能原型_20260324.md", "id": 3},
    {"name": "创作历史与作品管理", "path": "/opt/AiComic/原型/创作历史与作品管理原型_20260325.md", "id": 4},
    {"name": "会员订阅与支付", "path": "/opt/AiComic/原型/会员订阅与支付原型_20260325.md", "id": 5},
    {"name": "音效配乐", "path": "/opt/AiComic/原型/音效配乐原型_20260324.md", "id": 6},
    {"name": "分镜控制", "path": "/opt/AiComic/原型/分镜控制功能原型_20260324.md", "id": 7},
    {"name": "新手任务体系", "path": "/opt/AiComic/原型/新手任务体系原型_20260324.md", "id": 8},
    {"name": "数据统计", "path": "/opt/AiComic/原型/数据统计原型_20260324.md", "id": 9},
    {"name": "权限与安全", "path": "/opt/AiComic/原型/权限与安全原型_20260324.md", "id": 10},
    {"name": "分享与导出", "path": "/opt/AiComic/原型/分享与导出原型_20260325.md", "id": 11},
    {"name": "消息通知系统", "path": "/opt/AiComic/原型/消息通知系统原型_20260325.md", "id": 12},
    {"name": "个人中心完善", "path": "/opt/AiComic/原型/个人中心完善原型_20260325.md", "id": 13},
    {"name": "用户引导", "path": "/opt/AiComic/原型/用户引导原型_20260324.md", "id": 14},
    {"name": "性能优化", "path": "/opt/AiComic/原型/性能优化原型_20260324.md", "id": 15},
    {"name": "创作模板市场", "path": "/opt/AiComic/原型/创作模板市场原型_20260325.md", "id": 16},
]

def call_llm(prompt, max_tokens=8192):
    response = litellm.completion(
        model="openai/MiniMax-M2.7-highspeed",
        messages=[{"role": "user", "content": prompt}],
        api_key=os.environ.get("MINIMAX_API_KEY"),
        base_url="https://api.minimax.chat/v1",
        max_tokens=max_tokens,
        temperature=0.3
    )
    return response["choices"][0]["message"]["content"]

def execute_proto(proto):
    task_id = f"PROTO-DEV-{proto['id']:03d}"
    task_name = proto['name']
    
    print(f"开始: {task_id} - {task_name}")
    
    # 读取原型内容
    with open(proto['path'], 'r', encoding='utf-8') as f:
        content = f.read()
    
    prompt = f"""请根据以下原型文档实现代码：

{content}

要求：
1. 严格按照原型文档实现
2. 生成完整可运行的代码
3. 说明需要创建/修改的文件
"""
    
    try:
        result = call_llm(prompt, max_tokens=8192)
        
        output = TaskOutput(
            task_id=task_id,
            task_name=task_name,
            model="MiniMax-M2.7-highspeed",
            prompt=prompt,
            output=result,
            files_created=[],
            git_commit=None
        )
        save_output(output, "/opt/AiComic/scripts/output/")
        print(f"完成: {task_id}")
        return True
    except Exception as e:
        print(f"失败: {task_id} - {e}")
        return False

def main():
    print("=" * 60)
    print("原型队列执行器")
    print(f"时间: {datetime.now()}")
    print(f"任务数: {len(PROTOTYPES)}")
    print("=" * 60)
    
    success = 0
    failed = 0
    
    for proto in PROTOTYPES:
        if execute_proto(proto):
            success += 1
        else:
            failed += 1
        time.sleep(1)  # 避免限流
    
    print("=" * 60)
    print(f"执行完成: 成功 {success}, 失败 {failed}")
    print("=" * 60)

if __name__ == "__main__":
    main()
