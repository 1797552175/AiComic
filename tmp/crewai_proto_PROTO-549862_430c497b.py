#!/usr/bin/env python3
"""CrewAI Prototype Task - PROTO-549862"""
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

task_description = "【原型文件】分镜控制功能原型_20260324.md\n【参考路径】/opt/AiComic/原型/分镜控制功能原型_20260324.md\n\n【一、背景与目标】\n\n### 背景\n竞品分析显示，Leinad新增了\"镜头运动预设\"功能。分镜控制是动态漫区别于普通视频的关键差异点，也是我方产品特色。\n\n### 目标\n- 用户可以控制每个分镜的镜头类型（推/拉/摇/移/跟）\n- 支持镜头角度（正面/侧面/背面/特写）\n- 支持镜头运动轨迹描述\n\n---\n\n\n【二、功能清单】\n\n| 序号 | 功能点 | 描述 | 优先级 |\n|------|--------|------|--------|\n| 1 | 镜头类型选择 | 预设镜头运动类型 | P0 |\n| 2 | 镜头角度控制 | 切换视角和景别 | P0 |\n| 3 | 运动轨迹描述 | 自然语言描述镜头运动 | P1 |\n| 4 | 分镜时间线 | 拖拽调整分镜顺序和时长 | P2 |\n\n---\n\n\n【四、验收标准】\n\n- [ ] 用户可以切换镜头类型（推/拉/摇/移/跟）\n- [ ] 用户可以切换镜头角度（正/侧/背/特写）\n- [ ] 分镜预览能体现所选镜头效果\n\n---\n\n\n【原始任务描述】\n实现原型功能"

task = Task(
    description=task_description,
    agent=engineer,
    expected_output='Complete code implementation with git commit'
)

crew = Crew(agents=[engineer], tasks=[task], process=Process.sequential, verbose=True)
result = crew.kickoff()
with open('/opt/AiComic/scripts/generated/proto_result_430c497b.result', 'w') as f:
    f.write(str(result))