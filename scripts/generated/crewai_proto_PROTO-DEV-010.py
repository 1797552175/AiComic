#!/usr/bin/env python3
"""
原型开发任务: 权限与安全
Task ID: PROTO-DEV-010
"""

import os
import sys
import re
import subprocess

sys.path.insert(0, '/opt/AiComic/scripts')
from common import TaskOutput, save_output, ensure_dir

import litellm

CONFIG = {
    "task_name": "权限与安全",
    "output_dir": "/opt/AiComic/scripts/output/",
    "project_root": "/opt/AiComic",
    "model": "MiniMax-M2.7-highspeed",
    "author": "Claude",
    "commit_message": None,
}

litellm.drop_params = True

PROTOTYPE_CONTENT = """
# 权限与安全设置原型

> 版本：v1.0 | 日期：2026-03-24 | 状态：待评审

---

## 一、背景与目标

保障用户账号安全，提供完善的权限管理功能。

### 目标
- 账号安全保护
- 隐私设置
- 访问权限控制

---

## 二、功能清单

| 序号 | 功能点 | 描述 | 优先级 |
|------|--------|------|--------|
| 1 | 修改密码 | 密码修改 | P0 |
| 2 | 两步验证 | 2FA认证 | P1 |
| 3 | 登录日志 | 查看登录记录 | P1 |
| 4 | 隐私设置 | 作品可见性 | P2 |
| 5 | 第三方授权 | OAuth管理 | P2 |

---

## 三、界面原型描述

### 3.1 安全设置

```
┌─────────────────────────────────────────────────────────────┐
│ 安全设置                                         [×]      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  密码设置：                                               │
│  当前密码：[______________]                               │
│  新密码：   [______________]                               │
│  确认密码：[______________]                               │
│                                                             │
│              [修改密码]                                    │
│                                                             │
│  ───────────────────────────────────────                   │
│                                                             │
│  两步验证：                                               │
│  ┌─────────────────────────────────────────────────┐   │
│  │ ☑ 开启两步验证                                    │   │
│  │   └─ 绑定 Google Authenticator               │   │
│  └─────────────────────────────────────────────────┘   │
│                                                             │
│  ───────────────────────────────────────                   │
│                                                             │
│  登录日志：                                               │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 📱 iPhone  北京  2026-03-24 10:00  当前      │   │
│  │ 💻 Windows  上海  2026-03-23 15:30           │   │
│  │ 📱 Android  深圳  2026-03-22 09:15           │   │
│  └─────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 隐私设置

```
┌─────────────────────────────────────────────────────────────┐
│ 隐私设置                                         [×]      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  作品可见性：                                             │
│  ○ 公开  ● 私密  ○ 仅粉丝                           │
│                                                             │
│  个人资料可见性：                                         │
│  ☑ 在作品中被识别                                       │
│  ☑ 被其他用户搜索到                                     │
│  ☐ 显示在线状态                                         │
│                                                             │
│  数据使用：                                               │
│  ☑ 允许分析数据以优化产品                              │
│  ☐ 接收个性化广告                                      │
│                                                             │
│              [保存设置]                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 四、验收标准

- [ ] 用户可以修改密码
- [ ] 用户可以开启两部验证
- [ ] 用户可以查看登录日志
- [ ] 用户可以设置隐私选项

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
    task_id = "PROTO-DEV-010"
    print(f"开始执行任务: {task_id} - 权限与安全")
    
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
        task_name="权限与安全",
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
