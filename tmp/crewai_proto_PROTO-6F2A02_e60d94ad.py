#!/usr/bin/env python3
"""CrewAI Prototype Task - PROTO-6F2A02"""
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
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120, cwd='/opt/AiComic')
        return result.stdout + result.stderr

shell = ShellTool()

# Main Engineer Agent
engineer = Agent(
    role='Senior Full-Stack Engineer',
    goal='Implement the prototype according to the specification',
    backstory='Expert Python/React developer with 10 years experience',
    verbose=True,
    llm=llm,
    tools=[shell]
)

task_description = "【原型文件】分镜时间线原型_20260324.md\n【参考路径】/opt/AiComic/原型/分镜时间线原型_20260324.md\n\n【一、背景与目标】\n\n### 背景\n竞品分析显示，Leinad有镜头运动预设功能。我方需要支持分镜时间线编辑，让用户精细控制每个分镜。\n\n### 目标\n- 支持分镜时间线可视化\n- 支持拖拽调整分镜顺序\n- 支持调整分镜时长\n\n---\n\n\n【原始任务描述】\n实现原型功能"

task = Task(
    description=task_description,
    agent=engineer,
    expected_output='Complete code implementation with git commit'
)

crew = Crew(agents=[engineer], tasks=[task], process=Process.sequential, verbose=True)
result = crew.kickoff()
with open('/opt/AiComic/scripts/generated/proto_result_e60d94ad.result', 'w') as f:
    f.write(str(result))