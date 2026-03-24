"""
AI创作动态漫 - FastAPI 应用入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router as api_router
from config.config import settings

app = FastAPI(
    title="AI创作动态漫 API",
    description="从文字剧本到动态漫视频的一站式创作平台",
    version="1.0.0",
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "AI创作动态漫 API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
