#!/usr/bin/env python3
"""
原型开发任务: 创作模板市场
Task ID: PROTO-DEV-016
"""

import os
import sys
import re
import subprocess

sys.path.insert(0, '/opt/AiComic/scripts')
from common import TaskOutput, save_output, ensure_dir

import litellm

CONFIG = {
    "task_name": "创作模板市场",
    "output_dir": "/opt/AiComic/scripts/output/",
    "project_root": "/opt/AiComic",
    "model": "MiniMax-M2.7-highspeed",
    "author": "Claude",
    "commit_message": None,
}

litellm.drop_params = True

PROTOTYPE_CONTENT = """
# 创作模板市场原型

> 版本：v1.0 | 日期：2026-03-25 | 状态：待评审
> 预估工作量：1小时

---

## 一、背景与目标

用户提供预设模板，降低创作门槛，提升内容多样性。参考Canva模板市场。

### 目标
- 丰富的模板分类
- 快速应用到项目
- 模板创作者激励

---

## 二、模板分类

| 分类 | 示例 |
|------|------|
| 风格 | 热血少年/唯美浪漫/悬疑惊悚/古风武侠 |
| 场景 | 校园/职场/都市/奇幻 |
| 篇幅 | 单格/四格/短篇/长篇 |

---

## 三、功能清单

| 序号 | 功能点 | 描述 | 优先级 |
|------|--------|------|--------|
| 1 | 模板浏览 | 网格展示+分类筛选 | P0 |
| 2 | 模板预览 | 预览封面和内容 | P0 |
| 3 | 一键应用 | 应用模板到当前项目 | P0 |
| 4 | 模板收藏 | 收藏喜欢的模板 | P1 |
| 5 | 创作者上传 | 上传自制模板 | P2 |

---

## 四、页面结构

### 模板市场页（/templates）
```
┌─────────────────────────────────────────┐
│  🔍 搜索模板...[          ]            │
├─────────────────────────────────────────┤
│  分类：                                  │
│  [全部] [风格] [场景] [篇幅] [收藏]     │
├─────────────────────────────────────────┤
│  ┌────┐ ┌────┐ ┌────┐ ┌────┐           │
│  │img │ │img │ │img │ │img │           │
│  │    │ │    │ │    │ │    │           │
│  ├────┤ ├────┤ ├────┤ ├────┤           │
│  │热血│ │校园│ │悬疑│ │古风│           │
│  │少年│ │恋爱│ │惊悚│ │武侠│           │
│  └────┘ └────┘ └────┘ └────┘           │
└─────────────────────────────────────────┘
```

---

*产品经理机器人产出 · 2026-03-25*

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
    task_id = "PROTO-DEV-016"
    print(f"开始执行任务: {task_id} - 创作模板市场")
    
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
        task_name="创作模板市场",
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
