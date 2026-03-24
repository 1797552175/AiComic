#!/usr/bin/env python3
"""
原型开发任务: 分镜控制
Task ID: PROTO-DEV-007
"""

import os
import sys
import re
import subprocess

sys.path.insert(0, '/opt/AiComic/scripts')
from common import TaskOutput, save_output, ensure_dir

import litellm

CONFIG = {
    "task_name": "分镜控制",
    "output_dir": "/opt/AiComic/scripts/output/",
    "project_root": "/opt/AiComic",
    "model": "MiniMax-M2.7-highspeed",
    "author": "Claude",
    "commit_message": None,
}

litellm.drop_params = True

PROTOTYPE_CONTENT = """
# 分镜控制功能原型

> 版本：v1.0 | 日期：2026-03-24 | 状态：待评审

---

## 一、背景与目标

### 背景
竞品分析显示，Leinad新增了"镜头运动预设"功能。分镜控制是动态漫区别于普通视频的关键差异点，也是我方产品特色。

### 目标
- 用户可以控制每个分镜的镜头类型（推/拉/摇/移/跟）
- 支持镜头角度（正面/侧面/背面/特写）
- 支持镜头运动轨迹描述

---

## 二、功能清单

| 序号 | 功能点 | 描述 | 优先级 |
|------|--------|------|--------|
| 1 | 镜头类型选择 | 预设镜头运动类型 | P0 |
| 2 | 镜头角度控制 | 切换视角和景别 | P0 |
| 3 | 运动轨迹描述 | 自然语言描述镜头运动 | P1 |
| 4 | 分镜时间线 | 拖拽调整分镜顺序和时长 | P2 |

---

## 三、界面原型描述

### 3.1 分镜控制面板

**布局：**
```
┌─────────────────────────────────────────────────────────────┐
│ 分镜控制                                                  [×] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  当前分镜：第 1 镜                                         │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                                                     │   │
│  │              分镜预览区域                           │   │
│  │                                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  镜头类型：                                                 │
│  ┌────┐┌────┐┌────┐┌────┐┌────┐┌────┐                 │
│  │静止││推进││拉远││摇镜││平移││跟随│                 │
│  └────┘└────┘└────┘└────┘└────┘└────┘                 │
│                                                             │
│  镜头角度：                                                 │
│  ┌────┐┌────┐┌────┐┌────┐                             │
│  │正面││侧面││背面││特写│                             │
│  └────┘└────┘└────┘└────┘                             │
│                                                             │
│  运动描述：                                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 镜头从左向右缓慢移动...                             │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│           [上一镜]    [下一镜]         [应用并关闭]         │
└─────────────────────────────────────────────────────────────┘
```

---

## 四、验收标准

- [ ] 用户可以切换镜头类型（推/拉/摇/移/跟）
- [ ] 用户可以切换镜头角度（正/侧/背/特写）
- [ ] 分镜预览能体现所选镜头效果

---

## 五、不做事项

- ❌ 不做分镜时间线编辑（后续版本）
- ❌ 不做自定义运动轨迹（仅预设类型）

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
    task_id = "PROTO-DEV-007"
    print(f"开始执行任务: {task_id} - 分镜控制")
    
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
        task_name="分镜控制",
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
