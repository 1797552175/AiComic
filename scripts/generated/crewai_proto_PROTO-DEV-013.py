#!/usr/bin/env python3
"""
原型开发任务: 个人中心完善
Task ID: PROTO-DEV-013
"""

import os
import sys
import re
import subprocess

sys.path.insert(0, '/opt/AiComic/scripts')
from common import TaskOutput, save_output, ensure_dir

import litellm

CONFIG = {
    "task_name": "个人中心完善",
    "output_dir": "/opt/AiComic/scripts/output/",
    "project_root": "/opt/AiComic",
    "model": "MiniMax-M2.7-highspeed",
    "author": "Claude",
    "commit_message": None,
}

litellm.drop_params = True

PROTOTYPE_CONTENT = """
# 个人中心完善原型

> 版本：v1.0 | 日期：2026-03-25 | 状态：待评审
> 预估工作量：1.5小时

---

## 一、背景与目标

用户管理个人账号、会员权益、创作统计等。

### 目标
- 账号信息安全
- 会员权益可视化
- 创作数据展示

---

## 二、功能清单

| 序号 | 功能点 | 描述 | 优先级 |
|------|--------|------|--------|
| 1 | 账号信息 | 头像/昵称/邮箱/手机 | P0 |
| 2 | 修改密码 | 密码修改/忘记密码 | P0 |
| 3 | 会员信息 | 当前等级/到期时间 | P0 |
| 4 | 创作统计 | 作品数/分享数/获赞数 | P1 |
| 5 | 会员升级 | 升级套餐/续费 | P1 |
| 6 | 账号安全 | 登录日志/设备管理 | P2 |

---

## 三、页面结构

### 个人中心页（/profile）
```
┌─────────────────────────────────────────┐
│  👤 个人中心                    [保存]  │
├─────────────────────────────────────────┤
│  头像：[上传]                           │
│  昵称：[______________]                 │
│  邮箱：[______________] [验证]          │
│  手机：[______________] [更换]          │
│                                         │
│  ── 会员信息 ──                         │
│  当前等级：Pro  ¥29/月                  │
│  到期时间：2026-04-25                   │
│  [升级] [续费]                          │
│                                         │
│  ── 创作统计 ──                         │
│  作品总数：12  分享次数：34  获赞：128 │
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
    task_id = "PROTO-DEV-013"
    print(f"开始执行任务: {task_id} - 个人中心完善")
    
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
        task_name="个人中心完善",
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
