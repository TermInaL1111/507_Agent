# 507 Agent — 最终 TODO

> 2026-05-13 收工

## 已完成 (本次 Sprint)

- [x] 模型切换: Qwen3-Max → DeepSeek V3
- [x] Agent 架构: 删除课表 regex pre-check，请求直通 Agent
- [x] ReAct 可视化: Thought → Action → Observation 可展开卡片
- [x] 用户上下文: System Prompt 注入姓名/学号/班级
- [x] Memory Tool: remember/recall user context via Redis
- [x] 全局 Agent FAB: 课表/导航/会话页悬浮按钮
- [x] AgentPanel: 课表/导航页嵌入侧边 Agent 聊天
- [x] 地图标注: 修复点击无响应，改用 setMap()
- [x] 双校区: 南望山 + 未来城，校园导航筛选 + 定位
- [x] 课表去重: upload + Agent tool 双重去重
- [x] 知识库隔离: kb_shared / kb_personal 分集合
- [x] 可信度提示: 回答末尾显示 📌/⚠️/💡 标签
- [x] 重名消歧: System Prompt 规则
- [x] FAQ 生成: 从学生手册 LLM 提取 10 个问题
- [x] 业务入口链接: get_campus_service_link 工具
- [x] 冲突检测: 结构化 check card 返回
- [x] 时间节点提取: extract_time_nodes 工具
- [x] 缺陷总结: docs/BUGS_AND_FIXES.md
- [x] Sprint 计划: docs/superpowers/plans/

## 待完成 (Day 3-4)

- [ ] 收藏功能 (bookmarks via Redis)
- [ ] 课表表格/Gantt 显示精度验证
- [ ] 扫描版 PDF OCR 支持
- [ ] API key 轮换 (已泄露到 git history!)
- [ ] README 更新
- [ ] 演示准备

## Agent 工具清单 (15 个)

1. rag_summary_tools — RAG 知识检索
2. reorder_documents_tools — 文档重排序
3. get_user_info_tools — 用户信息
4. get_weather_tools — 天气
5. what_time_is_now — 时间
6. get_schedule_week — 整周课表 → schedule card
7. get_schedule_today — 今日课表 → schedule card
8. create_schedule_event — 添加日程 + 冲突检测
9. search_campus_locations_tool — 搜地点
10. get_campus_route — 路线规划
11. get_training_program — 培养方案
12. recommend_courses — 选课建议
13. doc_preview — 通用文书生成
14. faq_recommend — FAQ 推荐
15. get_campus_service_link — 业务入口链接
16. extract_time_nodes — 时间节点提取
17. remember_user_context — 记忆存储
18. recall_user_context — 记忆读取

## 当前运行状态

```
507-agent-frontend   Up
507-agent-backend    Up
507-agent-django-user Up
507-agent-redis      Up
507-agent-mysql      Up
```

模型: DeepSeek V3 (deepseek-chat) via ChatOpenAI
向量库: ChromaDB rag_collection (学生手册 315 chunks) + kb_personal
前端: Nginx :80 → backend :8000 / django :8001
