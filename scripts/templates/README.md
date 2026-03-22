# CrewAI 脚本模板库

## 目录结构

```
scripts/
├── common/               # 公共模块
│   ├── __init__.py
│   └── base.py          # TaskOutput, save_output 等工具
├── templates/            # 脚本模板
│   ├── crud_template.py        # 增删改查
│   ├── api_template.py         # REST API 开发
│   ├── page_template.py        # 前端页面
│   ├── batch_template.py       # 批处理任务
│   ├── crawler_template.py     # 数据采集
│   ├── test_template.py        # 测试用例生成
│   └── multiagent_template.py  # 多Agent协作
└── generator.py                # 模板生成器
```

## 模板列表

### crud_template.py
适用场景：需要对某个实体做完整的增删改查
参数：entity(实体名), fields(字段列表), framework, database

### api_template.py
适用场景：开发一组REST API端点
参数：api_name, endpoints(端点列表), framework, auth_method

### page_template.py
适用场景：开发前端页面
参数：pages(页面列表), frontend_framework, ui_library, style

### multiagent_template.py
适用场景：复杂任务需要多个Agent分工协作
参数：agents(Agent配置), task_description, parallel

## 使用流程

1. 研发机器人读取原型文档
2. 确定任务类型，选择合适模板
3. 填充 CONFIG 字典参数
4. SSH 到 Server B，执行脚本

## 在 Server B 上执行

```bash
# 先同步模板（如果 Server A 有更新）
scp -r /opt/AiComic/scripts root@150.109.243.164:/opt/AiComic/scripts

# 在 Server B 上执行
docker exec crewai-runtime python /opt/AiComic/scripts/templates/crud_template.py
```
