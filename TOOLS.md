# TOOLS.md - 项目工具说明

## 任务板

- **工具**：飞书多维表格
- **app_token**：`InUZbPrTZaRm5LsRz9jctF27nGu`
- **table_id**：`tblNWtihltzV0SOO`
- **链接**：https://ecnrw0lxawsd.feishu.cn/base/InUZbPrTZaRm5LsRz9jctF27nGu

### 状态选项

| 状态 | 含义 |
|------|------|
| 待分配 | 任务刚创建，等待 Bot 认领 |
| 进行中 | Bot 已认领，正在执行 |
| 待审核 | Bot 已完成，等待验收 |
| 已完成 | 验收通过，任务结束 |

## Server B 信息

| 项目 | 值 |
|------|-----|
| 地址 | `150.109.243.164` |
| SSH 用户 | `root` |
| Docker 容器 | `crewai-runtime`（带 `/opt/AiComic` 持久化挂载）|
| 脚本目录 | `/opt/AiComic/scripts/` |
| 输出目录 | `/opt/AiComic/scripts/output/` |

### 启动/重启 CrewAI 容器

```bash
# 方式1：用启动脚本（推荐）
bash /opt/AiComic/scripts/start_crewai.sh

# 方式2：用 docker-compose
cd /opt/AiComic/scripts && docker compose up -d

# 方式3：手动
docker stop crewai-runtime; docker rm crewai-runtime
docker run -d --name crewai-runtime \
  -v /opt/AiComic:/opt/AiComic \
  -w /opt/AiComic \
  python:3.11-slim sleep infinity
```

### 常用命令

```bash
# SSH 连接
ssh root@150.109.243.164

# 进入 Docker 容器
docker exec -it crewai-runtime bash

# 执行脚本（脚本在宿主机，容器内直接可见）
docker exec crewai-runtime python /opt/AiComic/scripts/generated/xxx.py

# 查看日志
docker logs -f crewai-runtime

# 重启容器
docker restart crewai-runtime
```

## 脚本模板库

**位置**：`/opt/AiComic/scripts/`

| 模板 | 用途 |
|------|------|
| `crud_template.py` | 增删改查操作 |
| `api_template.py` | REST API 开发 |
| `page_template.py` | 前端页面 |
| `multiagent_template.py` | 多 Agent 协作（最通用） |

**使用方式**：
```bash
python /opt/AiComic/scripts/generator.py \
  --type multiagent \
  --name "任务名称" \
  --output /opt/AiComic/scripts/generated/
```

## 应用代码

**后端**：`/opt/AiComic/apps/backend/`
- `services/` — 核心服务（storyboard、image、motion、audio、video）
- `api/` — API 路由
- `models/` — 数据模型
- `config/` — 配置管理（settings.py）

## 飞书群

- **项目群**：`oc_5159dddd87a707d99f3f2eb5e9beec9f`
- **架构文档**：`YXMCdbSWFo2JNoxvyXXcJRIon0b`

## Bot 目标会话

| Bot | 会话 Key |
|-----|---------|
| 研发机器人 | `agent:main:feishu:direct:ou_633e8feb08c1c9b318b707f23cba3850` |
| 产品经理 | `agent:main:feishu:direct:ou_1fc8e7e760b4403f1bfe021de16fdcb7` |
| 营销机器人 | `agent:main:feishu:direct:ou_0fe6e8361ab0874a8d7c0df9df1be598` |
| 状态监控 | `agent:main:feishu:direct:ou_8c538c96e404739a2377e837e50e2d4a` |

## 问题记录

| 日期 | 问题 | 解决方案 | 状态 |
|------|------|---------|------|
| 2026-03-23 | 容器无持久化挂载，容器内创建的文件宿主机看不到 | 启动容器加 `-v /opt/AiComic:/opt/AiComic` | ✅ 已修复 |
| 2026-03-23 | rsync 不可用 | 改用 `tar + scp` 同步文件 | ✅ 已绕过 |
| 2026-03-23 | 容器内 /opt/AiComic 不存在 | 启动脚本自动 mkdir | ✅ 已修复 |

---

## 完整流程问题记录（2026-03-23）

### 🔴 阻塞性问题

| 问题 | 原因 | 解决方案 | 状态 |
|------|------|---------|------|
| MiniMax API Key 无效 | API认证失败（401） | 需要用户提供有效的 MiniMax API Key | ⏳ 待修复 |
| 容器重启后文件不刷新 | volume mount 缓存问题 | 每次同步后需 `docker restart crewai-runtime` | ✅ 已发现 |
| Python 3.6 不兼容 dirs_exist_ok | copytree 参数 | 手动处理目录复制 | ✅ 已修复 |

### 🟡 CrewAI 1.11.0 API 变化

| 问题 | 旧写法 | 新写法 |
|------|--------|--------|
| Process 枚举 | `Process.parallel` | `Process.hierarchical`（需manager）或 `Process.sequential` |
| Task 依赖 | `task.context = [other_task]` | 仍可用，但 hierarchical 模式需要 manager_agent |
| memory 参数 | `memory=True` | 需验证 |
| Agent LLM | 默认 OPENAI_API_KEY | 需显式设置 `llm=f"openai/{model}"` 或安装 litellm |

### ⚠️ 待优化项

1. `generator.py` Python 3.6 兼容性问题
2. 容器 volume mount 每次同步后需重启
3. 模板中 MiniMax API Key 需要环境变量传入
4. litellm 尚未安装到容器（每次新装后重启丢失）

### ✅ 已验证可用的流程

1. ✅ 宿主机到 Server B 文件同步（tar+scp）
2. ✅ 容器启动带持久化挂载（docker run -v）
3. ✅ 脚本在容器内执行并保存到宿主机
4. ✅ litellm 安装后 CrewAI 可调用 MiniMax API（key有效时）
