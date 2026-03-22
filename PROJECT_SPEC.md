# PROJECT_SPEC.md - 产品规格与路线图

> 最后更新：2026-03-22

## 产品愿景

**一句话**：让漫画创作者通过 AI 将静态漫画一键动态化，生成可配音的动态漫视频。

**核心价值**：降低动态漫制作门槛，让创作者专注于创意本身。

---

## 核心功能

### P0 - MVP（必须完成）

| 功能 | 状态 |
|------|------|
| 剧本输入（用户输入漫画脚本） | 🚧 进行中 |
| AI 分镜（将剧本拆分为画面描述） | 🚧 进行中 |
| 画面生成（调用图像生成模型） | 🚧 进行中 |
| 动态化（让静态画面产生动效） | ⏳ 待开始 |
| 配音配乐（AI 生成配音和 BGM） | ⏳ 待开始 |
| 视频合成（将所有元素合成为视频） | ⏳ 待开始 |

### P1 - 下一版本

- 多角色协同（不同 Agent 负责不同模块）
- 风格一致性控制（保持画风统一）
- 用户自定义画风模板

### P2 - 规划中

- 社区分享（作品展示、点赞、评论）
- 创作者经济（付费解锁高级风格）
- API 开放（供其他平台接入）

---

## 技术架构

### 目录规范（monorepo）

```
apps/
├── backend/           # Python/FastAPI 后端
│   ├── api/           # API 路由
│   ├── models/       # 数据模型（数据库 schema）
│   ├── services/     # 核心业务服务
│   │   ├── storyboard.py      # 分镜生成
│   │   ├── image_generator.py  # 图像生成
│   │   ├── motion_engine.py    # 动态化引擎
│   │   ├── audio_service.py   # 配音配乐
│   │   └── video_compositor.py # 视频合成
│   ├── config/        # 配置管理
│   ├── utils/        # 工具函数
│   ├── Dockerfile
│   └── docker-compose.yml
└── frontend/         # Next.js 前端（待开发）
```

### 协同架构

```
Server A（OpenClaw · 飞书 Bot 协作层）
    用户 → 状态监控（协调） → 产品经理 → 原型/PRD
                        → 研发 → CrewAI 脚本 → Server B
Server B（CrewAI + Claude Code 执行）
    脚本执行 → 输出到 apps/backend/ 或 /opt/AiComic/scripts/output/
```

### 关键约定

1. **所有代码必须 git push**：`git@github.com:1797552175/AiComic.git`
2. **commit 格式**：`feat: [需求名] - [简要描述]`
3. **CrewAI 脚本**优先使用 `scripts/templates/` 中的模板
4. **任务板**：`InUZbPrTZaRm5LsRz9jctF27nGu`
5. **沟通**：飞书项目群 `oc_5159dddd87a707d99f3f2eb5e9beec9f`
