#!/usr/bin/env python3
"""CrewAI Prototype Task - PROTO-AC456C"""
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

task_description = "【原型文件】新手任务体系原型_20260324.md\n【参考路径】/opt/AiComic/原型/新手任务体系原型_20260324.md\n\n【一、背景与目标】\n\n参考Duolingo、游戏化的任务体系设计，提升用户活跃度和留存。\n\n### 目标\n- 引导用户完成首次创作\n- 提升用户活跃度\n- 增加产品趣味性\n\n---\n\n\n【二、功能清单】\n\n| 序号 | 功能点 | 描述 | 优先级 |\n|------|--------|------|--------|\n| 1 | 每日任务 | 每日创作任务 | P1 |\n| 2 | 成就系统 | 解锁成就徽章 | P1 |\n| 3 | 经验值 | 创作获取经验 | P2 |\n| 4 | 等级系统 | 用户成长体系 | P2 |\n\n---\n\n\n【四、验收标准】\n\n- [ ] 每日任务正确显示和刷新\n- [ ] 任务完成正确奖励经验值\n- [ ] 成就徽章正确解锁\n- [ ] 用户等级正确提升\n\n---\n\n*产品经理机器人产出 · 2026-03-24*\n\n【原始任务描述】\n实现原型功能"

task = Task(
    description=task_description,
    agent=engineer,
    expected_output='Complete code implementation with git commit'
)

crew = Crew(agents=[engineer], tasks=[task], process=Process.sequential, verbose=True)
result = crew.kickoff()
with open('/opt/AiComic/scripts/generated/proto_result_96d12f0f.result', 'w') as f:
    f.write(str(result))