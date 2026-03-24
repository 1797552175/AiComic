#!/usr/bin/env python3
"""
原型开发任务: 性能优化
Task ID: PROTO-DEV-015
"""

import os
import sys
import re
import subprocess

sys.path.insert(0, '/opt/AiComic/scripts')
from common import TaskOutput, save_output, ensure_dir

import litellm

CONFIG = {
    "task_name": "性能优化",
    "output_dir": "/opt/AiComic/scripts/output/",
    "project_root": "/opt/AiComic",
    "model": "MiniMax-M2.7-highspeed",
    "author": "Claude",
    "commit_message": None,
}

litellm.drop_params = True

PROTOTYPE_CONTENT = """
# 性能优化与错误处理原型

> 版本：v1.0 | 日期：2026-03-24 | 状态：待评审

---

## 一、背景与目标

参考Linear、Vercel的错误处理设计，提供良好的性能监控和错误处理体验。

### 目标
- 实时性能监控
- 友好的错误提示
- 优雅的加载状态

---

## 二、功能清单

| 序号 | 功能点 | 描述 | 优先级 |
|------|--------|------|--------|
| 1 | 加载状态 | 优雅的loading动画 | P0 |
| 2 | 错误页面 | 友好的错误提示 | P0 |
| 3 | 性能监控 | 加载时间统计 | P1 |
| 4 | 重试机制 | 失败自动重试 | P1 |

---

## 三、界面原型描述

### 3.1 加载状态

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│                     生成中...                              │
│                                                             │
│                     ╭──────────╮                          │
│                     │   ◐◐◐   │                          │
│                     ╰──────────╯                          │
│                                                             │
│              角色「小明」生成中...                        │
│              ████████████░░░░  75%                        │
│                                                             │
│              预计剩余时间：约 15 秒                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 错误页面

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│                     ⚠️ 出错了                              │
│                                                             │
│              生成失败，请稍后重试                          │
│                                                             │
│              错误代码：ERR_API_TIMEOUT                    │
│              错误时间：2026-03-24 10:00:23               │
│                                                             │
│              ┌──────────────────────┐                      │
│              │       重新生成       │                      │
│              └──────────────────────┘                      │
│                                                             │
│              [查看帮助]  [返回首页]                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 性能监控面板

```
┌─────────────────────────────────────────────────────────────┐
│ 性能监控                                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  页面加载：                                             │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 首页：1.2s  ████████████████░░░░  良好       │   │
│  │ 角色库：2.1s  ██████████████████░░░  一般     │   │
│  │ 生成页：5.3s  ████████████████████░  较慢    │   │
│  └─────────────────────────────────────────────────┘   │
│                                                             │
│  API响应：                                                │
│  ┌─────────────────────────────────────────────────┐   │
│  │ /api/characters: 120ms  ✓                       │   │
│  │ /api/comics/generate: 5200ms  ⚠️ 较慢         │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 四、验收标准

- [ ] 加载状态显示正确
- [ ] 错误页面友好显示
- [ ] 性能数据正确统计
- [ ] 重试机制正常工作

---

*产品经理机器人产出 · 2026-03-24*
"""

def call_llm(prompt, max_tokens=4096):
    """调用 LLM"""
    response = litellm.completion(
        model="MiniMax/MiniMax-M2.7-highspeed",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
    )
    return response["choices"][0]["message"]["content"]

def save_file(path, content):
    """保存文件"""
    ensure_dir(os.path.dirname(path))
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return path

def main():
    task_id = "PROTO-DEV-015"
    print(f"开始执行任务: {task_id} - 性能优化")
    
    # 构建提示词
    prompt = f"""
请根据以下原型文档实现功能代码：

{PROTOTYPE_CONTENT}

## 实现要求
1. 严格按照原型文档进行实现
2. 生成完整的代码文件
3. 代码必须可运行，无语法错误
4. 完成后进行 git commit

请生成代码并说明需要创建/修改的文件。
"""
    
    # 调用 LLM 生成代码
    print(f"正在调用 LLM 生成代码...")
    result = call_llm(prompt, max_tokens=8192)
    
    print(f"LLM 返回结果:")
    print(result[:500] if len(result) > 500 else result)
    
    # 保存结果
    output = TaskOutput(
        task_id=task_id,
        task_name="性能优化",
        model=CONFIG["model"],
        prompt=prompt,
        output=result,
        files_created=[],
        git_commit=None,
    )
    
    save_output(output, CONFIG["output_dir"])
    print(f"任务完成: {task_id}")
    
    return result

if __name__ == "__main__":
    main()
