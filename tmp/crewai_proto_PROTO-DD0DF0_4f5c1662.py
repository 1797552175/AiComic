#!/usr/bin/env python3
"""CrewAI Prototype Task - PROTO-DD0DF0"""
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
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60, cwd='/opt/AiComic')
        return result.stdout + result.stderr

shell = ShellTool()

# Backend Engineer Agent
backend = Agent(role='Backend Engineer', goal='Implement API endpoints and database models', backstory='5 years FastAPI experience', verbose=True, llm=llm, tools=[shell])

# Frontend Engineer Agent
frontend = Agent(role='Frontend Engineer', goal='Implement UI components', backstory='5 years React experience', verbose=True, llm=llm, tools=[shell])

# DevOps Agent
devops = Agent(role='DevOps Engineer', goal='Write tests and ensure deployable', backstory='3 years CI/CD experience', verbose=True, llm=llm, tools=[shell])

task_description = '''【原型文件】角色一致性功能原型_20260324.md
【参考路径】/opt/AiComic/原型/角色一致性功能原型_20260324.md

【一、背景与目标】

### 背景
竞品分析显示，**角色一致性是用户最强需求**，也是行业共同难题。Leinad、NovelAI等竞品均未完全解决该问题，这是我方核心差异化突破点。

### 目标
- 用户创建角色后，在不同场景/动作下保持外观一致
- 支持角色换装、换场景、换表情但保持身份识别
- 降低创作门槛，无需每次重新描述角色外观

---


【二、功能清单】

| 序号 | 功能点 | 描述 | 优先级 |
|------|--------|------|--------|
| 1 | 角色卡创建 | 上传参考图，AI提取角色特征 | P0 |
| 2 | 角色特征描述 | 自动生成角色文字描述供编辑 | P0 |
| 3 | 角色一致性生成 | 基于角色卡生成新图像 | P0 |
| 4 | 角色库管理 | 创建/编辑/删除/收藏角色 | P1 |
| 5 | 角色变体 | 同一角色不同服装/发型/姿态 | P2 |

---


【原始任务描述】
实现原型功能'''

task1 = Task(description=task_description + '\n\n[Backend] Write code in /opt/AiComic/apps/backend/', agent=backend, expected_output='Backend code created')
task2 = Task(description=task_description + '\n\n[Frontend] Write code in /opt/AiComic/apps/frontend/', agent=frontend, expected_output='Frontend code created')
task3 = Task(description='Write tests. Run tests. Git add/commit/push.', agent=devops, expected_output='Tests pass and code pushed')

crew = Crew(agents=[backend, frontend, devops], tasks=[task1, task2, task3], verbose=True)
result = crew.kickoff()
with open('/opt/AiComic/scripts/generated/proto_result_4f5c1662.result', 'w') as f:
    f.write(str(result))