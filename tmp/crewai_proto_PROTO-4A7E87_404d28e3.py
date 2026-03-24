#!/usr/bin/env python3
"""CrewAI Prototype Task - PROTO-4A7E87"""
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

task_description = "【原型文件】音效配乐原型_20260324.md\n【参考路径】/opt/AiComic/原型/音效配乐原型_20260324.md\n\n【一、背景与目标】\n\n### 背景\n漫画不仅是视觉内容，配乐和音效能极大提升作品表现力。竞品较少涉足此领域，是差异化机会。\n\n### 目标\n- 支持背景音乐选择\n- 支持音效添加\n- 与漫画分镜同步\n\n---\n\n\n【二、功能清单】\n\n| 序号 | 功能点 | 描述 | 优先级 |\n|------|--------|------|--------|\n| 1 | 背景音乐 | 选择/上传BGM | P2 |\n| 2 | 音效库 | 预置音效素材 | P2 |\n| 3 | 音画同步 | 音乐与分镜同步播放 | P2 |\n\n---\n\n\n【四、验收标准】\n\n- [ ] 用户可以选择背景音乐\n- [ ] 用户可以添加音效\n- [ ] 音画同步播放正常\n\n---\n\n*产品经理机器人产出 · 2026-03-24*\n\n【原始任务描述】\n实现原型功能"

task = Task(
    description=task_description,
    agent=engineer,
    expected_output='Complete code implementation with git commit'
)

crew = Crew(agents=[engineer], tasks=[task], process=Process.sequential, verbose=True)
result = crew.kickoff()
with open('/opt/AiComic/scripts/generated/proto_result_404d28e3.result', 'w') as f:
    f.write(str(result))