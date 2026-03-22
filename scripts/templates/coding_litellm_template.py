"""
litellm 直接调用模板 - 最简单可靠的方案
直接用 litellm 调用 MiniMax，不依赖 CrewAI 的 tool calling

⚠️ 需要环境变量:
export OPENAI_API_KEY=sk-cp-X-OrjwZ_qtWkXMytgCnkP28VhiHEhKQ3aGdtIJEHpfE9fmO0jTL4VRewWUjMQhMhvJeNFE5l3FgPhjnXA_hW7ifdA3Sm9uv2mraenxVJzUYNYbf2MvGtb_g
export OPENAI_BASE_URL=https://api.minimax.chat/v1
"""

import os
import sys
sys.path.insert(0, '/opt/AiComic/scripts')
from common import TaskOutput, save_output, ensure_dir

import litellm

CONFIG = {
    "task_name": "用户注册API开发",
    "output_dir": "/opt/AiComic/scripts/output/",
    "target_file": "/opt/AiComic/apps/backend/api/users.py",
    "model": "MiniMax-M2.7-highspeed"
}

litellm.drop_params = True
litellm.set_verbose = False

def call_llm(prompt):
    response = litellm.completion(
        model=f"openai/{CONFIG['model']}",
        messages=[{"role": "user", "content": prompt}],
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        max_tokens=4096,
        temperature=0.3
    )
    return response["choices"][0]["message"]["content"]

def extract_code(response_text):
    import re
    code_match = re.search(r'```python\s*(.*?)\s*```', response_text, re.DOTALL)
    if code_match:
        return code_match.group(1)
    # 如果没有markdown块，尝试普通文本
    code_match = re.search(r'(from\s+fastapi.*)', response_text, re.DOTALL)
    if code_match:
        return code_match.group(0)
    return response_text

def write_and_check_syntax(code, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        f.write(code)
    
    # 语法检查
    import py_compile
    try:
        py_compile.compile(filepath, doraise=True)
        return True, "语法检查通过"
    except py_compile.PyCompileError as e:
        return False, f"语法错误: {e}"

if __name__ == "__main__":
    output = TaskOutput(CONFIG["task_name"])
    ensure_dir(CONFIG["output_dir"])
    
    # 构建 prompt
    prompt = f"""请根据以下需求生成完整的Python代码（FastAPI用户注册API）：

需求：
1. POST /api/users/register 接口
2. 接收 username, email, password
3. 邮箱格式校验、密码长度>=8
4. bcrypt hash 存储密码
5. 返回 user_id 和 JWT token

要求：
- 使用 FastAPI + Pydantic + SQLAlchemy（mock即可）
- 输出完整可运行的代码
- 用 markdown python 代码块包裹

输出文件：{CONFIG['target_file']}"""

    print(f"开始生成代码... (model: {CONFIG['model']})")
    result = call_llm(prompt)
    
    # 保存原始结果
    save_output(result, f"{CONFIG['output_dir']}{CONFIG['task_name']}_raw.txt")
    
    # 提取并写入代码
    code = extract_code(result)
    success, msg = write_and_check_syntax(code, CONFIG['target_file'])
    
    if success:
        print(f"✅ {msg}: {CONFIG['target_file']}")
        # 读取生成的文件内容摘要
        with open(CONFIG['target_file']) as f:
            lines = len(f.readlines())
        save_output(f"生成成功，共{lines}行代码。文件: {CONFIG['target_file']}",
                   f"{CONFIG['output_dir']}{CONFIG['task_name']}_done.txt")
    else:
        print(f"⚠️ {msg}")
        save_output(f"生成失败: {msg}\n\n原始结果:\n{result}",
                   f"{CONFIG['output_dir']}{CONFIG['task_name']}_error.txt")
    
    print(output.summary())
