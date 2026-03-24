#!/usr/bin/env python3
"""CrewAI Prototype Task - PROTO-6F2A02"""
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

task_description = 'Implement prototype: 【原型文件】分镜时间线原型_20260324.md
【参考路径】/opt/AiComic/原型/分镜时间线原型_20260324.md

【一、背景与目标】

### 背景
竞品分析显示，Leinad有镜头运动预设功能。我方需要支持分镜时间线编辑，让用户精细控制每个分镜。

### 目标
- 支持分镜时间线可视化
- 支持拖拽调整分镜顺序
- 支持调整分镜时长

---


【原始任务描述】
实现原型功能'
task = Task(description=task_description, agent=coder, expected_output='Code and git commit')

crew = Crew(agents=[coder], tasks=[task], process=Process.sequential, verbose=True)
result = crew.kickoff()
with open('_opt_AiComic_scripts_generated_proto_result_717eb6ee.result', 'w') as f:
    f.write(str(result))