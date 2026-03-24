#!/usr/bin/env python3
"""CrewAI Prototype Task - PROTO-E335E3"""
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

task_description = 'Implement prototype: 【原型文件】数据统计原型_20260324.md
【参考路径】/opt/AiComic/原型/数据统计原型_20260324.md

【一、背景与目标】

### 背景
运营团队需要数据支持决策，用户需要了解创作趋势。

### 目标
- 展示用户创作数据
- 展示平台运营数据
- 提供数据导出功能

---


【二、功能清单】

| 序号 | 功能点 | 描述 | 优先级 |
|------|--------|------|--------|
| 1 | 创作统计 | 生成数量、趋势图 | P1 |
| 2 | 用户行为 | 留存、转化分析 | P2 |
| 3 | 内容分析 | 热门风格、角色 | P2 |
| 4 | 收益分析 | 付费、订阅 | P2 |

---


【四、验收标准】

- [ ] 展示用户创作统计数据
- [ ] 展示趋势图表
- [ ] 支持导出报表

---

*产品经理机器人产出 · 2026-03-24*

【原始任务描述】
实现原型功能'
task = Task(description=task_description, agent=coder, expected_output='Code and git commit')

crew = Crew(agents=[coder], tasks=[task], process=Process.sequential, verbose=True)
result = crew.kickoff()
with open('_opt_AiComic_scripts_generated_proto_result_3ac54987.result', 'w') as f:
    f.write(str(result))