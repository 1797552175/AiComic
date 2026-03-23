"""
Coding Agent 模板 - 直接执行代码生成的 CrewAI 脚本
用法: python coding_direct_template.py

⚠️ 需要环境变量:
export OPENAI_API_KEY=sk-cp-X-OrjwZ_qtWkXMytgCnkP28VhiHEhKQ3aGdtIJEHpfE9fmO0jTL4VRewWUjMQhMhvJeNFE5l3FgPhjnXA_hW7ifdA3Sm9uv2mraenxVJzUYNYbf2MvGtb_g
export OPENAI_BASE_URL=https://api.minimax.chat/v1
"""

import os
import sys
sys.path.insert(0, '/opt/AiComic/scripts')
from common import TaskOutput, save_output, ensure_dir

from crewai import Agent, Task, Crew, Process

CONFIG = {
    "task_name": "用户注册API开发",
    "output_dir": "/opt/AiComic/scripts/output/",
    "target_file": "/opt/AiComic/apps/backend/api/users.py",
}

ensure_dir(CONFIG["output_dir"])

# Agent 不带工具，直接生成代码文本
coding_agent = Agent(
    role="后端工程师",
    goal="根据需求生成完整可运行的Python代码",
    backstory="资深Python后端工程师，精通FastAPI和SQLAlchemy",
    verbose=True,
    llm="openai/MiniMax-M2.7-highspeed"
)

coding_task = Task(
    description=f"""
请根据以下需求生成完整的Python代码：

开发一个用户注册API：
1. FastAPI POST /api/users/register
2. 接收 username, email, password
3. 参数校验（邮箱格式、密码长度>=8）
4. 密码用 bcrypt hash
5. 返回 user_id 和 JWT token

要求：
- 使用 FastAPI + Pydantic
- 输出完整的 Python 代码文件内容
- 只输出代码，不需要解释
- 代码要可以直接运行

输出文件：{CONFIG['target_file']}
""",
    agent=coding_agent,
    expected_output="完整的Python代码"
)

if __name__ == "__main__":
    output = TaskOutput(CONFIG["task_name"])
    
    crew = Crew(
        agents=[coding_agent],
        tasks=[coding_task],
        process=Process.sequential
    )
    
    result = crew.kickoff()
    result_text = str(result)
    
    # 保存原始输出
    save_output(result_text, f"{CONFIG['output_dir']}{CONFIG['task_name']}_raw.txt")
    
    # 尝试提取代码并写入文件
    try:
        # 提取 markdown 代码块
        import re
        code_match = re.search(r'```python\s*(.*?)\s*```', result_text, re.DOTALL)
        if code_match:
            code = code_match.group(1)
        else:
            # 如果没有代码块，把整个结果当作代码
            code = result_text
        
        # 写入文件
        os.makedirs(os.path.dirname(CONFIG['target_file']), exist_ok=True)
        with open(CONFIG['target_file'], 'w') as f:
            f.write(code)
        
        print(f"✅ 代码已写入: {CONFIG['target_file']}")
        
        # 尝试语法检查
        import py_compile
        py_compile.compile(CONFIG['target_file'], doraise=True)
        print(f"✅ 语法检查通过")
        
        save_output(f"代码已生成并通过语法检查: {CONFIG['target_file']}", 
                    f"{CONFIG['output_dir']}{CONFIG['task_name']}_done.txt")
        
    except Exception as e:
        print(f"⚠️ 代码写入或检查失败: {e}")
        print("原始结果已保存到 output 目录")
    
    print(output.summary())
