#!/usr/bin/env python3
"""CrewAI 多 Agent 任务脚本 - TODO-TEST-001"""
import os
import subprocess
os.environ["OPENAI_API_KEY"] = os.environ.get("MINIMAX_API_KEY", "")

from crewai import Agent, Task, Crew, Process
from crewai.llm import LLM
from crewai.tools import BaseTool

llm = LLM(model="openai/MiniMax-M2.7-highspeed", is_litellm=True, api_key=os.environ.get("MINIMAX_API_KEY", ""), max_retries_on_rate_limit_error=5)

# Shell 命令执行工具
class ShellCommandTool(BaseTool):
    name: str = "shell_command"
    description: str = "执行 shell 命令并返回输出结果"

    def _run(self, cmd: str):
        # Fix fullwidth punctuation in generated Python code
        import re
        fullwidth_map = {'\uff1a': ':', '\uff08': '(', '\uff09': ')', '\uff0c': ',', '\uff0e': '.', '\uff01': '!', '\uff1f': '?', '\uff1b': ';', '\uff0d': '-', '\uff1d': '=', '\uff0b': '+', '\uff02': '"', '\uff07': "'"}
        for fw, asc in fullwidth_map.items():
            cmd = cmd.replace(fw, asc)
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30, cwd='/opt/AiComic')
        output = result.stdout + result.stderr
        print('[shell] $ ' + cmd + ' -> ' + str(result.returncode))
        return output

shell_tool = ShellCommandTool()

# 3 个 Agent
pm = Agent(role="产品经理", goal="分析需求，输出实现方案", backstory="资深产品经理，擅长技术方案设计", verbose=True, llm=llm)
backend = Agent(role="后端工程师", goal="根据方案实现后端代码，必须使用 shell_command 工具执行真正的命令", backstory="10年后端，精通Python/FastAPI", verbose=True, llm=llm, tools=[shell_tool])
reviewer = Agent(role="代码审查员", goal="审查代码质量和安全性", backstory="资深代码审查员，擅长Python安全", verbose=True, llm=llm)

# 顺序任务
task_analysis = Task(description="分析任务：实现功能", agent=pm, expected_output="实现方案文档")
task_code = Task(description="根据方案实现代码：实现功能。重要：必须使用 shell_command 工具执行真正的命令来完成任务，不要只生成代码。完成后将结果写入 /opt/AiComic/scripts/generated/crewai_result_1f7d2e3c.result", agent=backend, expected_output="命令执行结果")
task_review = Task(description="审查代码：实现功能", agent=reviewer, expected_output="审查报告")

crew = Crew(agents=[pm, backend, reviewer], tasks=[task_analysis, task_code, task_review], process=Process.sequential, verbose=True)

result = crew.kickoff()
print('任务完成: ' + str(result))
with open('/opt/AiComic/scripts/generated/crewai_result_1f7d2e3c.result', 'w') as f:
    f.write(str(result))
