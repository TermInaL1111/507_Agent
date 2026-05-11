# 507 Agent — 开发交接指引

> 最后更新: 2026-05-11 | 分支: `agent-centric`

---

## 1. 项目一句话概述

将 507 Agent 从传统菜单式 Web 应用改造为 **以 Agent 对话为核心的统一校园服务智能体平台**，所有功能（课表、导航、培养方案、文书生成）通过聊天框触发。

---

## 2. 技术栈与架构

```
frontend (Vue 3 + Element Plus)  :80
    ├── /api/* → backend:8000
    └── /user/* → django-user:8001

backend (FastAPI + LangChain + ChromaDB)  :8000
    ├── Agent: ChatTongyi (Qwen3-Max) + 12 工具
    ├── RAG: ChromaDB + Qwen3-Reranker
    └── SSE: response | tool_call | tool_result | sources | done | error

django-user (Django 5.2 + DRF + SimpleJWT)  :8001

mysql (8.4) :3306 | redis (7) :6379
```

- JWT: Django 签发, FastAPI 验证 — `.env` 中 `SECRET_KEY == DJANGO_SECRET_KEY`
- Agent 通过 `contextvars` 注入 user_id, 工具无需传 token
- Docker Compose 部署, 阿里云 ECS (4C4G, 成都), Docker 镜像源已配好

---

## 3. 当前工作状态

### 3.1 已完成 (Phase 1-4)

10 个 UC 全部实现 (meta_memory.md 有详细记录), 包括:
- UC-01~08: 注册/登录、RAG 知识问答、Agent 多轮对话、课表/培养方案/选课/导航/请假条
- 5 场景 E2E 验证全部通过 (100% 工具选择准确率)
- 前端已改造为 Agent 对话中心化 UI (侧边栏 10→7 菜单)

### 3.2 正在进行 (当前 Spec)

**通用文书生成框架** — 请假条改造为 Agent 对话驱动 + 可配置模板

详细设计 → `docs/superpowers/specs/2026-05-11-document-generation-framework-design.md`
实施计划 → `docs/superpowers/plans/2026-05-11-document-generation-framework.md`

**关键设计决策:**
- 文书类型 = 模板文件 + 规范文档 + 字段定义 (3 文件即配, 零代码)
- Agent 工具 `doc_preview`: 两阶段 (preview → 确认 → generate)
- 自动补全: Django 账号信息 + 课表课程信息 (课程请假自动匹配课程)
- 模板引擎: `{{placeholder}}` 占位符, 保留原格式
- 旧文件列表: leave_service.py / leave.py / schemas/leave.py / LeaveRequest.vue → 删除

### 3.3 待开发 (下阶段)
- Agent 体验优化 (工具调用可视化、打字动画改进等) — 第二个 spec
- 向量库检索修复
- 课程日程 UI 优化

---

## 4. 快速开始

```bash
# 1. 进入项目
cd /root/zhsx
git checkout agent-centric

# 2. 查看设计文档
cat docs/superpowers/specs/2026-05-11-document-generation-framework-design.md
cat docs/superpowers/plans/2026-05-11-document-generation-framework.md

# 3. 开发模式 (本地)
cd backend && uv sync && uv run uvicorn main:app --port 8000 --reload
cd DjangoUserService && uv sync && uv run python manage.py runserver 127.0.0.1:8001
cd front && npm install && npm run dev

# 4. 部署模式 (Docker)
docker compose up -d --build

# 5. 查看日志
docker logs 507-agent-backend --tail 50
docker compose ps
```

---

## 5. 关键文件索引

### 项目级
| 文件 | 用途 |
|------|------|
| `CLAUDE.md` | 项目架构速查 |
| `fw.md` | 项目范围文档 (8 模块完整定义) |
| `meta/meta_memory.md` | 开发日志 (Phase 1-4 记录, 错误修复记录) |
| `docker-compose.yml` | 5 服务编排 |
| `documents/leave/` | 请假条配置 (template.docx + spec.md + fields.json) |

### 后端关键文件
| 文件 | 用途 |
|------|------|
| `backend/main.py` | FastAPI 入口, 路由注册, startup 事件 |
| `backend/app/agent/agent.py` | AgentFactory + `get_agent_stream_response` (SSE 流式主逻辑) |
| `backend/app/agent/agent_tools.py` | 12+1 个 LangChain 工具 (含 doc_preview) |
| `backend/app/prompt/main_prompt.txt` | System Prompt |
| `backend/app/services/document_generator.py` | 通用模板填充引擎 (NEW) |
| `backend/app/router/chat.py` | 聊天 SSE / 文件上传 / RAG 端点 |
| `backend/app/router/documents.py` | 文书下载端点 (NEW) |
| `backend/app/rag/vector_store.py` | ChromaDB 向量存储 + DocumentSpecStore (NEW) |
| `backend/app/utils/django_user_client.py` | Django 用户信息查询 (NEW) |

### 前端关键文件
| 文件 | 用途 |
|------|------|
| `front/src/views/AIChat.vue` | 聊天 UI (1697 行) — SSE 处理, result_card 渲染, 工具调用可视化 |
| `front/src/App.vue` | 侧边栏 + 全局布局 |
| `front/src/router/index.js` | 路由配置 |
| `front/src/store/user.js` | JWT 认证 + 用户状态 (Pinia) |

---

## 6. 实施计划缩略 (11 Task)

```
Task 1  ✅ 创建 documents/leave/ 配置层 (template.docx + spec.md + fields.json)
Task 2  ⬜ 创建 DocumentGenerator 通用模板引擎 (TDD)
Task 3  ⬜ 创建文档下载 API + 旧路径兼容重定向
Task 4  ⬜ Django用户客户端 + ChromaDB文档类型索引 + 课表查询辅助函数
Task 5  ⬜ 替换 generate_leave_request 为通用 doc_preview 工具
Task 6  ⬜ 更新 Agent 工具注册 + System Prompt
Task 7  ⬜ 注册新路由 + 删除旧文件 (leave_service/leave router/schemas)
Task 8  ⬜ 前端: 新增 document_preview / document_result 卡片渲染
Task 9  ⬜ 前端: 删除 LeaveRequest.vue, 更新路由和侧边栏
Task 10 ⬜ Docker 重建 + 部署验证 + E2E 测试
Task 11 ⬜ git push
```

> **Task 1 已提交** (`documents/leave/` + docker-compose volume mount)。Task 2-9 在 plan 文件中有完整的代码、命令和预期输出。

---

## 7. 实施建议

1. **按顺序执行** — 每个 Task 依赖前一个 Task 的输出 (Task 2→4→5 链式依赖)
2. **TDD**: Task 2 先写测试再写代码, 运行 `uv run pytest backend/tests/test_document_generator.py -v`
3. **每个 Task 完成后立即 commit** (plan 中每个 Task 最后一步都是 commit 命令)
4. **Task 10 是验证关口** — rebuild Docker 镜像后做 E2E 测试
5. **Agent 体验优化是下一个 spec** — 不要在这个 spec 中混入其他改动

### 如果你用 Claude Code 执行:

```bash
# 推荐方式: subagent-driven (每个 Task 一个子代理)
# 在 Claude Code 对话中说:
"Use superpowers:subagent-driven-development to implement docs/superpowers/plans/2026-05-11-document-generation-framework.md"
```

### 如果人工执行:

打开 plan 文件, 从 Task 2 开始, 逐 step 执行, 每完成一个 Task 就 commit。

---

## 8. 常见问题

| 问题 | 解决 |
|------|------|
| 401 Unauthorized | `.env` 中 `SECRET_KEY == DJANGO_SECRET_KEY` |
| Docker 构建失败 | docker-compose v2 required; 阿里云镜像已配好 |
| 容器间通信失败 | `MYSQL_HOST: mysql`, `DJANGO_API_URL: http://django-user:8001` |
| ChromaDB 索引为空 | 检查 `DOCUMENTS_DIR` 环境变量 + 容器内 `/app/documents/` 挂载 |
| 前端 AMap 不显示 | docker build 需要 `--build-arg VITE_AMAP_KEY=xxx` |
| 导入错误 | `uv sync` 重新解析依赖; 确认在 `backend/` 目录下 |

---

## 9. Git 仓库

- Remote: `https://github.com/TermInaL1111/507_Agent.git`
- 分支: `agent-centric` (开发分支), `version1.0` (原始分支)
- 已配置 `.gitignore` (含 `.superpowers/`, `.env`, `chromadb/`)
- 每个阶段完成必须 git push

---

## 10. 下一步规划

1. **写完并验证当前 spec** (通用文书框架, 11 Tasks)
2. **Agent 体验 spec** — brainstorming + plan (工具调用可视化、打字动画、pre-check 重构等)
3. **向量库修复** — ChromaDB 检索返回空的问题
4. **扩展文书类型** — 奖学金申请、活动申报等 (只需在 `documents/` 下新建目录)
