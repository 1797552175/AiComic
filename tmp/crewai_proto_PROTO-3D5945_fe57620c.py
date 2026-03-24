#!/usr/bin/env python3
"""CrewAI Prototype Task - PROTO-3D5945"""
import os
import sys
os.environ['OPENAI_API_KEY'] = os.environ.get('MINIMAX_API_KEY', '')

from crewai import Agent, Task, Crew
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

# 2 Frontend Engineers
frontend1 = Agent(role='Frontend Engineer 1', goal='Implement UI components in React', backstory='5 years React experience', verbose=True, llm=llm, tools=[shell])
frontend2 = Agent(role='Frontend Engineer 2', goal='Implement UI state management and API integration', backstory='5 years React experience', verbose=True, llm=llm, tools=[shell])

# 1 Backend Engineer
backend = Agent(role='Backend Engineer', goal='Implement FastAPI endpoints and database models', backstory='5 years Python/FastAPI experience', verbose=True, llm=llm, tools=[shell])

# 1 DevOps Engineer
devops = Agent(role='DevOps Engineer', goal='Write tests and ensure deployable', backstory='3 years CI/CD experience', verbose=True, llm=llm, tools=[shell])

task_description = "【原型文件】AI创作动态漫功能原型_20260322.md\n【参考路径】/opt/AiComic/原型/AI创作动态漫功能原型_20260322.md\n\n【原始任务描述】\n实现原型功能"

# 4 concurrent tasks
task1 = Task(description='[Frontend1] ' + task_description, agent=frontend1, expected_output='React components created')
task2 = Task(description='[Frontend2] ' + task_description, agent=frontend2, expected_output='State management done')
task3 = Task(description='[Backend] ' + task_description, agent=backend, expected_output='API endpoints created')
task4 = Task(description='[DevOps] ' + task_description, agent=devops, expected_output='Tests pass and code pushed')

crew = Crew(agents=[frontend1, frontend2, backend, devops], tasks=[task1, task2, task3, task4], verbose=True)
result = crew.kickoff()
with open('/opt/AiComic/scripts/generated/proto_result_fe57620c.result', 'w') as f:
    f.write(str(result))