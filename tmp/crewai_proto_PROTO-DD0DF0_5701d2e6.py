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

task_description = "【原型文件】角色一致性功能原型_20260324.md\n【参考路径】/opt/AiComic/原型/角色一致性功能原型_20260324.md\n\n【一、背景与目标】\n\n### 背景\n竞品分析显示，**角色一致性是用户最强需求**，也是行业共同难题。Leinad、NovelAI等竞品均未完全解决该问题，这是我方核心差异化突破点。\n\n### 目标\n- 用户创建角色后，在不同场景/动作下保持外观一致\n- 支持角色换装、换场景、换表情但保持身份识别\n- 降低创作门槛，无需每次重新描述角色外观\n\n---\n\n\n【二、功能清单】\n\n| 序号 | 功能点 | 描述 | 优先级 |\n|------|--------|------|--------|\n| 1 | 角色卡创建 | 上传参考图，AI提取角色特征 | P0 |\n| 2 | 角色特征描述 | 自动生成角色文字描述供编辑 | P0 |\n| 3 | 角色一致性生成 | 基于角色卡生成新图像 | P0 |\n| 4 | 角色库管理 | 创建/编辑/删除/收藏角色 | P1 |\n| 5 | 角色变体 | 同一角色不同服装/发型/姿态 | P2 |\n\n---\n\n\n【原始任务描述】\n实现原型功能"

task = Task(
    description=task_description,
    agent=engineer,
    expected_output='Complete code implementation with git commit'
)

crew = Crew(agents=[engineer], tasks=[task], process=Process.sequential, verbose=True)
result = crew.kickoff()
with open('/opt/AiComic/scripts/generated/proto_result_5701d2e6.result', 'w') as f:
    f.write(str(result))