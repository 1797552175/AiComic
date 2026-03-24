#!/usr/bin/env python3
"""
原型开发任务: 创作历史与作品管理
Task ID: PROTO-DEV-004
"""

import os
import sys
import re
import subprocess

sys.path.insert(0, '/opt/AiComic/scripts')
from common import TaskOutput, save_output, ensure_dir

import litellm

CONFIG = {
    "task_name": "创作历史与作品管理",
    "output_dir": "/opt/AiComic/scripts/output/",
    "project_root": "/opt/AiComic",
    "model": "MiniMax-M2.7-highspeed",
    "author": "Claude",
    "commit_message": None,
}

litellm.drop_params = True

PROTOTYPE_CONTENT = """
# 创作历史与作品管理原型

> 版本：v1.0 | 日期：2026-03-25 | 状态：待评审
> 预估工作量：2小时

---

## 一、背景与目标

用户生成漫画后需要管理、编辑、分享作品。参考NovelAI的故事管理功能，设计作品管理模块。

### 目标
- 集中管理所有创作作品
- 支持作品编辑和导出
- 支持分享和发布

---

## 二、功能清单

| 序号 | 功能点 | 描述 | 优先级 |
|------|--------|------|--------|
| 1 | 作品列表 | 卡片式展示所有作品 | P0 |
| 2 | 作品文件夹 | 支持自定义文件夹分类 | P1 |
| 3 | 作品搜索 | 标题/时间/标签搜索 | P1 |
| 4 | 作品导出 | PNG序列/MP4/PDF导出 | P0 |
| 5 | 作品分享 | 生成分享链接/二维码 | P1 |
| 6 | 批量操作 | 批量移动/删除/导出 | P2 |

---

## 三、页面结构

### 3.1 作品列表页（/works）
- 顶部：搜索框 + 筛选器（时间/格式/状态）
- 左侧：文件夹树（全部/最近/收藏/我的文件夹）
- 主体：网格卡片（缩略图+标题+时间+操作按钮）
- 卡片支持右键菜单：打开/分享/移动/删除

### 3.2 作品详情页（/work/:id）
- 预览区：大图/轮播
- 详情区：标题/描述/标签/创建时间
- 操作区：编辑/导出/分享/删除

---

## 四、数据结构

```typescript
interface Project {
  id: string;
  title: string;
  cover: string;        // 封面图
  folder_id: string;    // 所属文件夹
  status: 'draft' | 'published';
  created_at: Date;
  updated_at: Date;
  shots: Shot[];        // 分镜列表
  tags: string[];
}

interface Folder {
  id: string;
  name: string;
  parent_id: string | null;
  project_count: number;
}
```

---

## 五、API设计

| 接口 | 方法 | 描述 |
|------|------|------|
| /api/projects | GET | 获取作品列表 |
| /api/projects/:id | GET | 获取作品详情 |
| /api/projects/:id | PUT | 更新作品 |
| /api/projects/:id | DELETE | 删除作品 |
| /api/folders | GET/POST | 文件夹CRUD |
| /api/projects/:id/export | POST | 导出作品 |

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
    task_id = "PROTO-DEV-004"
    print(f"开始执行任务: {task_id} - 创作历史与作品管理")
    
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
        task_name="创作历史与作品管理",
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
