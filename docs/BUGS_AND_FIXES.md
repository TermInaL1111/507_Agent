# 507 Agent 缺陷总结与修复记录

> 最后更新: 2026-05-13

## 架构缺陷

| # | 缺陷 | 根因 | 修复 |
|---|------|------|------|
| A1 | 课表查询不走 Agent | `schedule_ai_service.py` 正则 pre-check 拦截所有课表请求 | 删除 pre-check，请求直通 Agent |
| A2 | 校园导航 pre-check 同样用正则 | `campus_ai_service.py` 正则匹配 | 保留（校园导航响应对延迟敏感） |
| A3 | Agent 工具输出纯文本 | 工具返回字符串，前端只渲染 markdown | 工具返回 `<!--CARD:JSON-->` 标记，前端解析为 result_card |
| A4 | Agent Middleware 死代码 | `agent_middleware.py` 定义但未接入 AgentExecutor | 保留待后续启用 |

## 数据缺陷

| # | 缺陷 | 根因 | 修复 |
|---|------|------|------|
| D1 | PDF 课表重复导入 | `create_schedule_event` 无去重检查 | Agent tool + upload handler 加去重（同标题+同星期+同时间） |
| D2 | 用户文件污染共享知识库 | `kb_type="personal"` 只标记元数据，检索不过滤 | 分 `rag_collection`(共享) + `kb_personal`(个人) 两个集合 |
| D3 | MD5 去重对上传文件无效 | `check_md5_hex` 的 `and not file_id` 条件跳过去重 | 去掉 file_id 豁免 |
| D4 | ChromaDB 集合名变更丢数据 | `rag_collection` → `kb_shared` 改名但不迁移 | 保持 `rag_collection` 配置名 |

## 前端缺陷

| # | 缺陷 | 根因 | 修复 |
|---|------|------|------|
| F1 | 地图标注点点击无响应 | `map.add(markers)` 不可靠 | 改用 `marker.setMap(map)` + `clickable:true` |
| F2 | 未来城校区坐标错误 | 硬编码了错误的经纬度 (114.52 vs 114.614) | 搜索修正为正确坐标 |
| F3 | 后端 API 缺少 campus 字段 | `CampusLocation` dataclass 无 campus | 添加 campus 字段 + 7 个未来城地点 |
| F4 | 工具调用只显示 chip 名 | 前端只渲染 tool_call 名称 | 改为可展开卡片：Thought → Action → Observation |
| F5 | 新建会话需输入内容 | Sessions.vue 弹窗要求填写 query | 改为直接跳转 `/aichat`，不要求输入 |
| F6 | 侧边栏"文书辅助"重复 | 和 AI 对话都是跳到聊天页 | 删除重复菜单项 |
| F7 | 周课表无法切换周 | 后端 API 不支持 week_offset | 前端加 prev/next 按钮 + 后端加参数 |
| F8 | nginx upstream 容器名不匹配 | docker-compose service name vs container name | 修改 nginx.conf 使用实际容器名 |

## 模型切换

| # | 变更 | 原因 |
|---|------|------|
| M1 | Qwen3-Max → DeepSeek V3 | Qwen 额度不够 |
| M2 | DeepSeek V4 Flash → V3 | V4 thinking mode 与 LangChain 不兼容 |

## 新增 Agent 工具

| 工具 | 用途 | 灵感 |
|------|------|------|
| `doc_preview` | 通用文书生成（请假条等） | 设计 spec |
| `faq_recommend` | FAQ 推荐 | 需求文档 |
| `remember_user_context` | 存储用户偏好至 Redis | HelloAgents "Memory as Tool" |
| `recall_user_context` | 读取用户偏好 | HelloAgents "Memory as Tool" |
| `get_campus_service_link` | 查询校园业务入口链接 | 需求文档 |
| `extract_time_nodes` | 从对话提取时间节点 | 需求文档 |

## 待修复

| # | 缺陷 | 状态 |
|---|------|------|
| P0 | 课表表格/Gantt 时间显示不准 | 待测试验证 |
| P2 | 扫描版 PDF 无法提取文字 | 需 OCR 或要求文本 PDF |
