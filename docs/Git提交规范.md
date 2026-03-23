# Git 提交规范（统一版）

## 格式
```
<type>: <task_id> - <简短描述>
```

## Type 类型
| Type | 用途 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat: T010 - 用户登录认证` |
| `fix` | Bug修复 | `fix: TODO-IMG-001 - 修复图生图空指针` |
| `docs` | 文档更新 | `docs: 更新架构文档` |
| `refactor` | 重构 | `refactor: 重构认证模块` |
| `chore` | 维护任务 | `chore: 更新依赖版本` |

## 规则
1. **必须 push**：禁止只 commit 不 push
2. **任务ID必须**：所有 commit 必须关联任务ID
3. **描述简洁**：不超过50字
4. **禁止无关提交**：不允许提交与任务无关的代码

## 示例
```bash
git add .
git commit -m "feat: T010 - 用户登录认证功能"
git push origin main
```
