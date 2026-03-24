#!/usr/bin/env python3
"""CrewAI Prototype Task - PROTO-TEST3"""
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

task_description = 'Implement prototype: 【原型文件】故事编辑器原型_20260324.md
【参考路径】/opt/AiComic/原型/故事编辑器原型_20260324.md

【一、背景与目标】

### 背景
NovelAI有成熟的故事编辑器，支持分章节管理和角色关系图谱。借鉴其设计，我方需要故事编辑器来管理漫画剧本。

### 目标
- 支持多章节剧本管理
- 支持角色关系图谱
- 支持分镜与剧本同步

---


【二、功能清单】

| 序号 | 功能点 | 描述 | 优先级 |
|------|--------|------|--------|
| 1 | 章节管理 | 创建/编辑/删除章节 | P0 |
| 2 | 剧本编辑 | 编写分镜剧本内容 | P0 |
| 3 | 角色引用 | 在剧本中引用角色卡 | P0 |
| 4 | 关系图谱 | 可视化角色关系 | P1 |
| 5 | 导出/导入 | 支持JSON格式导出 | P2 |

---


【四、验收标准】

- [ ] 用户可以创建/编辑/删除章节
- [ ] 用户可以在剧本中引用角色卡
- [ ] 用户可以查看角色关系图谱

---

*产品经理机器人产出 · 2026-03-24*

【原始任务描述】
实现原型功能'
task = Task(description=task_description, agent=coder, expected_output='Code and git commit')

crew = Crew(agents=[coder], tasks=[task], process=Process.sequential, verbose=True)
result = crew.kickoff()
with open('_opt_AiComic_scripts_generated_proto_result_4f388ec0.result', 'w') as f:
    f.write(str(result))