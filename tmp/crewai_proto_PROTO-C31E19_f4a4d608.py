#!/usr/bin/env python3
"""CrewAI Prototype Task - PROTO-C31E19"""
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

task_description = "【原型文件】用户引导原型_20260324.md\n【参考路径】/opt/AiComic/原型/用户引导原型_20260324.md\n\n【一、背景与目标】\n\n### 背景\n竞品分析显示，用户上手难度是重要痛点。需要设计友好的新手引导流程，帮助用户快速理解产品价值。\n\n### 目标\n- 降低用户上手门槛\n- 引导用户完成首次创作\n- 提升用户留存率\n\n---\n\n\n【二、功能清单】\n\n| 序号 | 功能点 | 描述 | 优先级 |\n|------|--------|------|--------|\n| 1 | 新手引导页 | 产品介绍和核心价值 | P0 |\n| 2 | 角色创建引导 | 一步步创建第一个角色 | P0 |\n| 3 | 首次生成引导 | 引导用户完成首次漫画生成 | P0 |\n| 4 | 教程中心 | 视频/图文教程 | P1 |\n| 5 | 示例作品 | 展示优秀案例 | P1 |\n\n---\n\n\n【四、验收标准】\n\n- [ ] 新用户首次访问时显示引导页\n- [ ] 用户可以一步步创建第一个角色\n- [ ] 用户可以完成首次漫画生成\n- [ ] 教程中心提供视频/图文教程\n\n---\n\n*产品经理机器人产出 · 2026-03-24*\n\n【原始任务描述】\n实现原型功能"

task = Task(
    description=task_description,
    agent=engineer,
    expected_output='Complete code implementation with git commit'
)

crew = Crew(agents=[engineer], tasks=[task], process=Process.sequential, verbose=True)
result = crew.kickoff()
with open('/opt/AiComic/scripts/generated/proto_result_f4a4d608.result', 'w') as f:
    f.write(str(result))