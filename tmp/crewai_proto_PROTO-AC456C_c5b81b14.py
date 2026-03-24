#!/usr/bin/env python3
"""CrewAI Prototype Task - PROTO-AC456C"""
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

task_description = 'Implement prototype: 【原型文件】新手任务体系原型_20260324.md
【参考路径】/opt/AiComic/原型/新手任务体系原型_20260324.md

【一、背景与目标】

参考Duolingo、游戏化的任务体系设计，提升用户活跃度和留存。

### 目标
- 引导用户完成首次创作
- 提升用户活跃度
- 增加产品趣味性

---


【二、功能清单】

| 序号 | 功能点 | 描述 | 优先级 |
|------|--------|------|--------|
| 1 | 每日任务 | 每日创作任务 | P1 |
| 2 | 成就系统 | 解锁成就徽章 | P1 |
| 3 | 经验值 | 创作获取经验 | P2 |
| 4 | 等级系统 | 用户成长体系 | P2 |

---


【四、验收标准】

- [ ] 每日任务正确显示和刷新
- [ ] 任务完成正确奖励经验值
- [ ] 成就徽章正确解锁
- [ ] 用户等级正确提升

---

*产品经理机器人产出 · 2026-03-24*

【原始任务描述】
实现原型功能'
task = Task(description=task_description, agent=coder, expected_output='Code and git commit')

crew = Crew(agents=[coder], tasks=[task], process=Process.sequential, verbose=True)
result = crew.kickoff()
with open('_opt_AiComic_scripts_generated_proto_result_c5b81b14.result', 'w') as f:
    f.write(str(result))