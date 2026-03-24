#!/usr/bin/env python3
"""CrewAI Prototype Task - PROTO-4A7E87"""
import os
import sys
os.environ['OPENAI_API_KEY'] = os.environ.get('MINIMAX_API_KEY', '')

from crewai import Agent, Task, Crew, Process
from crewai.llm import LLM
from crewai.tools import BaseTool

llm = LLM(model='openai/MiniMax-M2.7-highspeed', is_litellm=True, api_key=os.environ.get('MINIMAX_API_KEY', ''))

# Shell command tool
class ShellTool(BaseTool):
    name: str = 'shell'
    description: str = 'Execute shell command'

    def _run(self, cmd: str):
        import subprocess
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60, cwd='/opt/AiComic')
        return result.stdout + result.stderr

shell = ShellTool()

# Agent
coder = Agent(role='Python Engineer', goal='Implement code based on prototype description', backstory='10 years Python experience, expert in FastAPI', verbose=True, llm=llm, tools=[shell])

task_description = 'Implement prototype: 【原型文件】音效配乐原型_20260324.md
【参考路径】/opt/AiComic/原型/音效配乐原型_20260324.md

【一、背景与目标】

### 背景
漫画不仅是视觉内容，配乐和音效能极大提升作品表现力。竞品较少涉足此领域，是差异化机会。

### 目标
- 支持背景音乐选择
- 支持音效添加
- 与漫画分镜同步

---


【二、功能清单】

| 序号 | 功能点 | 描述 | 优先级 |
|------|--------|------|--------|
| 1 | 背景音乐 | 选择/上传BGM | P2 |
| 2 | 音效库 | 预置音效素材 | P2 |
| 3 | 音画同步 | 音乐与分镜同步播放 | P2 |

---


【四、验收标准】

- [ ] 用户可以选择背景音乐
- [ ] 用户可以添加音效
- [ ] 音画同步播放正常

---

*产品经理机器人产出 · 2026-03-24*

【原始任务描述】
实现原型功能'
task = Task(description=task_description, agent=coder, expected_output='Code and git commit')

crew = Crew(agents=[coder], tasks=[task], process=Process.sequential, verbose=True)
result = crew.kickoff()
with open('_opt_AiComic_scripts_generated_proto_result_6ecf987e.result', 'w') as f:
    f.write(str(result))