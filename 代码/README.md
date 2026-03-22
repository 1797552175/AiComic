# AI创作动态漫 - 后端服务

## 项目结构

```
代码/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI 入口
│   └── config.py         # 配置管理
├── models/
│   ├── __init__.py
│   ├── database.py      # SQLAlchemy 模型
│   └── schemas.py       # Pydantic schemas
├── services/
│   ├── __init__.py
│   ├── script_parser.py # 剧本解析服务
│   └── storyboard.py    # 分镜生成服务
├── api/
│   ├── __init__.py
│   └── routes.py        # API 路由
├── utils/
│   ├── __init__.py
│   └── helpers.py       # 工具函数
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API 文档

启动服务后访问: http://localhost:8000/docs
