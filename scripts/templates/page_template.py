"""
前端页面模板 - React/Vue 页面开发
用法: 复制并修改 CONFIG，然后执行
"""

from crewai import Agent, Task, Crew, Process
from dotenv import load_dotenv
load_dotenv()

import sys
sys.path.insert(0, '/opt/AiComic/scripts')
from common import TaskOutput, save_output, ensure_dir

# ============ 配置区 ============
CONFIG = {
    "task_name": "用户注册页面",
    "output_dir": "/opt/AiComic/代码/frontend/",
    
    "pages": [
        {
            "name": "RegisterPage",
            "path": "/register",
            "description": "用户注册页面",
            "components": ["UsernameInput", "EmailInput", "PasswordInput", "SubmitButton"],
            "features": ["表单验证", "密码强度检测", "加载状态", "错误提示"]
        }
    ],
    
    "frontend_framework": "react",     # react / vue / nextjs
    "ui_library": "shadcn/ui",         # shadcn/ui / antd / element-ui
    "style": "tailwindcss",            # tailwindcss / styled-components
    "api_base": "/api",               # API 基础路径
}

# ============ Agents ============
frontend_agent = Agent(
    role="前端工程师",
    goal=f"实现 {CONFIG['pages'][0]['name']} 页面",
    backstory=f"资深前端开发，擅长 {CONFIG['frontend_framework']} 和 {CONFIG['ui_library']}",
    verbose=True
)

test_agent = Agent(
    role="前端测试工程师",
    goal="编写 Playwright 端到端测试",
    backstory="E2E测试专家，精通 Playwright",
    verbose=True
)

# ============ Tasks ============
page_task = Task(
    description=f"""
实现 {CONFIG['pages'][0]['name']}：
- 路径: {CONFIG['pages'][0]['path']}
- 功能: {', '.join(CONFIG['pages'][0]['features'])}
- 组件: {', '.join(CONFIG['pages'][0]['components'])}
- UI框架: {CONFIG['ui_library']}
- 样式: {CONFIG['style']}
- API调用: {CONFIG['api_base']}
输出完整的 React 组件代码
""",
    agent=frontend_agent,
    expected_output="完整的页面组件代码文件"
)

test_task = Task(
    description=f"为 {CONFIG['pages'][0]['name']} 编写 Playwright E2E 测试",
    agent=test_agent,
    expected_output="Playwright 测试文件"
)

# ============ 启动 ============
if __name__ == "__main__":
    output = TaskOutput(CONFIG["task_name"])
    ensure_dir(CONFIG["output_dir"])
    
    crew = Crew(
        agents=[frontend_agent, test_agent],
        tasks=[page_task, test_task],
        process=Process.parallel
    )
    
    result = crew.kickoff()
    save_output(str(result), f"{CONFIG['output_dir']}{CONFIG['task_name']}_result.txt")
    print(output.summary())
