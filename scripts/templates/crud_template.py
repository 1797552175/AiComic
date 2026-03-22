"""
CRUD 增删改查模板
用法: 复制此文件，填充 CONFIG 字典，然后执行
"""

from crewai import Agent, Task, Crew, Process
from dotenv import load_dotenv
load_dotenv()

import sys
sys.path.insert(0, '/opt/AiComic/scripts')
from common import TaskOutput, ensure_dir, save_output, get_project_root

# ============ 配置区（修改这里） ============
CONFIG = {
    "task_name": "用户管理CRUD",           # 任务名称
    "model": "MiniMax-M2.7-highspeed",     # 模型
    "output_dir": "/opt/AiComic/代码/",      # 输出目录
    
    # 数据模型
    "entity": "User",                        # 实体名（首字母大写）
    "fields": [                              # 字段列表
        {"name": "id", "type": "int", "pk": True},
        {"name": "username", "type": "str", "required": True},
        {"name": "email", "type": "str", "required": True},
        {"name": "password_hash", "type": "str", "required": True},
        {"name": "created_at", "type": "datetime"},
    ],
    
    # API端点（不写则自动生成）
    "endpoints": ["create", "read", "update", "delete", "list"],
    
    # 框架
    "framework": "fastapi",                 # fastapi / flask / django
    "database": "postgresql",               # postgresql / mysql / sqlite
}

# ============ Agent 定义（通用） ============
backend_agent = Agent(
    role="后端工程师",
    goal=f"实现 {CONFIG['entity']} 的完整 CRUD API",
    backstory="资深后端开发，擅长 FastAPI 和数据库设计",
    verbose=True
)

test_agent = Agent(
    role="测试工程师",
    goal=f"为 {CONFIG['entity']} API 编写测试用例",
    backstory="专业测试工程师，注重代码质量和边界条件",
    verbose=True
)

# ============ Task 定义 ============
create_api = Task(
    description=f"实现 {CONFIG['entity']} 的创建接口 POST /{CONFIG['entity'].lower()}s/",
    agent=backend_agent,
    expected_output=f"{CONFIG['entity']} 创建 API 代码"
)

read_api = Task(
    description=f"实现 {CONFIG['entity']} 的读取接口 GET /{CONFIG['entity'].lower()}s/<id>",
    agent=backend_agent,
    expected_output=f"{CONFIG['entity']} 读取 API 代码"
)

update_api = Task(
    description=f"实现 {CONFIG['entity']} 的更新接口 PUT /{CONFIG['entity'].lower()}s/<id>",
    agent=backend_agent,
    expected_output=f"{CONFIG['entity']} 更新 API 代码"
)

delete_api = Task(
    description=f"实现 {CONFIG['entity']} 的删除接口 DELETE /{CONFIG['entity'].lower()}s/<id>",
    agent=backend_agent,
    expected_output=f"{CONFIG['entity']} 删除 API 代码"
)

test_api = Task(
    description=f"为所有 {CONFIG['entity']} API 编写 pytest 测试用例，覆盖正常和异常场景",
    agent=test_agent,
    expected_output="完整的测试代码"
)

# ============ 启动 ============
if __name__ == "__main__":
    output = TaskOutput(CONFIG["task_name"])
    
    crew = Crew(
        agents=[backend_agent, test_agent],
        tasks=[create_api, read_api, update_api, delete_api, test_api],
        process=Process.parallel
    )
    
    result = crew.kickoff()
    save_output(str(result), f"{CONFIG['output_dir']}{CONFIG['task_name']}_result.txt")
    print(output.summary())
