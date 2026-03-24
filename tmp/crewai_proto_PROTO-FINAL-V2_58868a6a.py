#!/usr/bin/env python3
"""CrewAI Prototype Task - PROTO-FINAL-V2"""
"""执行流程：Phase1(4个开发并行) -> Phase2(测试) -> Phase3(部署)"""
import os
import sys
os.environ['OPENAI_API_KEY'] = os.environ.get('MINIMAX_API_KEY', '')
os.environ['LANG'] = 'en_US.UTF-8'

from crewai import Agent, Task, Crew, Process
from crewai.llm import LLM
from crewai.tools import BaseTool

llm = LLM(model='openai/MiniMax-M2.7-highspeed', is_litellm=True, api_key=os.environ.get('MINIMAX_API_KEY', ''), max_retries_on_rate_limit_error=5)

class ShellTool(BaseTool):
    name: str = 'shell'
    description: str = 'Execute shell command in /opt/AiComic',

    def _run(self, cmd: str):
        import subprocess
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120, cwd='/opt/AiComic')
        return result.stdout + result.stderr

shell = ShellTool()

# === Phase 1: Manager Agent (协调者，不带工具) ===
manager = Agent(role='Project Manager', goal='Coordinate 4 developers to complete prototype implementation', backstory='Senior tech lead with 10 years experience coordinating teams', verbose=True, llm=llm)

# === Phase 1: 开发 Agent (由 Manager 协调) ===
frontend1 = Agent(role='Frontend Engineer 1', goal='Implement UI components in React', backstory='5 years React experience', verbose=True, llm=llm, tools=[shell])
frontend2 = Agent(role='Frontend Engineer 2', goal='Implement UI state management and API integration', backstory='5 years React experience', verbose=True, llm=llm, tools=[shell])
backend1 = Agent(role='Backend Engineer 1', goal='Implement FastAPI endpoints', backstory='5 years Python/FastAPI experience', verbose=True, llm=llm, tools=[shell])
backend2 = Agent(role='Backend Engineer 2', goal='Implement database models and SQL', backstory='5 years SQLAlchemy experience', verbose=True, llm=llm, tools=[shell])

# === Phase 2: 测试 Agent (串行执行) ===
tester = Agent(role='Test Engineer', goal='Write unit tests for completed code', backstory='3 years testing experience', verbose=True, llm=llm, tools=[shell])

# === Phase 3: DevOps Agent (串行执行) ===
devops = Agent(role='DevOps Engineer', goal='Verify code and git push', backstory='3 years CI/CD experience', verbose=True, llm=llm, tools=[shell])

# 原始任务描述
task_description = "【原型文件】故事编辑器原型_20260324.md\n【参考路径】/opt/AiComic/原型/故事编辑器原型_20260324.md\n\n【背景与目标】\n### 背景\nNovelAI有成熟的故事编辑器，支持分章节管理和角色关系图谱。借鉴其设计，我方需要故事编辑器来管理漫画剧本。\n\n### 目标\n- 支持多章节剧本管理\n- 支持角色关系图谱\n- 支持分镜与剧本同步\n\n---\n\n【一、背景与目标】\n### 背景\nNovelAI有成熟的故事编辑器，支持分章节管理和角色关系图谱。借鉴其设计，我方需要故事编辑器来管理漫画剧本。\n\n### 目标\n- 支持多章节剧本管理\n- 支持角色关系图谱\n- 支持分镜与剧本同步\n\n---\n\n【功能清单】\n| 序号 | 功能点 | 描述 | 优先级 |\n|------|--------|------|--------|\n| 1 | 章节管理 | 创建/编辑/删除章节 | P0 |\n| 2 | 剧本编辑 | 编写分镜剧本内容 | P0 |\n| 3 | 角色引用 | 在剧本中引用角色卡 | P0 |\n| 4 | 关系图谱 | 可视化角色关系 | P1 |\n| 5 | 导出/导入 | 支持JSON格式导出 | P2 |\n\n---\n\n【二、功能清单】\n| 序号 | 功能点 | 描述 | 优先级 |\n|------|--------|------|--------|\n| 1 | 章节管理 | 创建/编辑/删除章节 | P0 |\n| 2 | 剧本编辑 | 编写分镜剧本内容 | P0 |\n| 3 | 角色引用 | 在剧本中引用角色卡 | P0 |\n| 4 | 关系图谱 | 可视化角色关系 | P1 |\n| 5 | 导出/导入 | 支持JSON格式导出 | P2 |\n\n---\n\n【验收标准】\n- [ ] 用户可以创建/编辑/删除章节\n- [ ] 用户可以在剧本中引用角色卡\n- [ ] 用户可以查看角色关系图谱\n\n---\n\n*产品经理机器人产出 · 2026-03-24*\n\n【四、验收标准】\n- [ ] 用户可以创建/编辑/删除章节\n- [ ] 用户可以在剧本中引用角色卡\n- [ ] 用户可以查看角色关系图谱\n\n---\n\n*产品经理机器人产出 · 2026-03-24*\n\n【原始任务描述】\n实现原型功能"

# === Phase 1: 4个开发任务并行 ===
# Frontend1 任务
task_fe1 = Task(description= '''【Frontend1 职责】实现 UI 组件
参考原型文档完成任务开发：
{task_description}
具体要求：
- 使用 React 实现 UI 组件
- 组件需要包含完整的样式和交互
- 代码放在 /opt/AiComic/apps/frontend/src/ 目录'''.format(task_description=task_description), agent=frontend1, expected_output='React components created in /opt/AiComic/apps/frontend/src/')

# Frontend2 任务
task_fe2 = Task(description= '''【Frontend2 职责】实现状态管理和 API 集成
参考原型文档完成任务开发：
{task_description}
具体要求：
- 使用 React Hooks 实现状态管理
- 调用后端 API 实现数据交互
- 与 Frontend1 协作确保组件集成正常'''.format(task_description=task_description), agent=frontend2, expected_output='State management and API integration completed')

# Backend1 任务
task_be1 = Task(description= '''【Backend1 职责】实现 FastAPI 后端接口
参考原型文档完成任务开发：
{task_description}
具体要求：
- 使用 FastAPI 实现 RESTful API
- 实现业务逻辑层
- 代码放在 /opt/AiComic/apps/backend/ 目录'''.format(task_description=task_description), agent=backend1, expected_output='FastAPI endpoints created in /opt/AiComic/apps/backend/')

# Backend2 任务
task_be2 = Task(description= '''【Backend2 职责】实现数据库模型
参考原型文档完成任务开发：
{task_description}
具体要求：
- 使用 SQLAlchemy 定义数据模型
- 编写必要的数据库迁移脚本
- 与 Backend1 协作确保 API 能正常访问数据'''.format(task_description=task_description), agent=backend2, expected_output='Database models created with SQLAlchemy')

# Phase 1 Crew: 开发阶段 (层级式，由 manager 协调)
dev_crew = Crew(
    agents=[frontend1, frontend2, backend1, backend2],
    tasks=[task_fe1, task_fe2, task_be1, task_be2],
    process=Process.hierarchical,
    manager_agent=manager,
    verbose=True
)

print("[Phase 1] 开始并行开发...")
dev_result = dev_crew.kickoff()
print("[Phase 1] 开发完成:", dev_result)

# === Phase 2: 测试任务 (串行) ===
# 依赖 Phase 1 完成
task_test = Task(
    description= '''【Test Engineer 职责】编写单元测试
注意：此任务在开发 Agent 完成后执行
具体要求：
- 为已完成的代码编写单元测试
- 测试覆盖率目标 > 70%
- 测试文件放在 /opt/AiComic/tests/ 目录
- 使用 pytest 框架'''.format(task_description=task_description),
    agent=tester,
    expected_output='Unit tests written in /opt/AiComic/tests/',
)

print("[Phase 2] 开始测试...")
test_crew = Crew(agents=[tester], tasks=[task_test], process=Process.sequential, verbose=True)
test_result = test_crew.kickoff()
print("[Phase 2] 测试完成:", test_result)

# === Phase 3: DevOps 任务 (串行) ===
# 依赖 Phase 2 完成
task_ops = Task(
    description= '''【DevOps Engineer 职责】验证代码并部署
注意：此任务在 Test Engineer 完成后执行
具体要求：
- 运行测试确保所有用例通过
- 检查代码质量和规范
- git commit 并 push 到仓库
- 更新相关文档'''.format(task_description=task_description),
    agent=devops,
    expected_output='Code verified and git pushed',
)

print("[Phase 3] 开始部署...")
ops_crew = Crew(agents=[devops], tasks=[task_ops], process=Process.sequential, verbose=True)
ops_result = ops_crew.kickoff()
print("[Phase 3] 部署完成:", ops_result)

# === 汇总结果 ===
final_result = {
    'dev_phase': str(dev_result),
    'test_phase': str(test_result),
    'ops_phase': str(ops_result),
}
with open('/opt/AiComic/scripts/generated/proto_result_58868a6a.result', 'w') as f:
    import json
    f.write(json.dumps(final_result, ensure_ascii=False, indent=2))