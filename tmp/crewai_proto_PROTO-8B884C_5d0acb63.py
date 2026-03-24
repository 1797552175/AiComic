#!/usr/bin/env python3
"""CrewAI Prototype Task - PROTO-8B884C"""
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

task_description = 'Implement prototype: 【原型文件】性能优化原型_20260324.md
【参考路径】/opt/AiComic/原型/性能优化原型_20260324.md

【一、背景与目标】

参考Linear、Vercel的错误处理设计，提供良好的性能监控和错误处理体验。

### 目标
- 实时性能监控
- 友好的错误提示
- 优雅的加载状态

---


【二、功能清单】

| 序号 | 功能点 | 描述 | 优先级 |
|------|--------|------|--------|
| 1 | 加载状态 | 优雅的loading动画 | P0 |
| 2 | 错误页面 | 友好的错误提示 | P0 |
| 3 | 性能监控 | 加载时间统计 | P1 |
| 4 | 重试机制 | 失败自动重试 | P1 |

---


【四、验收标准】

- [ ] 加载状态显示正确
- [ ] 错误页面友好显示
- [ ] 性能数据正确统计
- [ ] 重试机制正常工作

---

*产品经理机器人产出 · 2026-03-24*

【原始任务描述】
实现原型功能'
task = Task(description=task_description, agent=coder, expected_output='Code and git commit')

crew = Crew(agents=[coder], tasks=[task], process=Process.sequential, verbose=True)
result = crew.kickoff()
with open('_opt_AiComic_scripts_generated_proto_result_5d0acb63.result', 'w') as f:
    f.write(str(result))