#!/usr/bin/env python3
"""CrewAI Prototype Task - PROTO-549862"""
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

# 2 Backend Engineers
backend1 = Agent(role='Backend Engineer 1', goal='Implement FastAPI endpoints', backstory='5 years Python/FastAPI experience', verbose=True, llm=llm, tools=[shell])
backend2 = Agent(role='Backend Engineer 2', goal='Implement database models and SQL', backstory='5 years SQLAlchemy experience', verbose=True, llm=llm, tools=[shell])

# 1 Test Engineer
tester = Agent(role='Test Engineer', goal='Write unit tests', backstory='3 years testing experience', verbose=True, llm=llm, tools=[shell])

# 1 DevOps Engineer
devops = Agent(role='DevOps Engineer', goal='Verify code works, git commit/push', backstory='3 years CI/CD experience', verbose=True, llm=llm, tools=[shell])

task_description = "【原型文件】分镜控制功能原型_20260324.md\n【参考路径】/opt/AiComic/原型/分镜控制功能原型_20260324.md\n\n【一、背景与目标】\n\n### 背景\n竞品分析显示，Leinad新增了\"镜头运动预设\"功能。分镜控制是动态漫区别于普通视频的关键差异点，也是我方产品特色。\n\n### 目标\n- 用户可以控制每个分镜的镜头类型（推/拉/摇/移/跟）\n- 支持镜头角度（正面/侧面/背面/特写）\n- 支持镜头运动轨迹描述\n\n---\n\n\n【二、功能清单】\n\n| 序号 | 功能点 | 描述 | 优先级 |\n|------|--------|------|--------|\n| 1 | 镜头类型选择 | 预设镜头运动类型 | P0 |\n| 2 | 镜头角度控制 | 切换视角和景别 | P0 |\n| 3 | 运动轨迹描述 | 自然语言描述镜头运动 | P1 |\n| 4 | 分镜时间线 | 拖拽调整分镜顺序和时长 | P2 |\n\n---\n\n\n【四、验收标准】\n\n- [ ] 用户可以切换镜头类型（推/拉/摇/移/跟）\n- [ ] 用户可以切换镜头角度（正/侧/背/特写）\n- [ ] 分镜预览能体现所选镜头效果\n\n---\n\n\n【原始任务描述】\n实现原型功能"

# 6 concurrent tasks
task1 = Task(description='[Frontend1] ' + task_description, agent=frontend1, expected_output='React components created')
task2 = Task(description='[Frontend2] ' + task_description, agent=frontend2, expected_output='State management done')
task3 = Task(description='[Backend1] ' + task_description, agent=backend1, expected_output='API endpoints created')
task4 = Task(description='[Backend2] ' + task_description, agent=backend2, expected_output='Database models created')
task5 = Task(description='[Test] ' + task_description, agent=tester, expected_output='Tests written')
task6 = Task(description='[DevOps] ' + task_description, agent=devops, expected_output='Code git pushed')

crew = Crew(agents=[frontend1, frontend2, backend1, backend2, tester, devops], tasks=[task1, task2, task3, task4, task5, task6], verbose=True)
result = crew.kickoff()
with open('/opt/AiComic/scripts/generated/proto_result_3b6eb82b.result', 'w') as f:
    f.write(str(result))