#!/usr/bin/env python3
"""
原型开发任务: 数据统计
Task ID: PROTO-DEV-009
"""

import os
import sys
import re
import subprocess

sys.path.insert(0, '/opt/AiComic/scripts')
from common import TaskOutput, save_output, ensure_dir

import litellm

CONFIG = {
    "task_name": "数据统计",
    "output_dir": "/opt/AiComic/scripts/output/",
    "project_root": "/opt/AiComic",
    "model": "MiniMax-M2.7-highspeed",
    "author": "Claude",
    "commit_message": None,
}

litellm.drop_params = True

PROTOTYPE_CONTENT = """
# 数据统计与运营分析原型

> 版本：v1.0 | 日期：2026-03-24 | 状态：待评审

---

## 一、背景与目标

### 背景
运营团队需要数据支持决策，用户需要了解创作趋势。

### 目标
- 展示用户创作数据
- 展示平台运营数据
- 提供数据导出功能

---

## 二、功能清单

| 序号 | 功能点 | 描述 | 优先级 |
|------|--------|------|--------|
| 1 | 创作统计 | 生成数量、趋势图 | P1 |
| 2 | 用户行为 | 留存、转化分析 | P2 |
| 3 | 内容分析 | 热门风格、角色 | P2 |
| 4 | 收益分析 | 付费、订阅 | P2 |

---

## 三、界面原型描述

### 数据统计页面

```
┌─────────────────────────────────────────────────────────────┐
│ 数据统计                                    [导出报表]       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  概览：                                                    │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐          │
│  │ 总用户 │ │ 今日生成│ │ 付费用户│ │ 总收入 │          │
│  │ 12,345 │ │   567  │ │   234  │ │ ¥45,678│          │
│  └────────┘ └────────┘ └────────┘ └────────┘          │
│                                                             │
│  生成趋势：                                                 │
│  ┌─────────────────────────────────────────────────┐   │
│  │     📈                                        │   │
│  │   567                                        │   │
│  │  456    ╱╲                                  │   │
│  │ 345  ╱    ╲  ╱╲                            │   │
│  │ 234╱        ╲╱  ╲                          │   │
│  │──────────────────────────────────────────────│   │
│  │  周一  周二  周三  周四  周五  周六  周日   │   │
│  └─────────────────────────────────────────────────┘   │
│                                                             │
│  热门风格：日漫 68%  国漫 22%  美漫 10%               │
└─────────────────────────────────────────────────────────────┘
```

---

## 四、验收标准

- [ ] 展示用户创作统计数据
- [ ] 展示趋势图表
- [ ] 支持导出报表

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
    task_id = "PROTO-DEV-009"
    print(f"开始执行任务: {task_id} - 数据统计")
    
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
        task_name="数据统计",
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
