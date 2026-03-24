#!/usr/bin/env python3
"""CrewAI Prototype Task - PROTO-969B65"""
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

task_description = "【原型文件】版本历史原型_20260324.md\n【参考路径】/opt/AiComic/原型/版本历史原型_20260324.md\n\n【一、背景与目标】\n\n参考Notion、Google Docs的版本历史设计，提供内容版本管理和协作功能。\n\n### 目标\n- 追踪内容变更历史\n- 支持版本回滚\n- 多人协作编辑\n\n---\n\n\n【二、功能清单】\n\n| 序号 | 功能点 | 描述 | 优先级 |\n|------|--------|------|--------|\n| 1 | 版本历史 | 查看内容变更记录 | P1 |\n| 2 | 版本回滚 | 回滚到指定版本 | P2 |\n| 3 | 协作编辑 | 多人同时编辑 | P2 |\n| 4 | 评论系统 | 在内容中添加评论 | P2 |\n\n---\n\n\n【四、验收标准】\n\n- [ ] 用户可以查看版本历史\n- [ ] 用户可以回滚到指定版本\n- [ ] 协作编辑状态正确显示\n- [ ] 多人同时编辑不冲突\n\n---\n\n*产品经理机器人产出 · 2026-03-24*\n\n【原始任务描述】\n实现原型功能"

# 4 concurrent tasks
task1 = Task(description='[Frontend1] ' + task_description, agent=frontend1, expected_output='React components created')
task2 = Task(description='[Frontend2] ' + task_description, agent=frontend2, expected_output='State management done')
task3 = Task(description='[Backend] ' + task_description, agent=backend, expected_output='API endpoints created')
task4 = Task(description='[DevOps] ' + task_description, agent=devops, expected_output='Tests pass and code pushed')

crew = Crew(agents=[frontend1, frontend2, backend, devops], tasks=[task1, task2, task3, task4], verbose=True)
result = crew.kickoff()
with open('/opt/AiComic/scripts/generated/proto_result_50806bac.result', 'w') as f:
    f.write(str(result))