#!/usr/bin/env python3
"""CrewAI Prototype Task - PROTO-01FABD"""
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

task_description = '''【原型文件】权限与安全原型_20260324.md
【参考路径】/opt/AiComic/原型/权限与安全原型_20260324.md

【一、背景与目标】

保障用户账号安全，提供完善的权限管理功能。

### 目标
- 账号安全保护
- 隐私设置
- 访问权限控制

---


【二、功能清单】

| 序号 | 功能点 | 描述 | 优先级 |
|------|--------|------|--------|
| 1 | 修改密码 | 密码修改 | P0 |
| 2 | 两步验证 | 2FA认证 | P1 |
| 3 | 登录日志 | 查看登录记录 | P1 |
| 4 | 隐私设置 | 作品可见性 | P2 |
| 5 | 第三方授权 | OAuth管理 | P2 |

---


【四、验收标准】

- [ ] 用户可以修改密码
- [ ] 用户可以开启两部验证
- [ ] 用户可以查看登录日志
- [ ] 用户可以设置隐私选项

---

*产品经理机器人产出 · 2026-03-24*

【原始任务描述】
实现原型功能'''

task1 = Task(description=task_description + '\n\n[Backend] Write code in /opt/AiComic/apps/backend/', agent=backend, expected_output='Backend code created')
task2 = Task(description=task_description + '\n\n[Frontend] Write code in /opt/AiComic/apps/frontend/', agent=frontend, expected_output='Frontend code created')
task3 = Task(description='Write tests. Run tests. Git add/commit/push.', agent=devops, expected_output='Tests pass and code pushed')

crew = Crew(agents=[backend, frontend, devops], tasks=[task1, task2, task3], verbose=True)
result = crew.kickoff()
with open('/opt/AiComic/scripts/generated/proto_result_a160ab65.result', 'w') as f:
    f.write(str(result))