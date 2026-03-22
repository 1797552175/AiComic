# AiComic · AI 动态漫创作平台

> 让漫画动起来——从文字剧本到动态漫视频的一站式创作平台。

## 📁 项目结构

```
AiComic/
├── README.md            # 项目说明
├── AGENTS.md            # AI 协作者开发指引
├── SOUL.md             # AI 协作行为规范
├── IDENTITY.md         # 项目身份与定位
├── PROJECT_SPEC.md     # 产品规格与路线图
├── .cursorrules        # 编码规范
├── .cursorignore       # Cursor AI 忽略配置
├── .cursor/rules/      # Cursor 项目知识库
├── apps/               # 应用代码（monorepo 风格）
│   ├── backend/        # Python/FastAPI 后端
│   │   ├── api/        # API 路由
│   │   ├── models/     # 数据模型
│   │   ├── services/   # 核心服务（分镜/图像/动态化/合成）
│   │   ├── config/     # 配置管理
│   │   ├── utils/      # 工具函数
│   │   ├── Dockerfile
│   │   ├── docker-compose.yml
│   │   └── requirements.txt
│   └── frontend/       # Next.js 前端（待开发）
├── scripts/             # CrewAI 脚本模板库
│   ├── templates/       # 脚本模板（crud/api/page/multiagent）
│   ├── common/         # 公共模块
│   └── generator.py    # 脚本生成器
├── config/              # 环境配置模板
├── docs/               # 产品需求文档（PRD）
├── 原型/               # 功能原型设计
├── scripts/            # CrewAI 脚本模板库
├── test/               # 测试文件
└── 营销方案/           # 营销推广方案
```

## 🎯 核心链路

```
剧本输入 → AI 分镜 → 画面生成 → 动态化 → 配音配乐 → 合成输出
```

## 👥 团队角色

| Bot | 职责 | 输出 |
|-----|------|------|
| 状态监控 | 总协调、任务分发 | 任务板 |
| 产品经理 | 竞品分析、PRD、原型 | `docs/`、`原型/` |
| 研发 | 技术方案、CrewAI 脚本、代码 | `apps/backend/` |
| 营销 | 竞品验证、营销方案 | `营销方案/` |

## 🚀 快速开始

### 后端启动

```bash
cd apps/backend
cp config/.env.example .env
# 编辑 .env 填入真实 API Key
docker compose up -d
```

### 执行 CrewAI 脚本

```bash
# 生成脚本
python scripts/generator.py \
  --type multiagent \
  --name "分镜生成" \
  --output /opt/AiComic/scripts/generated/

# 同步到 Server B
scp /opt/AiComic/scripts/generated/xxx.py root@150.109.243.164:/opt/AiComic/scripts/generated/

# 在 Server B 执行
docker exec crewai-runtime python /opt/AiComic/scripts/generated/xxx.py
```

### Git 规范

```bash
git add .
git commit -m "feat: [需求名] - [简要描述]"
git push
```

## 📄 产出文档

| 文档 | 状态 |
|------|------|
| 产品需求文档（PRD） | ✅ 已完成 |
| 功能原型设计 v2.1 | ✅ 已完成 |
| 技术架构设计 | ✅ 已完成 |
| 竞品分析报告 | ✅ 已完成 |
| 后端代码实现 | 🚧 进行中 |
| 前端实现 | ⏳ 待开始 |
| 营销方案 | ⏳ 待开始 |

## 🔗 关键链接

- **任务板**：https://ecnrw0lxawsd.feishu.cn/base/InUZbPrTZaRm5LsRz9jctF27nGu
- **架构文档**：https://ecnrw0lxawsd.feishu.cn/docx/YXMCdbSWFo2JNoxvyXXcJRIon0b
- **Git 仓库**：git@github.com:1797552175/AiComic.git

---

_最后更新：2026-03-22_
