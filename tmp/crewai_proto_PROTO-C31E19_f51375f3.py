#!/usr/bin/env python3
"""CrewAI Prototype Task - PROTO-C31E19"""
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

task_description = '''【原型文件】用户引导原型_20260324.md
【参考路径】/opt/AiComic/原型/用户引导原型_20260324.md

【一、背景与目标】

### 背景
竞品分析显示，用户上手难度是重要痛点。需要设计友好的新手引导流程，帮助用户快速理解产品价值。

### 目标
- 降低用户上手门槛
- 引导用户完成首次创作
- 提升用户留存率

---


【二、功能清单】

| 序号 | 功能点 | 描述 | 优先级 |
|------|--------|------|--------|
| 1 | 新手引导页 | 产品介绍和核心价值 | P0 |
| 2 | 角色创建引导 | 一步步创建第一个角色 | P0 |
| 3 | 首次生成引导 | 引导用户完成首次漫画生成 | P0 |
| 4 | 教程中心 | 视频/图文教程 | P1 |
| 5 | 示例作品 | 展示优秀案例 | P1 |

---


【四、验收标准】

- [ ] 新用户首次访问时显示引导页
- [ ] 用户可以一步步创建第一个角色
- [ ] 用户可以完成首次漫画生成
- [ ] 教程中心提供视频/图文教程

---

*产品经理机器人产出 · 2026-03-24*

【原始任务描述】
实现原型功能'''

task1 = Task(description=task_description + '\n\n[Backend] Write code in /opt/AiComic/apps/backend/', agent=backend, expected_output='Backend code created')
task2 = Task(description=task_description + '\n\n[Frontend] Write code in /opt/AiComic/apps/frontend/', agent=frontend, expected_output='Frontend code created')
task3 = Task(description='Write tests. Run tests. Git add/commit/push.', agent=devops, expected_output='Tests pass and code pushed')

crew = Crew(agents=[backend, frontend, devops], tasks=[task1, task2, task3], verbose=True)
result = crew.kickoff()
with open('/opt/AiComic/scripts/generated/proto_result_f51375f3.result', 'w') as f:
    f.write(str(result))