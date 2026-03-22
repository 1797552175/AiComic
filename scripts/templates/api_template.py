"""
REST API 开发模板
用法: 复制并修改 CONFIG，然后执行 python api_template.py
"""

from crewai import Agent, Task, Crew, Process
from dotenv import load_dotenv
load_dotenv()

import sys
sys.path.insert(0, '/opt/AiComic/scripts')
from common import TaskOutput, save_output, ensure_dir

# ============ 配置区 ============
CONFIG = {
    "task_name": "用户认证API",
    "output_dir": "/opt/AiComic/代码/",
    
    # API 描述
    "api_name": "用户认证",
    "endpoints": [
        {
            "method": "POST",
            "path": "/auth/register",
            "description": "用户注册",
            "body": ["username", "email", "password"]
        },
        {
            "method": "POST", 
            "path": "/auth/login",
            "description": "用户登录",
            "body": ["email", "password"]
        },
        {
            "method": "POST",
            "path": "/auth/refresh",
            "description": "刷新Token"
        }
    ],
    
    "framework": "fastapi",
    "auth_method": "jwt",           # jwt / session / oauth2
}

# ============ Agents ============
backend_agent = Agent(
    role="后端工程师",
    goal=f"实现 {CONFIG['api_name']} REST API",
    backstory="10年后端经验，精通 FastAPI、认证安全和 REST 设计规范",
    verbose=True
)

docs_agent = Agent(
    role="技术文档工程师",
    goal="生成 OpenAPI 文档",
    backstory="专业技术写作者，擅长清晰准确的 API 文档",
    verbose=True
)

# ============ Tasks ============
tasks = []
for ep in CONFIG["endpoints"]:
    t = Task(
        description=f"实现 {ep['method']} {ep['path']} - {ep['description']}",
        agent=backend_agent,
        expected_output=f"{ep['method']} {ep['path']} 代码"
    )
    tasks.append(t)

docs_task = Task(
    description="生成完整的 OpenAPI (Swagger) 文档",
    agent=docs_agent,
    expected_output="YAML 或 JSON 格式的 OpenAPI 文档"
)
tasks.append(docs_task)

# ============ 启动 ============
if __name__ == "__main__":
    output = TaskOutput(CONFIG["task_name"])
    
    crew = Crew(
        agents=[backend_agent, docs_agent],
        tasks=tasks,
        process=Process.sequential  # API开发通常顺序执行
    )
    
    result = crew.kickoff()
    save_output(str(result), f"{CONFIG['output_dir']}{CONFIG['task_name']}_result.txt")
    print(output.summary())
