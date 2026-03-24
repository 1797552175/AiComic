"""
AiComic FastAPI 主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from api.routes import router

__version__ = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    print("[AiComic] 应用启动")
    yield
    print("[AiComic] 应用关闭")


app = FastAPI(
    title="AiComic API",
    description="AI 漫画生成 API",
    version=__version__,
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(router, prefix="/api", tags=["ai comic"])


@app.get("/")
async def root():
    return {"message": "AiComic API", "version": __version__}


@app.get("/health")
async def health():
    return {"status": "ok"}
