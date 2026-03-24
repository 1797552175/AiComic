#!/usr/bin/env python3
"""
原型开发任务: 消息通知系统
Task ID: PROTO-DEV-012
"""

import os
import sys
import re
import subprocess

sys.path.insert(0, '/opt/AiComic/scripts')
from common import TaskOutput, save_output, ensure_dir

import litellm

CONFIG = {
    "task_name": "消息通知系统",
    "output_dir": "/opt/AiComic/scripts/output/",
    "project_root": "/opt/AiComic",
    "model": "MiniMax-M2.7-highspeed",
    "author": "Claude",
    "commit_message": None,
}

litellm.drop_params = True

PROTOTYPE_CONTENT = """
# 消息通知系统原型

> 版本：v1.0 | 日期：2026-03-25 | 状态：待评审
> 预估工作量：1.5小时

---

## 一、背景与目标

参考Slack、Discord等工具的通知设计，提供清晰、及时的消息通知。

### 目标
- 重要消息不遗漏
- 通知分类清晰
- 用户可自定义设置

---

## 二、通知类型

| 类型 | 触发场景 | 优先级 |
|------|---------|--------|
| 任务完成 | 作品生成/导出完成 | 高 |
| 系统公告 | 新功能/维护通知 | 中 |
| 社区互动 | 点赞/评论/关注 | 低 |
| 会员到期 | 订阅即将到期 | 高 |

---

## 三、功能清单

| 序号 | 功能点 | 描述 | 优先级 |
|------|--------|------|--------|
| 1 | 通知列表 | 分页展示所有通知 | P0 |
| 2 | 通知详情 | 点击查看完整通知 | P0 |
| 3 | 未读标记 | 红点+数字提示 | P0 |
| 4 | 标记已读 | 单条/全部标记 | P1 |
| 5 | 通知设置 | 分类开关/免打扰时段 | P1 |
| 6 | 清空通知 | 删除历史通知 | P2 |

---

## 四、页面结构

### 通知面板（下拉）
```
┌─────────────────────────────────┐
│  通知                    [设置] │
├─────────────────────────────────┤
│  ● 您的作品《xxx》已生成完成   │
│    2分钟前                   [✓]│
│                                 │
│  ○ 系统维护通知：明天凌晨停机   │
│    1小时前                    [✓]│
│                                 │
│  ● 会员即将到期，请及时续费     │
│    3小时前                   [✓]│
├─────────────────────────────────┤
│  [全部标记为已读] [查看全部]   │
└─────────────────────────────────┘
```

---

## 五、技术实现

- WebSocket实时推送
- 通知存储在数据库
- 支持WebPush（浏览器通知）
- 设置存储在用户偏好

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
    task_id = "PROTO-DEV-012"
    print(f"开始执行任务: {task_id} - 消息通知系统")
    
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
        task_name="消息通知系统",
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
