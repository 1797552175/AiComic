#!/usr/bin/env python3
"""CrewAI Prototype Task - PROTO-C31E19"""
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

task_description = 'Implement prototype: 【原型文件】用户引导原型_20260324.md
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
实现原型功能'
task = Task(description=task_description, agent=coder, expected_output='Code and git commit')

crew = Crew(agents=[coder], tasks=[task], process=Process.sequential, verbose=True)
result = crew.kickoff()
with open('_opt_AiComic_scripts_generated_proto_result_a543e1bb.result', 'w') as f:
    f.write(str(result))