#!/usr/bin/env python3
"""
正确的 litellm 执行器
"""
import os
import sys
sys.path.insert(0, '/opt/AiComic/scripts')
from common import TaskOutput, save_output, ensure_dir
import litellm

PROTOTYPE_CONTENT = """原型内容占位"""

CONFIG = {
    "task_name": "test",
    "output_dir": "/opt/AiComic/scripts/output/",
    "project_root": "/opt/AiComic",
    "model": "MiniMax-M2.7-highspeed",
}

def call_llm(prompt, max_tokens=4096):
    response = litellm.completion(
        model="openai/MiniMax-M2.7-highspeed",
        messages=[{"role": "user", "content": prompt}],
        api_key=os.environ.get("MINIMAX_API_KEY"),
        base_url="https://api.minimax.chat/v1",
        max_tokens=max_tokens,
        temperature=0.3
    )
    return response["choices"][0]["message"]["content"]

if __name__ == "__main__":
    print("Testing litellm...")
    result = call_llm("Say 'Hello World' in exactly 3 words")
    print(f"Result: {result}")
