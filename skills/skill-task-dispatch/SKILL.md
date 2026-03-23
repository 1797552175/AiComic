# Skill: task-dispatch

> 状态监控机器人专用 - 任务下发

## 功能

通过 HTTP 接口向各 Bot 下发任务。

## 使用方法

```python
from skill_task_dispatch import dispatch_task, BOT_PORTS

# 下发任务
task = {
    "task_id": "T005",
    "task_type": "dev",
    "source": "状态监控机器人",
    "target": "研发机器人",
    "payload": {
        "任务描述": "T005 前端开发",
        "优先级": "P0",
        "依赖文件": []
    }
}

result = dispatch_task("dev", task)
```

## Bot 端口配置

| Bot | 端口 |
|-----|------|
| 产品经理机器人 | 8002 |
| 研发机器人 | 8003 |
| 营销机器人 | 8004 |

## 核心原则

⚠️ 状态监控机器人只负责分发任务，不自己执行！
