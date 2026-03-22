"""
Coding Agent 模板 - 带真实工具的 CrewAI 脚本
用法: python coding_template.py

⚠️ 需要环境变量:
export OPENAI_API_KEY=sk-cp-X-OrjwZ_qtWkXMytgCnkP28VhiHEhKQ3aGdtIJEHpfE9fmO0jTL4VRewWUjMQhMhvJeNFE5l3FgPhjnXA_hW7ifdA3Sm9uv2mraenxVJzUYNYbf2MvGtb_g
export OPENAI_BASE_URL=https://api.minimax.chat/v1
"""

import os
import sys
sys.path.insert(0, '/opt/AiComic/scripts')
from common import TaskOutput, save_output, ensure_dir

from crewai import Agent, Task, Crew, Process
from crewai_tools import (
    FileReadTool,
    FileWriterTool,
    DirectoryReadTool,
    DirectorySearchTool,
    SerpApiGoogleSearchTool
)

# ============ 工具初始化 ============
file_reader = FileReadTool()
file_writer = FileWriterTool()
dir_reader = DirectoryReadTool()
dir_search = DirectorySearchTool()

# ============ 配置区 ============
CONFIG = {
    "task_name": "AiComic功能开发",
    "output_dir": "/opt/AiComic/scripts/output/",
    "project_root": "/opt/AiComic",
    "task_description": """
开发一个用户注册功能，包含：
1. FastAPI POST /api/users/register 接口
2. 用户名、邮箱、密码的校验
3. 密码 hash 存储到数据库
4. 返回用户 ID 和 token
"""
}

ensure_dir(CONFIG["output_dir"])

# ============ 定义 Agent ============
backend_agent = Agent(
    role="后端工程师",
    goal="根据需求实现完整的、可运行的代码",
    backstory="资深Python后端工程师，精通FastAPI、SQLAlchemy和数据库设计",
    verbose=True,
    tools=[file_reader, file_writer, dir_reader, dir_search],
    llm="openai/MiniMax-M2.7-highspeed"
)

# ============ 任务 ============
coding_task = Task(
    description=f"""
你是一个后端工程师。请根据以下需求实现代码：

{CONFIG['task_description']}

要求：
1. 代码必须写入文件，不能只输出文本
2. 使用 FastAPI + SQLAlchemy
3. 输出目录：{CONFIG['project_root']}/apps/backend/api/users.py
4. 如果需要创建新文件，先列出目录结构
5. 完成后运行代码确保无语法错误
""",
    agent=backend_agent,
    expected_output="完整可运行的Python代码文件"
)

# ============ 启动 ============
if __name__ == "__main__":
    output = TaskOutput(CONFIG["task_name"])
    
    crew = Crew(
        agents=[backend_agent],
        tasks=[coding_task],
        process=Process.sequential
    )
    
    result = crew.kickoff()
    
    # 保存结果
    save_output(
        str(result),
        f"{CONFIG['output_dir']}{CONFIG['task_name']}_result.txt"
    )
    
    print(f"\n===== 执行完成 =====")
    print(output.summary())
    print(f"结果: {result}")
