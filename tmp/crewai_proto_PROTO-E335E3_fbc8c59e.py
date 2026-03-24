#!/usr/bin/env python3
"""CrewAI Prototype Task - PROTO-E335E3"""
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

task_description = "【原型文件】数据统计原型_20260324.md\n【参考路径】/opt/AiComic/原型/数据统计原型_20260324.md\n\n【一、背景与目标】\n\n### 背景\n运营团队需要数据支持决策，用户需要了解创作趋势。\n\n### 目标\n- 展示用户创作数据\n- 展示平台运营数据\n- 提供数据导出功能\n\n---\n\n\n【二、功能清单】\n\n| 序号 | 功能点 | 描述 | 优先级 |\n|------|--------|------|--------|\n| 1 | 创作统计 | 生成数量、趋势图 | P1 |\n| 2 | 用户行为 | 留存、转化分析 | P2 |\n| 3 | 内容分析 | 热门风格、角色 | P2 |\n| 4 | 收益分析 | 付费、订阅 | P2 |\n\n---\n\n\n【四、验收标准】\n\n- [ ] 展示用户创作统计数据\n- [ ] 展示趋势图表\n- [ ] 支持导出报表\n\n---\n\n*产品经理机器人产出 · 2026-03-24*\n\n【原始任务描述】\n实现原型功能"

task = Task(
    description=task_description,
    agent=engineer,
    expected_output='Complete code implementation with git commit'
)

crew = Crew(agents=[engineer], tasks=[task], process=Process.sequential, verbose=True)
result = crew.kickoff()
with open('/opt/AiComic/scripts/generated/proto_result_fbc8c59e.result', 'w') as f:
    f.write(str(result))