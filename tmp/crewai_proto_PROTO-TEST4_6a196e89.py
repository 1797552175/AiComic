#!/usr/bin/env python3
"""CrewAI Prototype Task - PROTO-TEST4"""
import os
import sys
os.environ['OPENAI_API_KEY'] = os.environ.get('MINIMAX_API_KEY', '')

from crewai import Agent, Task, Crew, Process
from crewai.llm import LLM
from crewai.tools import BaseTool

llm = LLM(model='openai/MiniMax-M2.7-highspeed', is_litellm=True, api_key=os.environ.get('MINIMAX_API_KEY', ''))

class ShellTool(BaseTool):
    name: str = 'shell'
    description: str = 'Execute shell command'

    def _run(self, cmd: str):
        import subprocess
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60, cwd='/opt/AiComic')
        return result.stdout + result.stderr

shell = ShellTool()

# Backend Engineer Agent
backend = Agent(role='Backend Engineer', goal='Implement API endpoints and database models', backstory='5 years FastAPI experience', verbose=True, llm=llm, tools=[shell])

# Frontend Engineer Agent
frontend = Agent(role='Frontend Engineer', goal='Implement UI components', backstory='5 years React experience', verbose=True, llm=llm, tools=[shell])

# DevOps Agent
devops = Agent(role='DevOps Engineer', goal='Write tests and ensure deployable', backstory='3 years CI/CD experience', verbose=True, llm=llm, tools=[shell])

task_description = '''【原型文件】故事编辑器原型_20260324.md
【参考路径】/opt/AiComic/原型/故事编辑器原型_20260324.md

【一、背景与目标】

### 背景
NovelAI有成熟的故事编辑器，支持分章节管理和角色关系图谱。借鉴其设计，我方需要故事编辑器来管理漫画剧本。

### 目标
- 支持多章节剧本管理
- 支持角色关系图谱
- 支持分镜与剧本同步

---


【二、功能清单】

| 序号 | 功能点 | 描述 | 优先级 |
|------|--------|------|--------|
| 1 | 章节管理 | 创建/编辑/删除章节 | P0 |
| 2 | 剧本编辑 | 编写分镜剧本内容 | P0 |
| 3 | 角色引用 | 在剧本中引用角色卡 | P0 |
| 4 | 关系图谱 | 可视化角色关系 | P1 |
| 5 | 导出/导入 | 支持JSON格式导出 | P2 |

---


【四、验收标准】

- [ ] 用户可以创建/编辑/删除章节
- [ ] 用户可以在剧本中引用角色卡
- [ ] 用户可以查看角色关系图谱

---

*产品经理机器人产出 · 2026-03-24*

【原始任务描述】
实现原型功能'''

task1 = Task(description=task_description + '\n\n[Backend] Write code in /opt/AiComic/apps/backend/', agent=backend, expected_output='Backend code created')
task2 = Task(description=task_description + '\n\n[Frontend] Write code in /opt/AiComic/apps/frontend/', agent=frontend, expected_output='Frontend code created')
task3 = Task(description='Write tests. Run tests. Git add/commit/push.', agent=devops, expected_output='Tests pass and code pushed')

crew = Crew(agents=[backend, frontend, devops], tasks=[task1, task2, task3], verbose=True)
result = crew.kickoff()
with open('/opt/AiComic/scripts/generated/proto_result_6a196e89.result', 'w') as f:
    f.write(str(result))