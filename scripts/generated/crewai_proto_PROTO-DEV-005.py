#!/usr/bin/env python3
"""
原型开发任务: 会员订阅与支付
Task ID: PROTO-DEV-005
"""

import os
import sys
import re
import subprocess

sys.path.insert(0, '/opt/AiComic/scripts')
from common import TaskOutput, save_output, ensure_dir

import litellm

CONFIG = {
    "task_name": "会员订阅与支付",
    "output_dir": "/opt/AiComic/scripts/output/",
    "project_root": "/opt/AiComic",
    "model": "MiniMax-M2.7-highspeed",
    "author": "Claude",
    "commit_message": None,
}

litellm.drop_params = True

PROTOTYPE_CONTENT = """
# 会员订阅与支付原型

> 版本：v1.0 | 日期：2026-03-25 | 状态：待评审
> 预估工作量：2小时

---

## 一、背景与目标

AiComic需要商业化，会员订阅是核心收入模式。参考Notion、Runway的订阅设计。

### 目标
- 清晰的会员权益分层
- 便捷的订阅流程
- 安全的支付体验

---

## 二、会员体系

| 等级 | 月费 | 权益 |
|------|------|------|
| 免费 | 0 | 每月5个作品，480p导出 |
| Pro | ¥29/月 | 无限作品，1080p导出，优先队列 |
| Team | ¥99/月 | 团队协作，API访问，专属客服 |

---

## 三、功能清单

| 序号 | 功能点 | 描述 | 优先级 |
|------|--------|------|--------|
| 1 | 会员页 | 展示各等级权益对比 | P0 |
| 2 | 订阅弹窗 | 选择套餐→支付 | P0 |
| 3 | 支付方式 | 微信/支付宝/信用卡 | P0 |
| 4 | 订单历史 | 查看订阅记录 | P1 |
| 5 | 会员标识 | 头像/作品水印 | P1 |
| 6 | 取消订阅 | 管理订阅状态 | P1 |

---

## 四、页面结构

### 会员页（/pricing）
- Hero区：会员权益介绍
- 对比表：免费vs Pro vs Team
- FAQ区：常见问题
- 底部：立即订阅按钮

### 订阅弹窗
```
┌─────────────────────────────────┐
│  选择您的订阅计划                │
├─────────────────────────────────┤
│  ○ 免费    ¥0/月                │
│  ● Pro    ¥29/月 [推荐]         │
│  ○ Team   ¥99/月               │
│                                 │
│  支付方式：                      │
│  [微信] [支付宝] [信用卡]       │
│                                 │
│  [立即订阅 - ¥29/月]            │
│                                 │
│  ↩ 7天无理由退款                │
└─────────────────────────────────┘
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
    task_id = "PROTO-DEV-005"
    print(f"开始执行任务: {task_id} - 会员订阅与支付")
    
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
        task_name="会员订阅与支付",
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
