# CLAUDE.md

507 Agent — 校园 AI 助手，3 个 Docker 服务：

| 服务 | 技术栈 | 端口 |
|------|--------|------|
| `frontend` | Vue 3 + Element Plus + Pinia | 80 |
| `backend` | FastAPI + LangChain (Qwen via DashScope) + ChromaDB | 8000 |
| `django-user` | Django 5.2 + DRF + SimpleJWT | 8001 |
| mysql | MySQL 8.4 (chat_history + django_user_service) | 3306 |
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
- `AgentFactory` 创建 LangChain `AgentExecutor`，模型 ChatTongyi (Qwen3-Max)，12 个工具
- 工具列表：RAG 摘要、重排序、天气、时间、用户信息、**整周课表、今日课表、创建日程、搜索校园地点、路线规划、培养方案检索、选课推荐**
- 用户上下文通过 `contextvars` 注入，工具调用时自动获取 user_id
- SSE 流式事件类型: `response`, `tool_call`, `tool_result`, `sources`, `done`, `error`

**请求路由** (Nginx in frontend container):
- `/api/*` → backend:8000
- `/user/*`, `/file/*` → django-user:8001

**前端聊天** (`front/src/views/AIChat.vue`):
- SSE 流式接收，支持 4 种 result_card: answer / recommendation / navigation / check
- Markdown 渲染 (marked + highlight.js + DOMPurify)

**数据库**: backend 用 SQLAlchemy async + aiomysql。ChatHistory、ScheduleEvent、SourceFile 三个 ORM 模型在 `chat_history` 库。

**当前分支**: `agent-centric` — 正在从传统菜单式 UI 改造为 Agent 对话中心化界面。原始分支 `version1.0`。

## 注意事项

- 所有 Dockerfile 已配置阿里云镜像源 (apt/pip/npm)，国内部署无需翻墙
- `docker-compose.yml` 需要 v2 (不能用 v1.29.2，不兼容 Docker 29.x)
- 前端构建时需要 `VITE_AMAP_KEY` 和 `VITE_AMAP_SECURITY_CODE`，作为 Docker build args 传入
- `Training Program/` 目录以只读方式挂载到 backend 容器用于文档检索
- 不要提交 `.env` 文件
