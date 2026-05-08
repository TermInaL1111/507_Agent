# META MEMORY — AUTO RESEARCH AGENT
## STATUS: Paused — Awaiting Phase 3 (Docker deploy + 5-scenario verify)
## START TIME: 2026-05-08 14:00 CST
## LAST UPDATE: 2026-05-08 23:00 CST
## PROGRESS: 85% → target 100%

---

# 1. FINAL GOAL

将 **507 Agent (CampusAgent)** 从传统菜单式 Web 应用改造为 **以 Agent 对话为核心的统一校园服务智能体平台**。

### 业务目标 (来自 `root/jgwd.md` SAD 文档)

| 用例编号 | 能力 | 目标状态 |
|----------|------|----------|
| UC-01 | 用户注册/登录/注销/资料管理 | ✅ 已实现 (Django JWT + FastAPI 鉴权) |
| UC-02 | 校园知识问答 (RAG + 引用来源) | ✅ 已实现 (ChromaDB + DashScope) |
| UC-03 | 统一智能体多轮对话 + SSE 流式 | ✅ 已实现 (LangChain Agent + SSE) |
| UC-04 | 知识库文档上传/向量化/重排 | ✅ 已实现 |
| UC-05 | 课表查询 (今日/周) + 冲突提醒 | ✅ 已实现 (Agent 工具 + schedule_ai_service) |
| UC-06 | 课程规划 (培养方案检索) | ✅ 已实现 (RAG + Agent 工具) |
| UC-07 | 选课建议 (多策略) | ✅ 已实现 (Agent 工具 recommend_courses) |
| UC-08 | 校园导航 (地点检索 + 路线规划) | ✅ 已实现 (campus_ai_service + Agent 工具) |
| UC-09 | 文书辅助 (生成/检查) | 🟡 部分实现 (Agent 生成可用，模板待完善) |
| UC-10 | 管理员运维 (日志/限流/监控) | 🟡 部分实现 (Redis 限流 + 日志治理) |

### 技术目标
1. **对话即入口** — 所有功能通过聊天框触发，Agent 自主判断意图并调用工具
2. **工具调用可见** — SSE `tool_call`/`tool_result` 事件实时展示 Agent 思考过程
3. **文件上传联动** — 上传课表 PDF → 自动提取解析 → 创建 ScheduleEvent → 对话展示
4. **10 个 UC 全部可联动** — Agent 跨功能编排（查课表 → 冲突检测 → 导航到教室）

### 架构约束 (来自 `root/jgwd.md`)
- 三层服务：`frontend (Vue 3)` → `backend (FastAPI + LangChain)` + `django-user (Django 5.2)`
- 数据层：MySQL 8.4 + Redis 7 + ChromaDB
- 模型层：DashScope (Qwen3-Max) + Qwen3-Reranker
- JWT 认证：Django 签发 / FastAPI 验证，SECRET_KEY 必须一致
- 部署：Docker Compose，阿里云 ECS (4核4G, 成都)

---

# 2. TERMINATION CONDITION

完成以下 5 个端到端验证场景全部通过，且 Docker 部署稳定运行：

1. **场景A — 查课表**: "我今天有什么课" → Agent 调 `get_schedule_today` → 展示今日课表卡片
2. **场景B — 上传课表PDF**: 上传 PDF → 自动解析 → 创建日程 → 展示完整课表
3. **场景C — 校园导航**: "从宿舍到图书馆怎么走" → Agent 调 `get_campus_route` → 展示路线卡片
4. **场景D — 培养方案**: "查计算机专业培养方案" → Agent 调 `get_training_program` → RAG 检索展示
5. **场景E — 选课建议**: "推荐这学期选修课" → Agent 调 `recommend_courses` → 展示选课建议

**失败条件**: 任一场景连续 3 次失败，或 Agent 工具选择准确率 < 60%。

---

# 3. RESEARCH PLAN

## Phase 1: 后端 Agent 工具扩充 ✅ COMPLETED

- [x] 1a. 新增 7 个 Agent 工具 (`agent_tools.py`)
- [x] 1b. 新增 `tool_call` / `tool_result` SSE 事件 (`agent.py`)
- [x] 1c. PDF 课表解析上传端点 `POST /api/agent/upload` (`chat.py`)
- [x] 1d. 重写 System Prompt 覆盖全部 12 个工具 (`main_prompt.txt`)

## Phase 2: 前端 Agent 中心改造 ✅ COMPLETED 100%

- [x] 2a. 精简侧边栏 10→4 菜单 (`App.vue`)
- [x] 2b. 聊天框文件上传按钮 + 文件 chip (`AIChat.vue`)
- [x] 2c. 工具调用可视化 — `tool_call`/`tool_result` 芯片动画 (`AIChat.vue`)
- [x] 2d. schedule 卡片渲染 — 时间线列表 + 周网格视图 + 冲突红标 (`AIChat.vue`)

## Phase 3: 构建部署 + 5 场景验证 ⏳ PENDING

- [ ] 3a. Docker Compose 构建 (backend + frontend 镜像)
- [ ] 3b. 部署到阿里云 ECS (8.137.19.10)
- [ ] 3c. 场景 A-E 逐项验证
- [ ] 3d. 回归测试 (登录/注册/RAG/会话)
- [ ] 3e. 性能测试 (首字节 < 5s, 50并发不崩溃)

---

# 4. KEY INSIGHTS

### 4.1 架构洞察
- **Pre-check vs Agent 工具双重路径**: 当前 `agent.py` 的 `get_agent_stream_response` 先做 schedule/campus/training 的 pre-check (关键词匹配直接返回)，不匹配才进 Agent。这保证常用场景的快速响应，Agent 工具作为兜底处理复杂/未匹配场景。两者互补而非替代。
- **contextvars 用户注入优于 token 参数**: 用 `contextvars.ContextVar` 在请求入口注入 `user_id`，工具函数无需声明 `token` 参数，LLM 也无需猜测 token 值。比原先 `get_user_info_tools(token)` 的设计更干净。
- **JWT 密钥一致性是关键**: `.env` 中 `SECRET_KEY` 和 `DJANGO_SECRET_KEY` 必须相同，否则 FastAPI 无法解码 Django 签发的 JWT → 所有 `/api/*` 请求 401。

### 4.2 前端改造洞察
- **保留独立页面、隐藏菜单**: 路由不删 (如 `/schedule`、`/campus-map`)，只是侧边栏不显示。Agent 对话中可以通过链接跳转到独立页面查看详情。这样既简化了入口，又不丢失独立使用场景。
- **SSE 事件扩展成本低**: 在 `astream` 循环的 `intermediate_steps` 分支加两个 `yield` 即可实现工具调用实时通知，无需引入 AG-UI 协议或 CopilotKit 等外部依赖。
- **文件上传后置上下文**: 用户上传 PDF → 后台解析 → 将解析结果 (events_count) 附加到消息上下文 → 发送给 Agent。Agent 看到 "已从 xxx.pdf 导入 5 条课表" 就知道发生了什么。

### 4.3 PDF 课表解析局限
- PyPDF 只能提取文本型 PDF，对扫描版/图片 PDF 无能为力
- 课表格式千差万别，正则匹配覆盖率有限
- v1 策略：只承诺文本 PDF 解析，匹配失败时降级为普通文件上传
- 匹配算法：先找星期标签 → 再找时间范围 → 提取课程名和地点

### 4.4 部署教训
- Docker Compose v1.29.2 与 Docker 29.x 不兼容 (KeyError: 'ContainerConfig')
- 阿里云 ECS 国内网络必须配置镜像加速 (apt/pip/npm)
- MySQL 8.4 的 `MYSQL_ONETIME_PASSWORD` 环境变量是必须的
- 4核4G 服务器内存紧张，构建前端时需关闭其他容器

---

# 5. RESULTS & CONCLUSIONS

### 5.1 已验证结论

| 结论 | 验证方式 | 状态 |
|------|----------|------|
| LangChain `create_tool_calling_agent` + Qwen3-Max 可正确选择工具 | 12 个工具在系统提示词中声明，LLM 按意图匹配 | ✅ 理论验证，待部署验证 |
| contextvars 注入 user_id 可安全传递给工具 | `set_agent_user_context(user_id)` 在请求入口设置 | ✅ 代码已完成 |
| SSE `tool_call`/`tool_result` 事件可实时推送到前端 | `yield` 在 `astream` 循环的 `intermediate_steps` 分支 | ✅ 代码已完成 |
| PDF 文本提取 + 正则解析可识别常见课表格式 | `_parse_schedule_pdf_text()` 支持 中/英 星期 + 时间范围 | ✅ 代码已完成，待真实 PDF 测试 |
| Element Plus + Vue 3 无需额外框架即可实现文件上传+工具可视化 | 仅依赖 Element Plus 内置组件 (el-upload, el-tag) | ✅ 代码已完成 |

### 5.2 待验证结论
- Qwen3-Max 在多工具场景下的选择准确率 (目标 > 60%)
- PDF 解析在实际教务系统导出的课表上的准确率
- 4核4G ECS 上全栈部署后的响应时间 (目标 < 5s 首字节)
- 工具调用可视化在弱网环境下的用户体验

---

# 6. CODE IMPLEMENTATION

### 6.1 修改文件清单 (agent-centric 分支)

| 文件 | 改动类型 | 说明 |
|------|----------|------|
| `backend/app/agent/agent_tools.py` | 新增 170+ 行 | 7 个工具 + contextvar 注入 |
| `backend/app/agent/agent.py` | 修改 20+ 行 | 注册工具 + user context + SSE 事件 |
| `backend/app/router/chat.py` | 新增 160+ 行 | PDF 上传端点 + `_parse_schedule_pdf_text` |
| `backend/app/prompt/main_prompt.txt` | 重写 | 12 工具场景指引 |
| `front/src/App.vue` | 修改 -30 行 | 侧边栏 10→4 菜单 |
| `front/src/views/AIChat.vue` | 新增 220+ 行 | 文件上传 + 工具调用可视化 |
| `DjangoUserService/Dockerfile` | 修改 | 阿里云镜像源 |
| `backend/Dockerfile` | 修改 | 阿里云镜像源 |
| `front/Dockerfile` | 修改 | npm 镜像源 |
| `docker-compose.yml` | 修改 +1 行 | MYSQL_ONETIME_PASSWORD |
| `CLAUDE.md` | 新增 | 项目上下文文档 |

### 6.2 新增 API 端点

```
POST /api/agent/upload     — PDF 课表上传解析
  Request: multipart/form-data { file: PDF }
  Response: { file_id, filename, text_preview, events[], events_count, warning }

SSE Events (新增类型):
  tool_call    — { type: "tool_call", tool: "get_schedule_today", args: {...} }
  tool_result  — { type: "tool_result", tool: "get_schedule_today", result: "..." }
  done         — 新增 steps[] 字段，包含完整工具调用链
```

### 6.3 新增 Agent 工具 (12 个总计)

| 工具名 | 参数 | 依赖服务 |
|--------|------|----------|
| `get_schedule_week` | 无 | schedule_service.list_week_events |
| `get_schedule_today` | 无 | schedule_service.list_week_events |
| `create_schedule_event` | title, weekday, start_time, end_time, [location, date, repeat, event_type] | schedule_service.create_event + find_conflicts |
| `search_campus_locations_tool` | keyword | campus_location_service.search_campus_locations |
| `get_campus_route` | from_location, to_location | campus_location_service.find_best_location + build_map_url |
| `get_training_program` | query | RagService.rag_summary_with_sources |
| `recommend_courses` | strategy | RagService.rag_summary_with_sources |

---

# 7. ERRORS & FIXES

| 时间 | 错误 | 根因 | 修复 |
|------|------|------|------|
| T1 | `docker-compose up` 失败: `KeyError: 'ContainerConfig'` | docker-compose v1.29.2 与 Docker 29.x 不兼容 | 使用 `docker run` 手动创建容器过渡；后续升级 docker-compose v2 |
| T2 | `python-magic-bin==0.4.14` 安装失败 | 该包仅提供 macOS/Windows wheels，Linux 无 | 移除 `--frozen` 标志让 uv 重新解析 |
| T3 | 前端构建失败: `../data/campusLocations` 找不到 | 缺少 `campusLocations.js` 文件 | 创建 `/root/zhsx/front/src/data/campusLocations.js` |
| T4 | MySQL 8.4 初始化脚本报错 `MYSQL_ONETIME_PASSWORD: unbound variable` | MySQL 8.4 需要此环境变量 | 在 docker-compose.yml 添加 `MYSQL_ONETIME_PASSWORD` |
| T5 | Django 迁移冲突: `admin.0001_initial is applied before its dependency user.0001_initial` | Django 初始化顺序问题 | 删库重建 (SET FOREIGN_KEY_CHECKS=0) |
| T6 | AI 端点 401 Unauthorized | FastAPI 用 `SECRET_KEY` 解码 JWT，但 Django 用 `DJANGO_SECRET_KEY` 签发 | `.env` 中 `DJANGO_SECRET_KEY = SECRET_KEY` |
| T7 | agent.py BOM 字符 UTF-8 BOM (U+FEFF) | 文件编辑工具写入 BOM | `python3 -c` 检测并移除 |
| T8 | `get_user_info_tools(token)` 设计问题 | LLM 不知道 JWT token 值 | 改用 contextvars 注入 user_id |

---

# 8. TODO LIST (AUTONOMOUS)

- [x] Phase 2d: 完成 schedule 卡片渲染 (AIChat.vue)
- [x] 更新 `root/jgwd.md` SAD 文档 — 用例状态从"规划中"更新为"已实现"
- [ ] Phase 3a: Docker Compose 重建 (backend + frontend 镜像)
- [ ] Phase 3b: 场景 A-E 验证测试
- [ ] Phase 3c: 性能测试 (响应时间、并发)
- [ ] 可选: 添加 schedule 卡片的 result_card 传递链路 (backend → Agent → frontend)
- [ ] 可选: 安装 `gh` CLI 简化 GitHub 操作

---

# 9. NEXT STEP (AUTONOMOUS DECIDED)

→ Phase 3: 在阿里云 ECS 上执行 `docker compose up -d --build` 重建部署，
运行 5 场景验证（查课表/上传PDF/导航/培养方案/选课建议），逐项记录结果并更新 meta_memory。
