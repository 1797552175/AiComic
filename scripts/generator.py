#!/usr/bin/env python3
"""
CrewAI 脚本生成器
根据原型文档自动生成填充好的脚本

用法:
  python generator.py --type crud --name 用户管理 --output /opt/AiComic/scripts/generated/
  python generator.py --type api --name 认证模块 --output /opt/AiComic/scripts/generated/
  python generator.py --type page --name 商品详情 --output /opt/AiComic/scripts/generated/
  python generator.py --type multiagent --name 电商开发 --output /opt/AiComic/scripts/generated/
"""

import argparse
import os
import sys
import shutil
from datetime import datetime

TEMPLATES_DIR = "/opt/AiComic/scripts/templates"
COMMON_DIR = "/opt/AiComic/scripts/common"

TEMPLATE_MAP = {
    "crud": "crud_template.py",
    "api": "api_template.py",
    "page": "page_template.py",
    "multiagent": "multiagent_template.py",
}

def generate(task_type: str, task_name: str, output_dir: str):
    if task_type not in TEMPLATE_MAP:
        print(f"未知类型: {task_type}")
        print(f"可用类型: {', '.join(TEMPLATE_MAP.keys())}")
        sys.exit(1)
    
    template_file = TEMPLATE_MAP[task_type]
    template_path = os.path.join(TEMPLATES_DIR, template_file)
    
    if not os.path.exists(template_path):
        print(f"模板不存在: {template_path}")
        sys.exit(1)
    
    # 读取模板
    with open(template_path) as f:
        content = f.read()
    
    # 替换任务名和日期
    date_str = datetime.now().strftime("%Y%m%d")
    safe_name = task_name.replace(" ", "_")
    
    content = content.replace(
        'task_name = "用户管理CRUD"',
        f'task_name = "{task_name}"'
    )
    content = content.replace(
        'task_name = "用户认证API"',
        f'task_name = "{task_name}"'
    )
    content = content.replace(
        'task_name = "用户注册页面"',
        f'task_name = "{task_name}"'
    )
    content = content.replace(
        'task_name = "电商商品详情页开发"',
        f'task_name = "{task_name}"'
    )
    
    # 输出文件
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{safe_name}_{date_str}.py")
    
    with open(output_file, 'w') as f:
        f.write(content)
    
    print(f"✓ 脚本已生成: {output_file}")
    
    # 同时复制 common 目录
    common_dest = os.path.join(output_dir, "common")
    if os.path.exists(COMMON_DIR):
        shutil.copytree(COMMON_DIR, common_dest, dirs_exist_ok=True)
        print(f"✓ 公共模块已复制: {common_dest}")
    
    return output_file


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CrewAI 脚本生成器")
    parser.add_argument("--type", "-t", required=True, 
                        choices=["crud", "api", "page", "multiagent"],
                        help="任务类型")
    parser.add_argument("--name", "-n", required=True,
                        help="任务名称")
    parser.add_argument("--output", "-o", default="/opt/AiComic/scripts/generated/",
                        help="输出目录")
    
    args = parser.parse_args()
    generate(args.type, args.name, args.output)
