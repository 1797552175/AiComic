#!/usr/bin/env python3
"""CrewAI Prototype Task - PROTO-3D5945"""
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

task_description = "【原型文件】AI创作动态漫功能原型_20260322.md\n【参考路径】/opt/AiComic/原型/AI创作动态漫功能原型_20260322.md\n\n【原始任务描述】\n实现原型功能"

task = Task(
    description=task_description,
    agent=engineer,
    expected_output='Complete code implementation with git commit'
)

crew = Crew(agents=[engineer], tasks=[task], process=Process.sequential, verbose=True)
result = crew.kickoff()
with open('/opt/AiComic/scripts/generated/proto_result_fb125a88.result', 'w') as f:
    f.write(str(result))