#!/usr/bin/env python3
"""
原型开发任务: 分享与导出
Task ID: PROTO-DEV-011
"""

import os
import sys
import re
import subprocess

sys.path.insert(0, '/opt/AiComic/scripts')
from common import TaskOutput, save_output, ensure_dir

import litellm

CONFIG = {
    "task_name": "分享与导出",
    "output_dir": "/opt/AiComic/scripts/output/",
    "project_root": "/opt/AiComic",
    "model": "MiniMax-M2.7-highspeed",
    "author": "Claude",
    "commit_message": None,
}

litellm.drop_params = True

PROTOTYPE_CONTENT = """
# 分享与导出功能原型

> 版本：v1.0 | 日期：2026-03-25 | 状态：待评审
> 预估工作量：1.5小时

---

## 一、背景与目标

用户完成创作后需要分享到社交媒体或导出本地。参考剪映的分享设计。

### 目标
- 支持多种格式导出
- 一键分享到社交平台
- 生成可嵌入的分享链接

---

## 二、功能清单

| 序号 | 功能点 | 描述 | 优先级 |
|------|--------|------|--------|
| 1 | 导出格式选择 | PNG序列/MP4/PDF/GIF | P0 |
| 2 | 导出进度 | 显示导出进度条 | P0 |
| 3 | 社交分享 | 微信/微博/抖音分享 | P1 |
| 4 | 分享链接 | 生成本站可查看链接 | P1 |
| 5 | 二维码 | 生成手机扫码预览 | P2 |
| 6 | 嵌入代码 | 生成可嵌入的iframe | P2 |

---

## 三、分享弹窗设计

```
┌─────────────────────────────────┐
│  分享与导出                      │
├─────────────────────────────────┤
│  导出格式：                      │
│  ○ PNG序列  ○ MP4  ○ PDF  ○ GIF │
│                                 │
│  视频设置：                      │
│  分辨率：1080p ▼                │
│  帧率：30fps ▼                  │
│                                 │
│  [        导出        ]         │
├─────────────────────────────────┤
│  分享到：                        │
│  [微博] [微信] [抖音] [复制链接] │
└─────────────────────────────────┘
```

---

## 四、技术实现

- 导出使用后端异步任务
- WebSocket推送导出进度
- 分享链接基于项目ID生成，无需登录查看
- 社交分享使用平台原生SDK

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
    task_id = "PROTO-DEV-011"
    print(f"开始执行任务: {task_id} - 分享与导出")
    
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
        task_name="分享与导出",
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
