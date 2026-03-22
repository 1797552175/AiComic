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
| Docker 容器 | `crewai-runtime` |
| 脚本目录 | `/opt/AiComic/scripts/` |
| 输出目录 | `/opt/AiComic/scripts/output/` |

### 常用命令

```bash
# SSH 连接
ssh root@150.109.243.164

# 进入 Docker 容器
docker exec -it crewai-runtime bash

# 执行脚本
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
