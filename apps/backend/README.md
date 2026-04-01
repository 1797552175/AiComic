# apps/backend - AI 创作动态漫后端

## 技术栈

- **Python 3.11+** with asyncio
- **FastAPI** — API 框架
- **SQLAlchemy + asyncpg** — 异步数据库
- **Pydantic** — 数据验证
- **Celery + Redis** — 异步任务队列
- **Docker** — 容器化部署

## 目录结构

```
backend/
├── api/              # API 路由
│   └── routes.py     # REST API 路由定义
├── models/           # 数据模型
│   ├── database.py   # 数据库连接
│   └── schemas.py    # Pydantic schemas
├── services/         # 核心业务逻辑
│   ├── storyboard.py      # 分镜生成服务
│   ├── image_generator.py # 图像生成服务
│   ├── motion_engine.py   # 动态化引擎
│   ├── audio_service.py   # 配音配乐服务
│   └── video_compositor.py # 视频合成服务
├── config/           # 配置管理
│   └── config.py    # Pydantic Settings（从 .env 读取）
├── utils/           # 工具函数
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 快速开始

```bash
cd apps/backend
cp ../../config/.env.example .env
# 填入真实 API Key
docker compose up -d
```

## 环境变量

详见 `../../config/.env.example`，所有配置通过 `config/config.py` 的 `Settings` 类管理。

## API 路由

启动后访问 `http://localhost:8000/docs` 查看 Swagger 文档。

| 端点 | 说明 |
|------|------|
| `POST /api/v1/storyboard` | 生成漫画分镜 |
| `POST /api/v1/generate-image` | 生成漫画图像 |
| `POST /api/v1/motion` | 动态化处理 |
| `POST /api/v1/audio` | 配音配乐 |
| `POST /api/v1/compose` | 视频合成 |
| `POST /api/projects/{project_id}/exports` | 导出任务创建 |
| `GET /api/exports/{task_id}` | 导出进度查询 |
| `GET /api/projects/{project_id}/share` | 分享信息生成 |
