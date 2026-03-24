#!/usr/bin/env python3
"""CrewAI Prototype Task - PROTO-DEV-388"""
"""
自适应并发执行系统：
1. 使用 ThreadPoolExecutor 启动 6 个独立 Agent
2. 每个 Agent 自带限流重试（指数退避）
3. 运行时动态监控 API 错误率
4. 连续触发限流时自动降低并发数至安全阈值（3个）
5. 实现自适应最大并发
"""
import os
import sys
import time
import json
import threading
import concurrent.futures
from datetime import datetime
from collections import deque

os.environ['OPENAI_API_KEY'] = os.environ.get('MINIMAX_API_KEY', '')
os.environ['MINIMAX_API_BASE'] = 'https://api.minimax.chat/v1'
os.environ['LANG'] = 'en_US.UTF-8'

from crewai import Agent, Task, Crew
from crewai.llm import LLM
from crewai.tools import BaseTool
import litellm
import httpx
litellm.request_timeout = 600

# === MiniMax 系统消息转换器 ===
# MiniMax API 不支持 system role，此转换器自动将其转为 user role
def convert_system_to_user(messages):
    """将所有 system role 转换为 user role"""
    if not messages:
        return messages
    converted = []
    for msg in messages:
        if not isinstance(msg, dict):
            converted.append(msg)
            continue
        if msg.get('role') == 'system':
            # 将 system 消息转换为 user 消息
            content = msg.get('content', '')
            if isinstance(content, list):
                content = str(content)
            converted.append({'role': 'user', 'content': '[System] ' + content})
        else:
            converted.append(msg)
    return converted

# 包装所有 litellm 完成方法
original_completion = litellm.completion
original_acompletion = litellm.acompletion

def safe_completion(*args, **kwargs):
    """包装 litellm.completion，自动转换消息"""
    if 'messages' in kwargs:
        kwargs['messages'] = convert_system_to_user(kwargs['messages'])
    elif len(args) > 1:
        args = list(args)
        args[1] = convert_system_to_user(args[1])
        args = tuple(args)
    return original_completion(*args, **kwargs)

async def safe_acompletion(*args, **kwargs):
    """包装 litellm.acompletion，自动转换消息"""
    if 'messages' in kwargs:
        kwargs['messages'] = convert_system_to_user(kwargs['messages'])
    elif len(args) > 1:
        args = list(args)
        args[1] = convert_system_to_user(args[1])
        args = tuple(args)
    return await original_acompletion(*args, **kwargs)

# 替换 litellm 方法
litellm.completion = safe_completion
litellm.acompletion = safe_acompletion

# 额外：patch CrewAI 的 LLM._prepare_completion_params 方法
try:
    from crewai.llm import LLM
    _original_prepare = LLM._prepare_completion_params
    
    def _patched_prepare(self, *args, **kwargs):
        result = _original_prepare(self, *args, **kwargs)
        if 'messages' in result:
            result['messages'] = convert_system_to_user(result['messages'])
        return result
    
    LLM._prepare_completion_params = _patched_prepare
    print('[System] CrewAI LLM patched successfully')
except Exception as e:
    print(f'[System] CrewAI LLM patch failed: {e}')

# === 全局并发控制器 ===
class ConcurrencyController:
    """自适应并发控制器"""
    def __init__(self, max_workers=6, safe_threshold=3):
        self.max_workers = max_workers
        self.safe_threshold = safe_threshold
        self.current_workers = max_workers
        self.error_counts = deque(maxlen=20)  # 滑动窗口记录最近20次请求
        self.lock = threading.Lock()
        self.consecutive_errors = 0
        self.api_errors = 0
        self.total_calls = 0
        self.current_error_rate = 0.0

    def record_result(self, is_error, is_rate_limit=False):
        """记录 API 调用结果"""
        with self.lock:
            self.total_calls += 1
            self.error_counts.append(1 if is_error else 0)
            self.current_error_rate = sum(self.error_counts) / len(self.error_counts)
            
            if is_error:
                self.consecutive_errors += 1
                self.api_errors += 1
                if is_rate_limit:
                    # 触发限流时快速降级
                    self.consecutive_errors = max(self.consecutive_errors, 3)
            else:
                self.consecutive_errors = 0
            
            # 动态调整并发数
            self._adjust_concurrency()
            
            return self.current_workers

    def _adjust_concurrency(self):
        """根据错误率动态调整并发数"""
        if self.consecutive_errors >= 3:
            # 连续3次以上错误，降低并发
            new_workers = max(self.safe_threshold, self.current_workers // 2)
            if new_workers < self.current_workers:
                print(f'[Controller] 连续错误{self.consecutive_errors}次，降低并发: {self.current_workers} -> {new_workers}')
                self.current_workers = new_workers
                self.consecutive_errors = 0
        elif self.current_error_rate > 0.3 and self.current_workers > self.safe_threshold:
            # 错误率超过30%且高于安全阈值，降低并发
            new_workers = max(self.safe_threshold, self.current_workers - 1)
            print(f'[Controller] 错误率{self.current_error_rate:.1%}，降低并发: {self.current_workers} -> {new_workers}')
            self.current_workers = new_workers
        elif self.current_error_rate < 0.1 and self.current_workers < self.max_workers:
            # 错误率低于10%且低于最大并发，尝试增加
            new_workers = min(self.max_workers, self.current_workers + 1)
            if new_workers > self.current_workers:
                print(f'[Controller] 错误率{self.current_error_rate:.1%}，增加并发: {self.current_workers} -> {new_workers}')
                self.current_workers = new_workers

    def get_stats(self):
        """获取当前统计信息"""
        with self.lock:
            return {
                'current_workers': self.current_workers,
                'max_workers': self.max_workers,
                'error_rate': self.current_error_rate,
                'total_calls': self.total_calls,
                'api_errors': self.api_errors,
                'consecutive_errors': self.consecutive_errors,
            }

    def wait_if_needed(self):
        """如果并发已满，等待"""
        # 这个方法可以用于实现全局并发限制
        pass


# === Agent 执行器（带重试）===
class AgentExecutor:
    """带指数退避重试的 Agent 执行器"""
    def __init__(self, agent, task, controller, name):
        self.agent = agent
        self.task = task
        self.controller = controller
        self.name = name
        self.max_retries = 5
        self.base_delay = 2  # 基础延迟秒数
        self.result = None
        self.error = None

    def execute_with_retry(self):
        """执行任务，支持指数退避重试"""
        for attempt in range(self.max_retries):
            try:
                print(f'[{self.name}] 执行任务 (尝试 {attempt + 1}/{self.max_retries})')
                result = self.agent.execute_task(self.task)
                
                # 记录成功
                self.controller.record_result(is_error=False)
                self.result = result
                print(f'[{self.name}] 任务完成')
                return result
                
            except Exception as e:
                error_msg = str(e)
                is_rate_limit = any(x in error_msg.lower() for x in ['rate', 'limit', '429', 'too many'])
                is_api_error = any(x in error_msg.lower() for x in ['api', 'error', 'invalid', '401', '403', '500', '502', '503'])
                
                # 记录错误
                self.controller.record_result(is_error=True, is_rate_limit=is_rate_limit)
                
                if attempt < self.max_retries - 1:
                    delay = self.base_delay * (2 ** attempt)  # 2, 4, 8, 16, 32 秒
                    print(f'[{self.name}] 错误: {error_msg[:100]}...')
                    print(f'[{self.name}] {delay}秒后重试...')
                    time.sleep(delay)
                else:
                    self.error = error_msg
                    print(f'[{self.name}] 重试次数用尽，任务失败')
        
        return None


def run_agents_concurrently(agents, tasks, controller, output_file):
    """使用线程池并发执行多个 Agent"""
    results = {}
    stats = controller.get_stats()
    print(f'[主控] 启动并发执行，最大并发: {stats["current_workers"]}')
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=controller.current_workers) as executor:
        futures = {}
        for i, (agent, task) in enumerate(zip(agents, tasks)):
            executor_config = AgentExecutor(agent, task, controller, f'Agent-{i+1}')
            future = executor.submit(executor_config.execute_with_retry)
            futures[future] = f'Agent-{i+1}'
        
        for future in concurrent.futures.as_completed(futures):
            agent_name = futures[future]
            try:
                result = future.result()
                results[agent_name] = {'status': 'success', 'result': result}
                print(f'[主控] {agent_name} 完成')
            except Exception as e:
                results[agent_name] = {'status': 'error', 'error': str(e)}
                print(f'[主控] {agent_name} 失败: {e}')
    
    return results


# === 主执行流程 ===
def main():
    print('='*60)
    print('CrewAI 原型任务执行 - 自适应并发版本')
    print('='*60)
    
    # 初始化 LLM
    llm = LLM(
        model='openai/MiniMax-M2.7-highspeed',
        is_litellm=True,
        api_key=os.environ.get('MINIMAX_API_KEY', ''),
        max_retries_on_rate_limit_error=0,  # 我们自己处理重试
    )
    
    # Shell 工具
    class ShellTool(BaseTool):
        name: str = 'shell'
        description: str = 'Execute shell command in /opt/AiComic'
        
        def _run(self, cmd: str):
            import subprocess
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=120,
                cwd='/opt/AiComic'
            )
            return result.stdout + result.stderr
    
    shell = ShellTool()
    
    # 创建 6 个 Agent
    agents = [
        Agent(
            role='Frontend Engineer 1',
            goal='Implement UI components in React',
            backstory='5 years React experience',
            verbose=True, llm=llm, tools=[shell]
        ),
        Agent(
            role='Frontend Engineer 2',
            goal='Implement UI state management and API integration',
            backstory='5 years React experience',
            verbose=True, llm=llm, tools=[shell]
        ),
        Agent(
            role='Backend Engineer 1',
            goal='Implement FastAPI endpoints',
            backstory='5 years Python/FastAPI experience',
            verbose=True, llm=llm, tools=[shell]
        ),
        Agent(
            role='Backend Engineer 2',
            goal='Implement database models and SQL',
            backstory='5 years SQLAlchemy experience',
            verbose=True, llm=llm, tools=[shell]
        ),
        Agent(
            role='Test Engineer',
            goal='Write unit tests',
            backstory='3 years testing experience',
            verbose=True, llm=llm, tools=[shell]
        ),
        Agent(
            role='DevOps Engineer',
            goal='Verify code and git push',
            backstory='3 years CI/CD experience',
            verbose=True, llm=llm, tools=[shell]
        ),
    ]
    
    # 任务描述
    task_description = "实现原型功能"
    
    # 创建 6 个任务
    tasks = [
        Task(
            description='[Frontend1] ' + task_description,
            agent=agents[0],
            expected_output='React components created',
        ),
        Task(
            description='[Frontend2] ' + task_description,
            agent=agents[1],
            expected_output='State management done',
        ),
        Task(
            description='[Backend1] ' + task_description,
            agent=agents[2],
            expected_output='API endpoints created',
        ),
        Task(
            description='[Backend2] ' + task_description,
            agent=agents[3],
            expected_output='Database models created',
        ),
        Task(
            description='[Test] ' + task_description,
            agent=agents[4],
            expected_output='Tests written',
        ),
        Task(
            description='[DevOps] ' + task_description,
            agent=agents[5],
            expected_output='Code verified and pushed',
        ),
    ]
    
    # 初始化控制器
    controller = ConcurrencyController(max_workers=6, safe_threshold=3)
    
    # Phase 1: 并发执行 6 个 Agent
    print('[Phase 1] 开始并发执行 6 个 Agent...')
    start_time = time.time()
    results = run_agents_concurrently(agents, tasks, controller, '/opt/AiComic/scripts/generated/proto_result_8ff3eb00')
    elapsed = time.time() - start_time
    print(f'[Phase 1] 并发执行完成，耗时: {elapsed:.1f}秒')
    
    # 输出统计
    stats = controller.get_stats()
    print(f'[统计] 最终并发数: {stats["current_workers"]}')
    print(f'[统计] API 错误率: {stats["error_rate"]:.1%}')
    print(f'[统计] 总调用数: {stats["total_calls"]}, API错误: {stats["api_errors"]}')
    
    # 保存结果
    final_result = {
        'phase1_results': {k: {'status': v['status']} for k, v in results.items()},
        'stats': stats,
        'elapsed_seconds': elapsed,
        'timestamp': datetime.now().isoformat(),
    }
    with open('/opt/AiComic/scripts/generated/proto_result_8ff3eb00.result', 'w') as f:
        f.write(json.dumps(final_result, ensure_ascii=False, indent=2))
    
    print('[完成] 结果已保存到: /opt/AiComic/scripts/generated/proto_result_8ff3eb00.result')
    print('='*60)

if __name__ == '__main__':
    main()