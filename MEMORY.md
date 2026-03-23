# MEMORY.md - 长期记忆

## 多Agent协作体系（2026-03-22）

### 架构文档
- **飞书文档**：https://ecnrw0lxawsd.feishu.cn/docx/YXMCdbSWFo2JNoxvyXXcJRIon0b
- 系统架构文档 - 多Agent协作体系

---

### 整体架构（两层）

| 层级 | 名称 | 职责 |
|------|------|------|
| Server A | OpenClaw 飞书Bot协作层 | 任务接收、分发、结果汇总 |
| Server B | CrewAI 任务执行层 | 任务执行、Claude Code多实例调度 |

**Server B 信息：**
- IP：150.109.243.164
- SSH：已与 Server A 打通（root@150.109.243.164）
- Docker容器：crewai-runtime（python:3.11-slim）
- CrewAI版本：1.11.0 + CrewAI-Tools 1.11.0
- 模型：MiniMax-M2.7-highspeed
- API：https://api.minimax.chat/v1
- 运行命令：`docker exec crewai-runtime python <脚本>.py`

---

### 4个飞书Bot职责

| Bot名称 | AppID | 主要职责 |
|---------|-------|---------|
| 状态监控机器人 | cli_a93532ba81f9dcbd | 总协调、任务分发、状态监控 |
| Claw产品经理机器人 | cli_a935c8fb40b8dccc | 竞品分析、输出原型文档 |
| Claw研发机器人 | cli_a9256d0e6b625cef | 读取原型，通过SSH下发到Server B |
| Claw营销机器人 | cli_a935f3edee78dcd1 | 验证代码、输出营销方案 |

**沟通媒介**：飞书多维表格（Bitable）
**调度方式**：状态监控机器人统一调度，发现空闲Bot主动分配任务

---

### 共享目录（/opt/AiComic/）

```
/opt/AiComic/
├── docs/           # 产品经理输出（设计文档、PRD）
├── 原型/           # 产品经理输出（原型描述）
├── 代码/           # 研发输出（必须git push）
├── 营销方案/       # 营销输出（推广方案）
└── 状态报告/      # 状态监控输出
```

---

### 工作流

```
用户 → 飞书 → 状态监控机器人
              ↓
       产品经理机器人
       （竞品分析 → 原型文档 → 写入 /opt/AiComic/原型/）
              ↓
       研发机器人
       （读取原型 → 通过SSH下发到Server B）
              ↓
       CrewAI
       （任务分解 → 并行调度多个Claude Code实例）
              ↓
       Claude Code实例 × N
       （前端/后端/测试分工执行）
              ↓
       结果写回 /opt/AiComic/代码/ → git push
              ↓
       营销机器人
       （验证代码 → 输出营销方案）
```

---

### Bot职责详解

**状态监控机器人**
- 定时轮询各目录（docs/、代码/、营销方案/）
- 发现新文件时主动@对应Bot告知任务
- 每5分钟检查各Bot活跃状态
- 发现空闲Bot主动思考下一步任务并在群里@分配

**产品经理机器人**
- 输出目录：/opt/AiComic/docs/ 和 /opt/AiComic/原型/
- 文件命名：任务名_YYYYMMDD.md
- 完成后在群里@Claw研发机器人告知开始干活

**研发机器人**
- 读取：/opt/AiComic/docs/ 下的需求文档
- 输出：/opt/AiComic/代码/
- 完成后自动 git add . && git commit && git push
- commit格式：feat: [需求文档名] - [简要描述]
- 完成后在群里@Claw营销机器人告知可验证

**营销机器人**
- 读取：/opt/AiComic/docs/ 和 /opt/AiComic/原型/
- 验证代码是否符合原型
- 如有问题：在群里@产品经理机器人提需求
- 如无问题：输出营销方案到 /opt/AiComic/营销方案/

---

### 重要原则

1. 每个Bot只读写自己负责的目录，不越权操作他Bot的产出
2. 代码必须git push，不能只写本地
3. 所有对外消息必须@目标Bot
4. 空闲时主动向状态监控机器人询问"我可以做什么"

---

### 密钥/账号信息

- **MiniMax API Key**：sk-cp-X-OrjwZ_qtWkXMytgCnkP28VhiHEhKQ3aGdtIJEHpfE9fmO0jTL4VRewWUjMQhMhvJeNFE5l3FgPhjnXA_hW7ifdA3Sm9uv2mraenxVJzUYNYbf2MvGtb_g
- **CrewAI运行命令**：docker exec crewai-runtime python <脚本>.py
- **Server B SSH**：root@150.109.243.164

---

## 项目：博客（/opt/my-blog）

每次改代码、改bug都在这个目录进行。

---

## 教训

### SSH后台任务管理（2026-03-22）
**问题：** 创建了多个未明确要求的后台SSH exec任务，连接远程服务器，导致大量失败记录。

**原则：**
- 不要主动创建后台exec任务连接远程服务器，除非用户明确要求
- 如果exec预计超过30秒才后台跑+定期推送进度
- 禁止在用户未同意的情况下创建重复的后台任务

---

## 用户偏好与上下文

- 用户使用飞书与OpenClaw交互
- 目标：搭建多Agent协作系统，自动完成产品设计→开发→营销全流程
- 项目目录：/opt/AiComic/

## 多Agent协作体系（2026-03-22 完整版）

### 架构文档
- 飞书文档：https://ecnrw0lxawsd.feishu.cn/docx/YXMCdbSWFo2JNoxvyXXcJRIon0b
- 系统架构文档 - 多Agent协作体系（完整版）

### 两层架构
- **Server A（OpenClaw）**：飞书多Bot协作层，IP: 当前服务器
  - 托管 4 个飞书 Bot
  - Bot列表：
    - 状态监控机器人：cli_a93532ba81f9dcbd（总协调、任务分发）
    - Claw产品经理机器人：cli_a935c8fb40b8dccc（竞品分析、原型文档）
    - Claw研发机器人：cli_a9256d0e6b625cef（读取原型、SSH下发到Server B）
    - Claw营销机器人：cli_a935f3edee78dcd1（验证代码、营销方案）
- **Server B（CrewAI）**：任务执行层，IP: 150.109.243.164
  - Docker容器：crewai-runtime（python:3.11-slim）
  - CrewAI版本：1.11.0 + CrewAI-Tools 1.11.0
  - 模型：MiniMax-M2.7-highspeed
  - API接口：https://api.minimax.chat/v1
  - SSH：root@150.109.243.164（已与Server A打通）

### 共享目录
/opt/AiComic/
- docs/：产品经理输出（设计文档、PRD）
- 原型/：产品经理输出（原型描述）
- 代码/：研发输出（必须git push）
- 营销方案/：营销输出（推广方案）
- 状态报告/：状态监控输出

### 工作流
用户 → 飞书 → 状态监控机器人 → 产品经理机器人 → 研发机器人 → CrewAI → Claude Code × N → 营销机器人 → 汇总

### MiniMax API Key
sk-cp-X-OrjwZ_qtWkXMytgCnkP28VhiHEhKQ3aGdtIJEHpfE9fmO0jTL4VRewWUjMQhMhvJeNFE5l3FgPhjnXA_hW7ifdA3Sm9uv2mraenxVJzUYNYbf2MvGtb_g

### CrewAI运行命令
docker exec crewai-runtime python <脚本>.py
