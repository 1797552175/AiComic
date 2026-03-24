#!/usr/bin/env python3
"""CrewAI Prototype Task - PROTO-549862"""
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

task_description = 'Implement prototype: 【原型文件】分镜控制功能原型_20260324.md
【参考路径】/opt/AiComic/原型/分镜控制功能原型_20260324.md

【一、背景与目标】

### 背景
竞品分析显示，Leinad新增了"镜头运动预设"功能。分镜控制是动态漫区别于普通视频的关键差异点，也是我方产品特色。

### 目标
- 用户可以控制每个分镜的镜头类型（推/拉/摇/移/跟）
- 支持镜头角度（正面/侧面/背面/特写）
- 支持镜头运动轨迹描述

---


【二、功能清单】

| 序号 | 功能点 | 描述 | 优先级 |
|------|--------|------|--------|
| 1 | 镜头类型选择 | 预设镜头运动类型 | P0 |
| 2 | 镜头角度控制 | 切换视角和景别 | P0 |
| 3 | 运动轨迹描述 | 自然语言描述镜头运动 | P1 |
| 4 | 分镜时间线 | 拖拽调整分镜顺序和时长 | P2 |

---


【四、验收标准】

- [ ] 用户可以切换镜头类型（推/拉/摇/移/跟）
- [ ] 用户可以切换镜头角度（正/侧/背/特写）
- [ ] 分镜预览能体现所选镜头效果

---


【原始任务描述】
实现原型功能'
task = Task(description=task_description, agent=coder, expected_output='Code and git commit')

crew = Crew(agents=[coder], tasks=[task], process=Process.sequential, verbose=True)
result = crew.kickoff()
with open('_opt_AiComic_scripts_generated_proto_result_6d65d7ce.result', 'w') as f:
    f.write(str(result))