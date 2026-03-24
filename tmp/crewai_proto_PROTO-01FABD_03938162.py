#!/usr/bin/env python3
"""CrewAI Prototype Task - PROTO-01FABD"""
import os
import sys
os.environ['OPENAI_API_KEY'] = os.environ.get('MINIMAX_API_KEY', '')

from crewai import Agent, Task, Crew, Process
from crewai.llm import LLM
from crewai.tools import BaseTool

llm = LLM(model='openai/MiniMax-M2.7-highspeed', is_litellm=True, api_key=os.environ.get('MINIMAX_API_KEY', ''))

# Shell command tool
class ShellTool(BaseTool):
    name: str = 'shell'
    description: str = 'Execute shell command'

    def _run(self, cmd: str):
        import subprocess
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60, cwd='/opt/AiComic')
        return result.stdout + result.stderr

shell = ShellTool()

# Agent
coder = Agent(role='Python Engineer', goal='Implement code based on prototype description', backstory='10 years Python experience, expert in FastAPI', verbose=True, llm=llm, tools=[shell])

task_description = 'Implement prototype: 【原型文件】权限与安全原型_20260324.md
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
实现原型功能'
task = Task(description=task_description, agent=coder, expected_output='Code and git commit')

crew = Crew(agents=[coder], tasks=[task], process=Process.sequential, verbose=True)
result = crew.kickoff()
with open('_opt_AiComic_scripts_generated_proto_result_03938162.result', 'w') as f:
    f.write(str(result))