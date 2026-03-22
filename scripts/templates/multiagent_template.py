"""
多Agent协作模板 - 复杂任务分解并行执行
用法: 复制并修改 CONFIG，然后执行

⚠️ 注意：需要先设置环境变量：
export OPENAI_API_KEY=your_minimax_key
export OPENAI_BASE_URL=https://api.minimax.chat/v1
"""

import os
from dotenv import load_dotenv
load_dotenv()

from crewai import Agent, Task, Crew, Process

import sys
sys.path.insert(0, '/opt/AiComic/scripts')
from common import TaskOutput, save_output, ensure_dir

# ============ 配置区 ============
CONFIG = {
    "task_name": "电商商品详情页开发",
    "output_dir": "/opt/AiComic/scripts/output/",
    
    # MiniMax API 配置（OpenAI兼容模式）
    "api_key": os.getenv("OPENAI_API_KEY", ""),
    "base_url": os.getenv("OPENAI_BASE_URL", "https://api.minimax.chat/v1"),
    
    # 定义参与任务的Agent（2-5个效果最好）
    "agents": [
        {
            "name": "pm",
            "role": "产品经理",
            "goal": "分析需求，输出产品规格说明书",
            "backstory": "资深产品经理，擅长需求分析和PRD撰写"
        },
        {
            "name": "frontend",
            "role": "前端工程师",
            "goal": "实现商品详情页UI",
            "backstory": "资深前端，React/Next.js专家"
        },
        {
            "name": "backend",
            "role": "后端工程师",
            "goal": "实现商品详情API",
            "backstory": "10年后端，精通FastAPI和PostgreSQL"
        },
        {
            "name": "tester",
            "role": "测试工程师",
            "goal": "编写商品模块的自动化测试",
            "backstory": "专业QA，擅长pytest和Playwright"
        }
    ],
    
    # 任务描述
    "task_description": """
开发一个电商商品详情页系统，包含：
1. 商品展示（图片、标题、价格、库存）
2. 规格选择（颜色、尺码）
3. 购物车添加
4. 评价展示
5. 相关商品推荐
需要同时开发前端页面和后端API，使用React + FastAPI技术栈。
"""
}

# ============ LLM 配置 ============
llm_config = {
    "model": "MiniMax-M2.7-highspeed",
    "api_key": CONFIG["api_key"],
    "base_url": CONFIG["base_url"],
}

# ============ 构建 Agents ============
agents = []
for cfg in CONFIG["agents"]:
    agent = Agent(
        role=cfg["role"],
        goal=cfg["goal"],
        backstory=cfg["backstory"],
        verbose=True,
        llm=f"openai/{llm_config['model']}"
    )
    agents.append(agent)

# PM 先输出规格书
pm_task = Task(
    description=f"作为产品经理，分析需求并输出产品规格说明书。\n{CONFIG['task_description']}",
    agent=agents[0],
    expected_output="产品规格说明书.md"
)

# 前端和后端并行
frontend_task = Task(
    description="根据产品规格说明书，开发商品详情页前端",
    agent=agents[1],
    expected_output="React组件代码"
)

backend_task = Task(
    description="根据产品规格说明书，开发商品详情页后端API",
    agent=agents[2],
    expected_output="FastAPI代码"
)

# 测试最后
test_task = Task(
    description="为商品模块编写完整测试（pytest + Playwright）",
    agent=agents[3],
    expected_output="测试代码文件"
)

# PM -> Frontend, Backend -> Tester
frontend_task.context = [pm_task]
backend_task.context = [pm_task]
test_task.context = [frontend_task, backend_task]

# ============ 启动 ============
if __name__ == "__main__":
    output = TaskOutput(CONFIG["task_name"])
    ensure_dir(CONFIG["output_dir"])
    
    if not CONFIG["api_key"]:
        print("错误: 请设置 OPENAI_API_KEY 环境变量")
        exit(1)
    
    crew = Crew(
        agents=agents,
        tasks=[pm_task, frontend_task, backend_task, test_task],
        process=Process.sequential
    )
    
    result = crew.kickoff()
    save_output(str(result), f"{CONFIG['output_dir']}{CONFIG['task_name']}_result.txt")
    print(output.summary())
