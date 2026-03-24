#!/usr/bin/env python3
"""
原型开发任务: 音效配乐
Task ID: PROTO-DEV-006
"""

import os
import sys
import re
import subprocess

sys.path.insert(0, '/opt/AiComic/scripts')
from common import TaskOutput, save_output, ensure_dir

import litellm

CONFIG = {
    "task_name": "音效配乐",
    "output_dir": "/opt/AiComic/scripts/output/",
    "project_root": "/opt/AiComic",
    "model": "MiniMax-M2.7-highspeed",
    "author": "Claude",
    "commit_message": None,
}

litellm.drop_params = True

PROTOTYPE_CONTENT = """
# 音效与配乐功能原型

> 版本：v1.0 | 日期：2026-03-24 | 状态：待评审

---

## 一、背景与目标

### 背景
漫画不仅是视觉内容，配乐和音效能极大提升作品表现力。竞品较少涉足此领域，是差异化机会。

### 目标
- 支持背景音乐选择
- 支持音效添加
- 与漫画分镜同步

---

## 二、功能清单

| 序号 | 功能点 | 描述 | 优先级 |
|------|--------|------|--------|
| 1 | 背景音乐 | 选择/上传BGM | P2 |
| 2 | 音效库 | 预置音效素材 | P2 |
| 3 | 音画同步 | 音乐与分镜同步播放 | P2 |

---

## 三、界面原型描述

### 音效设置面板

```
┌─────────────────────────────────────────────────────────────┐
│ 音效设置                                              [×] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ 背景音乐：                                                 │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ [选择音乐 ▼]  [上传音乐]                           │ │
│ │ 当前：happy_ambient.mp3  [▶] [停止]               │ │
│ │ 音量：○────●────○  80%                           │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                             │
│ 音效：                                                    │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 场景切换：[选择音效 ▼]  [▶]                       │ │
│ │ 对话框：[选择音效 ▼]  [▶]                        │ │
│ │ 背景音：[选择音效 ▼]  [▶]                        │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│           [取消]                        [应用到作品]       │
└─────────────────────────────────────────────────────────────┘
```

---

## 四、验收标准

- [ ] 用户可以选择背景音乐
- [ ] 用户可以添加音效
- [ ] 音画同步播放正常

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
    task_id = "PROTO-DEV-006"
    print(f"开始执行任务: {task_id} - 音效配乐")
    
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
        task_name="音效配乐",
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
