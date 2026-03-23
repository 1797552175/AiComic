#!/bin/bash
# 注册优化 - 添加邮箱验证状态
cd /opt/AiComic/apps/backend
python3 << 'PYEOF'
import re

# 读取现有users.py
with open('api/users.py', 'r') as f:
    content = f.read()

# 添加 email_verified 字段到 User 模型
old_model = '''class User(Base):
    用户表模型
    __tablename__ = users

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)'''

new_model = '''class User(Base):
    用户表模型
    __tablename__ = users

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    email_verified = Column(Integer, default=0)  # 0=未验证, 1=已验证'''

content = content.replace(old_model, new_model)

with open('api/users.py', 'w') as f:
    f.write(content)

print('REGISTER_OPT_DONE')
PYEOF
