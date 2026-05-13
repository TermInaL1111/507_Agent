# CLAUDE.md

507 Agent — 校园 AI 助手，5 个 Docker 服务：

| 服务 | 技术栈 | 端口 |
|------|--------|------|
| `frontend` | Vue 3 + Element Plus + Pinia | 80 |
| `backend` | FastAPI + LangChain (DeepSeek V3) + ChromaDB | 8000 |
| `django-user` | Django 5.2 + DRF + SimpleJWT | 8001 |
| mysql | MySQL 8.4 | 3306 |
| redis | Redis 7 | 6379 |

## 开发命令

```bash
cd backend && uv sync && uv run uvicorn main:app --port 8000 --reload
cd DjangoUserService && uv sync && uv run python manage.py migrate && uv run python manage.py runserver 127.0.0.1:8001
cd front && npm install && npm run dev
docker compose up -d --build   # 全栈部署
```

## 关键架构细节

**JWT 认证**: Django 签发 JWT (HS256)，FastAPI 用同一把 `SECRET_KEY` 解码。`.env` 里 `SECRET_KEY` 和 `DJANGO_SECRET_KEY` 必须一致，否则 401。

**Agent 系统** (`backend/app/agent/`):
- `AgentFactory` 创建 LangChain `AgentExecutor`，模型 **DeepSeek V3** (ChatOpenAI)
- **18 个工具**：RAG/重排序/天气/时间/用户信息/课表(3个)/校园(2个)/培养方案/选课/文书生成/FAQ推荐/业务入口/时间节点提取/记忆存储/记忆读取
- ReAct 模式: Thought → Action → Observation 流式可视化
- 用户上下文通过 `contextvars` 注入 + System Prompt 个性化
- Memory Tool: Redis 存储/读取用户偏好 (HelloAgents 模式)
- SSE 流式事件: `thought`, `response`, `tool_call`, `tool_result`, `sources`, `done`, `error`
- 课表查询直接走 Agent (已删除 regex pre-check)

**请求路由** (Nginx in frontend container):
- `/api/*` → backend:8000
- `/user/*`, `/file/*` → django-user:8001

**前端** (`front/src/views/`):
- AIChat.vue: SSE 流式 + ReAct 可视化 + 8 种 result_card + 收藏 + 可信度
- Schedule.vue: 周/日视图 + Gantt + AgentPanel + Agent FAB + 周偏移
- CampusMap.vue: 双校区筛选 + 高德地图标注 + AgentPanel
- Bookmarks.vue: 我的收藏
- AgentPanel.vue: 嵌入式侧边 Agent (课表/导航页复用)

**数据库**: backend 用 SQLAlchemy async + aiomysql。ChatHistory、ScheduleEvent、SourceFile 三个 ORM 模型在 `chat_history` 库。

**当前分支**: `agent-centric` — 正在从传统菜单式 UI 改造为 Agent 对话中心化界面。原始分支 `version1.0`。

## 注意事项

- 所有 Dockerfile 已配置阿里云镜像源 (apt/pip/npm)，国内部署无需翻墙
- `docker-compose.yml` 需要 v2 (不能用 v1.29.2，不兼容 Docker 29.x)
- 前端构建时需要 `VITE_AMAP_KEY` 和 `VITE_AMAP_SECURITY_CODE`，作为 Docker build args 传入
- `Training Program/` 目录以只读方式挂载到 backend 容器用于文档检索
- 不要提交 `.env` 文件
