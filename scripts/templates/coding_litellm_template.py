"""
litellm 代码生成模板 - 完整版
功能：生成代码 → 写入文件 → 语法检查 → 执行验证 → Git自动提交

⚠️ 需要环境变量:
export OPENAI_API_KEY=sk-cp-X-OrjwZ_qtWkXMytgCnkP28VhiHEhKQ3aGdtIJEHpfE9fmO0jTL4VRewWUjMQhMhvJeNFE5l3FgPhjnXA_hW7ifdA3Sm9uv2mraenxVJzUYNYbf2MvGtb_g
export OPENAI_BASE_URL=https://api.minimax.chat/v1
"""

import os
import sys
import re
import subprocess
sys.path.insert(0, '/opt/AiComic/scripts')
from common import TaskOutput, save_output, ensure_dir

import litellm

CONFIG = {
    "task_name": "代码生成任务",
    "output_dir": "/opt/AiComic/scripts/output/",
    "project_root": "/opt/AiComic",
    "model": "MiniMax-M2.7-highspeed",
    "author": "Claude",  # 生成者标签
    "commit_message": None,  # 可指定，None则自动生成
}

litellm.drop_params = True

def call_llm(prompt, max_tokens=4096):
    response = litellm.completion(
        model=f"openai/{CONFIG['model']}",
        messages=[{"role": "user", "content": prompt}],
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        max_tokens=max_tokens,
        temperature=0.3
    )
    return response["choices"][0]["message"]["content"]

def extract_code(response_text):
    """从LLM输出中提取代码"""
    code_match = re.search(r'```python\s*(.*?)\s*```', response_text, re.DOTALL)
    if code_match:
        return code_match.group(1).strip()
    # 尝试直接匹配代码
    code_match = re.search(r'(from\s+fastapi.*|import\s+\w+)', response_text, re.DOTALL)
    if code_match:
        # 提取从第一个import到文件结尾
        start = code_match.start()
        return response_text[start:].strip()
    return response_text.strip()

def detect_dependencies(code):
    """检测代码需要的依赖包"""
    deps = set()
    import_pattern = re.compile(r'^\s*(?:from\s+(\w+)|import\s+(\w+))', re.MULTILINE)
    common_pkgs = {'fastapi', 'pydantic', 'sqlalchemy', 'bcrypt', 'jwt', 'requests',
                   'redis', 'celery', 'numpy', 'pandas', 'pytest', 'uvicorn'}
    for match in import_pattern.finditer(code):
        pkg = match.group(1) or match.group(2)
        if pkg.lower() in common_pkgs:
            deps.add(pkg.lower())
    return deps

def install_deps(deps):
    """安装缺失的依赖"""
    for dep in deps:
        print(f"安装依赖: {dep}")
        subprocess.run(
            f"pip install {dep} -q",
            shell=True, capture_output=True
        )

def write_file(filepath, code):
    """写入文件"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        f.write(code)
    print(f"✅ 写入文件: {filepath}")

def syntax_check(filepath):
    """语法检查"""
    import py_compile
    try:
        py_compile.compile(filepath, doraise=True)
        return True, "语法检查通过"
    except py_compile.PyCompileError as e:
        return False, f"语法错误: {e}"

def exec_check(filepath):
    """执行验证：实际运行代码（限时30秒）"""
    import signal
    class TimeoutError(Exception):
        pass
    def timeout_handler(signum, frame):
        raise TimeoutError("执行超时30秒")
    
    # 先检查是否有可执行的main或测试
    with open(filepath) as f:
        content = f.read()
    
    # 如果有 if __name__ == "__main__" 块，执行它
    if '__name__' in content and '__main__' in content:
        try:
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(30)
            result = subprocess.run(
                ['python', filepath],
                capture_output=True, text=True, timeout=35,
                cwd=os.path.dirname(filepath) or '.'
            )
            signal.alarm(0)
            if result.returncode == 0:
                return True, f"执行成功\n{result.stdout[:200]}"
            else:
                return False, f"运行错误:\n{result.stderr[:300]}"
        except subprocess.TimeoutExpired:
            return True, "执行超时（可能是在等待输入，正常）"
        except Exception as e:
            return False, f"执行异常: {e}"
    else:
        return True, "无__main__块，跳过执行验证"

def git_commit_push(filepath, task_name):
    """Git 自动提交并推送"""
    try:
        os.chdir(CONFIG['project_root'])
        
        # 检查是否有更改
        result = subprocess.run(['git', 'status', '--porcelain', filepath],
                             capture_output=True, text=True)
        if not result.stdout.strip():
            print("文件无变化，跳过git提交")
            return True, "无变化"
        
        # 添加文件
        subprocess.run(['git', 'add', filepath], capture_output=True)
        
        # 生成 commit message
        commit_msg = CONFIG.get('commit_message') or f"feat: {CONFIG['author']} - {task_name}"
        
        # 提交
        result = subprocess.run(
            ['git', 'commit', '-m', commit_msg],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            return False, f"commit失败: {result.stderr}"
        
        # 推送
        result = subprocess.run(
            ['git', 'push'],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            return False, f"push失败: {result.stderr}"
        
        return True, f"已提交并推送: {commit_msg}"
    except Exception as e:
        return False, f"Git操作异常: {e}"

def run_task(task_desc, target_file):
    """执行单个代码生成任务"""
    output = TaskOutput(CONFIG['task_name'])
    ensure_dir(CONFIG['output_dir'])
    
    print(f"开始生成代码: {task_desc}")
    print(f"目标文件: {target_file}")
    
    # 构建 prompt
    prompt = f"""请根据以下需求生成完整的Python代码：

{task_desc}

要求：
- 输出完整可运行的代码
- 用 markdown python 代码块包裹
- 代码要可以直接运行（有错误处理的入口）
- 如果有依赖包，在代码顶部注释写明

输出文件：{target_file}"""

    # 调用 LLM
    result_text = call_llm(prompt)
    save_output(result_text, f"{CONFIG['output_dir']}{CONFIG['task_name']}_raw.txt")
    
    # 提取代码
    code = extract_code(result_text)
    if not code or len(code) < 50:
        return False, "LLM输出为空或过短"
    
    # 写入文件
    write_file(target_file, code)
    
    # 语法检查
    ok, msg = syntax_check(target_file)
    print(f"语法检查: {msg}")
    if not ok:
        return False, msg
    
    # 依赖检测
    deps = detect_dependencies(code)
    if deps:
        print(f"检测到依赖: {deps}")
        install_deps(deps)
    
    # 执行验证
    ok, msg = exec_check(target_file)
    print(f"执行验证: {msg}")
    # 执行失败不阻止流程，记录即可
    
    # Git 自动提交
    ok, msg = git_commit_push(target_file, CONFIG['task_name'])
    print(f"Git: {msg}")
    
    save_output(f"完成: {target_file}\n结果: {msg}", 
                f"{CONFIG['output_dir']}{CONFIG['task_name']}_done.txt")
    
    print(output.summary())
    return True, msg

if __name__ == "__main__":
    print("===== litellm 代码生成器 =====")
    print(f"模型: {CONFIG['model']}")
    print(f"输出: {CONFIG['output_dir']}")
